"""One-off: characterize the TP10_NOSL losers (why is TP-only losing?)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
h1 = resample_ohlc(m1, "1h")
h4 = resample_ohlc(m1, "4h")
d1 = resample_d1_utc(m1)
atr_h1 = wilder_atr(h1, 14)

events = rfs.collect_flip_events(m1, h1, h4, d1, atr_h1)
sim = rfs.M1Sim(m1)

trades = []
for e in sorted(events, key=lambda x: x["entry_ts"]):
    r = sim.run(pd.Timestamp(e["entry_ts"]), e["direction"], 1000.0, None,
                horizon_hours=720)
    trades.append({**e, **r})

df = pd.DataFrame(trades)
df = df[df.pnl_points.notna()]
df["dollars"] = df.pnl_points / 100.0
df["year"] = df.entry_ts.str[:4]

win = df[df.dollars > 0]
lose = df[df.dollars <= 0]
print(f"\nwinners: {len(win)}  total +${win.dollars.sum():,.0f}  "
      f"avg +${win.dollars.mean():.2f}")
print(f"losers:  {len(lose)}  total -${-lose.dollars.sum():,.0f}  "
      f"avg -${-lose.dollars.mean():.2f}")

print("\nlosers by direction:")
print(lose.groupby("direction").dollars.agg(["count", "sum", "mean"]).round(2))
print("\nall trades by direction (win rate):")
for d in ("BUY", "SELL"):
    sub = df[df.direction == d]
    print(f"  {d}: n={len(sub)}  wr={(sub.dollars > 0).mean():.3f}  "
          f"net=${sub.dollars.sum():,.0f}")
print("\nlosers by year:")
print(lose.groupby("year").dollars.agg(["count", "sum"]).round(0))
print("\nnet by year ($):")
print(df.groupby("year").dollars.sum().round(0))

print("\n15 worst trades:")
cols = ["entry_ts", "direction", "h4_close", "dollars", "mae_points",
        "hold_hours", "zone_sources"]
w = lose.nsmallest(15, "dollars")[cols]
w["mae_$"] = w.mae_points / 100.0
print(w.drop(columns="mae_points").to_string(index=False))

print("\nloss-size distribution ($):")
print((-lose.dollars).describe(percentiles=[.5, .75, .9, .95]).round(1))
