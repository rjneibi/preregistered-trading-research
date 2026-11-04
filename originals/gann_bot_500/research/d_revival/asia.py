"""Asia-session long: per-day trades, broker 01:00 open -> 09:00 open (exit at hour b open)."""
import numpy as np, sim, data, datetime as dt, sys
d = data.load(); T, O, C = d["t"], d["o"], d["c"]
D1 = sim.Bars(d, 86400)
sma = lambda n: np.array([D1.c[max(0, i - n + 1):i + 1].mean() for i in range(len(D1.c))])
S50, S200 = sma(50), sma(200)
def day_trades(a, b, sp, side=1, filt=None):
    out = []
    for k in range(200, len(D1.t)):
        day0 = int(D1.t[k])
        wd = dt.datetime.fromtimestamp(day0, dt.timezone.utc).weekday()
        if wd >= 5: continue
        i = np.searchsorted(T, day0 + a * 3600); j = np.searchsorted(T, day0 + b * 3600)
        if i >= len(T) or j >= len(T) or T[i] - (day0 + a * 3600) > 1800 or j <= i: continue
        s = side
        if filt == "sma50": s = side if D1.c[k - 1] > S50[k - 1] else -side
        if filt == "sma50_only": 
            if (D1.c[k - 1] > S50[k - 1]) != (side == 1): continue
        if filt == "sma200_only":
            if (D1.c[k - 1] > S200[k - 1]) != (side == 1): continue
        out.append((day0, s * (O[j] - O[i]) - sp))
    return out
def rep(lab, tr):
    r = np.array([x[1] for x in tr]); h = len(r) // 2
    pf = lambda x: x[x > 0].sum() / -x[x < 0].sum()
    eq = np.cumsum(r); dd = (np.maximum.accumulate(eq) - eq).max()
    print(f"{lab:34s} n={len(r)} win={np.mean(r>0):.0%} PF={pf(r):.2f} halves {pf(r[:h]):.2f}/{pf(r[h:]):.2f} total ${r.sum():.0f}/oz DD ${dd:.0f}")
    return r
if __name__ == '__main__':
    for sp in (0.35, 0.60):
        rep(f"long 01-09 spread {sp}", day_trades(1, 9, sp))
    rep("long 01-05", day_trades(1, 5, .35)); rep("long 05-09", day_trades(5, 9, .35)); rep("long 03-09", day_trades(3, 9, .35))
    rep("long 01-09 only above SMA50", day_trades(1, 9, .35, filt="sma50_only"))
    rep("long 01-09 only above SMA200", day_trades(1, 9, .35, filt="sma200_only"))
    rep("short 01-09 only below SMA50", day_trades(1, 9, .35, side=-1, filt="sma50_only"))
    rep("short NY 15-23", day_trades(15, 23, .35, side=-1))
    rep("short NY 15-23 only below SMA50", day_trades(15, 23, .35, side=-1, filt="sma50_only"))
    tr = day_trades(1, 9, .35)
    print("\nper year long 01-09 (spread .35): n win PF $/oz | buy&hold $/oz")
    ys = {}
    for t, r in tr: ys.setdefault(dt.datetime.fromtimestamp(t, dt.timezone.utc).year, []).append(r)
    for y, v in sorted(ys.items()):
        v = np.array(v); m = [k for k in range(len(D1.t)) if dt.datetime.fromtimestamp(int(D1.t[k]), dt.timezone.utc).year == y]
        print(f"  {y} {len(v):4d} {np.mean(v>0):.0%} {v[v>0].sum()/-v[v<0].sum():5.2f} {v.sum():+7.0f} | {D1.c[m[-1]]-D1.o[m[0]]:+7.0f}")
