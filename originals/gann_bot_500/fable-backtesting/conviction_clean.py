"""Round 16: NO-HINDSIGHT conviction filter. A trade is taken only when the
OTHER arm has already fired the same direction that day at or before this
entry's timestamp (simultaneous 12/16/20 closes count â€” the bot sees both).
The day's first unconfirmed signal is SKIPPED (it can't know the future)."""
import pandas as pd

B = r"@GANN_ROOT@/fable-backtesting"
v3 = pd.read_csv(f"{B}\\final_v2_trades.csv").rename(
    columns={"entry_ts": "ts", "pnl_v2": "pnl"})[["ts", "direction", "pnl"]]
v3["arm"] = "v3"
v5 = pd.read_csv(f"{B}\\forensics_trades.csv")
v5["pnl"] = v5.pnl * (v5.adx.gt(22).map({True: 1., False: .5})
                      * v5.news.map({True: 1.5, False: 1.}))
v5 = v5.rename(columns={"dir": "direction"})[["ts", "direction", "pnl"]]
v5["arm"] = "v5"
df = pd.concat([v3, v5]).sort_values("ts").reset_index(drop=True)
df["t"] = pd.to_datetime(df.ts)
df["date"] = df.t.dt.date

keep = []
for (d, direc), g in df.groupby(["date", "direction"]):
    arms = g.arm.values
    times = g.t.values
    for i in range(len(g)):
        other_before = any(arms[j] != arms[i] and times[j] <= times[i]
                           for j in range(len(g)))
        keep.append((g.index[i], other_before))
kmap = dict(keep)
df["keep_flag"] = df.index.map(kmap)

def pf(x):
    w = x[x > 0].sum(); l = -x[x <= 0].sum()
    return round(w / l, 2) if l > 0 else 99.0

for era, d in [("old", df[df.ts < "2021-06-19"]),
               ("new", df[df.ts >= "2021-06-19"]),
               ("2026H1", df[df.ts >= "2026-01-01"])]:
    t = d[d.keep_flag]
    cum = t.pnl.cumsum()
    mdd = (cum.cummax() - cum).max() if len(t) else 0
    print(f"{era:>6} CLEAN-CONVICTION: n={len(t)} (of {len(d)}) "
          f"wr={(t.pnl > 0).mean():.1%} pf={pf(t.pnl)} "
          f"net=${t.pnl.sum():,.0f} maxDD=${mdd:,.0f}")
    base = d
    print(f"{'':>6} baseline both-arms: n={len(base)} "
          f"wr={(base.pnl > 0).mean():.1%} pf={pf(base.pnl)} "
          f"net=${base.pnl.sum():,.0f}")

