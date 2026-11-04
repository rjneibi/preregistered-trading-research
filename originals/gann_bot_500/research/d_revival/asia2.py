import numpy as np, asia
for a, b in [(1.0, 9), (1.25, 9), (2, 9), (1.25, 5), (2, 5), (1.25, 7)]:
    for sp in (0.35, 0.6):
        asia.rep(f"long {a:>4}-{b} spread {sp}", asia.day_trades(a, b, sp))
tr = asia.day_trades(1.25, 9, .35)
r = np.array([x[1] for x in tr]); t = np.array([x[0] for x in tr])
for y0, y1 in [(2010, 2014), (2014, 2018), (2018, 2022), (2022, 2027)]:
    import datetime as dt
    s = (t >= dt.datetime(y0, 1, 1, tzinfo=dt.timezone.utc).timestamp()) & (t < dt.datetime(y1, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    x = r[s]; print(f"  {y0}-{y1-1}: n={len(x)} PF={x[x>0].sum()/-x[x<0].sum():.2f} ${x.sum():+.0f}/oz")
