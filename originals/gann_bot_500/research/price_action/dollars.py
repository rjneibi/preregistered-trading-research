"""Inside-bar 2025+ in dollars at a fixed 0.1 lot (10 oz gold). Descriptive."""
import datetime as dt
import numpy as np
import pa1 as P
T0 = 1735689600
for tf in (4, 24):
    tr = [x for x in P.trades(tf, "IB") if P.t[x[0]] >= T0]
    pnl = []; mon = {}
    for k, sgn, entry, risk, tend, fb in tr:
        p, ex = P.walk(k, sgn, entry, risk, tend, fb)
        n = int((P.t[ex] - P.t[k]) // 86400)
        usd = 10 * (p - P.COST + n * (-0.126 if sgn > 0 else -0.046))
        pnl.append(usd)
        m = dt.datetime.utcfromtimestamp(int(P.t[k])).strftime("%Y-%m"); mon[m] = mon.get(m, 0) + usd
    pnl = np.array(pnl); eq = np.cumsum(pnl); risk = np.array([x[3] for x in tr]) * 10
    w, l = pnl[pnl > 0], pnl[pnl < 0]
    print(f"{'H4' if tf == 4 else 'D1'}: {len(pnl)} trades, total ${pnl.sum():+,.0f}, avg ${pnl.mean():+.0f}/trade, "
          f"avg risk ${risk.mean():.0f}/trade, win {np.mean(pnl > 0):.0%}, avg win ${w.mean():+.0f}, avg loss ${l.mean():+.0f}, "
          f"worst drawdown ${(np.maximum.accumulate(eq) - eq).max():,.0f}")
    v = np.array(list(mon.values()))
    print(f"   months: {len(v)}, positive {np.sum(v > 0)}, avg ${v.mean():+.0f}/month, best ${v.max():+.0f}, worst ${v.min():+.0f}")
    print("   " + " ".join(f"{k[2:]}:{v:+.0f}" for k, v in mon.items()))
