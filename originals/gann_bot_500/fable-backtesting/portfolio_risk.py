"""Round 12: portfolio-level loss reduction for the v3(H4)+v5.1(H1) book.
From saved trade records (no rescan):
  Analysis: how much combined loss comes from same-day double-losses?
  Rule A (concentration cap): both arms same day + same direction ->
          the LATER entry takes half size.
  Rule B (daily breaker): if combined realized P&L for the day is worse
          than -$1,500 (~1.5 avg losses), skip remaining entries that day.
Scored on full 11y + per era + 2026H1: net, maxDD, worst day.
"""
import pandas as pd

BASE = r"@GANN_ROOT@/fable-backtesting"
v3 = pd.read_csv(f"{BASE}\\final_v2_trades.csv")
v3 = v3.rename(columns={"entry_ts": "ts", "pnl_v2": "pnl"})[
    ["ts", "direction", "pnl"]]
v3["arm"] = "v3"
v5 = pd.read_csv(f"{BASE}\\forensics_trades.csv")
v5["w"] = (v5.adx.gt(22).map({True: 1.0, False: 0.5})
           * v5.news.map({True: 1.5, False: 1.0}))
v5["pnl"] = v5.pnl * v5.w
v5 = v5.rename(columns={"dir": "direction"})[["ts", "direction", "pnl"]]
v5["arm"] = "v5"
df = pd.concat([v3, v5]).sort_values("ts").reset_index(drop=True)
df["date"] = df.ts.str[:10]

# ---- analysis: same-day double losses -------------------------------------
day = df.groupby("date").agg(n=("pnl", "size"), net=("pnl", "sum"),
                             arms=("arm", "nunique"))
both = day[day.arms == 2]
dl = both[both.net < 0]
print(f"days with trades: {len(day)}  both-arms days: {len(both)} "
      f"({len(both)/len(day):.0%})")
print(f"both-arms losing days: {len(dl)}  total=${dl.net.sum():,.0f}  "
      f"worst day=${day.net.min():,.0f}")
all_neg = day[day.net < 0]
print(f"ALL losing days: {len(all_neg)} total=${all_neg.net.sum():,.0f} — "
      f"double-loss days are "
      f"{dl.net.sum()/all_neg.net.sum():.0%} of daily losses\n")


def scored(weights, tag, sub=None):
    d = df if sub is None else sub
    p = d.pnl * weights.loc[d.index]
    cum = p.cumsum()
    mdd = (cum.cummax() - cum).max()
    wd = p.groupby(d.date).sum().min()
    print(f"  {tag:>18}: net=${p.sum():,.0f}  maxDD=${mdd:,.0f}  "
          f"worst_day=${wd:,.0f}")


def rule_a_weights():
    w = pd.Series(1.0, index=df.index)
    for (dt, dr), g in df.groupby(["date", "direction"]):
        if g.arm.nunique() == 2:
            w.loc[g.index[1:]] = 0.5     # later same-direction entries halved
    return w


def rule_b_weights(cap=-1500.0):
    w = pd.Series(1.0, index=df.index)
    for dt, g in df.groupby("date"):
        run = 0.0
        for i, r in g.iterrows():
            if run <= cap:
                w.loc[i] = 0.0
            run += r.pnl * w.loc[i]
    return w


wa, wb = rule_a_weights(), rule_b_weights()
wab = pd.concat([wa, wb], axis=1).min(axis=1)
for era_tag, sub in [
        ("FULL 11y", None),
        ("old era", df[df.ts < "2021-06-19"]),
        ("new era", df[df.ts >= "2021-06-19"]),
        ("2026 H1", df[df.ts >= "2026-01-01"])]:
    print(f"=== {era_tag} ===")
    scored(pd.Series(1.0, index=df.index), "baseline", sub)
    scored(wa, "A conc-cap", sub)
    scored(wb, "B daily-breaker", sub)
    scored(wab, "A+B", sub)
