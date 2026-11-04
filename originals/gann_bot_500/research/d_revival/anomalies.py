"""BOT-LAB-1 part D: documented gold anomalies on daily/hourly bars, net of costs.
TSMOM: hold long/short by sign of the N-day return (or close vs SMA N), rebalance daily at broker
00:00 (enter at the next day's open), cost = $0.35 per change of side + swap ignored.
Session drift: long from broker hour a to hour b every weekday."""
import numpy as np, sim, data, datetime as dt
d = data.load(); D1 = sim.Bars(d, 86400); H1 = sim.Bars(d, 3600)
o, c = D1.o, D1.c
yrs = np.array([dt.datetime.fromtimestamp(int(t), dt.timezone.utc).year for t in D1.t])
def report(lab, pnl, unit):
    # pnl per day in $/oz; report Sharpe-like and halves
    r = pnl / unit
    h = len(r) // 2
    sh = lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() else 0
    eq = np.cumsum(pnl); dd = (np.maximum.accumulate(eq) - eq).max()
    print(f"{lab:30s} total ${pnl.sum():8.0f}/oz  sharpe {sh(r):+.2f}  halves {sh(r[:h]):+.2f} / {sh(r[h:]):+.2f}  maxDD ${dd:.0f}")
# buy & hold reference
bh = c[1:] - c[:-1]
report("buy & hold", bh, c[:-1])
for n in (20, 50, 100, 200):
    for kind in ("ret", "sma"):
        pos = np.zeros(len(c))
        for i in range(n, len(c)):
            pos[i] = np.sign(c[i] - c[i - n]) if kind == "ret" else np.sign(c[i] - c[i - n + 1:i + 1].mean())
        # position decided at close i, applied over day i+1 (open i+1 -> close i+1) + overnight
        pnl = pos[:-1] * (c[1:] - c[:-1])
        cost = np.abs(np.diff(np.r_[0, pos[:-1]])) * 0.35
        report(f"TSMOM {kind}{n}", pnl - cost, c[:-1])
        # short-only removed: long-only version
        pl = np.maximum(pos[:-1], 0) * (c[1:] - c[:-1]) - np.abs(np.diff(np.r_[0, np.maximum(pos[:-1], 0)])) * 0.35
        report(f"   long-only {kind}{n}", pl, c[:-1])
# session drift, by broker hour blocks (broker 01-09 ~ Asia, 09-15 London, 15-23 NY)
hr = (H1.t // 3600) % 24
for a_, b_, lab in [(1, 9, "Asia 01-09"), (9, 15, "London 09-15"), (15, 23, "NY 15-23"), (19, 1, "late+open 19-01")]:
    sel = (hr >= a_) & (hr < b_) if a_ < b_ else ((hr >= a_) | (hr < b_))
    ret = (H1.c - H1.o)[sel]
    days = (H1.t[sel] // 86400)
    s = np.bincount(days - days.min(), weights=ret); s = s[s != 0] - 0.35
    report(f"long {lab}", s, np.full(len(s), 1.0) * np.mean(H1.c))
