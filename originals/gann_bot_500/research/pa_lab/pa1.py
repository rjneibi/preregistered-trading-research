"""PA-15/30 (2026-10-22): user asked to backtest price action on the 15 and 30 minute charts, "for at least
5 profit". Pre-declared before any result was looked at.

Data: XAU M15 2022-07-11..2026-10-12 (ta_lab/data/XAU_M15.npy, MT5 broker bars, ~100k). M30 = M15 pairs
aggregated on the half hour. Spread = bar spread, floor $0.22. Halves: H1 before 2024-09-01, H2 after.

Setups, all judged on CLOSED bars, entry at the next bar's open (buy at ask, sell at bid):
  PIN   rejection bar: one wick >= 2/3 of the range, range >= ATR14. Long wick below -> buy, above -> sell.
        Stop beyond the wick +$0.50.
  ENG   engulfing: body opposite to the previous bar's and covering it, range >= ATR14. Stop beyond the
        two bars' extreme +$0.50.
  IB    inside bar: bar inside the previous (mother) bar; stop-entry on a break of the mother high/low within
        the next 3 bars (first side touched); stop at the other side of the mother bar.
  BO20  close above the last 20 bars' high (buy) / below their low (sell). Stop = entry -/+ 1 ATR14.
Exits: take profit at +$5 (PRIMARY, the user's "at least 5") or +$10 (second spec); stop as above;
  stop distance below $2 -> $2, above $15 -> trade skipped; 24 h time stop. A bar touching both stop and
  target counts as the STOP (pessimistic). One trade at a time per setup and timeframe.
Random twin: 1000 runs; every trade keeps its bar, stop distance and target, direction by coin flip.
PASS (per setup x timeframe x target, 16 tests): n >= 150, net > 0 and PF >= 1.2 in BOTH halves, beats
  >= 95% of its twins, and t >= 3.0 (multiple-test bar for 16 tests).
Blind prediction (Claude): all 16 FAIL; PF 0.85-1.05; the $5 target loses to spread + losers bigger than $5.

    python pa1.py
"""
import os
import sys
from datetime import datetime, timezone

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SPLIT = int(datetime(2024, 9, 1, tzinfo=timezone.utc).timestamp())


def load():
    A = np.load(os.path.join(HERE, "..", "ta_lab", "data", "XAU_M15.npy"))
    m15 = dict(t=A["time"].astype(np.int64), o=A["open"].astype(float), h=A["high"].astype(float),
               l=A["low"].astype(float), c=A["close"].astype(float), sp=np.maximum(A["spread"] * 0.01, 0.22))
    g = m15["t"] // 1800
    starts = np.r_[0, np.flatnonzero(np.diff(g)) + 1]
    ends = np.r_[starts[1:], len(g)]
    m30 = dict(t=g[starts] * 1800, o=m15["o"][starts], c=m15["c"][ends - 1],
               h=np.maximum.reduceat(m15["h"], starts), l=np.minimum.reduceat(m15["l"], starts),
               sp=np.maximum.reduceat(m15["sp"], starts))
    return {"M15": m15, "M30": m30}


def atr(D, n=14):
    pc = np.r_[D["c"][0], D["c"][:-1]]
    tr = np.maximum(D["h"], pc) - np.minimum(D["l"], pc)
    tr = np.maximum(tr, D["h"] - D["l"])
    out = np.full(len(tr), np.nan)
    k = np.convolve(tr, np.ones(n) / n, "valid")
    out[n - 1:] = k
    return out


def signals(D, name):
    """[(i_entry_bar, sgn, stop_price or None, entry_kind, level)] - i = bar whose OPEN is the entry."""
    o, h, l, c = D["o"], D["h"], D["l"], D["c"]
    A = atr(D)
    rng = h - l
    out = []
    N = len(o)
    if name == "PIN":
        up, lo_w = h - np.maximum(o, c), np.minimum(o, c) - l
        for i in range(20, N - 1):
            if not rng[i] >= A[i] > 0:
                continue
            if lo_w[i] >= 2 / 3 * rng[i]:
                out.append((i + 1, 1, l[i] - 0.5, "mkt", None))
            elif up[i] >= 2 / 3 * rng[i]:
                out.append((i + 1, -1, h[i] + 0.5, "mkt", None))
    elif name == "ENG":
        for i in range(20, N - 1):
            if not rng[i] >= A[i] > 0:
                continue
            b0, b1 = c[i - 1] - o[i - 1], c[i] - o[i]
            if b0 < 0 < b1 and c[i] >= o[i - 1] and o[i] <= c[i - 1]:
                out.append((i + 1, 1, min(l[i], l[i - 1]) - 0.5, "mkt", None))
            elif b1 < 0 < b0 and c[i] <= o[i - 1] and o[i] >= c[i - 1]:
                out.append((i + 1, -1, max(h[i], h[i - 1]) + 0.5, "mkt", None))
    elif name == "IB":
        for i in range(20, N - 4):
            if not (h[i] < h[i - 1] and l[i] > l[i - 1]):
                continue
            mh, ml = h[i - 1], l[i - 1]
            for j in range(i + 1, i + 4):
                up_hit, dn_hit = h[j] >= mh, l[j] <= ml
                if up_hit and dn_hit:
                    break                                   # both sides in one bar: unknown order, no trade
                if up_hit:
                    out.append((j, 1, ml, "stop", mh)); break
                if dn_hit:
                    out.append((j, -1, mh, "stop", ml)); break
    elif name == "BO20":
        for i in range(21, N - 1):
            if not A[i] > 0:
                continue
            hh, ll = h[i - 20:i].max(), l[i - 20:i].min()
            if c[i] > hh:
                out.append((i + 1, 1, None, "mkt", A[i]))
            elif c[i] < ll:
                out.append((i + 1, -1, None, "mkt", A[i]))
    return out


def walk(D, i, sgn, entry, dist, tp, bar_s):
    """Entry on bar i at `entry`; -> ($ per 1 lot, exit bar)."""
    h, l, sp, o = D["h"], D["l"], D["sp"], D["o"]
    end = min(i + int(24 * 3600 / bar_s), len(o) - 1)
    stop, tgt = entry - sgn * dist, entry + sgn * tp
    if sgn == 1:
        sh = l[i:end + 1] <= stop
        th = h[i:end + 1] >= tgt
    else:
        sh = h[i:end + 1] + sp[i:end + 1] >= stop
        th = l[i:end + 1] + sp[i:end + 1] <= tgt
    ks = np.argmax(sh) if sh.any() else None
    kt = np.argmax(th) if th.any() else None
    if ks is not None and (kt is None or ks <= kt):
        return -dist * 100, i + ks
    if kt is not None:
        return tp * 100, i + kt
    xp = o[end] if sgn == 1 else o[end] + sp[end]
    return sgn * (xp - entry) * 100, end


def run(D, name, tp, bar_s):
    trades, busy = [], -1
    for i, sgn, stp, kind, lvl in signals(D, name):
        if i <= busy or i >= len(D["o"]) - 2:
            continue
        if kind == "stop":
            entry = (lvl + D["sp"][i]) if sgn == 1 else lvl
            entry = max(entry, D["o"][i] + D["sp"][i]) if sgn == 1 else min(entry, D["o"][i])   # gap through
        else:
            entry = D["o"][i] + D["sp"][i] if sgn == 1 else D["o"][i]
        dist = (sgn * (entry - stp)) if stp is not None else lvl
        if dist > 15:
            continue
        dist = max(dist, 2.0)
        p, k = walk(D, i, sgn, entry, dist, tp, bar_s)
        trades.append(dict(i=i, t=int(D["t"][i]), sgn=sgn, entry=entry, dist=dist, p=p))
        busy = k
    return trades


def stats(p):
    p = np.asarray(p, float)
    if not len(p):
        return dict(n=0, net=0, pf=0, win=0, t=0)
    w, l = p[p > 0].sum(), -p[p < 0].sum()
    t = p.mean() / (p.std(ddof=1) / np.sqrt(len(p))) if len(p) > 2 and p.std() > 0 else 0
    return dict(n=len(p), net=p.sum(), pf=w / l if l else 99, win=(p > 0).mean(), t=t)


def twin(D, trades, tp, bar_s, runs=1000, seed=20261022):
    alt = []
    for tr in trades:
        s = -tr["sgn"]; i = tr["i"]
        e = D["o"][i] + D["sp"][i] if s == 1 else D["o"][i]
        alt.append(walk(D, i, s, e, tr["dist"], tp, bar_s)[0])
    a, b = np.array([tr["p"] for tr in trades]), np.array(alt)
    rng = np.random.default_rng(seed)
    return np.array([np.where(rng.random(len(a)) < 0.5, b, a).sum() for _ in range(runs)])


def main():
    data = load()
    print(f"M15 {len(data['M15']['t'])} bars, M30 {len(data['M30']['t'])} bars, "
          f"{datetime.fromtimestamp(data['M15']['t'][0], timezone.utc):%Y-%m-%d}..{datetime.fromtimestamp(data['M15']['t'][-1], timezone.utc):%Y-%m-%d}")
    print(f"{'test':16s} {'n':>5s} {'net$/lot':>10s} {'PF':>5s} {'win':>5s} {'t':>5s} | {'H1 net':>8s} {'PF':>5s} | {'H2 net':>8s} {'PF':>5s} | twin% | verdict")
    for tf, bar_s in (("M15", 900), ("M30", 1800)):
        D = data[tf]
        for name in ("PIN", "ENG", "IB", "BO20"):
            for tp in (5.0, 10.0):
                tr = run(D, name, tp, bar_s)
                p = np.array([x["p"] for x in tr]); h2 = np.array([x["t"] >= SPLIT for x in tr])
                s, s1, s2 = stats(p), stats(p[~h2]), stats(p[h2])
                tw = twin(D, tr, tp, bar_s)
                beat = float(np.mean(tw < p.sum()))
                ok = (s["n"] >= 150 and s1["net"] > 0 and s2["net"] > 0 and s1["pf"] >= 1.2 and s2["pf"] >= 1.2
                      and beat >= 0.95 and s["t"] >= 3.0)
                print(f"{tf} {name:4s} TP${tp:<4.0f}  {s['n']:5d} {s['net']:+10.0f} {s['pf']:5.2f} {s['win']:5.0%} {s['t']:+5.1f} | "
                      f"{s1['net']:+8.0f} {s1['pf']:5.2f} | {s2['net']:+8.0f} {s2['pf']:5.2f} | {beat:5.0%} | {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
