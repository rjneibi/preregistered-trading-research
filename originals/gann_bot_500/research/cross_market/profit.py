"""Portfolio P&L of the RSI2 dip rule on US500 + US30 + USTEC (next-open execution, stressed-free base costs).
Each index gets 1/3 of equity x leverage L. Daily mark-to-market; equity compounds."""
import numpy as np, pandas as pd
import xm_lab as X

def positions(sym):
    d, sp = X.load(sym, "D1")
    c, o = d["c"], d["o"]
    s200, s5 = c.rolling(200).mean(), c.rolling(5).mean()
    df = c.diff(); up, dn = df.clip(lower=0).ewm(alpha=.5).mean(), (-df).clip(lower=0).ewm(alpha=.5).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, 1e-12))
    ret = pd.Series(0.0, index=c.index)       # daily return of a 1x position in this index
    i = 200
    while i < len(c) - 2:
        if rsi.iloc[i] < 10 and c.iloc[i] > s200.iloc[i]:
            j = i + 1
            while j < len(c) - 2 and j - i < 10 and c.iloc[j] <= s5.iloc[j]: j += 1
            path = [o.iloc[i + 1]] + list(c.iloc[i + 1:j + 1]) + [o.iloc[j + 1]]
            days = list(c.index[i + 1:j + 2])
            for k in range(1, len(path)):
                ret[days[k - 1]] += path[k] / path[k - 1] - 1
            ret[days[0]] -= sp / o.iloc[i + 1]
            for k in range(i + 1, j + 1):
                ret[c.index[k + 1]] -= (c.index[k + 1] - c.index[k]).days * 0.05 / 365
            i = j + 1
        else:
            i += 1
    return ret

R = pd.DataFrame({s: positions(s) for s in ("US500", "US30", "USTEC")}).fillna(0)
R = R[R.index >= "2013-01-01"]
for L in (1, 2, 3):
    port = (R * L / 3).sum(1)
    eq = (1 + port).cumprod()
    dd = (eq / eq.cummax() - 1)
    yr = (1 + port).groupby(port.index.year).prod() - 1
    cagr = eq.iloc[-1] ** (365.25 / (port.index[-1] - port.index[0]).days) - 1
    print(f"\nleverage {L}x (each index {L/3:.2f}x of equity): CAGR {cagr*100:+.1f}%  max drawdown {dd.min()*100:.1f}%  "
          f"$10,000 -> ${10000*eq.iloc[-1]:,.0f}  worst day {port.min()*100:.1f}%")
    print("  " + "  ".join(f"{y}:{v*100:+.1f}%" for y, v in yr.items()))
