"""EDGE-1 (2026-10-13): the documented, published edge families we had NOT tested yet - portfolio
level, not single-market rules.  PRE-DECLARED before any run:

F1 TSMOM   diversified time-series momentum (Moskowitz/Ooi/Pedersen 2012): every non-crypto market,
           signal = mean sign of 1/3/12-month return, each market sized to equal risk (60d vol),
           rebalanced every 21 days, costs = turnover x 1.5x median spread + 3%/yr financing on gross.
           PASS: Sharpe >= 0.4 in BOTH halves (2005-15, 2016-26) and random-sign control p < 0.05.
F2 XSMOM   sector rotation: hold top-3 of the XL* sector ETFs by 12-1 month return, monthly.
           PASS: excess Sharpe vs equal-weight sectors >= 0.3 in both halves.
F3 TOM     turn-of-month on US500: long from the 2nd-last close to the 3rd close of the new month.
           PASS: in-window mean daily return > out-of-window, t >= 2 overall and positive in both halves.
F4 CARRY   crypto funding carry: long spot / short perp on each coin while trailing 7-day funding > 0,
           0.3% round-trip cost per switch.  PASS: net yield > 5%/yr in both halves (2019-22, 2023-26),
           worst month > -2%.
F5 CXMOM   crypto cross-sectional momentum: weekly, long top-3 of 12 coins by 4-week return vs
           equal-weight all 12, 0.1%/side.  PASS: excess Sharpe >= 0.3 both halves.
F6 CTSMOM  crypto trend portfolio: each coin long when close > SMA50 else flat, equal risk, 0.1%/side.
           PASS: Sharpe >= buy&hold equal-weight in both halves AND maxDD at most 60% of buy&hold's,
           random-sign control p < 0.05.
F7 PAIRS   gold/silver log-ratio z (60d) mean reversion: enter |z| > 2, exit z crosses 0, max 40 days.
           PASS: PF >= 1.2 both halves, n >= 15 per half.
Then F9: the combined book of everything that passes plus the strategies already proven (index dip,
signal copying) - correlation and portfolio Sharpe.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
D1, D2 = os.path.join(HERE, "data"), os.path.join(HERE, "data_edge")
RNG = np.random.default_rng(7)
AN = 252


def load(path):
    z = np.load(path)
    idx = pd.to_datetime(z["t"], unit="s").normalize()
    df = pd.DataFrame(dict(o=z["o"], h=z["h"], l=z["l"], c=z["c"], sp=z["sp"]), index=idx)
    df = df[~df.index.duplicated(keep="last")]
    return df[df.c > 0]


def sharpe(r, ann=AN):
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std() * np.sqrt(ann)) if r.std() > 0 else 0.0


def maxdd(r):
    eq = (1 + pd.Series(r).fillna(0)).cumprod()
    return float((1 - eq / eq.cummax()).max())


def stats(r, ann=AN):
    r = pd.Series(r).dropna()
    yrs = len(r) / ann
    cagr = float((1 + r).prod() ** (1 / yrs) - 1) if yrs > 0 else 0
    return f"Sharpe {sharpe(r, ann):5.2f}  CAGR {cagr:+6.1%}  vol {r.std() * np.sqrt(ann):5.1%}  maxDD {maxdd(r):5.1%}"


def halves(r, cut):
    r = pd.Series(r).dropna()
    return r[r.index < cut], r[r.index >= cut]


# ------------------------------------------------------------------ F1 TSMOM
CRYPTO_OR_DUP = {"BTCUSDT", "ETHUSDT", "BTCUSD", "ETHUSD", "BITX", "DVOL", "VIXY", "VIXM",
                 # thin low-vol factor ETFs from VS-1 (not liquid markets) and duplicates of the CFD indices
                 "CDC", "CDL", "CFA", "CFO", "CSB", "EELV", "FDLO", "HDLB", "HSMV", "IDLV", "IVOL", "LVHD",
                 "SPY", "QQQ", "DIA", "GLD", "SLV", "UUP", "UK100"}


def universe():
    out = {}
    for p in sorted(glob.glob(os.path.join(D2, "*_D1.npz")) + glob.glob(os.path.join(D1, "*_D1.npz"))):
        n = os.path.basename(p)[:-7]
        if n.startswith("C_") or n in CRYPTO_OR_DUP:
            continue
        df = load(p)
        if len(df) > 750 and (n not in out or len(df) > len(out[n])):   # keep the longer history
            out[n] = df
    return out


def tsmom_weights(close, lookbacks=(21, 63, 252), reb=21):
    rets = close.pct_change(fill_method=None)
    vol = (rets.rolling(60).std() * np.sqrt(AN)).clip(lower=0.03)
    sig = sum(np.sign(close / close.shift(lb) - 1) for lb in lookbacks) / len(lookbacks)
    w = (sig * 0.10 / vol).clip(-2, 2)
    n_act = w.notna().sum(axis=1).replace(0, np.nan)
    w = w.mul(n_act.clip(lower=1) ** 0.5 / n_act, axis=0)                      # ~10% vol if uncorrelated
    keep = np.arange(len(w)) % reb == 0
    w = w.where(pd.Series(keep, index=w.index), np.nan).ffill()
    return w


def book_returns(w, close, spread_frac, fin=0.03, lag=1):
    rets = close.pct_change(fill_method=None).fillna(0)
    pos = w.shift(lag)
    gross = (pos * rets).sum(axis=1)
    turn = pos.diff().abs()
    cost = (turn * spread_frac).sum(axis=1) + pos.abs().sum(axis=1) * fin / AN
    return (gross - cost)[pos.notna().any(axis=1)]


def f1():
    u = universe()
    close = pd.DataFrame({n: d.c for n, d in u.items()}).sort_index()
    close = close[close.index >= "2004-01-01"].ffill(limit=5)
    jump = close.pct_change(fill_method=None).abs() > 0.4          # bad prints / contract rolls
    close = close.mask(jump)
    close = close[close.index.dayofweek < 5]
    sf = pd.Series({n: 1.5 * float((d.sp / d.c).median()) + 0.0002 for n, d in u.items()})
    w = tsmom_weights(close)
    r = book_returns(w, close, sf.reindex(close.columns))
    r = r[r.index >= "2005-01-01"]
    print(f"F1 TSMOM  {close.shape[1]} markets: {', '.join(close.columns)}")
    print(f"   all     {stats(r)}")
    a, b = halves(r, "2016-01-01")
    print(f"   2005-15 {stats(a)}\n   2016-26 {stats(b)}")
    r2 = book_returns(w, close, sf.reindex(close.columns), lag=2)
    print(f"   one extra day of execution lag: {stats(r2[r2.index >= '2005-01-01'])}")
    # random control: per-market signs drawn at each rebalance, same sizing
    s_true = sharpe(r)
    rets = close.pct_change(fill_method=None)
    vol = (rets.rolling(60).std() * np.sqrt(AN)).clip(lower=0.03)
    beat = 0
    for _ in range(200):
        keep = np.arange(len(close)) % 21 == 0
        rnd = pd.DataFrame(RNG.choice([-1.0, 1.0], size=close.shape), index=close.index, columns=close.columns)
        rnd = rnd.where(pd.Series(keep, index=close.index), np.nan).ffill()
        wr = (rnd * 0.10 / vol).clip(-2, 2)
        n_act = wr.notna().sum(axis=1).replace(0, np.nan)
        wr = wr.mul(n_act.clip(lower=1) ** 0.5 / n_act, axis=0)
        rr = book_returns(wr, close, sf.reindex(close.columns))
        beat += sharpe(rr[rr.index >= "2005-01-01"]) >= s_true
    p = (beat + 1) / 201
    ok = sharpe(a) >= 0.4 and sharpe(b) >= 0.4 and p < 0.05
    print(f"   random-sign control p = {p:.3f}   -> {'PASS' if ok else 'FAIL'}")
    # per asset class contribution
    contrib = (w.shift(1) * close.pct_change(fill_method=None))
    contrib = contrib[contrib.index >= "2005-01-01"].sum().sort_values()
    print("   best/worst contributors:", ", ".join(f"{k} {v:+.2f}" for k, v in list(contrib.items())[:4]),
          "...", ", ".join(f"{k} {v:+.2f}" for k, v in list(contrib.items())[-6:]))
    return r, ok


# ------------------------------------------------------------------ F2 XSMOM sectors
def f2():
    secs = [s for s in "XLE XLF XLK XLU XLV XLP XLI XLB XLY".split() if os.path.exists(os.path.join(D2, f"{s}_D1.npz"))]
    if len(secs) < 6:
        print("F2 XSMOM  not enough sector ETFs:", secs)
        return None, False
    close = pd.DataFrame({s: load(os.path.join(D2, f"{s}_D1.npz")).c for s in secs}).sort_index().ffill(limit=5).dropna()
    rets = close.pct_change()
    mom = close.shift(21) / close.shift(252) - 1
    me = close.index.to_series().groupby(close.index.to_period("M")).transform("max") == close.index.to_series()
    w = pd.DataFrame(0.0, index=close.index, columns=secs)
    rank = mom.rank(axis=1, ascending=False)
    w[:] = np.where(rank <= 3, 1 / 3, 0.0)
    w = w.where(me.values[:, None], np.nan).ffill()
    w[mom.isna().any(axis=1)] = np.nan
    pos = w.shift(1)
    strat = (pos * rets).sum(axis=1) - pos.diff().abs().sum(axis=1) * 0.0005
    ew = rets.mean(axis=1)
    ex = (strat - ew)[pos.notna().any(axis=1)]
    a, b = halves(ex, "2016-01-01")
    ok = sharpe(a) >= 0.3 and sharpe(b) >= 0.3
    print(f"F2 XSMOM  sectors {secs}\n   top-3 {stats(strat[pos.notna().any(axis=1)])}\n   equal {stats(ew[pos.notna().any(axis=1)])}")
    print(f"   excess Sharpe all {sharpe(ex):.2f}  H1 {sharpe(a):.2f}  H2 {sharpe(b):.2f} -> {'PASS' if ok else 'FAIL'}")
    return strat[pos.notna().any(axis=1)], ok


# ------------------------------------------------------------------ F3 turn of month
def f3():
    df = load(os.path.join(D1, "US500_D1.npz"))
    r = df.c.pct_change().dropna()
    per = r.index.to_period("M")
    pos_in_m = r.groupby(per).cumcount()
    n_in_m = r.groupby(per).transform("size")
    win = (pos_in_m <= 2) | (pos_in_m >= n_in_m - 1)      # last 1 day + first 3 days of month
    out = []
    for name, rr, ww in (("all", r, win), ("H1", r[r.index < "2019-01-01"], win[r.index < "2019-01-01"]),
                         ("H2", r[r.index >= "2019-01-01"], win[r.index >= "2019-01-01"])):
        a, b = rr[ww], rr[~ww]
        t = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
        out.append((name, a.mean(), b.mean(), t))
        print(f"F3 TOM    US500 {name}: in-window {a.mean() * 1e4:+.1f} bp/day (n={len(a)})  rest {b.mean() * 1e4:+.1f} bp/day  t={t:.2f}")
    ok = out[0][3] >= 2 and out[1][1] > out[1][2] and out[2][1] > out[2][2]
    # strategy: in market only in window, 5%/yr financing while long, spread 1.5x median
    sp = 1.5 * float((df.sp / df.c).median())
    pos = win.astype(float)
    sr = pos * r - pos.diff().abs().fillna(0) * sp - pos * 0.05 / AN
    print(f"   TOM-only strategy {stats(sr)}  (time in market {pos.mean():.0%})  -> {'PASS' if ok else 'FAIL'}")
    return sr, ok


# ------------------------------------------------------------------ crypto helpers
COINS = "BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX".split()


def crypto_close():
    return pd.DataFrame({c: load(os.path.join(D2, f"C_{c}_D1.npz")).c for c in COINS}).sort_index()


def f4():
    rows = {}
    for c in COINS:
        p = os.path.join(D2, f"F_{c}.npz")
        if not os.path.exists(p):
            continue
        z = np.load(p)
        s = pd.Series(z["r"], index=pd.to_datetime(z["t"], unit="s")).resample("D").sum()
        rows[c] = s
    f = pd.DataFrame(rows).sort_index()
    on = (f.rolling(7).mean() > 0).shift(1)                  # decide on yesterday's trailing funding
    on = on.astype(float).where(f.notna())
    switch = on.diff().abs().fillna(0)
    net = (on * f - switch * 0.003 / 2)                       # half the round trip on each switch
    port = net.mean(axis=1).dropna()
    port = port[port.index >= "2019-12-01"]
    a, b = halves(port, "2023-01-01")
    m = port.resample("ME").sum()
    print("F4 CARRY  funding carry, equal weight across coins (delta neutral, return on the spot leg's capital)")
    for name, x in (("all", port), ("2019-22", a), ("2023-26", b)):
        print(f"   {name}: yield {x.mean() * 365:+.1%}/yr  Sharpe {sharpe(x, 365):.2f}  worst day {x.min():+.2%}")
    print(f"   worst month {m.min():+.2%}, months negative {(m < 0).mean():.0%}")
    print("   per coin yield/yr:", ", ".join(f"{c} {net[c].mean() * 365:+.0%}" for c in net.columns))
    ok = a.mean() * 365 > 0.05 and b.mean() * 365 > 0.05 and m.min() > -0.02
    print(f"   NOTE capital: spot leg + perp margin ~ 1.3-1.5x notional; yield above is per spot notional -> {'PASS' if ok else 'FAIL'}")
    return port, ok


def f5():
    close = crypto_close()
    wk = close.resample("W-SUN").last()
    r = wk.pct_change()
    mom = wk / wk.shift(4) - 1
    rank = mom.rank(axis=1, ascending=False)
    w = (rank <= 3).astype(float).div(3)
    w[mom.notna().sum(axis=1) < 6] = np.nan
    pos = w.shift(1)
    strat = (pos * r).sum(axis=1) - pos.diff().abs().sum(axis=1) * 0.001
    ew = r.where(pos.notna()).mean(axis=1)
    valid = pos.notna().any(axis=1)
    ex = (strat - ew)[valid]
    a, b = halves(ex, "2022-07-01")
    ok = sharpe(a, 52) >= 0.3 and sharpe(b, 52) >= 0.3
    print(f"F5 CXMOM  top-3 {stats(strat[valid], 52)}\n   equal  {stats(ew[valid], 52)}")
    print(f"   excess Sharpe all {sharpe(ex, 52):.2f}  H1 {sharpe(a, 52):.2f}  H2 {sharpe(b, 52):.2f} -> {'PASS' if ok else 'FAIL'}")
    return strat[valid], ok


def f6():
    close = crypto_close()
    r = close.pct_change()
    vol = r.rolling(60).std()
    sig = (close > close.rolling(50).mean()).astype(float).where(close.rolling(50).mean().notna())

    def run(sig):
        w = (sig * (0.02 / vol)).clip(upper=1.0)
        n = w.notna().sum(axis=1).replace(0, np.nan)
        w = w.div(n, axis=0)
        pos = w.shift(1)
        out = (pos * r).sum(axis=1) - pos.diff().abs().sum(axis=1) * 0.001
        return out[pos.notna().any(axis=1)]
    s = run(sig)
    bh = run(sig.notna().astype(float).where(sig.notna()))
    a, b = halves(s, "2022-07-01")
    ba, bb = halves(bh, "2022-07-01")
    beat = 0
    for _ in range(200):                         # shuffle each coin's on/off run order (same time in market)
        rs = sig.copy()
        for c in rs.columns:
            v = rs[c].dropna().values
            runs = np.split(v, np.where(np.diff(v) != 0)[0] + 1)
            RNG.shuffle(runs)
            rs.loc[rs[c].notna(), c] = np.concatenate(runs)
        beat += sharpe(run(rs), 365) >= sharpe(s, 365)
    p = (beat + 1) / 201
    ok = sharpe(a, 365) >= sharpe(ba, 365) and sharpe(b, 365) >= sharpe(bb, 365) and maxdd(s) <= 0.6 * maxdd(bh) and p < 0.05
    print(f"F6 CTSMOM trend {stats(s, 365)}\n   b&h   {stats(bh, 365)}")
    print(f"   H1 trend {sharpe(a, 365):.2f} vs b&h {sharpe(ba, 365):.2f} | H2 trend {sharpe(b, 365):.2f} vs b&h {sharpe(bb, 365):.2f} | run-shuffle p = {p:.3f} -> {'PASS' if ok else 'FAIL'}")
    return s, ok


def f7():
    g, s = load(os.path.join(D1, "XAUUSD_D1.npz")), load(os.path.join(D1, "XAGUSD_D1.npz"))
    df = pd.DataFrame(dict(g=g.c, s=s.c, gsp=g.sp / g.c, ssp=s.sp / s.c)).dropna()
    lr = np.log(df.g / df.s)
    z = (lr - lr.rolling(60).mean()) / lr.rolling(60).std()
    cost = 1.5 * (df.gsp.median() + df.ssp.median()) + 2 * 0.0002
    trades, i, zz, idx = [], 60, z.values, df.index
    while i < len(df) - 1:
        if abs(zz[i]) > 2:
            sgn = -np.sign(zz[i])                # +1 = long the ratio (long gold, short silver)
            e = i + 1
            j = e
            while j < min(e + 40, len(df) - 1) and np.sign(zz[j]) == np.sign(zz[i]):
                j += 1
            x = j + 1 if j + 1 < len(df) else j
            ret = sgn * (lr.iloc[x] - lr.iloc[e]) - cost - 0.04 * (x - e) / 365
            trades.append((idx[e], ret))
            i = x
        i += 1
    t = pd.Series([r for _, r in trades], index=[d for d, _ in trades])

    def pf(x):
        return x[x > 0].sum() / -x[x < 0].sum() if (x < 0).any() else np.inf
    a, b = halves(t, "2016-01-01")
    ok = pf(a) >= 1.2 and pf(b) >= 1.2 and len(a) >= 15 and len(b) >= 15
    print(f"F7 PAIRS  gold/silver z>2: n={len(t)} PF {pf(t):.2f} mean {t.mean():+.2%} | H1 n={len(a)} PF {pf(a):.2f} | H2 n={len(b)} PF {pf(b):.2f} -> {'PASS' if ok else 'FAIL'}")
    return t, ok


if __name__ == "__main__":
    which = sys.argv[1:] or ["f1", "f2", "f3", "f4", "f5", "f6", "f7"]
    res = {}
    for k in which:
        print()
        res[k] = globals()[k]()
    pd.to_pickle({k: v[0] for k, v in res.items()}, os.path.join(HERE, "edge_results.pkl"))
    print("\nSUMMARY:", {k: ("PASS" if v[1] else "FAIL") for k, v in res.items()})
