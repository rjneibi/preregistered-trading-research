"""XAU-R3S3-FADE rebuilt from its description: fade the flip at R3/S3, same filters and exits as FINAL_v3 and FINAL_v4, direction reversed. No fade harness survives, so this is an L2 rebuild."""
import json
import os
import sys

import numpy as np
import pandas as pd

clock = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "_copy", f"sb_fable_{clock}"))
sys.path[:0] = [ROOT, ROOT + "/research/flip_scalp"]
os.chdir(ROOT + "/research/flip_scalp")
import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1, resample_ohlc
from innovate_r3s3 import SimX


def st(p):
    p = np.array([x for x in p if x is not None], float)
    w, l = p[p > 0].sum(), -p[p < 0].sum()
    return dict(n=len(p), wr=round(float((p > 0).mean()), 3), pf=round(float(w / l), 3), net=round(float(p.sum())))


rep = {}
flip = {"BUY": "SELL", "SELL": "BUY"}
for nm, tp_k, sl_k in (("v3_geometry", 1.4, 2.1), ("v4_geometry", 0.8, 2.4)):
    all_ = []
    for name in ("v3",):
        f = pd.read_csv(os.path.join(HERE, f"fable_v3_{clock}.csv"))
        atr = f.tp / 1.4
        for era, g in f.groupby("era"):
            start = pd.Timestamp(g.ts.min()).tz_convert("UTC") - pd.Timedelta(days=5)
            end = pd.Timestamp(g.ts.max()).tz_convert("UTC") + pd.Timedelta(days=5)
            m1 = load_m1(start, end)
            sim = SimX(m1, resample_ohlc(m1, "4h"))
            res = [sim.run({"entry_ts": t, "direction": flip[d]}, tp=tp_k * a, sl=sl_k * a) for t, d, a in zip(g.ts, g.dir, atr[g.index])]
            rep[f"{nm} {era}"] = st(res)
            all_ += res
    rep[f"{nm} pooled"] = st(all_)
print(clock, rep)
json.dump(rep, open(os.path.join(HERE, f"fade_{clock}.json"), "w"), indent=1)
