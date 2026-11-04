"""PA-1 (PREREG.md frozen before this ran): classic price-action patterns on gold, H1/H4/D1, 2010-2026."""
import datetime as dt
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "d_revival"))
from data import load  # noqa: E402

COST, STRESS, IC = 0.40, 0.80, 0.22
BIGN = 10 ** 9


def us_dst(y):  # same rule as exit2.to_utc
    mar = dt.date(y, 3, 1); nov = dt.date(y, 11, 1)
    s = mar + dt.timedelta(days=(6 - mar.weekday()) % 7 + 7)
    e = nov + dt.timedelta(days=(6 - nov.weekday()) % 7)
    f = lambda d: int(dt.datetime(y, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
    return f(s), f(e)


def to_utc(tb):
    off = np.full(len(tb), 2 * 3600, dtype=np.int64)
    for y in range(2009, 2028):
        s, e = us_dst(y)
        off[(tb >= s) & (tb < e)] = 3 * 3600
    return tb - off


m = load()
t = to_utc(m["t"]); o, h, l, c = m["o"], m["h"], m["l"], m["c"]
N = len(t)


def bars(tf):
    key = t // (tf * 3600)
    st = np.flatnonzero(np.diff(key, prepend=key[0] - 1))
    en = np.r_[st[1:], N]
    hh, ll = np.maximum.reduceat(h, st), np.minimum.reduceat(l, st)   # all groups, then filter
    ok = (en - st) >= (0.5 * tf * 60 if tf < 24 else 600)
    st, en, hh, ll = st[ok], en[ok], hh[ok], ll[ok]
    B = dict(i0=st, o=o[st], h=hh, l=ll, c=c[en - 1])
    pc = np.r_[B["c"][0], B["c"][:-1]]
    tr = np.maximum(B["h"] - B["l"], np.maximum(abs(B["h"] - pc), abs(B["l"] - pc)))
    atr = np.empty(len(st)); atr[:14] = tr[:14].mean()
    for i in range(14, len(st)):
        atr[i] = atr[i - 1] + (tr[i] - atr[i - 1]) / 14
    B["atr"] = atr
    return B


def signals(B, pat):
    """yields (i, sgn, stop level) or (i, 0, (hi, lo)) for OCO breakouts"""
    O, Hh, L, C, A = B["o"], B["h"], B["l"], B["c"], B["atr"]
    for i in range(21, len(O) - 1):
        rng = Hh[i] - L[i]
        if rng <= 0:
            continue
        if pat in ("PIN", "PINX"):
            if rng < 0.5 * A[i]:
                continue
            lw = min(O[i], C[i]) - L[i]; uw = Hh[i] - max(O[i], C[i])
            top, bot = Hh[i] - rng / 3, L[i] + rng / 3
            if lw >= 2 * rng / 3 and min(O[i], C[i]) >= top and (pat == "PIN" or L[i] < L[i - 20:i].min()):
                yield i, 1, L[i]
            elif uw >= 2 * rng / 3 and max(O[i], C[i]) <= bot and (pat == "PIN" or Hh[i] > Hh[i - 20:i].max()):
                yield i, -1, Hh[i]
        elif pat == "ENG":
            if C[i - 1] < O[i - 1] and C[i] > O[i] and O[i] <= C[i - 1] and C[i] >= O[i - 1] and C[i - 1] < C[i - 4]:
                yield i, 1, min(L[i], L[i - 1])
            elif C[i - 1] > O[i - 1] and C[i] < O[i] and O[i] >= C[i - 1] and C[i] <= O[i - 1] and C[i - 1] > C[i - 4]:
                yield i, -1, max(Hh[i], Hh[i - 1])
        elif pat == "IB":
            if Hh[i] < Hh[i - 1] and L[i] > L[i - 1]:
                yield i, 0, (Hh[i - 1], L[i - 1])
        elif pat == "NR7":
            r7 = Hh[i - 6:i + 1] - L[i - 6:i + 1]
            if rng <= r7.min() and (r7 == rng).sum() == 1:
                yield i, 0, (Hh[i], L[i])
        elif pat == "SFP":
            ph, pl = Hh[i - 20:i].max(), L[i - 20:i].min()
            if Hh[i] > ph and C[i] < ph:
                yield i, -1, Hh[i]
            elif L[i] < pl and C[i] > pl:
                yield i, 1, L[i]


def walk(k, sgn, entry, risk, tend, fillbar=False):
    """M1 from index k; returns ($/oz pnl, exit index). Stop first on a shared bar."""
    end = min(np.searchsorted(t, tend), N)
    if end <= k:
        end = k + 1
    stop, tgt = entry - sgn * risk, entry + sgn * 2 * risk
    lo, hi = l[k:end], h[k:end]
    hs = (lo <= stop) if sgn > 0 else (hi >= stop)
    ht = (hi >= tgt) if sgn > 0 else (lo <= tgt)
    if fillbar:
        ht[0] = False                                    # ignore the fill bar's favourable extreme
    qs = int(np.argmax(hs)) if hs.any() else BIGN
    qt = int(np.argmax(ht)) if ht.any() else BIGN
    if qs == BIGN and qt == BIGN:
        return sgn * (c[end - 1] - entry), end - 1
    if qs <= qt:
        op = o[k + qs]
        fill = op if (qs > 0 and ((sgn > 0 and op < stop) or (sgn < 0 and op > stop))) else stop
        return sgn * (fill - entry), k + qs
    return 2 * risk, k + qt


def trades(tf, pat):
    B = bars(tf)
    out, busy = [], -1
    hold = 10 * tf * 3600
    for i, sgn, lv in signals(B, pat):
        k = B["i0"][i + 1]
        if k <= busy:
            continue
        A = B["atr"][i]
        if sgn != 0:
            entry = o[k]
            risk = max(sgn * (entry - lv), 0.25 * A)
            out.append((k, sgn, entry, risk, t[k] + hold, False))
            busy = walk(k, sgn, entry, risk, t[k] + hold)[1]
        else:
            hi_, lo_ = lv
            kend = B["i0"][i + 4] if i + 4 < len(B["i0"]) else N
            uh = np.flatnonzero(h[k:kend] >= hi_); ul = np.flatnonzero(l[k:kend] <= lo_)
            a = uh[0] if len(uh) else BIGN; b = ul[0] if len(ul) else BIGN
            if (a == BIGN and b == BIGN) or a == b:
                continue
            sgn = 1 if a < b else -1
            kk = k + min(a, b)
            lvl = hi_ if sgn > 0 else lo_
            entry = max(o[kk], lvl) if sgn > 0 else min(o[kk], lvl)
            risk = max(sgn * (entry - (lo_ if sgn > 0 else hi_)), 0.25 * A)
            out.append((kk, sgn, entry, risk, t[kk] + hold, True))
            busy = walk(kk, sgn, entry, risk, t[kk] + hold, True)[1]
    return out


def run(tr, flip=None):
    """Twin: same moment, price, risk and exit rules, random direction."""
    res = []
    for j, (k, sgn, entry, risk, tend, fb) in enumerate(tr):
        s = sgn if flip is None else int(flip[j])
        p, _ = walk(k, s, entry, risk, tend, fb)
        res.append((int(t[k]), p, risk))
    return res


WIN = {"A 2010-17": (0, 1514764800), "B 2018-26": (1514764800, 9e9), "C 2023+": (1672531200, 9e9)}


def R(res, cost, lo=0, hi=9e9):
    return np.array([(p - cost) / rk for tt, p, rk in res if lo <= tt < hi])


if __name__ == "__main__":
    for tf in (1, 4, 24):
        for pat in ("PIN", "PINX", "ENG", "IB", "NR7", "SFP"):
            tr = trades(tf, pat)
            real = run(tr)
            rng = np.random.default_rng(11)
            tw = [run(tr, rng.choice([-1, 1], len(tr))) for _ in range(20)]
            ok = True
            cells = []
            for wn, (lo, hi) in WIN.items():
                r = R(real, COST, lo, hi); tws = np.mean([R(x, COST, lo, hi).mean() for x in tw])
                s2 = R(real, STRESS, lo, hi).mean()
                g = r.mean() > 0 and r.mean() - tws >= 0.05 and (not wn.startswith("B") or s2 > 0)
                ok &= g
                cells.append(f"{wn[:1]} n{len(r)} {r.mean():+.3f} tw{tws:+.3f}{'*' if g else ' '}")
            r = R(real, COST); twa = np.concatenate([R(x, COST) for x in tw])
            ts = (r.mean() - twa.mean()) / np.sqrt(r.var(ddof=1) / len(r) + twa.var(ddof=1) / len(twa))
            ok &= ts >= 2.8
            name = {1: "H1", 4: "H4", 24: "D1"}[tf]
            print(f"{name} {pat:5s} n{len(r):5d} gross {R(real, 0).mean():+.3f} IC {R(real, IC).mean():+.3f} "
                  f"net {r.mean():+.3f}R win {np.mean(r > 0):.0%} | " + " | ".join(cells) +
                  f" | t {ts:+.2f} -> {'PASS' if ok else 'FAIL'}", flush=True)
