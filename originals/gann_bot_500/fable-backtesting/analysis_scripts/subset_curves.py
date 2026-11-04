"""Equity curves: S1+S2 flips vs R3+S3 flips (TP$10/SL$10)."""
import json
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1
from research.dr_backtest.metrics import basic_stats

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
sim = rfs.M1Sim(m1)
events = [json.loads(l) for l in
          (REPO / "research/flip_scalp/events.jsonl").read_text().splitlines()]
events.sort(key=lambda x: x["entry_ts"])

fig, ax = plt.subplots(figsize=(12, 5))
for label, srcs, color in [("S1+S2 flips", {"S1", "S2"}, "#c62828"),
                           ("R3+S3 flips", {"R3", "S3"}, "#2e7d32")]:
    pnl, ts = [], []
    for e in events:
        if not (srcs & set(e["zone_sources"])):
            continue
        r = sim.run(pd.Timestamp(e["entry_ts"]), e["direction"], 1000.0, 1000.0)
        if r["pnl_points"] is None:
            continue
        pnl.append(r["pnl_points"] / 100.0)
        ts.append(pd.Timestamp(e["entry_ts"]))
    cum = pd.Series(pnl).cumsum()
    s = basic_stats([p * 100 for p in pnl])
    cut = int(round(len(pnl) * 0.7))
    s_oos = basic_stats([p * 100 for p in pnl[cut:]])
    print(f"{label}: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
          f"net=${cum.iloc[-1]:,.0f}  OOS pf={s_oos['pf']}")
    ax.plot(ts, cum.values, lw=1.3, color=color,
            label=f"{label}  (n={s['n']}, PF {s['pf']}, net ${cum.iloc[-1]:,.0f})")

ax.axhline(0, color="grey", lw=0.8)
ax.set_title("Flip scalp TP$10/SL$10 — which zones to trade? (per 1 oz)")
ax.set_ylabel("cumulative $")
ax.legend(loc="upper left")
fig.tight_layout()
fig.savefig(REPO / "research/flip_scalp/subset_equity.png", dpi=130)
print("wrote subset_equity.png")
