"""EXIT-2 descriptive add-on (not a gate): what the 24h close did to trades that were in profit."""
import numpy as np
import exit2 as X

E = X.entries()
r0 = X.run(E, "E0"); r4 = X.run(E, "E4"); r3 = X.run(E, "E3")
m4 = {tt: (p, rk) for tt, p, rk in r4}
ts_profit = []
for i, sgn, A, hv in E:
    k = X.H["i0"][i + 1]; tt = int(X.t[k])
    p0, ex = X.walk(i, sgn, A, hv, "E0")
    if ex - X.t[k] >= 20 * 3600 and p0 > 0:     # closed by the 24h limit, in profit
        ts_profit.append((tt, p0, m4[tt][0], 2.4 * A))
a = np.array([(p0, p4) for _, p0, p4, _ in ts_profit])
print(f"E0 trades closed by the 24h limit while in profit: {len(a)} of {len(r0)}")
print(f"  avg banked at 24h {a[:,0].mean():+.2f}$/oz; same trades held (E4) {a[:,1].mean():+.2f}$/oz;"
      f" held did better on {(a[:,1] > a[:,0]).mean():.0%}, worse on {(a[:,1] < a[:,0]).mean():.0%}")
big = sorted(r3, key=lambda x: -x[1])[:8]
import datetime as dt
print("biggest let-it-run (E3 trail) winners, $/oz (x10 = pips):")
for tt, p, rk in big:
    print(" ", dt.datetime.fromtimestamp(tt, dt.timezone.utc).date(), f"{p:+.1f}$  = {p/rk:+.1f}R")
r = np.array([(p - 0.5) / rk for _, p, rk in r3])
print(f"E3: trades >= +3R: {(r >= 3).mean():.1%}; they add {r[r>=3].sum():+.0f}R, the rest {r[r<3].sum():+.0f}R")
