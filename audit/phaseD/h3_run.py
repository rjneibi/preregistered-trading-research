"""H3-SILVER as frozen on 2026-07-06, see prereg/H3-SILVER.md for the open calls. Usage: h3_run.py <build|run>.
build makes silver M1 and the silver cost matrix from the ticks on disk, read only. run applies the gates in order."""
import glob
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.join(HERE, "..", "phaseC")
GB = os.path.join(HERE, "..", "_copy", "goldbot")
sys.path[:0] = [PC, GB, os.path.join(GB, "prereg")]
from clockfix import shifted
from cost_matrix import CostMatrix, build_matrix, save_matrix
from goldbot.config import load_config
from goldbot.data import load_ohlc, resample_ohlc
from goldbot.ou_estimator import fit_ou

TICKS = sorted(glob.glob("@GANN_ROOT@/fable-backtesting/download/xagusd-bi5-*.csv"))
HIST = "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"
OUT = os.path.join(HERE, "..", "_copy", "data", "xag_m1_ticks.parquet.npz")
MAT = os.path.join(HERE, "xag_cost_matrix.json")
ENTRY, STOP, TIME_H = 2.0, 4.0, 240
FEE = 5.0


def build():
    frames = []
    for f in TICKS:
        d = pd.read_csv(f, usecols=["timestamp", "bidPrice"])
        d["m"] = d.timestamp // 60000
        g = d.groupby("m").bidPrice
        frames.append(pd.DataFrame({"o": g.first(), "h": g.max(), "l": g.min(), "c": g.last()}))
        print(os.path.basename(f), len(frames[-1]), flush=True)
    a = pd.concat(frames)
    a = a[~a.index.duplicated()].sort_index()
    np.savez(OUT, t=a.index.values, o=a.o.values, h=a.h.values, l=a.l.values, c=a.c.values)
    m = build_matrix(TICKS, time_col="timestamp", bid_col="bidPrice", ask_col="askPrice", time_unit="ms")
    save_matrix(m, MAT)
    print("built", len(a), a.index[0], a.index[-1])


def true_utc(m1):
    secs = m1.index.tz_localize(None).values.astype("datetime64[s]").astype(np.int64)
    out = m1.copy()
    out.index = m1.index - pd.to_timedelta(shifted(secs).astype(int), unit="h")
    return out[~out.index.duplicated()].sort_index()


def silver_h1():
    z = np.load(OUT)
    idx = pd.to_datetime(z["t"] * 60, unit="s", utc=True)
    m1 = pd.DataFrame({k: z[k] for k in "ohlc"}, index=idx)
    m1.columns = ["open", "high", "low", "close"]
    return resample_ohlc(m1, "1h")


def month_betas(lx, lg):
    """Trailing 90-day OLS beta at each month start, causal."""
    months = sorted(set(lx.index.to_period("M").astype(str)))
    b = {}
    for mo in months:
        t0 = pd.Timestamp(mo + "-01", tz="UTC")
        w = (lx.index < t0) & (lx.index >= t0 - pd.Timedelta(days=90))
        if w.sum() < 500:
            continue
        x, y = lg[w].values, lx[w].values
        b[mo] = float(np.cov(x, y, bias=True)[0, 1] / np.var(x))
    return b


def trade(df, betas, cm_g, cm_s, is_end, mult=1.0):
    """Signals on the close, fills on the next open."""
    lx, lg = np.log(df.xc.values), np.log(df.gc.values)
    idx = df.index
    mo = idx.to_period("M").astype(str)
    tr = []
    pos = None
    first = 2200
    for i in range(first, len(df) - 1):
        m = mo[i]
        if m not in betas:
            continue
        b = betas[m]
        t = idx[i]
        w = (idx[max(0, i - 2000):i + 1] >= t - pd.Timedelta(days=90)).sum()
        s = lx[i + 1 - w:i + 1] - b * lg[i + 1 - w:i + 1]
        f = fit_ou(s, dt=1.0, min_obs=500)
        z = None
        if f.valid:
            z = (s[-1] - f.mu) / (f.sigma / np.sqrt(2 * f.theta))
        if pos is None:
            if z is not None and abs(z) >= ENTRY:
                pos = dict(i=i + 1, side=-np.sign(z), beta=b, t=idx[i + 1], xo=df.xo.values[i + 1], go=df.go.values[i + 1])
        else:
            hrs = (t - pos["t"]).total_seconds() / 3600
            cross = z is not None and z * pos["side"] >= 0
            stop = z is not None and abs(z) >= STOP
            if cross or stop or hrs >= TIME_H:
                x1, g1 = df.xo.values[i + 1], df.go.values[i + 1]
                ta, tb = pos["t"], idx[i + 1]
                gold_gross = pos["side"] * (x1 - pos["xo"]) * 100
                notional = 100 * pos["xo"]
                silver_oz = pos["beta"] * notional / pos["go"]
                silver_gross = -pos["side"] * (g1 - pos["go"]) * silver_oz
                sl = silver_oz / 5000
                nights = int(((pd.date_range(ta, tb, freq="1h", inclusive="left").hour == 22)).sum())
                cost = mult * (cm_g.trade_cost_usd(ta, tb) + cm_s.trade_cost_usd(ta, tb, lots=sl)) + nights * FEE * (1 + sl)
                tr.append(dict(entry=str(ta), exit=str(tb), side=int(pos["side"]), beta=round(pos["beta"], 4), gross=gold_gross + silver_gross, cost=cost, net=gold_gross + silver_gross - cost,
                               nights=nights, why="cross" if cross else ("stop" if stop else "time"), slice="IS" if tb <= is_end else "OOS"))
                pos = None
    return pd.DataFrame(tr)


def pf(x):
    w, l = x[x > 0].sum(), -x[x < 0].sum()
    return round(float(w / l), 3) if l else None


def run_clock(name, gold_m1, sil, cfg, cost_g):
    gh = resample_ohlc(gold_m1, "1h")
    df = pd.DataFrame({"xo": gh.open, "xc": gh.close}).join(pd.DataFrame({"go": sil.open, "gc": sil.close}), how="inner").dropna()
    lx, lg = np.log(df.xc), np.log(df.gc)
    betas = month_betas(lx, lg)
    keep = df.index.to_period("M").astype(str).isin(list(betas))
    df = df[keep]
    lx, lg = lx[keep], lg[keep]
    b = df.index.to_period("M").astype(str).map(betas).values.astype(float)
    spread = (lx.values - b * lg.values)
    cut = int(len(df) * 0.7)
    is_end = df.index[cut - 1]
    fit = fit_ou(spread[:cut], dt=1.0, min_obs=cfg.spread_research.min_obs)
    rep = dict(clock=name, bars=len(df), first=str(df.index[0]), last=str(df.index[-1]), is_end=str(is_end), beta_min=round(float(b.min()), 3), beta_max=round(float(b.max()), 3))
    rep["gate1_fit"] = dict(valid=fit.valid, reason=fit.reason, phi1=fit.phi1, half_life_h=fit.half_life, n=fit.n)
    hl_ok = bool(fit.valid and 4 <= fit.half_life <= 240)
    rep["gate1_pass"] = hl_ok
    # stationarity diagnostic on the same IS spread, beside the frozen gate and deciding nothing
    fits = []
    for mo in sorted(betas):
        m = df.index.to_period("M").astype(str) == mo
        if m.sum() > 300:
            f = fit_ou(lx[m].values - betas[mo] * lg[m].values, dt=1.0, min_obs=100)
            fits.append(dict(month=mo, valid=f.valid, hl=f.half_life))
    rep["monthly_fit_valid_share"] = round(float(np.mean([f["valid"] for f in fits])), 3)
    rep["monthly_valid_hl_median_h"] = float(np.median([f["hl"] for f in fits if f["valid"]])) if any(f["valid"] for f in fits) else None
    if not hl_ok:
        rep["verdict"] = "FAILED at validity gate 1. No trading conclusion"
        return rep, None
    cm_s_med = CostMatrix.load(MAT, stat="median", k_slip=0.5, commission_per_lot_rt=7.0, contract_oz=5000)
    t = trade(df, betas, cost_g, cm_s_med, is_end)
    oos, is_ = t[t.slice == "OOS"], t[t.slice == "IS"]
    eq = fit.sigma / np.sqrt(2 * fit.theta)
    px = float(df.xc.iloc[cut - 1])
    capture = 0.5 * eq * px
    allin = float(((t.cost / 100).mean())) if len(t) else None
    rep["trading"] = dict(n=len(t), is_n=len(is_), is_pf=pf(is_.net), oos_n=len(oos), oos_pf=pf(oos.net), oos_net=round(float(oos.net.sum())), why=t.why.value_counts().to_dict(), avg_nights=round(float(t.nights.mean()), 2))
    rep["carry"] = dict(capture_usd_oz=round(capture, 2), cost_usd_oz=round(allin, 2), pass_=bool(capture >= 2 * allin))
    g2 = rep["trading"]["oos_pf"] is not None and rep["trading"]["oos_pf"] >= 1.2
    g3 = len(oos) >= 30 and (pf(is_.net) or 0) >= 1 and (pf(oos.net) or 0) >= 1
    rep["gates"] = dict(g2_oos_pf=bool(g2), g3_n_and_not_inverted=bool(g3), g4_carry=rep["carry"]["pass_"])
    rep["verdict"] = "PASS" if g2 and g3 and rep["carry"]["pass_"] else "FAILED at cost or OOS gates"
    return rep, t


def main():
    if sys.argv[1] == "build":
        build()
        return
    cfg = load_config(os.path.join(GB, "config.yaml"))
    M = os.path.join(GB, "results", "cost_matrix.json")
    cg = CostMatrix.load(M, stat="median", k_slip=0.5, commission_per_lot_rt=7.0)
    sil = silver_h1()
    m1 = load_ohlc(HIST, data_tz="UTC")
    rep = {}
    for name, g in (("true_utc", true_utc(m1)), ("recorded", m1)):
        r, t = run_clock(name, g, sil, cfg, cg)
        rep[name] = r
        if t is not None:
            t.to_csv(os.path.join(HERE, f"h3_trades_{name}.csv"), index=False)
        print(json.dumps(r, indent=1, default=str), flush=True)
    json.dump(rep, open(os.path.join(HERE, "h3_result.json"), "w"), indent=1, default=str)


main()
