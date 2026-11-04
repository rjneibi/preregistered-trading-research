"""OWN-SWEEP (2026-10-14, descriptive): the stop-hunt question on the user's OWN bot (flip_bot v1.2 conviction
entries, EXIT-2 entry code, 2010-2026 M1). Simplified exit: stop m*ATR, TP 0.8 ATR, 24h close (no derisk/bail).
Equal risk: results in R (stop distance), cost $0.50/oz. Twins: 20 random-time/random-side sets (EXIT-2 twins)."""
import io, contextlib
import numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    import exit2 as X
t, o, h, l, c, H = X.t, X.o, X.h, X.l, X.c, X.H


def trade(i, sgn, A, m, tp=0.8):
    k = H["i0"][i + 1]; px = o[k]
    end = min(np.searchsorted(t, t[k] + 86400), len(t))
    fav = (h[k:end] - px) if sgn > 0 else (px - l[k:end])
    adv = (px - l[k:end]) if sgn > 0 else (h[k:end] - px)
    s = np.flatnonzero(adv >= m * A); s = s[0] if len(s) else 10**9
    p = np.flatnonzero(fav >= tp * A); p = p[0] if len(p) else 10**9
    if s <= p and s < 10**9:                                     # stop first on a shared bar
        back = bool((fav[s + 1:] >= m * A).any())
        return -m * A, True, back, int(t[k]), A
    if p < 10**9:
        return tp * A, False, False, int(t[k]), A
    return sgn * (c[end - 1] - px), False, False, int(t[k]), A


E = X.entries()
E = [e for e in E if e[0] + 1 < len(H["i0"])]
TW = [[e for e in X.twins(E, s) if e[0] + 1 < len(H["i0"])] for s in range(20)]
print(f"own-bot entries: {len(E)}")
for m in (1.2, 2.4, 3.6, 4.8):
    r = [trade(i, s, A, m) for i, s, A, _ in E]
    R = np.array([(x[0] - 0.5) / (m * x[4]) for x in r]); yrs = np.array([x[3] for x in r])
    ns = sum(x[1] for x in r); nb = sum(x[2] for x in r)
    tw = [trade(i, s, A, m) for T in TW for i, s, A, _ in T]
    twR = np.mean([(x[0] - 0.5) / (m * x[4]) for x in tw]); tws = sum(x[1] for x in tw); twb = sum(x[2] for x in tw)
    eq = np.cumsum(R); dd = (np.maximum.accumulate(eq) - eq).max()
    half = yrs < 1514764800
    print(f"stop {m:.1f} ATR{' (live)' if m == 2.4 else '       '}  avg {R.mean():+.3f}R  (2010-17 {R[half].mean():+.3f}, 2018-26 {R[~half].mean():+.3f})"
          f"  win {np.mean(R > 0):3.0%}  maxDD {dd:5.1f}R  twin {twR:+.3f}R  |  stop-outs {ns}, then went +stop {nb / max(ns,1):3.0%}"
          f"  (twins {twb / max(tws,1):3.0%})")
