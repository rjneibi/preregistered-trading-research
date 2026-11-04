"""PA-1b (PREREG_IB.md frozen before this ran): D1 inside-bar breakout, unchanged rule, on silver and US indices."""
import datetime as dt
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DD = os.path.join(HERE, "..", "cross_market", "data")
BIGN = 10 ** 9
HOLD = 10 * 86400


def npz(name):
    z = np.load(os.path.join(DD, name + ".npz"))
    return {k: z[k] for k in z.files}


def atr14(B):
    pc = np.r_[B["c"][0], B["c"][:-1]]
    tr = np.maximum(B["h"] - B["l"], np.maximum(abs(B["h"] - pc), abs(B["l"] - pc)))
    a = np.empty(len(tr)); a[:14] = tr[:14].mean()
    for i in range(14, len(tr)):
        a[i] = a[i - 1] + (tr[i] - a[i - 1]) / 14
    return a


def walk(F, k, sgn, entry, risk, tend, fillbar):
    t, o, h, l, c = F["t"], F["o"], F["h"], F["l"], F["c"]
    end = min(np.searchsorted(t, tend), len(t))
    if end <= k:
        end = k + 1
    stop, tgt = entry - sgn * risk, entry + sgn * 2 * risk
    lo, hi = l[k:end], h[k:end]
    hs = (lo <= stop) if sgn > 0 else (hi >= stop)
    ht = (hi >= tgt) if sgn > 0 else (lo <= tgt)
    if fillbar:
        ht = ht.copy(); ht[0] = False
    qs = int(np.argmax(hs)) if hs.any() else BIGN
    qt = int(np.argmax(ht)) if ht.any() else BIGN
    if qs == BIGN and qt == BIGN:
        return sgn * (c[end - 1] - entry), end - 1
    if qs <= qt:
        op = o[k + qs]
        fill = op if (qs > 0 and ((sgn > 0 and op < stop) or (sgn < 0 and op > stop))) else stop
        return sgn * (fill - entry), k + qs
    return 2 * risk, k + qt


def trades(D, F):
    A = atr14(D)
    out, busy_t = [], -1
    for i in range(21, len(D["t"]) - 4):
        if not (D["h"][i] < D["h"][i - 1] and D["l"][i] > D["l"][i - 1]):
            continue
        if D["t"][i + 1] <= busy_t or D["t"][i + 1] < F["t"][0]:
            continue
        hi_, lo_ = D["h"][i - 1], D["l"][i - 1]
        k = np.searchsorted(F["t"], D["t"][i + 1]); kend = np.searchsorted(F["t"], D["t"][i + 4])
        if k >= len(F["t"]) - 1:
            break
        uh = np.flatnonzero(F["h"][k:kend] >= hi_); ul = np.flatnonzero(F["l"][k:kend] <= lo_)
        a = uh[0] if len(uh) else BIGN; b = ul[0] if len(ul) else BIGN
        if (a == BIGN and b == BIGN) or a == b:
            continue
        sgn = 1 if a < b else -1
        kk = k + min(a, b)
        lvl = hi_ if sgn > 0 else lo_
        entry = max(F["o"][kk], lvl) if sgn > 0 else min(F["o"][kk], lvl)
        risk = max(sgn * (entry - (lo_ if sgn > 0 else hi_)), 0.25 * A[i])
        out.append((kk, sgn, entry, risk))
        _, ex = walk(F, kk, sgn, entry, risk, F["t"][kk] + HOLD, True)
        busy_t = F["t"][ex]
    return out


def run(F, tr, cost, swl, sws, flip=None):
    res = []
    for j, (k, sgn, entry, risk) in enumerate(tr):
        s = sgn if flip is None else int(flip[j])
        p, ex = walk(F, k, s, entry, risk, F["t"][k] + HOLD, True)
        nights = int((F["t"][ex] - F["t"][k]) // 86400)
        fin = nights * (swl if s > 0 else sws)                 # swap is signed (negative = you pay)
        res.append((int(F["t"][k]), (p - cost + fin) / risk, s))
    return res


def gold():
    """PA-1 gold D1 IB re-shown with its current swap (-0.126 long / -0.046 short $/oz/night)."""
    import pa1 as P
    tr = P.trades(24, "IB")
    out = []
    for k, sgn, entry, risk, tend, fb in tr:
        p, ex = P.walk(k, sgn, entry, risk, tend, fb)
        n = int((P.t[ex] - P.t[k]) // 86400)
        out.append((int(P.t[k]), (p - P.COST + n * (-0.126 if sgn > 0 else -0.046)) / risk, sgn))
    return out


MKTS = {  # name: (D1 file, fine file, cost = 1.5x median spread, swap long, swap short)
    "XAGUSD": ("XAGUSD_D1", "XAGUSD_H1", None, -0.0023, 0.0002),
    "US500": ("US500_D1", "US500_M1", None, -0.31, -0.26),
    "US30": ("US30_D1", "US30_M1", None, -2.21, -1.99),
    "USTEC": ("USTEC_D1", "USTEC_M1", None, -0.82, -0.75),
}

if __name__ == "__main__":
    pooled, pooled_tw, ok_mk, halves_ok = [], [], 0, True
    for name, (dn, fn, _, swl, sws) in MKTS.items():
        D, F = npz(dn), npz(fn)
        cost = 1.5 * float(np.median(F["sp"]))
        tr = trades(D, F)
        real = run(F, tr, cost, swl, sws)
        rng = np.random.default_rng(11)
        tw = [run(F, tr, cost, swl, sws, rng.choice([-1, 1], len(tr))) for _ in range(20)]
        r = np.array([x[1] for x in real]); s = np.array([x[2] for x in real]); tt = np.array([x[0] for x in real])
        twr = np.concatenate([[x[1] for x in T] for T in tw])
        mid = np.median(tt); h1, h2 = r[tt < mid].mean(), r[tt >= mid].mean()
        halves_ok &= h1 > 0 and h2 > 0
        ok_mk += r.mean() > 0
        pooled.append(r); pooled_tw.append(twr)
        gross = np.array([x[1] for x in run(F, tr, 0.0, 0.0, 0.0)])
        y0, y1 = dt.datetime.utcfromtimestamp(tt[0]).year, dt.datetime.utcfromtimestamp(tt[-1]).year
        print(f"{name:7s} {y0}-{y1} n{len(r):4d} cost {cost:.3f}  gross {gross.mean():+.3f}R  net {r.mean():+.3f}R  twin {twr.mean():+.3f}R  "
              f"halves {h1:+.3f}/{h2:+.3f}  long n{(s > 0).sum()} {r[s > 0].mean():+.3f}  short n{(s < 0).sum()} {r[s < 0].mean():+.3f}  "
              f"win {np.mean(r > 0):.0%}", flush=True)
    P_, T_ = np.concatenate(pooled), np.concatenate(pooled_tw)
    d = P_.mean() - T_.mean()
    ts = d / np.sqrt(P_.var(ddof=1) / len(P_) + T_.var(ddof=1) / len(T_))
    ok = ok_mk >= 3 and d >= 0.05 and ts >= 2.0 and halves_ok
    print(f"POOLED n{len(P_)} net {P_.mean():+.3f}R  twin {T_.mean():+.3f}R  diff {d:+.3f}R  t {ts:+.2f}  "
          f"markets>0 {ok_mk}/4  halves all >0 {halves_ok}  -> {'PASS' if ok else 'FAIL'}")
    g = gold(); gr = np.array([x[1] for x in g]); gs = np.array([x[2] for x in g])
    print(f"GOLD (PA-1 data, with swap) n{len(gr)} net {gr.mean():+.3f}R  long {gr[gs > 0].mean():+.3f}  short {gr[gs < 0].mean():+.3f}")
