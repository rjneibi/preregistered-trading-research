import pandas as pd
import sys
sys.path.insert(0, r"@GANN_ROOT@")
from research.dr_backtest.metrics import basic_stats

df = pd.read_csv(r"@GANN_ROOT@/research/flip_scalp/r3s3_judgment_filters.csv")
for label, d in [("baseline (all)", df),
                 ("no-Monday", df[df.dow != "Mon"]),
                 ("no-Mon + skip 00:00 close", df[(df.dow != "Mon") & (df.hour != 0)])]:
    d = d.reset_index(drop=True)
    cut = int(round(len(d) * 0.7))
    s = basic_stats(list(d.pnl))
    si = basic_stats(list(d.pnl[:cut]))
    so = basic_stats(list(d.pnl[cut:]))
    cum = d.pnl.cumsum()
    mdd = (cum.cummax() - cum).max()
    print(f"{label:>26}: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
          f"IS={si['pf']} OOS={so['pf']} net=${d.pnl.sum():,.0f} "
          f"maxDD=${mdd:,.0f}")
