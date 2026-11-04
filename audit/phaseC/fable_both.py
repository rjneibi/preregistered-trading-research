"""Regenerates the flip events, then FINAL_v3 and FINAL_v4 trades. Usage: fable_both.py <recorded|true>.
Loop bodies follow analysis_scripts/final_v3.py and h1_2026_test.py. Nothing is tuned."""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

clock = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "_copy", f"sb_fable_{clock}"))
sys.path[:0] = [ROOT, ROOT + "/research/flip_scalp"]
os.chdir(ROOT + "/research/flip_scalp")
import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1, resample_ohlc, resample_d1_utc, wilder_atr
from innovate_r3s3 import SimX, r3s3_level

ERAS = (("old", "2015-06-19T00:00:00Z", "2021-06-18T23:59:00Z", "events_2015_2021.jsonl"), ("new", "2021-06-19T00:00:00Z", "2026-06-19T17:57:00Z", "events.jsonl"))


def st(p):
    p = np.array(p, float)
    w, l = p[p > 0].sum(), -p[p < 0].sum()
    return dict(n=len(p), wr=round(float((p > 0).mean()), 3), pf=round(float(w / l), 3) if l else None, net=round(float(p.sum())), losses=int((p < 0).sum()))


rep = dict(v3={}, v4={}, ev={})
V3, V4 = [], []
for era, a, b, fname in ERAS:
    start, end = pd.Timestamp(a), pd.Timestamp(b)
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    t0 = time.time()
    m1 = load_m1(start - pd.Timedelta(days=60), end)
    h1, h4, d1 = resample_ohlc(m1, "1h"), resample_ohlc(m1, "4h"), resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    ev = rfs.collect_flip_events(m1, h1, h4, d1, atr_h1)
    if clock == "recorded":
        old = [json.loads(x) for x in open(f"@GANN_ROOT@/research/flip_scalp/{fname}").read().splitlines()]
        key = lambda e: (str(e["entry_ts"]), e["direction"])
        rep["ev"][era] = dict(regen=len(ev), stored=len(old), same_keys=len({key(e) for e in ev} & {key(e) for e in old}))
        print(era, rep["ev"][era], flush=True)
    sim = SimX(m1, h4)
    from regime_switch import load_events
    with open(fname, "w") as f:
        for e in ev:
            f.write(json.dumps({k: (v if not isinstance(v, pd.Timestamp) else v.isoformat()) for k, v in e.items()}, default=str) + "\n")
    es = [e for e in load_events(fname) if pd.Timestamp(e["entry_ts"]).hour in (12, 16, 20)]
    seen, res = set(), []
    for e in es:
        day = pd.Timestamp(e["entry_ts"]).date()
        if day in seen:
            continue
        seen.add(day)
        p = sim.run(e, tp=1.4 * e["atr_at_build"], sl=2.1 * e["atr_at_build"], level=r3s3_level(e))
        res.append(p)
        V3.append((str(e["entry_ts"]), e["direction"], era, p, 1.4 * e["atr_at_build"], 2.1 * e["atr_at_build"]))
    rep["v3"][era] = st([x for x in res if x is not None])
    res = []
    for day_open in d1.index[(d1.index >= start) & (d1.index <= end)]:
        if day_open.strftime("%a") == "Mon":
            continue
        built = rfs.build_day_zones(day_open, d1, h4, atr_h1, h1.index)
        if built is None:
            continue
        zones, atr = built
        live = [z for z in zones if z["source"] in ("R3", "S3") and not z["baseline_flipped"]]
        if not live:
            continue
        day_h1 = h1[(h1.index >= day_open) & (h1.index < day_open + pd.Timedelta(days=1))]
        for open_ts, row in day_h1.iterrows():
            cur = open_ts + pd.Timedelta(hours=1)
            if not (12 <= cur.hour <= 20) or cur > end:
                continue
            close = float(row["close"])
            hit = None
            for z in live:
                if z["side_orig"] == "support" and close < z["level"]:
                    hit = ("SELL", z)
                elif z["side_orig"] == "resistance" and close > z["level"]:
                    hit = ("BUY", z)
                if hit:
                    break
            if hit:
                e = {"entry_ts": cur.isoformat(), "atr_at_build": atr, "direction": hit[0]}
                p = sim.run(e, tp=0.8 * atr, sl=2.4 * atr, level=hit[1]["level"])
                if p is not None:
                    res.append(p)
                    V4.append((cur.isoformat(), hit[0], era, p, 0.8 * atr, 2.4 * atr))
                break
    rep["v4"][era] = st(res)
    print(clock, era, "v3", rep["v3"][era], "v4", rep["v4"][era], round(time.time() - t0), "s", flush=True)
for nm, T in (("v3", V3), ("v4", V4)):
    df = pd.DataFrame(T, columns=["ts", "dir", "era", "pnl", "tp", "sl"]).dropna()
    df = df.sort_values("ts")
    df.to_csv(os.path.join(HERE, f"fable_{nm}_{clock}.csv"), index=False)
    rep[nm]["pooled"] = st(df.pnl)
    y = df[df.ts.str.startswith("2025")]
    rep[nm]["y2025"] = st(y.pnl) if len(y) else None
    c = df.pnl.cumsum()
    rep[nm]["maxdd"] = round(float((c.cummax() - c).max()))
json.dump(rep, open(os.path.join(HERE, f"fable_{clock}.json"), "w"), indent=1, default=str)
print(json.dumps(rep))
