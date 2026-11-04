"""FINAL_v4 on H1 2026 (2026-01-01 -> 2026-06-19). Monthly P&L breakdown.
Spec: H1-close flip of R3/S3, 12-20 UTC, no Mon, 1/day, TP 0.8xATR /
SL 2.4xATR / ts24h. Also FINAL_v3 (H4, 1.4/2.1) reference line."""
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from research.dr_backtest.metrics import basic_stats
from innovate_r3s3 import SimX

START = pd.Timestamp("2026-01-01T00:00:00Z")
END = pd.Timestamp("2026-06-19T17:57:00Z")
rfs.BT_START, rfs.BT_END = START, END
rfs.apply_config()
m1 = load_m1(START - pd.Timedelta(days=100), END)
h1 = resample_ohlc(m1, "1h")
h4 = resample_ohlc(m1, "4h")
d1 = resample_d1_utc(m1)
atr_h1 = wilder_atr(h1, 14)
sim = SimX(m1, h4)

trades = []
for day_open in d1.index[(d1.index >= START) & (d1.index <= END)]:
    if day_open.strftime("%a") == "Mon":
        continue
    built = rfs.build_day_zones(day_open, d1, h4, atr_h1, h1.index)
    if built is None:
        continue
    zones, atr = built
    live = [z for z in zones if z["source"] in ("R3", "S3")
            and not z["baseline_flipped"]]
    if not live:
        continue
    day_h1 = h1[(h1.index >= day_open) &
                (h1.index < day_open + pd.Timedelta(days=1))]
    for open_ts, row in day_h1.iterrows():
        cursor = open_ts + pd.Timedelta(hours=1)
        if not (12 <= cursor.hour <= 20) or cursor > END:
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
            e = {"entry_ts": cursor.isoformat(), "atr_at_build": atr}
            p = sim.run(e | {"direction": hit[0]}, tp=0.8 * atr,
                        sl=2.4 * atr, level=hit[1]["level"])
            if p is not None:
                trades.append({"entry_time": cursor.strftime("%Y-%m-%d %H:%M"),
                               "direction": hit[0], "zone": hit[1]["source"],
                               "level": hit[1]["level"],
                               "entry_price": round(close, 2),
                               "tp_usd": round(0.8 * atr, 2),
                               "sl_usd": round(2.4 * atr, 2),
                               "pnl_usd_1lot": round(p, 0)})
            break

df = pd.DataFrame(trades)
df["cumulative"] = df.pnl_usd_1lot.cumsum()
df.to_csv(REPO / "fable-backtesting" / "trades_2026H1.csv", index=False)
s = basic_stats(list(df.pnl_usd_1lot))
cum = df.pnl_usd_1lot.cumsum()
mdd = (cum.cummax() - cum).max()
print(f"FINAL_v4 2026-H1: n={s['n']} wins={(df.pnl_usd_1lot > 0).sum()} "
      f"losses={(df.pnl_usd_1lot <= 0).sum()} wr={s['win_rate']} "
      f"pf={s['pf']} net=${df.pnl_usd_1lot.sum():,.0f} maxDD=${mdd:,.0f}")
df["month"] = df.entry_time.str[:7]
print(df.groupby("month").agg(
    trades=("pnl_usd_1lot", "size"),
    wins=("pnl_usd_1lot", lambda x: int((x > 0).sum())),
    losses=("pnl_usd_1lot", lambda x: int((x <= 0).sum())),
    net=("pnl_usd_1lot", "sum")).to_string())
print("\nall trades:")
print(df.drop(columns="month").to_string(index=False))
