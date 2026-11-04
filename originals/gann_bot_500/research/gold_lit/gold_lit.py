"""GOLD-LIT-1 (PREREG.md frozen before this ran): published gold anomalies, tested as published."""
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "d_revival"))
sys.path.insert(0, os.path.join(HERE, "..", "exit2"))
from data import load  # noqa: E402

U = dt.timezone.utc
WIN = {"A 2010-17": ("2010", "2018"), "B 2018-26": ("2018", "2027"), "C 2023+": ("2023", "2027")}


def tstat(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 2 else np.nan


# ---------------- H-A intraday hat
def utc_m1():
    from exit2 import to_utc  # same UTC conversion as EXIT-2
    m = load()
    return to_utc(m["t"]), m["o"], m["c"]


def leg(t, o, c, h_in, m_in, h_out, sgn):
    """Per weekday: enter at the first M1 open at/after h_in:m_in UTC, exit at the last close before h_out."""
    day = t // 86400
    sec = t % 86400
    rows = []
    s_in, s_out = h_in * 3600 + m_in * 60, h_out * 3600
    df = pd.DataFrame({"day": day, "sec": sec, "o": o, "c": c})
    a = df[(df.sec >= s_in) & (df.sec < s_in + 1800)].groupby("day").first()
    b = df[(df.sec < s_out) & (df.sec >= s_out - 1800)].groupby("day").last()
    j = a.join(b, lsuffix="_in", rsuffix="_out", how="inner")
    j = j[j.sec_out > j.sec_in]
    wd = pd.to_datetime(j.index * 86400, unit="s").weekday
    j = j[wd < 5]
    r = sgn * (j.c_out - j.o_in)
    r.index = pd.to_datetime(r.index * 86400, unit="s")
    return r


def hat():
    t, o, c = utc_m1()
    out = {}
    for name, args in (("H-A1 Asia long 00:15-07", (0, 15, 7, 1)), ("H-A2 US short 13:00-20", (13, 0, 20, -1))):
        base = leg(t, o, c, *args)
        h, m, ho, s = args
        shift = leg(t, o, c, h, m + 15, ho, s)
        ok = True
        print(name, f"n={len(base)}")
        for w, (lo, hi) in WIN.items():
            x, xs = base[lo:hi], shift[lo:hi]
            net, stress, sh = (x - 0.40).mean(), (x - 0.80).mean(), (xs - 0.40).mean()
            g = net > 0 and sh > 0 and (w.startswith("A") or stress > 0)
            ok &= g
            print(f"   {w}: n{len(x)} gross {x.mean():+.3f} net {net:+.3f} $/oz  x2cost {stress:+.3f}  "
                  f"+15min {sh:+.3f}  win {(x - 0.4 > 0).mean():.0%}  {'ok' if g else '--'}")
        tt = tstat(base - 0.40)
        ok &= tt >= 2
        yr = (base - 0.40).groupby(base.index.year).sum()
        print(f"   ALL net t={tt:+.2f}  by year $/oz: " + " ".join(f"{k % 100:02d}:{v:+.0f}" for k, v in yr.items()))
        print("   ->", "PASS" if ok else "FAIL")
        out[name] = base
    return out


# ---------------- monthly tests
def monthly():
    z = np.load(os.path.join(HERE, "..", "cross_market", "data_edge", "XAUUSD_D1.npz"))
    s = pd.Series(z["c"], index=pd.to_datetime(z["t"], unit="s"))
    return s.resample("ME").last().pct_change().dropna()


def seasonality(r):
    fin = 0.03 / 12
    halves = {"2004-14": ("2004", "2015"), "2015-26": ("2015", "2027")}
    for name, months in (("H-B1 Sep+Nov", (9, 11)), ("H-B2 Dec-Feb", (12, 1, 2))):
        sel = r.index.month.isin(months)
        ok = True
        print(name)
        for hn, (lo, hi) in halves.items():
            x = r[lo:hi]; m = x.index.month.isin(months)
            g = x[m].mean() > x[~m].mean()
            ok &= g
            print(f"   {hn}: in {x[m].mean():+.2%} (n{m.sum()})  others {x[~m].mean():+.2%}  {'ok' if g else '--'}")
        a, b = r[sel], r[~sel]
        wt = (a.mean() - b.mean()) / np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        net = (a - fin).mean()
        ok &= wt >= 2 and net > 0
        print(f"   ALL: in {a.mean():+.2%} vs others {b.mean():+.2%}  Welch t={wt:+.2f}  net/month {net:+.2%}  "
              f"-> {'PASS' if ok else 'FAIL'}")


def sharpe(x):
    return x.mean() / x.std(ddof=1) * np.sqrt(12)


def mdd(x):
    e = (1 + x).cumprod()
    return (1 - e / e.cummax()).max()


def momentum(r):
    fin = 0.03 / 12
    bh = r - fin
    lvl = (1 + r).cumprod()
    halves = {"2004-14": ("2004", "2015"), "2015-26": ("2015", "2027")}
    for name, lb in (("H-C1 12m momentum", 12), ("H-C2 24m momentum", 24)):
        pos = (lvl / lvl.shift(lb) - 1 > 0).astype(float).shift(1)          # decided at prior month end
        sw = pos.diff().abs().fillna(0)
        strat = (pos * (r - fin) - sw * 0.0005).dropna()
        b = bh.loc[strat.index]
        ok = True
        print(name, f"months {len(strat)}, invested {pos.loc[strat.index].mean():.0%}")
        for hn, (lo, hi) in halves.items():
            s1, b1 = strat[lo:hi], b[lo:hi]
            g = sharpe(s1) >= sharpe(b1)
            ok &= g
            print(f"   {hn}: Sharpe {sharpe(s1):.2f} vs hold {sharpe(b1):.2f}  CAGR {(1 + s1).prod() ** (12 / len(s1)) - 1:+.1%}"
                  f" vs {(1 + b1).prod() ** (12 / len(b1)) - 1:+.1%}  {'ok' if g else '--'}")
        g = mdd(strat) < mdd(b)
        ok &= g
        print(f"   ALL: Sharpe {sharpe(strat):.2f} vs {sharpe(b):.2f}  maxDD {mdd(strat):.0%} vs {mdd(b):.0%}  "
              f"-> {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    hat()
    r = monthly()
    print(f"monthly data {r.index[0]:%Y-%m}..{r.index[-1]:%Y-%m} n={len(r)}")
    seasonality(r)
    momentum(r)
