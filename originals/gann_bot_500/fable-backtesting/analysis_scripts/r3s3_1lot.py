"""R3+S3 flip scalp at 1.00 lot (100 oz): TP $10 / SL $10, full $ accounting.
Also reports the TP-only-no-SL variant at the same size as a risk illustration.
"""
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

LOT_OZ = 100.0          # 1.00 lot XAUUSD = 100 oz -> $100 per $1 move
OUT = REPO / "research" / "flip_scalp"

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
sim = rfs.M1Sim(m1)
events = [json.loads(l) for l in (OUT / "events.jsonl").read_text().splitlines()]
events.sort(key=lambda x: x["entry_ts"])
sub = [e for e in events if {"R3", "S3"} & set(e["zone_sources"])]
print(f"R3/S3 flip events: {len(sub)}")

rows = []
for e in sub:
    ts = pd.Timestamp(e["entry_ts"])
    r = sim.run(ts, e["direction"], 1000.0, 1000.0)
    rn = sim.run(ts, e["direction"], 1000.0, None, horizon_hours=720)
    if r["pnl_points"] is None:
        continue
    rows.append({
        "entry_time": ts.strftime("%Y-%m-%d %H:%M"),
        "direction": e["direction"],
        "zones": "+".join(e["zone_sources"]),
        "entry_price": round(e["h4_close"], 2),
        "result": {"TP": "WIN", "SL": "LOSS",
                   "AMBIGUOUS_SAME_BAR": "LOSS"}.get(r["status"], r["status"]),
        "pnl_usd_1lot": round(r["pnl_points"] / 100.0 * LOT_OZ, 0),
        "hold_hours": r["hold_hours"],
        "exit_time": pd.Timestamp(r["exit_ts"]).strftime("%Y-%m-%d %H:%M"),
        "nosl_pnl_usd_1lot": (round(rn["pnl_points"] / 100.0 * LOT_OZ, 0)
                              if rn["pnl_points"] is not None else None),
        "nosl_worst_drawdown_usd": round(rn["mae_points"] / 100.0 * LOT_OZ, 0),
    })

df = pd.DataFrame(rows)
df["cumulative_usd"] = df.pnl_usd_1lot.cumsum()
df.to_csv(OUT / "r3s3_trades_1lot.csv", index=False)

pnl = df.pnl_usd_1lot
peak = df.cumulative_usd.cummax()
mdd = (peak - df.cumulative_usd).max()
cut = int(round(len(df) * 0.7))
s_all = basic_stats(list(pnl))
s_is = basic_stats(list(pnl[:cut]))
s_oos = basic_stats(list(pnl[cut:]))
print(f"\n=== R3+S3, 1.00 lot, TP$10/SL$10 ===")
print(f"trades={len(df)} wins={(pnl > 0).sum()} losses={(pnl < 0).sum()} "
      f"wr={s_all['win_rate']}")
print(f"net=${pnl.sum():,.0f}  maxDD=${mdd:,.0f}  "
      f"avg/trade=${pnl.mean():,.0f}  trades/week={len(df)/261:.2f}")
print(f"PF all={s_all['pf']}  IS={s_is['pf']}  OOS={s_oos['pf']}")
print(f"per year:")
df["year"] = df.entry_time.str[:4]
print(df.groupby("year").pnl_usd_1lot.agg(["count", "sum"]).round(0))

n = df.nosl_pnl_usd_1lot.dropna()
print(f"\n=== same trades, NO stop (TP-only), 1.00 lot ===")
print(f"net=${n.sum():,.0f}  worst single trade=${n.min():,.0f}")
print(f"median worst-drawdown-while-open=${df.nosl_worst_drawdown_usd.median():,.0f}"
      f"  p90=${df.nosl_worst_drawdown_usd.quantile(.9):,.0f}"
      f"  max=${df.nosl_worst_drawdown_usd.max():,.0f}")

fig, ax = plt.subplots(figsize=(12, 5))
ts = pd.to_datetime(df.entry_time)
ax.plot(ts, df.cumulative_usd, lw=1.4, color="#2e7d32")
ax.axhline(0, color="grey", lw=0.8)
ax.set_title(f"R3+S3 zone-flip scalp — 1.00 lot, TP $10 / SL $10 "
             f"({len(df)} trades, net ${pnl.sum():,.0f}, maxDD ${mdd:,.0f})")
ax.set_ylabel("cumulative $ (1.00 lot)")
fig.tight_layout()
fig.savefig(OUT / "r3s3_equity_1lot.png", dpi=130)
print("\nwrote r3s3_trades_1lot.csv + r3s3_equity_1lot.png")
