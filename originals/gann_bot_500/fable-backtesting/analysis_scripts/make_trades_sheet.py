"""Turn trades_headline.jsonl (TP$10/SL$10 flip scalp) into a readable P&L
sheet + equity curve. Dollars = price dollars captured per 1 oz (0.01 lot)."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(r"@GANN_ROOT@/research/flip_scalp")
rows = [json.loads(l) for l in
        (OUT / "trades_headline.jsonl").read_text().splitlines()]

df = pd.DataFrame(rows)
df = df[df.pnl_points.notna()].copy()
df["entry_time"] = pd.to_datetime(df.entry_ts).dt.strftime("%Y-%m-%d %H:%M")
df["exit_time"] = pd.to_datetime(df.exit_ts).dt.strftime("%Y-%m-%d %H:%M")
df["pnl_usd"] = (df.pnl_points / 100).round(2)
df["result"] = df.status.map({"TP": "WIN", "SL": "LOSS",
                              "AMBIGUOUS_SAME_BAR": "LOSS",
                              "TIMEOUT": "TIMEOUT"})
df["zones"] = df.zone_sources.apply(lambda z: "+".join(z))
df["entry_price"] = df.h4_close.round(2)
df["cumulative_usd"] = df.pnl_usd.cumsum().round(2)

cols = ["entry_time", "direction", "zones", "entry_price", "result",
        "pnl_usd", "cumulative_usd", "exit_time", "hold_hours"]
sheet = df[cols]
sheet.to_csv(OUT / "trades_pnl.csv", index=False)

wins = df[df.pnl_usd > 0]
losses = df[df.pnl_usd < 0]
print(f"trades={len(df)} wins={len(wins)} losses={len(losses)}")
print(f"gross win=${wins.pnl_usd.sum():,.0f} gross loss=${losses.pnl_usd.sum():,.0f}")
print(f"net=${df.pnl_usd.sum():,.2f}  final cum=${df.cumulative_usd.iloc[-1]:,.2f}")
print("\nLAST 25 TRADES:")
print(sheet.tail(25).to_string(index=False))

# equity curve
ts = pd.to_datetime(df.entry_ts)
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(ts, df.cumulative_usd, lw=1.2, color="#1565c0")
ax.axhline(0, color="grey", lw=0.8)
ax.fill_between(ts, df.cumulative_usd, 0,
                where=df.cumulative_usd >= 0, alpha=.15, color="green")
ax.fill_between(ts, df.cumulative_usd, 0,
                where=df.cumulative_usd < 0, alpha=.15, color="red")
ax.set_title("Zone-flip scalp, enter on flip, TP $10 / SL $10 — "
             "cumulative P&L per 1 oz (1,262 trades, 2021-2026)")
ax.set_ylabel("cumulative $")
fig.tight_layout()
fig.savefig(OUT / "equity_curve.png", dpi=130)
print(f"\nwrote {OUT / 'trades_pnl.csv'} and equity_curve.png")
