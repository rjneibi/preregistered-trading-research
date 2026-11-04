"""L2 items: CYCLES-1-10 statistics and DOOR-3 from trade lists on both clocks, FX-TRANSFER-1 from stored trades. The cycle scripts were one-off shell work, so these are recomputations."""
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
GB = os.path.join(HERE, "..", "_copy", "goldbot")
sys.path[:0] = [HERE, GB, os.path.join(GB, "prereg")]
import run_verdict as rv
from cost_matrix import CostMatrix
from goldbot.config import load_config
from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr
from goldbot.events import generate_events_final
from goldbot.triple_barrier import run_exits

rep = {}


def supf(y, trim=0.15):
    """Quandt-Andrews sup-F for one break in the mean."""
    y = np.asarray(y, float)
    n = len(y)
    sse0 = ((y - y.mean()) ** 2).sum()
    best, at = 0.0, None
    for k in range(int(n * trim), int(n * (1 - trim))):
        a, b = y[:k], y[k:]
        sse = ((a - a.mean()) ** 2).sum() + ((b - b.mean()) ** 2).sum()
        f = (sse0 - sse) / (sse / (n - 2))
        if f > best:
            best, at = f, k
    return round(float(best), 2), at


def psr(x, sr0=0.0):
    x = np.asarray(x, float)
    sr = x.mean() / x.std(ddof=1)
    return round(float(st.norm.cdf((sr - sr0) * math.sqrt(len(x) - 1) / math.sqrt(1 - st.skew(x) * sr + (st.kurtosis(x, fisher=False) - 1) / 4 * sr * sr))), 3)


def cycles(path, label):
    t = pd.read_csv(path, parse_dates=["entry_ts"])
    t = t.sort_values("entry_ts").reset_index(drop=True)
    t["a"] = t.net_p90 / (t.atr * 100)
    t["g"] = t.gross_usd / (t.atr * 100)
    t["c"] = t.cost_p90 / (t.atr * 100)
    out = {}
    for nm, col in (("net_per_atr", "a"), ("gross_per_atr", "g"), ("cost_per_atr", "c")):
        f, k = supf(t[col].values)
        out[f"supF_{nm}"] = dict(F=f, date=str(t.entry_ts[k])[:10])
    mo = t.set_index("entry_ts").a.resample("ME").sum()
    mo = mo[mo.index >= t.entry_ts.min()]
    out["psr_monthly_full"] = psr(mo.values)
    for nm, a in (("modern_2021_06", "2021-06-19"), ("recent_2023_01", "2023-01-01")):
        w = t[t.entry_ts >= pd.Timestamp(a, tz="UTC")]
        h = w[w.entry_ts.dt.hour == 20]
        r = w[w.entry_ts.dt.hour != 20]
        tt = st.ttest_1samp(h.a, 0)
        p = float(tt.pvalue)
        out[nm] = dict(n=len(w), total_p90=round(float(w.net_p90.sum())), hour20_n=len(h), hour20_p90=round(float(h.net_p90.sum())), rest_p90=round(float(r.net_p90.sum())), hour20_mean_atr=round(float(h.a.mean()), 4), t=round(float(tt.statistic), 2), p=round(p, 3), sidak_k3=round(1 - (1 - p) ** 3, 3), total_med=round(float(w.net_med.sum())), hour20_med=round(float(h.net_med.sum())))
    rep[f"cycles {label}"] = out
    print(label, json.dumps(out)[:900], flush=True)


cycles(os.path.join(HERE, "h1_recorded_clock_trades.csv"), "recorded")
cycles(os.path.join(HERE, "h1_true_utc_trades.csv"), "true_utc")

# DOOR-3 ---------------------------------------------------------------------
cfg = load_config(os.path.join(GB, "config.yaml"))
M = os.path.join(GB, "results", "cost_matrix.json")
cm_med = CostMatrix.load(M, stat="median", k_slip=0.5, commission_per_lot_rt=7.0)
cm_p90 = CostMatrix.load(M, stat="p90", k_slip=0.5, commission_per_lot_rt=7.0)
e = cfg.exits.final
for clock, p in (("recorded", "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"), ("true_utc", os.path.join(HERE, "..", "_copy", "data", "xauusd_m1_trueutc.csv"))):
    full = load_ohlc(p, data_tz="UTC")
    end_ = full.index[-1]
    all_, base = [], []
    for era, (start, end) in rv.ERAS.items():
        end = end or end_
        m1 = full[(full.index >= start - rv.WARMUP) & (full.index <= end)]
        h1, h4, d1 = resample_ohlc(m1, "1h"), resample_ohlc(m1, "4h"), resample_d1_utc(m1)
        ev = generate_events_final(h1, h4, d1, wilder_atr(h1, e.atr.period), cfg, start, end)
        all_.append(run_exits(m1, ev, k_tp_atr=e.k_tp_atr, sl_usd=20.0, time_stop_h=e.time_stop_h, fill_mode="gap_open", bail_enabled=e.bail.enabled, hivol_half_x=e.bail.hivol_half_x, lovol_bail_h=e.bail.lovol_bail_h, lovol_bail_x=e.bail.lovol_bail_x))
        base.append(run_exits(m1, ev, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr, time_stop_h=e.time_stop_h, fill_mode="gap_open", bail_enabled=e.bail.enabled, hivol_half_x=e.bail.hivol_half_x, lovol_bail_h=e.bail.lovol_bail_h, lovol_bail_x=e.bail.lovol_bail_x))
    d, b = pd.concat(all_), pd.concat(base)
    for x in (d, b):
        x["cost"] = [cm_p90.trade_cost_usd(u, v) for u, v in zip(x.entry_ts, x.exit_ts)]
    wins = b[b.resolution == "TP"]
    rep[f"door3 {clock}"] = dict(n=len(d), fixed20_pf=round(rv.pf(d.gross_usd - d.cost), 3), fixed20_net=round(float((d.gross_usd - d.cost).sum())), baseline_pf=round(rv.pf(b.gross_usd - b.cost), 3), baseline_net=round(float((b.gross_usd - b.cost).sum())), winners=len(wins), winners_reaching_20=int((wins.mae_usd.abs() >= 2000).sum()), max_winner_mae_usd_per_oz=round(float(wins.mae_usd.abs().max() / 100), 2), resolution=d.resolution.value_counts().to_dict())
    print(clock, rep[f"door3 {clock}"], flush=True)
stored = pd.read_csv("@GANN_ROOT@/research/goldbot/results/door3_fixed20_trades.csv")
rep["door3 stored"] = dict(n=len(stored), net_with_swap=round(float(stored.net_usd.sum()), 2), pf=round(rv.pf(stored.net_usd), 3), gross=round(float(stored.gross_usd.sum()), 2))
print(rep["door3 stored"], flush=True)

# FX --------------------------------------------------------------------------
fx = {}
for f in sorted(glob.glob("@GANN_ROOT@/research/fx_backtest/results/trades_*.csv")):
    t = pd.read_csv(f)
    c = [x for x in t.columns if x.lower() in ("pnl_r", "r", "pnl", "pnl_usd", "net", "net_r")]
    if not c:
        fx[os.path.basename(f)] = list(t.columns)[:12]
        continue
    r = t[c[0]].values.astype(float)
    fx[os.path.basename(f)] = dict(col=c[0], n=len(r), pf=round(float(r[r > 0].sum() / -r[r < 0].sum()), 3) if (r < 0).any() else None)
rep["fx"] = fx
print(fx, flush=True)
json.dump(rep, open(os.path.join(HERE, "l2_recompute.json"), "w"), indent=1, default=str)
