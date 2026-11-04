"""DR screen under the project's own cost matrix, both clocks. Original screen had no spread. No rule changes. Writes dr_matrix.json."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "_copy", "goldbot", "prereg")]
from cost_matrix import CostMatrix

M = os.path.join(HERE, "..", "_copy", "goldbot", "results", "cost_matrix.json")
rep = {}


def pf(v):
    return round(float(v[v > 0].sum() / -v[v < 0].sum()), 3)


for stat in ("median", "p90"):
    cm = CostMatrix.load(M, stat=stat, k_slip=0.5, commission_per_lot_rt=7.0)
    for c in ("recorded", "true"):
        for p in "DR":
            x = [json.loads(l) for l in open(os.path.join(HERE, "..", "_copy", f"sb_fable_{c}", "research", "dr_backtest", f"trades_{p}.jsonl")) if l.strip()]
            x = [e for e in x if e.get("pnl_points") is not None and e.get("exit_ts_final")]
            ts = pd.to_datetime([e["entry_ts"] for e in x], utc=True)
            ex = pd.to_datetime([e["exit_ts_final"] for e in x], utc=True)
            r = np.array([e["pnl_points"] for e in x], float)
            cost = np.array([cm.trade_cost_usd(a, b) for a, b in zip(ts, ex)])
            n = r - cost
            o = np.arange(len(n)) >= int(len(n) * 0.7)
            day = pd.Series(n, index=ts).groupby(ts.date).sum()
            rep[f"{c} {p} {stat}"] = dict(n=len(n), avg_cost_pts=round(float(cost.mean()), 1), pf=pf(n), is_pf=pf(n[~o]), oos_pf=pf(n[o]), days=len(day), day_pf=pf(day.values), mean_per_trade=round(float(n.mean()), 1), by_year={int(k): round(float(v)) for k, v in pd.Series(n, index=ts).groupby(ts.year).sum().items()}, long_share=round(float(np.mean([e["direction"] == "BUY" for e in x])), 3))
            print(c, p, stat, rep[f"{c} {p} {stat}"], flush=True)
json.dump(rep, open(os.path.join(HERE, "dr_matrix.json"), "w"), indent=1)
