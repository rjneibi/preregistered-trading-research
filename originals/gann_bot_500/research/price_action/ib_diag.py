"""PA-1 diagnostic (not a gate): D1 inside-bar breakout split by side and year."""
import io, contextlib, datetime as dt
import numpy as np
import pa1 as P
tr = P.trades(24, "IB"); res = P.run(tr)
r = np.array([(p - P.COST) / rk for _, p, rk in res]); s = np.array([x[1] for x in tr])
yr = np.array([dt.datetime.utcfromtimestamp(x[0]).year for x in res])
print(f"long n{(s>0).sum()} {r[s>0].mean():+.3f}R  short n{(s<0).sum()} {r[s<0].mean():+.3f}R")
print("by year R sum:", " ".join(f"{y%100:02d}:{r[yr==y].sum():+.1f}" for y in np.unique(yr)))
eq = np.cumsum(r); print(f"total {r.sum():+.1f}R over {len(r)} trades, maxDD {(np.maximum.accumulate(eq)-eq).max():.1f}R, trades/yr {len(r)/16.7:.0f}")
