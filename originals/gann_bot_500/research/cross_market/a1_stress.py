"""XM-1b: try to BREAK the one pass (A1 RSI2 mean-reversion on US500) before believing it.
  1 execution: enter/exit at the NEXT day's open instead of the signal close
  2 costs: spread x2 and financing 7%/yr
  3 parameter neighbourhood (no picking - the whole grid is shown)
  4 untouched markets: US30 (2012+), USTEC (2022+), IWM US small caps (2003+), EWA Australia (2003+)
  5 per-year table, worst trade, losing streak, equity drawdown at 100% notional per trade
"""
import numpy as np
import pandas as pd

import xm_lab as X


def rsi2_trades(sym, thr=10, exit_ma=5, maxd=10, trend=200, next_open=False, sp_mult=1.0, fin=0.05):
    d, sp = X.load(sym, "D1")
    if sp == 0:
        sp = 0.0002 * d["c"].median()
    sp *= sp_mult
    c, o = d["c"], d["o"]
    smaT, smaX = c.rolling(trend).mean(), c.rolling(exit_ma).mean()
    diff = c.diff()
    up, dn = diff.clip(lower=0).ewm(alpha=.5).mean(), (-diff).clip(lower=0).ewm(alpha=.5).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, 1e-12))
    out, i = [], trend
    while i < len(c) - 2:
        if rsi.iloc[i] < thr and (trend <= 1 or c.iloc[i] > smaT.iloc[i]):
            j = i + 1
            while j < len(c) - 2 and j - i < maxd and c.iloc[j] <= smaX.iloc[j]:
                j += 1
            pin = o.iloc[i + 1] if next_open else c.iloc[i]
            pout = o.iloc[j + 1] if next_open else c.iloc[j]
            t_in, t_out = (c.index[i + 1], c.index[j + 1]) if next_open else (c.index[i], c.index[j])
            nights = (t_out - t_in).days
            out.append((c.index[i], pout / pin - 1 - sp / pin - nights * fin / 365))
            i = j + 1
        else:
            i += 1
    return pd.Series([r for _, r in out], index=[t for t, _ in out])


def line(name, r):
    h = len(r) // 2
    a, b = r.values[:h], r.values[h:]
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    print(f"  {name:44s} n={len(r):4d} win {np.mean(r > 0):.0%} avg {r.mean()*100:+.3f}% | PF h1 {X.pf(a):.2f} h2 {X.pf(b):.2f} | "
          f"total {(eq.iloc[-1]-1)*100:+.0f}% maxDD {dd*100:.1f}%")


if __name__ == "__main__":
    print("1-2 execution and cost stress, US500")
    line("baseline (signal close)", rsi2_trades("US500"))
    line("next-day open in/out", rsi2_trades("US500", next_open=True))
    line("next open + spread x2 + financing 7%", rsi2_trades("US500", next_open=True, sp_mult=2, fin=0.07))
    print("\n3 parameter neighbourhood, US500, next-open execution (PF half1/half2)")
    print("        " + "".join(f"exitMA {m:<14d}" for m in (3, 5, 10)))
    for thr in (5, 10, 15, 25):
        row = []
        for m in (3, 5, 10):
            r = rsi2_trades("US500", thr=thr, exit_ma=m, next_open=True)
            h = len(r) // 2
            row.append(f"{X.pf(r.values[:h]):.2f}/{X.pf(r.values[h:]):.2f} n{len(r):<4d}  ")
        print(f"  RSI<{thr:<3d} " + "".join(row))
    r = rsi2_trades("US500", trend=1, next_open=True)
    line("no SMA200 trend filter", r)
    print("\n4 markets the rule was never fitted on (next-open execution)")
    for s in ("US30", "USTEC", "IWM", "EWA"):
        line(s, rsi2_trades(s, next_open=True))
    r = rsi2_trades("IWM", next_open=True)
    line("IWM 2003-2011 only (before the US500 sample)", r[r.index < "2012-08-01"])
    print("\n5 US500 per year (next-open)")
    r = rsi2_trades("US500", next_open=True)
    y = r.groupby(r.index.year)
    print("  " + "  ".join(f"{k}:{v.sum()*100:+.1f}%({len(v)})" for k, v in y))
    lose = (r < 0).astype(int)
    streak = lose.groupby((lose != lose.shift()).cumsum()).sum().max()
    print(f"  worst trade {r.min()*100:.2f}%  best {r.max()*100:.2f}%  longest losing streak {streak}")
