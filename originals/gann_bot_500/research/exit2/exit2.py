"""EXIT-2 (see PREREG.md, frozen before this file ran): flip_bot v1.2 conviction entries, six
profit-side exits. Walks every trade on M1. Prints the gate table and writes exit2_trades.csv."""
import datetime as dt
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "d_revival"))
from data import load  # noqa: E402

COST, STRESS = 0.50, 1.00
D = 86400
VARIANTS = {   # name: (tp_atr or None, max_hours, trail)
    "E0": (0.8, 24, False), "E1": (None, 24, False), "E2": (None, 72, False),
    "E3": (None, 120, True), "E4": (0.8, 240, False), "E5": (2.4, 72, False),
}


def us_dst(y):
    mar = dt.date(y, 3, 1); nov = dt.date(y, 11, 1)
    s = mar + dt.timedelta(days=(6 - mar.weekday()) % 7 + 7)
    e = nov + dt.timedelta(days=(6 - nov.weekday()) % 7)
    return int(dt.datetime(y, s.month, s.day, tzinfo=dt.timezone.utc).timestamp()), \
        int(dt.datetime(y, e.month, e.day, tzinfo=dt.timezone.utc).timestamp())


def to_utc(tb):
    off = np.full(len(tb), 2 * 3600, dtype=np.int64)
    for y in range(2009, 2028):
        s, e = us_dst(y)
        off[(tb >= s) & (tb < e)] = 3 * 3600
    return tb - off


m = load()
t = to_utc(m["t"]); o, h, l, c = m["o"], m["h"], m["l"], m["c"]
assert np.all(np.diff(t) > 0)
# ---- UTC H1
hk = t // 3600
starts = np.flatnonzero(np.diff(hk, prepend=hk[0] - 1))
H = dict(k=hk[starts], i0=starts, o=o[starts], h=np.maximum.reduceat(h, starts),
         l=np.minimum.reduceat(l, starts), c=c[np.r_[starts[1:] - 1, len(t) - 1]])
nH = len(H["k"])
pc = np.r_[H["c"][0], H["c"][:-1]]
tr = np.maximum(H["h"] - H["l"], np.maximum(abs(H["h"] - pc), abs(H["l"] - pc)))
atr = np.empty(nH); atr[:14] = tr[:14].mean()
for i in range(14, nH):
    atr[i] = atr[i - 1] + (tr[i] - atr[i - 1]) / 14
# ---- UTC days
dk = H["k"] // 24
dstarts = np.flatnonzero(np.diff(dk, prepend=dk[0] - 1))
dends = np.r_[dstarts[1:], nH]


def entries():
    out = []
    for j in range(1, len(dstarts)):
        a, b = dstarts[j], dends[j]
        pa, pb = dstarts[j - 1], dends[j - 1]
        if pb - pa < 12:
            continue
        day = int(dk[a])
        if dt.datetime.fromtimestamp(day * D, dt.timezone.utc).weekday() == 0:
            continue
        ph, pl, pcl = H["h"][pa:pb].max(), H["l"][pa:pb].min(), H["c"][pb - 1]
        pp = (ph + pl + pcl) / 3
        r3, s3 = pp + (ph - pl), pp - (ph - pl)
        # "dead": crossed by any of the last 10 UTC-H4 closes completed before today 08:00 UTC
        kk = H["k"]; sel = np.flatnonzero((kk < day * 24 + 8) & ((kk + 1) % 4 == 0))[-10:]
        h4c = H["c"][sel]
        dead = {1: bool((h4c > r3).any()), -1: bool((h4c < s3).any())}
        done = set()
        for i in range(a, b):
            hr = int(H["k"][i] % 24) + 1                    # close hour of this H1 bar
            if hr not in (12, 16, 20):
                continue
            for sgn, lvl in ((1, r3), (-1, s3)):
                if sgn in done or dead[sgn]:
                    continue
                if (H["c"][i] > lvl) if sgn > 0 else (H["c"][i] < lvl):
                    med = np.median(atr[max(0, i - 90 * 24):i + 1])
                    out.append((i, sgn, float(atr[i]), bool(atr[i] > med)))
                    done.add(sgn)
    return out


def walk(i, sgn, A, hivol, var):
    """M1 walk from the open of the M1 bar after H1 bar i. Same-bar order: stop, derisk, bail, TP.
    Returns ($/oz pnl before cost, exit time)."""
    tp_atr, max_h, trail = VARIANTS[var]
    k = H["i0"][i + 1]
    px, t0 = o[k], t[k]
    end = min(np.searchsorted(t, t0 + max_h * 3600), len(t))
    if end <= k:
        end = k + 1
    lo, hi, op, tt = l[k:end], h[k:end], o[k:end], t[k:end]
    fav = hi if sgn > 0 else lo
    adv = sgn * (px - (lo if sgn > 0 else hi))
    stop = np.full(end - k, px - sgn * 2.4 * A)
    if trail:
        best = np.maximum.accumulate(fav) if sgn > 0 else np.minimum.accumulate(fav)
        prev = np.r_[px, best[:-1]]                       # stop moves at the END of a bar
        armed = np.maximum.accumulate(sgn * (prev - px) >= 1.0 * A)
        tl = np.maximum(px, prev - 2.4 * A) if sgn > 0 else np.minimum(px, prev + 2.4 * A)
        stop = np.where(armed, np.maximum(stop, tl) if sgn > 0 else np.minimum(stop, tl), stop)
    hit_s = (lo <= stop) if sgn > 0 else (hi >= stop)
    BIG = end - k + 5
    first = lambda m: int(np.argmax(m)) if m.any() else BIG
    qs = first(hit_s)
    qb = BIG if hivol else first((tt - t0 >= 8 * 3600) & (adv >= 1.0 * A))
    qp = BIG if tp_atr is None else first(sgn * (fav - px) >= tp_atr * A)
    qd = first(adv >= 1.2 * A) if hivol else BIG
    q = min(qs, qb, qp)
    pnl, rem = 0.0, 1.0
    if qd < q:                                            # half out at -1.2 ATR, stop untouched
        pnl, rem = -0.5 * 1.2 * A, 0.5
    if q >= BIG:
        return pnl + rem * sgn * (c[end - 1] - px), t[end - 1]
    if q == qs:
        st = stop[q]
        fill = op[q] if (sgn > 0 and op[q] < st) or (sgn < 0 and op[q] > st) else st
        return pnl + rem * sgn * (fill - px), tt[q]
    if q == qb:
        return pnl + rem * sgn * (c[k + q] - px), tt[q]
    return pnl + rem * tp_atr * A, tt[q]


def run(ents, var):
    res, busy = [], -1
    for i, sgn, A, hv in ents:
        if i + 1 >= nH:
            continue
        k = H["i0"][i + 1]
        if t[k] < busy:
            continue
        pnl, tx = walk(i, sgn, A, hv, var)
        busy = tx
        res.append((int(t[k]), pnl, 2.4 * A))
    return res


def twins(ents, seed):
    rng = np.random.default_rng(seed)
    out = []
    for i, sgn, A, hv in ents:
        day = int(H["k"][i] // 24)
        cand = np.flatnonzero((H["k"] >= day * 24 + 11) & (H["k"] <= day * 24 + 19))
        j = int(rng.choice(cand))
        out.append((j, int(rng.choice([-1, 1])), float(atr[j]), hv))
    return out


WIN = {"A 2010-17": (0, 1514764800), "B 2018-26": (1514764800, 9e9), "C 2023+": (1672531200, 9e9)}


def stat(res, cost, lo=0, hi=9e9):
    r = np.array([(p - cost) / rk for tt, p, rk in res if lo <= tt < hi])
    if len(r) == 0:
        return dict(n=0, avg=np.nan, pf=np.nan, wr=np.nan)
    g, b = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), avg=r.mean(), pf=g / b if b else np.inf, wr=(r > 0).mean(), r=r)


if __name__ == "__main__":
    E = entries()
    print("entries", len(E), "first", dt.datetime.fromtimestamp(int(H["k"][E[0][0]] * 3600), dt.timezone.utc),
          "last", dt.datetime.fromtimestamp(int(H["k"][E[-1][0]] * 3600), dt.timezone.utc))
    TW = [twins(E, s) for s in range(20)]
    real, twin = {}, {}
    for v in VARIANTS:
        real[v] = run(E, v)
        twin[v] = [run(tw, v) for tw in TW]
        print("ran", v, len(real[v]), flush=True)
    rows = []
    for v in VARIANTS:
        line = [v]
        ok = True
        for wn, (lo, hi) in WIN.items():
            s = stat(real[v], COST, lo, hi); s2 = stat(real[v], STRESS, lo, hi); s0 = stat(real["E0"], COST, lo, hi)
            tw = np.mean([stat(x, COST, lo, hi)["avg"] for x in twin[v]])
            g = (v == "E0" or s["avg"] > s0["avg"]) and s["avg"] - tw >= 0.05 and s2["avg"] > 0
            ok &= g and v != "E0"
            line.append(f"{wn}: n{s['n']} avg{s['avg']:+.3f}R PF{s['pf']:.2f} wr{s['wr']:.0%} twin{tw:+.3f} "
                        f"x2cost{s2['avg']:+.3f} {'ok' if g else '--'}")
        s = stat(real[v], COST)
        tws = np.concatenate([stat(x, COST)["r"] for x in twin[v]])
        diff = s["avg"] - tws.mean()
        tstat = diff / np.sqrt(s["r"].var(ddof=1) / len(s["r"]) + tws.var(ddof=1) / len(tws))
        ok &= tstat >= 2
        line.append(f"ALL: n{s['n']} avg{s['avg']:+.3f}R PF{s['pf']:.2f} vs twin t={tstat:+.2f}")
        line.append("PASS" if ok else ("baseline" if v == "E0" else "FAIL"))
        print("\n".join(line[:1] + ["   " + x for x in line[1:]]))
    import csv
    with open(os.path.join(HERE, "exit2_trades.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["variant", "utc_entry", "pnl_per_oz", "risk_per_oz"])
        for v in VARIANTS:
            for row in real[v]:
                w.writerow([v, dt.datetime.fromtimestamp(row[0], dt.timezone.utc).isoformat(), round(row[1], 3),
                            round(row[2], 3)])
