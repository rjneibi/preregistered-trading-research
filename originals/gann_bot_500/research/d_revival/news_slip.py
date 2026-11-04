"""NFP pre-range breakout: slippage stress + per-year + risk in $."""
import numpy as np, datetime as dt
import news_lab as N
T, O, H, L, C = N.T, N.O, N.H, N.L, N.C

def brk(i0, hold, slip, sp_news, pre=30, cap=60, worst_both=True):
    hi, lo = H[i0 - pre:i0].max(), L[i0 - pre:i0].min()
    for j in range(i0, i0 + cap):
        up, dn = H[j] + sp_news >= hi, L[j] <= lo
        if not (up or dn):
            continue
        if up and dn and worst_both:
            return -1.0 - 2 * slip / (hi - lo + sp_news), hi - lo
        sgn = 1 if up else -1
        fill = (max(hi, O[j] + sp_news) + slip) if sgn == 1 else (min(lo, O[j]) - slip)
        stop = lo if sgn == 1 else hi + 0.35
        risk = sgn * (fill - stop)
        for x in range(j, j + hold):
            adv = L[x] if sgn == 1 else H[x] + 0.35
            if sgn * (adv - stop) <= 0:
                s2 = slip if x < i0 + 15 else 0
                px = (min(stop, O[x]) if x > j else stop) - s2 if sgn == 1 else (max(stop, O[x] + .35) if x > j else stop) + s2
                return sgn * (px - fill) / risk, risk
        ex = C[j + hold] if sgn == 1 else C[j + hold] + 0.35
        return sgn * (ex - fill) / risk, risk
    return None, None

ev = [N.at(N.bt(d_, 15, 30)) for d_, _, _ in N.EVENTS["NFP"]]
days = [d_ for d_, _, _ in N.EVENTS["NFP"]]
for slip in (0, 0.5, 1, 2, 3, 5):
    for sp in (0.8, 2.0):
        res = [brk(i, 120, slip, sp) for i in ev]
        r = np.array([x[0] for x in res if x[0] is not None])
        gl = -r[r < 0].sum()
        h = len(r) // 2
        pf = lambda a: a[a > 0].sum() / -a[a < 0].sum()
        print(f"slip ${slip:3.1f} spread ${sp:.1f}: n={len(r)} win={np.mean(r>0):.0%} PF={r[r>0].sum()/gl:4.2f} avg={r.mean():+.3f}R  halves {pf(r[:h]):.2f}/{pf(r[h:]):.2f}")
res = [brk(i, 120, 1.0, 2.0) for i in ev]
print("\nper year (slip $1, spread $2):  n  sumR  median risk$")
ys = {}
for d_, (r, rk) in zip(days, res):
    if r is not None: ys.setdefault(d_.year, []).append((r, rk))
for y, v in sorted(ys.items()):
    print(f"  {y} {len(v):3d} {sum(a for a,_ in v):+6.2f}  {np.median([b for _,b in v]):6.2f}")
