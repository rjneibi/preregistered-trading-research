"""Round 11: (A) VIRGIN 2010-2015 test of v5 exits (+ADX tilt; news weight
omitted — calendar predates our data). (B) Portfolio correlation v3(H4) vs
v5.1(H1) from saved trade records. (C) 1%-risk compounding projection."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))
sys.path.insert(0, str(REPO / "fable-backtesting"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from regime_switch import wilder_adx_d1
from bail_exit_v5 import Sim5, scan_entries

# ---- (A) virgin 2010-2015 -------------------------------------------------
start = pd.Timestamp("2010-06-01T00:00:00Z")
end = pd.Timestamp("2015-06-18T23:59:00Z")
rfs.BT_START, rfs.BT_END = start, end
rfs.apply_config()
m1 = load_m1(start - pd.Timedelta(days=100), end)
h1 = resample_ohlc(m1, "1h")
h4 = resample_ohlc(m1, "4h")
d1 = resample_d1_utc(m1)
atr_h1 = wilder_atr(h1, 14)
adx = wilder_adx_d1(d1)
entries = scan_entries(start, end, m1, h1, h4, d1, atr_h1)
sim = Sim5(m1)

rows = []
for e in entries:
    kw = dict(half_x=1.2) if e["hivol"] else dict(bail_t=8, bail_x=1.0)
    p = sim.run(e, **kw)
    if p is None:
        continue
    a = adx[adx.index < pd.Timestamp(e["ts"]).floor("D")]
    tilt = 1.0 if (len(a) and a.iloc[-1] > 22) else 0.5
    rows.append({"ts": e["ts"], "pnl": p, "p51": p * tilt})
d = pd.DataFrame(rows)
for col, tag in [("pnl", "v5 flat"), ("p51", "v5+ADXtilt")]:
    p = d[col]
    pf = round(p[p > 0].sum() / -p[p <= 0].sum(), 2)
    cum = p.cumsum()
    mdd = (cum.cummax() - cum).max()
    print(f"VIRGIN 2010-15 {tag}: n={len(p)} wr={(p > 0).mean():.1%} "
          f"pf={pf} net=${p.sum():,.0f} maxDD=${mdd:,.0f}")
d["year"] = d.ts.str[:4]
print(d.groupby("year").p51.agg(["count", "sum"]).round(0).to_string())

# ---- (B) portfolio correlation --------------------------------------------
v3 = pd.read_csv(REPO / "fable-backtesting" / "final_v2_trades.csv")
v3["month"] = v3.entry_ts.str[:7]
m3 = v3.groupby("month").pnl_v2.sum()
v51 = pd.read_csv(REPO / "fable-backtesting" / "forensics_trades.csv")
v51["w"] = (v51.adx.gt(22).map({True: 1.0, False: 0.5})
            * v51.news.map({True: 1.5, False: 1.0}))
v51["p"] = v51.pnl * v51.w
m5 = v51.assign(month=v51.ts.str[:7]).groupby("month").p.sum()
both = pd.concat([m3.rename("v3_H4"), m5.rename("v51_H1")], axis=1).dropna()
corr = both.corr().iloc[0, 1]
combo = both.sum(axis=1)
for name, s in [("v3_H4", both.v3_H4), ("v51_H1", both.v51_H1),
                ("COMBINED", combo)]:
    cum = s.cumsum()
    mdd = (cum.cummax() - cum).max()
    print(f"PORTFOLIO {name}: months={len(s)} net=${s.sum():,.0f} "
          f"maxDD_monthly=${mdd:,.0f} avg/mo=${s.mean():,.0f}")
print(f"monthly P&L correlation v3 vs v5.1: {corr:.2f}")

# ---- (C) compounding at 1% risk -------------------------------------------
t = v51.sort_values("ts")
eq, peak = 10000.0, 10000.0
for _, r in t.iterrows():
    frac = 0.01 if eq >= 0.95 * peak else 0.005
    risk_d = 2.4 * (r.pnl / abs(r.pnl) if r.pnl else 1)  # placeholder
    # R-multiple approx: pnl / (2.4*ATR*100) at 1 lot -> use SL$ = 2.4*atr*100
    # forensics csv lacks atr; approximate R via pnl scaled by era avg SL.
print("(compounding uses R-multiples; see summary in chat)")
eqs = []
eq, peak = 10000.0, 10000.0
med_loss = -t[t.pnl <= 0].pnl.median()          # ~1R proxy in $ at 1 lot
for _, r in t.iterrows():
    frac = 0.01 if eq >= 0.95 * peak else 0.005
    R = (r.p if r.p else 0) / med_loss
    eq *= (1 + frac * R)
    peak = max(peak, eq)
    eqs.append(eq)
s = pd.Series(eqs)
mdd = ((s.cummax() - s) / s.cummax()).max()
years = 11.0
cagr = (eq / 10000) ** (1 / years) - 1
print(f"COMPOUND 1%-risk (R-proxy, $10k start, 11y): final=${eq:,.0f} "
      f"CAGR={cagr:.1%} maxDD={mdd:.1%}")
