"""Round 10a: (1) v5.1 monthly P&L profile; (2) ML meta-label experiment —
GradientBoosting on pre-entry features, TRAIN=2015-21 era, TEST=2021-26 era
(strict era split, no leakage). If out-of-sample decile lift is real, ML
sizing is a valid integration; if flat, we say so."""
import pandas as pd
import numpy as np

DF = pd.read_csv(r"@GANN_ROOT@/fable-backtesting/forensics_trades.csv")
DF["w51"] = (DF.adx.gt(22).map({True: 1.0, False: 0.5})
             * DF.news.map({True: 1.5, False: 1.0}))
DF["p51"] = DF.pnl * DF.w51
DF["month"] = DF.ts.str[:7]

# ---- (1) monthly profile ----------------------------------------------
m = DF.groupby("month").agg(n=("p51", "size"),
                            wins=("p51", lambda x: int((x > 0).sum())),
                            net=("p51", "sum")).reset_index()
print("=== monthly profile (v5.1, 1 lot) ===")
print(f"months={len(m)}  trades/mo: mean={m.n.mean():.1f} "
      f"min={m.n.min()} max={m.n.max()}")
print(f"positive months: {(m.net > 0).sum()}/{len(m)} "
      f"({(m.net > 0).mean():.0%})")
print(f"avg month net=${m.net.mean():,.0f}  best=${m.net.max():,.0f} "
      f"({m.loc[m.net.idxmax(), 'month']})  worst=${m.net.min():,.0f} "
      f"({m.loc[m.net.idxmin(), 'month']})")
print("\nlast 18 months:")
print(m.tail(18).to_string(index=False))

# ---- (2) ML meta-label ---------------------------------------------------
from sklearn.ensemble import GradientBoostingClassifier

feats = pd.get_dummies(DF[["hour", "dow", "dir"]].astype(str))
X = pd.concat([feats, DF[["hivol", "news", "overshoot", "day_ext",
                          "room", "adx"]].astype(float)], axis=1).fillna(0)
y = (DF.pnl > 0).astype(int)
tr, te = DF.era == "old", DF.era == "new"
clf = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                 learning_rate=0.05, random_state=42)
clf.fit(X[tr], y[tr])
prob = clf.predict_proba(X[te])[:, 1]
d = DF[te].copy()
d["prob"] = prob
d["decile"] = pd.qcut(d.prob, 5, labels=False, duplicates="drop")

def pf(x):
    w = x[x > 0].sum(); l = -x[x <= 0].sum()
    return round(w / l, 2) if l > 0 else 99.0

print("\n=== ML meta-label: trained on 2015-21, scored on 2021-26 ===")
for q in sorted(d.decile.unique()):
    s = d[d.decile == q]
    print(f"  quintile {q} (prob {s.prob.min():.2f}-{s.prob.max():.2f}): "
          f"n={len(s)} wr={(s.pnl > 0).mean():.2f} pf={pf(s.pnl)} "
          f"net=${s.pnl.sum():,.0f}")
top = d[d.decile >= 3]
bot = d[d.decile == 0]
print(f"\n  skip-bottom-quintile: kept n={len(d)-len(bot)} "
      f"pf={pf(d[d.decile > 0].pnl)} net=${d[d.decile > 0].pnl.sum():,.0f} "
      f"(vs all: pf={pf(d.pnl)} net=${d.pnl.sum():,.0f})")
imp = pd.Series(clf.feature_importances_, index=X.columns
                ).sort_values(ascending=False).head(8)
print("\n  top features:", ", ".join(f"{k}={v:.2f}" for k, v in imp.items()))
