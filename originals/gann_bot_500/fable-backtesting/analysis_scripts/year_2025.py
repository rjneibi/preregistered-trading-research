"""FINAL_v2 performance for calendar year 2025 (from final_v2_trades.csv)."""
import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
from research.dr_backtest.metrics import basic_stats

OUT = REPO / "research" / "flip_scalp"
df = pd.read_csv(OUT / "final_v2_trades.csv")
df = df[df.entry_ts.str.startswith("2025")].reset_index(drop=True)

for col, lbl in [("pnl_v2", "FINAL_v2"), ("pnl_v2_pyr", "FINAL_v2+ADXpyr")]:
    s = basic_stats(list(df[col]))
    cum = df[col].cumsum()
    mdd = (cum.cummax() - cum).max()
    print(f"{lbl} 2025: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
          f"net=${df[col].sum():,.0f} maxDD=${mdd:,.0f} "
          f"best=${df[col].max():,.0f} worst=${df[col].min():,.0f}")

df["month"] = df.entry_ts.str[:7]
m = df.groupby("month").agg(trades=("pnl_v2", "size"),
                            net_v2=("pnl_v2", "sum"),
                            net_pyr=("pnl_v2_pyr", "sum"),
                            wins=("pnl_v2", lambda x: (x > 0).sum()))
print("\nmonthly:")
print(m.to_string())

df.to_csv(OUT / "trades_2025.csv", index=False)
fig, ax = plt.subplots(figsize=(12, 5))
ts = pd.to_datetime(df.entry_ts)
ax.plot(ts, df.pnl_v2.cumsum(), lw=1.5, color="#1b5e20", label="FINAL_v2")
ax.plot(ts, df.pnl_v2_pyr.cumsum(), lw=1.5, color="#b26a00",
        label="+ ADX-gated pyramid")
ax.axhline(0, color="grey", lw=0.8)
s = basic_stats(list(df.pnl_v2))
ax.set_title(f"FINAL_v2 — calendar year 2025, 1.00 lot "
             f"(n={s['n']}, WR {s['win_rate']:.0%}, net ${df.pnl_v2.sum():,.0f})")
ax.set_ylabel("cumulative $")
ax.legend(loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "equity_2025.png", dpi=130)
print("\nwrote trades_2025.csv + equity_2025.png")
