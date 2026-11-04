"""SW-1: the classic SWING techniques, one engine, same costs, same gates.  (pre-declared)

Every rule: signal at the daily close i, enter at the next open, exit at the open after the exit
condition (max hold 15 days), spread 1.5x median + 2bp floor, financing 5%/yr long, 1.5%/yr short.
Discovery market US500 (2012+).  PASS on US500 = PF >= 1.15 in both halves, n >= 30 per half, and
random-twin p < 0.005 (0.05 / ~10 rules).  CONFIRMED = also PF > 1.0 on at least 3 of the 4 markets it
never saw (US30, USTEC, IWM, EWA).  The same rules are also run on gold (XAUUSD 2005+) for comparison.

Mean reversion (buy weakness, sell strength):
  MR1 RSI2<10 > SMA200, exit close>SMA5                     (Connors 2008)
  MR2 IBS<0.2 (close in bottom 20% of day's range), exit IBS>0.8 or close>prev high
  MR3 3 down closes in a row > SMA200, exit first up close
  MR4 close < lower Bollinger(20,2) > SMA200, exit close > SMA20
  MR5 "double 7s": close = 7-day low > SMA200, exit close = 7-day high
  MR6 RSI2>90 below SMA200 -> SHORT, exit close<SMA5        (does it work the other way?)
Trend / momentum (buy strength):
  TR1 55-day breakout, exit close < 20-day low               (Turtle style)
  TR2 pullback-in-trend: SMA50>SMA200, close crosses back above EMA20 after >=3 closes below it, exit
      close < SMA50 or +2 ATR
  TR3 52-week-high momentum: close = 252-day high, exit close < SMA50
  TR4 inside-day / NR7 breakout: day range = narrowest of 7, buy if next close > its high, exit 5 days
"""
import numpy as np
import pandas as pd

import xm_lab as X

RNG = np.random.default_rng(11)
MAXH = 15


def prep(sym):
    d, sp = X.load(sym, "D1")
    d = d.copy()
    if sp == 0:
        sp = 0.0002 * d["c"].median()
    c = d["c"]
    d["s5"], d["s20"], d["s50"], d["s200"] = (c.rolling(n).mean() for n in (5, 20, 50, 200))
    d["e20"] = c.ewm(span=20, adjust=False).mean()
    df = c.diff()
    up, dn = df.clip(lower=0).ewm(alpha=.5).mean(), (-df).clip(lower=0).ewm(alpha=.5).mean()
    d["rsi2"] = 100 - 100 / (1 + up / dn.replace(0, 1e-12))
    rng = (d["h"] - d["l"]).replace(0, np.nan)
    d["ibs"] = (c - d["l"]) / rng
    d["bbl"] = d["s20"] - 2 * c.rolling(20).std()
    d["lo7"], d["hi7"] = c.rolling(7).min(), c.rolling(7).max()
    d["hi55"], d["lo20"] = d["h"].rolling(55).max().shift(1), d["l"].rolling(20).min().shift(1)
    d["hi252"] = c.rolling(252).max()
    d["dn3"] = (df < 0).rolling(3).sum() == 3
    tr = pd.concat([d["h"] - d["l"], (d["h"] - c.shift()).abs(), (d["l"] - c.shift()).abs()], axis=1).max(1)
    d["atr"] = tr.rolling(14).mean()
    d["nr7"] = rng == rng.rolling(7).min()
    below = (c < d["e20"]).astype(int)
    d["below_run"] = below.groupby((below != below.shift()).cumsum()).cumsum()
    return d, sp


def rule(name, d):
    """Return (side, entry mask, exit function(i, j) -> bool)."""
    c, up = d["c"].values, (d["c"] > d["s200"]).values
    g = lambda k: d[k].values
    if name == "MR1":
        return 1, (g("rsi2") < 10) & up, lambda i, j: c[j] > g("s5")[j]
    if name == "MR2":
        return 1, g("ibs") < 0.2, lambda i, j: g("ibs")[j] > 0.8 or c[j] > g("h")[j - 1]
    if name == "MR3":
        return 1, g("dn3") & up, lambda i, j: c[j] > c[j - 1]
    if name == "MR4":
        return 1, (c < g("bbl")) & up, lambda i, j: c[j] > g("s20")[j]
    if name == "MR5":
        return 1, (c <= g("lo7")) & up, lambda i, j: c[j] >= g("hi7")[j]
    if name == "MR6":
        return -1, (g("rsi2") > 90) & ~up & (g("s200") > 0), lambda i, j: c[j] < g("s5")[j]
    if name == "TR1":
        return 1, c > g("hi55"), lambda i, j: c[j] < g("lo20")[j]
    if name == "TR2":
        prev_run = np.r_[0, g("below_run")[:-1]]
        sig = (g("s50") > g("s200")) & (c > g("e20")) & (prev_run >= 3)
        return 1, sig, lambda i, j: c[j] < g("s50")[j] or c[j] > c[i] + 2 * g("atr")[i]
    if name == "TR3":
        return 1, (c >= g("hi252")) & (g("s200") > 0), lambda i, j: c[j] < g("s50")[j]
    if name == "TR4":
        nr = np.r_[False, g("nr7")[:-1]]
        sig = nr & (c > np.r_[np.nan, g("h")[:-1]])
        return 1, sig, lambda i, j: j - i >= 5
    raise KeyError(name)


def run(d, sp, side, sig, ex, fin_l=0.05, fin_s=0.015, maxh=MAXH):
    o, idx = d["o"].values, d.index
    sig = np.nan_to_num(sig.astype(float)).astype(bool)
    sig[:252] = False
    out, i, n = [], 0, len(d)
    while i < n - 2:
        if sig[i]:
            j = i + 1
            while j < n - 2 and j - i < maxh and not ex(i, j):
                j += 1
            pin, pout = o[i + 1], o[j + 1]
            nights = (idx[j + 1] - idx[i + 1]).days
            r = side * (pout / pin - 1) - sp / pin - nights * (fin_l if side > 0 else fin_s) / 365
            out.append((idx[i], r, j - i))
            i = j + 1
        else:
            i += 1
    return out


def twin_p(d, sp, side, trades, k=2000):
    """Random entries (any day after warm-up) with the same hold lengths: how often >= the rule's mean."""
    o, idx = d["o"].values, d.index
    n = len(d)
    lens = np.array([h for _, _, h in trades])
    days = (idx[1:] - idx[:-1]).days
    cd = np.r_[0, np.cumsum(days)]
    actual = np.mean([r for _, r, _ in trades])
    fin = 0.05 if side > 0 else 0.015
    hits = 0
    for _ in range(k):
        e = RNG.integers(252, n - MAXH - 3, len(lens))
        L = RNG.permutation(lens)
        pin, pout = o[e + 1], o[e + L + 1]
        r = side * (pout / pin - 1) - sp / pin - (cd[e + L + 1] - cd[e + 1]) * fin / 365
        hits += r.mean() >= actual
    return hits / k


def stats(tr):
    r = np.array([x for _, x, _ in tr])
    h = len(r) // 2
    return r, r[:h], r[h:]


RULES = ["MR1", "MR2", "MR3", "MR4", "MR5", "MR6", "TR1", "TR2", "TR3", "TR4"]
CONFIRM = ["US30", "USTEC", "IWM", "EWA"]

if __name__ == "__main__":
    data = {s: prep(s) for s in ["US500"] + CONFIRM + ["XAUUSD"]}
    print(f"{'rule':5s} {'US500 n':>7s} {'win':>4s} {'avg%':>7s} {'PF h1/h2':>11s} {'twin p':>7s} {'hold':>4s} | "
          + " ".join(f"{s:>11s}" for s in CONFIRM) + " |  verdict   | gold PF h1/h2")
    for nm in RULES:
        d, sp = data["US500"]
        side, sig, ex = rule(nm, d)
        tr = run(d, sp, side, sig, ex)
        r, a, b = stats(tr)
        p = twin_p(d, sp, side, tr)
        ok = len(a) >= 30 and len(b) >= 30 and X.pf(a) >= 1.15 and X.pf(b) >= 1.15 and p < 0.005
        conf = []
        for s in CONFIRM:
            dd, ss = data[s]
            sd, sg, se = rule(nm, dd)
            rr = np.array([x for _, x, _ in run(dd, ss, sd, sg, se)])
            conf.append((X.pf(rr) if len(rr) else 0, len(rr)))
        nconf = sum(pf_ > 1 for pf_, _ in conf)
        dg, sg_ = data["XAUUSD"]
        gs, gsig, gex = rule(nm, dg)
        _, ga, gb = stats(run(dg, sg_, gs, gsig, gex))
        v = "CONFIRMED" if ok and nconf >= 3 else ("pass-only" if ok else "fail")
        print(f"{nm:5s} {len(r):7d} {np.mean(r > 0):4.0%} {r.mean()*100:+7.3f} {X.pf(a):5.2f}/{X.pf(b):<5.2f} {p:7.3f} "
              f"{np.mean([h for *_, h in tr]):4.1f} | " + " ".join(f"{pf_:5.2f} n{n_:<4d}" for pf_, n_ in conf)
              + f" | {v:10s} | {X.pf(ga):.2f}/{X.pf(gb):.2f}")
