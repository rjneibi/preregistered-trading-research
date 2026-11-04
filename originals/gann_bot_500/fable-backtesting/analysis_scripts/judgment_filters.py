"""Testable 'human judgment' filters on the R3+S3 flip scalp (1 lot, TP/SL $10):
  (a) H4 bias agreement (live structure.get_h4_bias)
  (b) session hour of the H4 close
  (c) ATR regime (entry ATR vs trailing 30-day median)
  (d) day of week
"""
import json
import logging
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))
for name in ("levels", "signal", "signals", "structure"):
    logging.getLogger(name).setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

import structure as structure_mod
import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, wilder_atr, completed_h4_before, bars_to_dicts,
)
from research.dr_backtest.metrics import basic_stats

LOT = 100.0
rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
h1 = resample_ohlc(m1, "1h")
h4 = resample_ohlc(m1, "4h")
atr_h1 = wilder_atr(h1, 14)
atr_med = atr_h1.rolling(24 * 30, min_periods=100).median()  # ~30 trading days
sim = rfs.M1Sim(m1)

events = [json.loads(l) for l in
          (REPO / "research/flip_scalp/events.jsonl").read_text().splitlines()]
events.sort(key=lambda x: x["entry_ts"])
sub = [e for e in events if {"R3", "S3"} & set(e["zone_sources"])]

trades = []
for e in sub:
    ts = pd.Timestamp(e["entry_ts"])
    r = sim.run(ts, e["direction"], 1000.0, 1000.0)
    if r["pnl_points"] is None:
        continue
    bars = bars_to_dicts(completed_h4_before(h4, ts).tail(250))
    bias = structure_mod.get_h4_bias(bars) if len(bars) >= 200 else "n/a"
    agree = ((e["direction"] == "BUY" and bias == "bullish") or
             (e["direction"] == "SELL" and bias == "bearish"))
    pos = h1.index.searchsorted(ts - pd.Timedelta(hours=1), side="right") - 1
    a, am = float(atr_h1.iloc[pos]), float(atr_med.iloc[pos])
    trades.append({
        "ts": ts, "dir": e["direction"], "pnl": r["pnl_points"] / 100 * LOT,
        "bias": bias, "agree": agree, "hour": ts.hour,
        "dow": ts.strftime("%a"),
        "vol": "high" if a > am else "low",
    })

df = pd.DataFrame(trades)

def show(label, mask):
    d = df[mask]
    if len(d) == 0:
        print(f"{label:>28}: n=0")
        return
    s = basic_stats(list(d.pnl))
    cut = int(round(len(d) * 0.7))
    s_oos = basic_stats(list(d.pnl.iloc[cut:]))
    print(f"{label:>28}: n={s['n']:>3} wr={s['win_rate']} pf={s['pf']:<6} "
          f"net=${d.pnl.sum():>9,.0f}  OOS_pf={s_oos['pf']}")

print("=== baseline ===")
show("ALL R3+S3", df.pnl.notna())
print("\n=== (a) H4 bias ===")
show("bias AGREES with flip", df.agree)
show("bias neutral", (~df.agree) & (df.bias == "neutral"))
show("bias OPPOSES flip", (~df.agree) & df.bias.isin(["bullish", "bearish"]))
print("\n=== (b) session hour (UTC H4 close) ===")
for h in sorted(df.hour.unique()):
    show(f"close {h:02d}:00", df.hour == h)
print("\n=== (c) ATR regime ===")
show("high vol (ATR>30d median)", df.vol == "high")
show("low vol", df.vol == "low")
print("\n=== (d) day of week ===")
for d_ in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sun"]:
    show(d_, df.dow == d_)
print("\n=== combos ===")
show("agree + high vol", df.agree & (df.vol == "high"))
show("agree + low vol", df.agree & (df.vol == "low"))
df.to_csv(REPO / "research/flip_scalp/r3s3_judgment_filters.csv", index=False)
print("\nwrote r3s3_judgment_filters.csv")
