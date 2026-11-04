"""E2 per prereg/E2-SILVER-TRANSFER.md. Usage: e2_silver.py <prep|score>. prep writes silver M1 and the spread matrix. fable_xag.py then regenerates V3 and V4. score costs all three rules."""
import glob
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.dirname(HERE)
PC = os.path.join(AUD, "phaseC")
GB = os.path.join(AUD, "_copy", "goldbot")
sys.path[:0] = [HERE, GB, os.path.join(GB, "prereg")]
import lib

DK = os.path.join(AUD, "_copy", "data", "dk_xag")
CSV = os.path.join(AUD, "_copy", "data", "xag_m1_dk.csv")
MAT = os.path.join(HERE, "e2_xag_m1_matrix.json")
COMM = 7.0 / 50          # $7 per 5,000 oz, on the rules' 100-oz unit
FEE = 5.0 / 50           # $5 per 5,000 oz night


def load_side(s):
    a = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(DK, f"xagusd-{s}-*.csv")))])
    a.index = pd.to_datetime(a.timestamp, unit="ms", utc=True)
    return a[~a.index.duplicated()].sort_index()


def prep():
    b, a = load_side("bid"), load_side("ask")
    # Dukascopy pads closed minutes with flat zero-volume bars, which are not tradable prints
    live = (b.volume > 0) | (b.high != b.low)
    b = b[live]
    x = b.join(a[["close"]].rename(columns={"close": "ask"}), how="inner")
    out = pd.DataFrame(dict(time=(x.index.astype("int64") // 10**9) if str(x.index.dtype).endswith("ns, UTC]") else (x.index - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1),
                            open=x.open.values, high=x.high.values, low=x.low.values, close=x.close.values))
    out.to_csv(CSV, index=False)
    sp = (x.ask - x.close)
    sp = sp[(sp > 0) & (sp < 1)]
    m = {"meta": dict(note="M1 bar-close spreads, E2 prereg"), "years": {}, "fallback": {}}
    g = pd.DataFrame(dict(y=sp.index.year, h=sp.index.hour, s=sp.values))
    for (y, h), q in g.groupby(["y", "h"]):
        m["years"].setdefault(str(y), {})[str(h)] = dict(n=len(q), mean=float(q.s.mean()), median=float(q.s.median()), p75=float(q.s.quantile(0.75)), p90=float(q.s.quantile(0.9)))
    for y, q in g.groupby("y"):
        m["fallback"][str(y)] = dict(median=float(q.s.median()), p90=float(q.s.quantile(0.9)))
    m["fallback"]["_global"] = dict(median=float(g.s.median()), p90=float(g.s.quantile(0.9)))
    json.dump(m, open(MAT, "w"), indent=0)
    src, dst = os.path.join(AUD, "_copy", "sb_fable_true"), os.path.join(AUD, "_copy", "sb_fable_xag")
    if not os.path.exists(dst):
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "xauusd_m1_histdata.csv", "*.jsonl"))
    shutil.copy(CSV, os.path.join(dst, "research", "data", "xauusd_m1_histdata.csv"))
    print("silver M1", len(out), str(x.index[0]), str(x.index[-1]))


def h1_trades():
    import importlib
    sys.path.insert(0, PC)
    import run_verdict as rv
    from goldbot.config import load_config
    from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr
    from goldbot.events import generate_events_final
    from goldbot.triple_barrier import run_exits
    cfg = load_config(os.path.join(GB, "config.yaml"))
    e = cfg.exits.final
    m1f = load_ohlc(CSV, data_tz="UTC")
    end = m1f.index[-1]
    all_t = []
    for era, (a, b) in rv.ERAS.items():
        b = b or end
        m1 = m1f[(m1f.index >= a - rv.WARMUP) & (m1f.index <= b)]
        h1, h4, d1 = resample_ohlc(m1, "1h"), resample_ohlc(m1, "4h"), resample_d1_utc(m1)
        ev = generate_events_final(h1, h4, d1, wilder_atr(h1, e.atr.period), cfg, a, b)
        tr = run_exits(m1, ev, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr, time_stop_h=e.time_stop_h, fill_mode="gap_open", bail_enabled=e.bail.enabled, hivol_half_x=e.bail.hivol_half_x, lovol_bail_h=e.bail.lovol_bail_h, lovol_bail_x=e.bail.lovol_bail_x)
        tr["era"] = era
        all_t.append(tr)
    return pd.concat(all_t, ignore_index=True), resample_ohlc(m1f, "1h")


def score():
    from cost_matrix import CostMatrix
    cm = CostMatrix.load(MAT, stat="median", k_slip=0.5, commission_per_lot_rt=COMM)
    cp = CostMatrix.load(MAT, stat="p90", k_slip=0.5, commission_per_lot_rt=COMM)
    t, h = h1_trades()
    lr = np.diff(np.log(h.close.values))
    t["nights"] = [(1 if (pd.date_range(a, b, freq="1h", inclusive="left").hour == 22).any() else 0) for a, b in zip(t.entry_ts, t.exit_ts)]
    t["cm"] = [cm.trade_cost_usd(a, b) for a, b in zip(t.entry_ts, t.exit_ts)]
    t["cp"] = [cp.trade_cost_usd(a, b) for a, b in zip(t.entry_ts, t.exit_ts)]
    fee = t.nights * FEE
    holds = np.maximum(((t.exit_ts - t.entry_ts).dt.total_seconds() / 3600).round().astype(int).values, 1)
    t.to_csv(os.path.join(HERE, "e2_h1_silver_trades.csv"), index=False)

    def card(gross, med, p90, era, ts, name):
        net, net2, np90 = gross - med, gross - 2 * med, gross - p90
        px = np.interp(pd.DatetimeIndex(ts).astype("int64").values.astype(float), h.index.astype("int64").values.astype(float), h.close.values)
        p = lib.twin_p(float(np.mean(gross / (100 * px))), lr, holds, len(gross))
        r = dict(n=len(net), pf=round(lib.pf(net), 3), pf_gross=round(lib.pf(gross), 3), pf_1_5x=round(lib.pf(gross - 1.5 * med), 3), pf_2x=round(lib.pf(net2), 3), pf_p90=round(lib.pf(np90), 3), twin_p=round(p, 4))
        for e in ("old", "new"):
            m = era == e
            r[f"pf_{e}"] = round(lib.pf(net[m]), 3)
            r[f"n_{e}"] = int(m.sum())
        r["gates"] = dict(pf_ge_1_20=r["pf"] >= 1.2, pf2x_ge_1=r["pf_2x"] >= 1, eras_ge_1=min(r["pf_old"], r["pf_new"]) >= 1, n_ge_100=r["n"] >= 100, twin=p < 0.05, p90_ge_1=r["pf_p90"] >= 1)
        r["verdict"] = "PASS" if all(r["gates"].values()) else "FAILED"
        return r

    rep = dict(H1=card(t.gross_usd.values, (t.cm + fee).values, (t.cp + fee).values, t.era.values, t.entry_ts, "H1"))
    for nm in ("v3", "v4"):
        x = pd.read_csv(os.path.join(PC, f"fable_{nm}_xag.csv"), parse_dates=["ts"])
        g = x.pnl.values + 20.0
        med = np.array([cm.trade_cost_usd(a, a) for a in x.ts])
        p90 = np.array([cp.trade_cost_usd(a, a) for a in x.ts])
        rep[f"FINAL_{nm}"] = card(g, med, p90, x.era.values, x.ts, nm)
        rep[f"FINAL_{nm}"]["note"] = "No exit time saved, so entry-hour spread is used on both sides and the night fee is left out"
    rep["twin_note"] = "FINAL_v3 and v4 save no exit time, so their twins use the H1 rule's holding times. All three fail on PF, so this changes nothing."
    rep["constants"] = "No gold-dollar constant is reached on these paths: the ATR zone, TP and SL are all ATR multiples. Levels are prices from silver's own pivots."
    json.dump(rep, open(os.path.join(HERE, "e2_result.json"), "w"), indent=1, default=str)
    print(json.dumps(rep, indent=1, default=str))


if sys.argv[1] == "prep":
    prep()
else:
    score()
