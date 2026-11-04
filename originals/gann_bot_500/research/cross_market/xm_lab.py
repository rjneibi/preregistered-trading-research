"""XM-1: beyond gold - documented effects on indices, a multi-asset trend portfolio, and whether other
markets LEAD gold.  Data: broker demo feed D1/H1 (server time = UTC+2/+3, cash US session 16:30-23:00).

PRE-DECLARED (written before any result was seen):
  costs   spread = 1.5 x the median recorded H1 spread; financing on CFDs: longs 5%/yr, shorts 1.5%/yr of
          notional per calendar night (retail index-CFD norm, worse than this demo's house swaps).
  halves  first half / second half of each test's own sample.
  PASS    net mean > 0 AND net PF >= 1.15 in BOTH halves, n >= 30 per half, AND the rule beats a random
          twin of the same exposure (permutation p < 0.05) - so plain index drift cannot pass.
  A1 index short-term mean reversion (Connors RSI2<10 above SMA200, exit close>SMA5 or 10 days)  US500, US30
  A2 turn-of-month (close of last day -> close of 3rd day)                                      US500, US30
  A3 pre-FOMC drift (24h before the 14:00 ET statement, H1 2018+)                                US500, US30
  A4 overnight drift (cash close -> next 10:00 ET vs 10:00 ET -> close, H1 2018+)                US500, US30
  B  trend portfolio (12m sign, vol-targeted 10%/asset) on gold, silver, US500, US30, TLT, EURUSD:
     PASS = net Sharpe >= 0.5 in both halves AND above the same basket held long (vol-targeted).
  C  lead-lag: corr(this bar's return of X, gold's NEXT bar) for X in TLT, US500, XAG, EURUSD, gold,
     D1 2005+ and H1 2018+.  PASS = |corr| >= 0.03 with the same sign in both halves (then trade-tested).
"""
import datetime as dt
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"@GANN_ROOT@/fable-backtesting")
from build_calendar import FOMC  # noqa: E402

DD = r"@GANN_ROOT@/research/cross_market/data"
FIN_L, FIN_S = 0.05 / 365, 0.015 / 365
RNG = np.random.default_rng(7)


def load(sym, tf):
    z = np.load(f"{DD}\\{sym}_{tf}.npz")
    df = pd.DataFrame({k: z[k] for k in ("o", "h", "l", "c", "sp")},
                      index=pd.to_datetime(z["t"], unit="s"))
    df = df[~df.index.duplicated()]
    return df, 1.5 * float(np.median(z["sp"][z["sp"] > 0])) if (z["sp"] > 0).any() else 0.0


def pf(r):
    r = np.asarray(r)
    return r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else float("inf")


def verdict(name, r, twin_means, gate=True):
    r = np.asarray(r)
    h = len(r) // 2
    a, b = r[:h], r[h:]
    p = (np.asarray(twin_means) >= r.mean()).mean() if len(twin_means) else float("nan")
    ok = gate and len(a) >= 30 and len(b) >= 30 and a.mean() > 0 and b.mean() > 0 and pf(a) >= 1.15 and pf(b) >= 1.15 and p < 0.05
    print(f"  {name:34s} n={len(r):4d} | half1 avg {a.mean()*100:+.3f}% PF {pf(a):.2f} | half2 avg {b.mean()*100:+.3f}% "
          f"PF {pf(b):.2f} | vs random twin p={p:.3f}  {'PASS' if ok else 'fail'}")
    return ok


def hold_ret(c, i, j, sp, side=1):
    """Net return of a hold from close i to close j (positional), spread once, financing per night."""
    nights = (c.index[j] - c.index[i]).days
    g = side * (c.iloc[j] / c.iloc[i] - 1)
    return g - sp / c.iloc[i] - nights * (FIN_L if side > 0 else FIN_S)


def twins(c, pool, lens, sp, k=1000):
    """Mean net return of random holds: entries drawn from pool, hold lengths resampled from lens."""
    out = []
    pool, lens = np.asarray(pool), np.asarray(lens)
    for _ in range(k):
        e = RNG.choice(pool, len(lens))
        L = RNG.permutation(lens)
        out.append(np.mean([hold_ret(c, i, min(i + n, len(c) - 1), sp) for i, n in zip(e, L)]))
    return out


# ---------------------------------------------------------------- A1, A2 (daily)
def a1_a2(sym):
    d, sp = load(sym, "D1")
    c = d["c"]
    sma200, sma5 = c.rolling(200).mean(), c.rolling(5).mean()
    diff = c.diff()
    up, dn = diff.clip(lower=0).ewm(alpha=.5).mean(), (-diff).clip(lower=0).ewm(alpha=.5).mean()
    rsi2 = 100 - 100 / (1 + up / dn.replace(0, 1e-12))
    r, lens, i = [], [], 200
    while i < len(c) - 1:
        if rsi2.iloc[i] < 10 and c.iloc[i] > sma200.iloc[i]:
            j = i + 1
            while j < len(c) - 1 and j - i < 10 and c.iloc[j] <= sma5.iloc[j]:
                j += 1
            r.append(hold_ret(c, i, j, sp)); lens.append(j - i)
            i = j + 1
        else:
            i += 1
    pool = np.flatnonzero((c > sma200).values[:-11])
    pool = pool[pool >= 200]
    verdict(f"A1 {sym} RSI2 mean-reversion", r, twins(c, pool, lens, sp))
    # A2 turn of month
    m = c.index.to_period("M")
    last = np.flatnonzero(m[1:] != m[:-1])          # index of the last day of each month
    r2 = [hold_ret(c, i, i + 4, sp) for i in last if i + 4 < len(c)]
    verdict(f"A2 {sym} turn-of-month", r2, twins(c, np.arange(1, len(c) - 5), [4] * len(r2), sp))


# ---------------------------------------------------------------- A3, A4 (H1)
def a3_a4(sym):
    d, sp = load(sym, "H1")
    o, c = d["o"], d["c"]
    fomc = {dt.date.fromisoformat(x) for x in (FOMC.split() if isinstance(FOMC, str) else FOMC)}
    at21 = d[d.index.hour == 21]                    # bar opening 21:00 server = 14:00 ET
    days = at21.index.normalize()
    r_f, r_o = [], []
    px = at21["o"].values
    for k in range(1, len(at21)):
        if (days[k] - days[k - 1]).days > 4:
            continue
        g = px[k] / px[k - 1] - 1 - sp / px[k - 1] - (days[k] - days[k - 1]).days * FIN_L
        (r_f if days[k].date() in fomc else r_o).append(g)
    r_o = np.array(r_o)
    tw = [RNG.choice(r_o, len(r_f)).mean() for _ in range(2000)]
    verdict(f"A3 {sym} pre-FOMC 24h drift", r_f, tw)
    # A4 overnight: close of the 22:00 bar (23:00 server) -> open of the 17:00 bar next session
    cl = d[d.index.hour == 22]["c"]
    op = d[d.index.hour == 17]["o"]
    on, day_ = [], []
    cl_d = {t.normalize(): v for t, v in cl.items()}
    op_items = list(op.items())
    for t, v in op_items:
        prev = [x for x in (t.normalize() - pd.Timedelta(days=k) for k in (1, 2, 3)) if x in cl_d]
        if prev:
            on.append((v / cl_d[prev[0]] - 1, (t.normalize() - prev[0]).days))
        if t.normalize() in cl_d:
            day_.append(cl_d[t.normalize()] / v - 1)
    on_g = np.array([x for x, _ in on])
    on_n = np.array([x - n * FIN_L for x, n in on]) - sp / d["c"].median()   # financing + one spread
    day_ = np.array(day_) - sp / d["c"].median()
    print(f"  A4 {sym} gross mean overnight {on_g.mean()*100:+.4f}%/night vs intraday {(day_ + sp / d['c'].median()).mean()*100:+.4f}%/day")
    verdict(f"A4 {sym} long overnight only (net)", on_n, [], gate=False)
    verdict(f"A4 {sym} long intraday only (net)", day_, [], gate=False)


# ---------------------------------------------------------------- B trend portfolio
def b_trend():
    syms = ["XAUUSD", "XAGUSD", "US500", "US30", "TLT", "EURUSD"]
    px, cost = {}, {}
    for s in syms:
        d, sp = load(s, "D1")
        d = d[d.index >= "2004-06-01"]
        px[s] = d["c"]
        cost[s] = max(sp, 0.0002 * d["c"].median())   # TLT has no recorded spread: assume 2bp
    P = pd.DataFrame(px).ffill()
    R = P.pct_change()
    vol = R.rolling(60).std() * np.sqrt(252)
    w_lo = (0.10 / vol).clip(upper=2.0)
    sig = np.sign(P / P.shift(252) - 1)
    out = {}
    for name, w in (("trend", sig * w_lo), ("long-only", w_lo)):
        w = w.shift(1)                               # decided at yesterday's close
        n_av = w.notna().sum(1).replace(0, np.nan)
        gross = (w * R).sum(1) / n_av
        turn = (w.diff().abs() * pd.DataFrame({s: cost[s] / P[s] for s in syms})).sum(1) / n_av
        days = pd.Series(P.index, index=P.index).diff().dt.days.fillna(1)
        carry = ((w.clip(lower=0) * FIN_L + (-w).clip(lower=0) * FIN_S).sum(1) / n_av).mul(days)
        net = (gross - turn - carry).dropna()
        net = net[net.index >= "2005-06-01"]
        out[name] = net
    h = out["trend"].index[len(out["trend"]) // 2]
    sh = lambda x: x.mean() / x.std() * np.sqrt(252)
    ok = True
    for lab, m in (("half1", out["trend"].index < h), ("half2", out["trend"].index >= h)):
        t, lo = out["trend"][m], out["long-only"][m]
        cagr = (1 + t).prod() ** (252 / len(t)) - 1
        dd = ((1 + t).cumprod() / (1 + t).cumprod().cummax() - 1).min()
        print(f"  B trend portfolio {lab}: Sharpe {sh(t):.2f} (long-only {sh(lo):.2f})  CAGR {cagr*100:+.1f}%  maxDD {dd*100:.1f}%  "
              f"corr to long-only {np.corrcoef(t, lo)[0,1]:+.2f}")
        ok &= sh(t) >= 0.5 and sh(t) > sh(lo)
    print(f"  B verdict: {'PASS' if ok else 'fail'}")


# ---------------------------------------------------------------- C lead-lag into gold
def c_leadlag():
    for tf, start in (("D1", "2005-01-01"), ("H1", "2018-06-01")):
        cols = {}
        for s in ["XAUUSD", "TLT", "US500", "XAGUSD", "EURUSD"]:
            d, _ = load(s, tf)
            cols[s] = d["c"][d.index >= start]
        P = pd.DataFrame(cols)
        R = np.log(P).diff()                          # NaN where a market has no bar (no stale fills)
        nxt = R["XAUUSD"].shift(-1)
        print(f"  C {tf}: corr(X now, gold next bar)   half1 | half2   (n)")
        for s in R.columns:
            m = R[s].notna() & nxt.notna()
            x, y = R[s][m], nxt[m]
            h = len(x) // 2
            c1, c2 = np.corrcoef(x[:h], y[:h])[0, 1], np.corrcoef(x[h:], y[h:])[0, 1]
            ok = abs(c1) >= .03 and abs(c2) >= .03 and np.sign(c1) == np.sign(c2)
            print(f"     {s:7s} {c1:+.3f} | {c2:+.3f}   ({len(x)})  {'PASS' if ok else ''}")


if __name__ == "__main__":
    print("A1/A2 daily index effects (2012-2026)")
    for s in ("US500", "US30"):
        a1_a2(s)
    print("\nA3/A4 H1 index effects (2018-2026)")
    for s in ("US500", "US30"):
        a3_a4(s)
    print("\nB multi-asset trend following (2005-2026)")
    b_trend()
    print("\nC do other markets lead gold?")
    c_leadlag()
