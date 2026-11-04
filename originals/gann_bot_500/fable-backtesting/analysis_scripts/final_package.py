"""Final candidate package: R3/S3 flips, no Monday, TP$8/SL$12, 24h time stop.
Full 2021-2026 stats + equity curve + trades CSV."""
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
from tune_r3s3 import Sim, load_events, OUT

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
sim = Sim(m1)
ev = load_events(OUT / "events.jsonl")   # no-Monday R3/S3

rows = []
for e in ev:
    r = sim.run(e, entry="market", tp_usd=8.0, sl_usd=12.0, time_stop_h=24)
    if r["pnl"] is None:
        continue
    rows.append({
        "entry_time": pd.Timestamp(e["entry_ts"]).strftime("%Y-%m-%d %H:%M"),
        "direction": e["direction"],
        "zones": "+".join(e["zone_sources"]),
        "entry_price": round(e["h4_close"], 2),
        "exit": r["status"],
        "pnl_usd_1lot": round(r["pnl"], 0),
    })
df = pd.DataFrame(rows)
df["cumulative_usd"] = df.pnl_usd_1lot.cumsum()
df.to_csv(OUT / "final_candidate_trades.csv", index=False)

pnl = df.pnl_usd_1lot
cum = df.cumulative_usd
mdd = (cum.cummax() - cum).max()
s = basic_stats(list(pnl))
cut = int(round(len(df) * 0.7))
si = basic_stats(list(pnl[:cut]))
so = basic_stats(list(pnl[cut:]))
print(f"FINAL 2021-26: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
      f"IS={si['pf']} OOS={so['pf']} net=${pnl.sum():,.0f} maxDD=${mdd:,.0f}")
print(f"exit mix: {df.exit.value_counts().to_dict()}")
print(f"trades/week: {len(df)/261:.2f}")

fig, ax = plt.subplots(figsize=(12, 5))
ts = pd.to_datetime(df.entry_time)
ax.plot(ts, cum, lw=1.4, color="#1b5e20")
ax.axhline(0, color="grey", lw=0.8)
ax.set_title(f"FINAL: R3/S3 flip scalp, no Monday, TP$8/SL$12/24h stop — 1 lot "
             f"(n={len(df)}, WR {s['win_rate']:.0%}, PF {s['pf']}, "
             f"net ${pnl.sum():,.0f}, maxDD ${mdd:,.0f})")
ax.set_ylabel("cumulative $ (1.00 lot)")
fig.tight_layout()
fig.savefig(OUT / "final_candidate_equity.png", dpi=130)
print("wrote final_candidate_trades.csv + final_candidate_equity.png")
