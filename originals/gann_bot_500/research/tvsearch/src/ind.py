"""TradingView built-in indicators re-implemented in numpy, following the Pine v5 reference formulas.

Conventions (match Pine):
  ta.sma / ta.wma / ta.vwma  plain rolling windows, NaN until the window is full.
  ta.ema   alpha = 2/(n+1), seeded with the SMA of the first n values (NaN before) - TradingView's built-in.
  ta.rma   alpha = 1/n, seeded with the SMA of the first n values (Wilder). RSI, ATR, ADX use rma.
  ta.vwap  anchored cumulative sum(src*vol)/sum(vol), reset at each anchor; bands = sqrt(E[src^2]-vwap^2)*k.
Every array is aligned to the input bars and uses only data up to that bar (no lookahead).
"""
import numpy as np
from scipy.signal import lfilter

NAN = np.nan


def _first_valid(x):
    ok = np.flatnonzero(~np.isnan(x))
    return ok[0] if len(ok) else len(x)


def sma(x, n):
    x = np.asarray(x, float); out = np.full(len(x), NAN)
    f = _first_valid(x)
    if len(x) - f < n:
        return out
    c = np.cumsum(np.r_[0.0, x[f:]])
    out[f + n - 1:] = (c[n:] - c[:-n]) / n
    return out


def _smooth(x, n, alpha):
    """EMA-type recursion seeded with SMA(n) at the first full window."""
    x = np.asarray(x, float); out = np.full(len(x), NAN)
    f = _first_valid(x)
    if len(x) - f < n:
        return out
    seed = x[f:f + n].mean()
    out[f + n - 1] = seed
    rest = x[f + n:]
    if len(rest):
        out[f + n:] = lfilter([alpha], [1, -(1 - alpha)], rest, zi=[(1 - alpha) * seed])[0]
    return out


def ema(x, n):
    return _smooth(x, n, 2.0 / (n + 1))


def rma(x, n):
    return _smooth(x, n, 1.0 / n)


def wma(x, n):
    x = np.asarray(x, float); w = np.arange(1, n + 1, dtype=float)
    out = np.full(len(x), NAN)
    if len(x) >= n:
        out[n - 1:] = np.convolve(x, w[::-1], "valid") / w.sum()
    return out


def hma(x, n):
    return wma(2 * wma(x, max(n // 2, 1)) - wma(x, n), max(int(np.sqrt(n)), 1))


def vwma(x, v, n):
    return sma(np.asarray(x) * v, n) / sma(v, n)


def dema(x, n):
    e = ema(x, n)
    return 2 * e - ema(e, n)


def tema(x, n):
    e1 = ema(x, n); e2 = ema(e1, n)
    return 3 * e1 - 3 * e2 + ema(e2, n)


def alma(x, n, offset=0.85, sigma=6.0):
    m = offset * (n - 1); s = n / sigma
    w = np.exp(-((np.arange(n) - m) ** 2) / (2 * s * s))
    out = np.full(len(x), NAN)
    if len(x) >= n:
        out[n - 1:] = np.convolve(np.asarray(x, float), w[::-1], "valid") / w.sum()
    return out


def kama(x, n, fast=2, slow=30):
    x = np.asarray(x, float); out = np.full(len(x), NAN)
    if len(x) <= n:
        return out
    ch = np.abs(x[n:] - x[:-n])
    vol = np.convolve(np.abs(np.diff(x)), np.ones(n), "valid")
    er = np.where(vol > 0, ch / np.where(vol > 0, vol, 1), 0)
    fs, ss = 2 / (fast + 1), 2 / (slow + 1)
    sc = (er * (fs - ss) + ss) ** 2
    k = x[n - 1]
    for i in range(n, len(x)):
        k = k + sc[i - n] * (x[i] - k)
        out[i] = k
    return out


def ma(kind, x, n, v=None):
    return {"sma": sma, "ema": ema, "wma": wma, "hma": hma, "dema": dema, "tema": tema, "alma": alma,
            "kama": kama, "rma": rma}[kind](x, n) if kind != "vwma" else vwma(x, v, n)


def stdev(x, n):
    """ta.stdev (population, biased) over n bars."""
    m = sma(x, n)
    return np.sqrt(np.maximum(sma(np.asarray(x) ** 2, n) - m * m, 0))


def tr(h, l, c):
    pc = np.r_[NAN, c[:-1]]
    t = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    t[0] = h[0] - l[0]
    return t


def atr(h, l, c, n=14):
    return rma(tr(h, l, c), n)


def rsi(x, n=14):
    d = np.diff(np.asarray(x, float), prepend=NAN)
    up, dn = rma(np.where(d > 0, d, 0.0)[1:], n), rma(np.where(d < 0, -d, 0.0)[1:], n)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(dn == 0, 100.0, np.where(up == 0, 0.0, 100 - 100 / (1 + up / dn)))
    return np.r_[NAN, np.where(np.isnan(up), NAN, r)]


def vwap(src, v, anchor):
    """anchor = integer id per bar (session/week/month); resets when it changes. Returns vwap, stdev."""
    src = np.asarray(src, float); v = np.asarray(v, float)
    new = np.r_[True, anchor[1:] != anchor[:-1]]
    g = np.cumsum(new) - 1
    def gcum(a):
        c = np.cumsum(a); base = np.r_[0.0, c][np.flatnonzero(new)]
        return c - base[g]
    sv, s2v, sv0 = gcum(src * v), gcum(src * src * v), gcum(v)
    with np.errstate(divide="ignore", invalid="ignore"):
        vw = sv / sv0
        sd = np.sqrt(np.maximum(s2v / sv0 - vw * vw, 0))
    vw = np.where(sv0 > 0, vw, src)
    return vw, np.where(sv0 > 0, sd, 0.0)


def macd(x, f=12, s=26, sig=9):
    m = ema(x, f) - ema(x, s)
    return m, ema(m, sig)


def stoch(h, l, c, n=14, k=3, d=3):
    hh, ll = rolling_max(h, n), rolling_min(l, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 100 * (c - ll) / (hh - ll)
    kk = sma(raw, k)
    return kk, sma(kk, d)


def stochrsi(x, n_rsi=14, n_st=14, k=3, d=3):
    r = rsi(x, n_rsi)
    hh, ll = rolling_max(r, n_st), rolling_min(r, n_st)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 100 * (r - ll) / (hh - ll)
    kk = sma(raw, k)
    return kk, sma(kk, d)


def cci(h, l, c, n=20):
    tp = (h + l + c) / 3
    m = sma(tp, n)
    from numpy.lib.stride_tricks import sliding_window_view as swv
    md = np.full(len(tp), NAN)
    if len(tp) >= n:
        w = swv(tp, n)
        md[n - 1:] = np.abs(w - w.mean(1, keepdims=True)).mean(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (tp - m) / (0.015 * md)


def willr(h, l, c, n=14):
    hh, ll = rolling_max(h, n), rolling_min(l, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 * (c - hh) / (hh - ll)


def roc(x, n=9):
    out = np.full(len(x), NAN); out[n:] = 100 * (x[n:] - x[:-n]) / x[:-n]
    return out


def mom(x, n=10):
    out = np.full(len(x), NAN); out[n:] = x[n:] - x[:-n]
    return out


def tsi(x, r=25, s=13):
    d = np.diff(np.asarray(x, float), prepend=NAN)[1:]
    num, den = ema(ema(d, r), s), ema(ema(np.abs(d), r), s)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.r_[NAN, 100 * num / den]


def ao(h, l):
    m = (h + l) / 2
    return sma(m, 5) - sma(m, 34)


def rolling_max(x, n):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    out = np.full(len(x), NAN)
    if len(x) >= n:
        out[n - 1:] = swv(np.asarray(x, float), n).max(1)
    return out


def rolling_min(x, n):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    out = np.full(len(x), NAN)
    if len(x) >= n:
        out[n - 1:] = swv(np.asarray(x, float), n).min(1)
    return out


def bbands(x, n=20, k=2.0):
    m = sma(x, n); s = stdev(x, n)
    return m, m + k * s, m - k * s


def keltner(h, l, c, n=20, k=1.5, atr_n=10):
    m = ema(c, n); a = atr(h, l, c, atr_n)
    return m, m + k * a, m - k * a


def donchian(h, l, n=20):
    return rolling_max(h, n), rolling_min(l, n)


def adx(h, l, c, n=14):
    up = np.diff(h, prepend=NAN); dn = -np.diff(l, prepend=NAN)
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    t = rma(tr(h, l, c)[1:], n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100 * rma(pdm[1:], n) / t; mdi = 100 * rma(mdm[1:], n) / t
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    dx = np.where(np.isnan(dx) & ~np.isnan(t), 0.0, dx)
    a = rma(dx, n)
    return np.r_[NAN, pdi], np.r_[NAN, mdi], np.r_[NAN, a]


def aroon(h, l, n=14):
    from numpy.lib.stride_tricks import sliding_window_view as swv
    up = np.full(len(h), NAN); dn = np.full(len(h), NAN)
    if len(h) > n:
        wh, wl = swv(h, n + 1), swv(l, n + 1)
        up[n:] = 100 * (wh.argmax(1)) / n   # Pine: 100 * (highestbars(n+1) + n) / n; argmax of the last occurrence differs only on ties
        dn[n:] = 100 * (wl.argmin(1)) / n
    return up, dn


def supertrend(h, l, c, n=10, mult=3.0):
    """Pine ta.supertrend. Returns (dir, line) with dir +1 = uptrend, -1 = downtrend (Pine itself uses -1 for up)."""
    a = atr(h, l, c, n); hl2 = (h + l) / 2
    N = len(c); d = np.full(N, NAN); line = np.full(N, NAN)
    pu = pl = 0.0; pst = NAN; first = True
    for i in range(N):
        if np.isnan(a[i]):
            continue
        u, lo = hl2[i] + mult * a[i], hl2[i] - mult * a[i]
        if not first:
            lo = lo if (lo > pl or c[i - 1] < pl) else pl
            u = u if (u < pu or c[i - 1] > pu) else pu
            di = (-1 if c[i] > u else 1) if pst == pu else (1 if c[i] < lo else -1)
        else:
            di = 1; first = False
        st = lo if di == -1 else u
        d[i], line[i] = -di, st
        pu, pl, pst = u, lo, st
    return d, line


def psar(h, l, start=0.02, inc=0.02, mx=0.2):
    N = len(h); out = np.full(N, NAN); d = np.full(N, NAN)
    if N < 2:
        return d, out
    up = h[1] >= h[0]
    af, ep = start, (h[1] if up else l[1])
    s = l[0] if up else h[0]
    for i in range(1, N):
        s = s + af * (ep - s)
        if up:
            s = min(s, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < s:
                up, s, ep, af = False, ep, l[i], start
            elif h[i] > ep:
                ep, af = h[i], min(af + inc, mx)
        else:
            s = max(s, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > s:
                up, s, ep, af = True, ep, h[i], start
            elif l[i] < ep:
                ep, af = l[i], min(af + inc, mx)
        out[i] = s; d[i] = 1 if up else -1
    return d, out


def ichimoku(h, l, conv=9, base=26, lead=52, disp=26):
    don = lambda n: (rolling_max(h, n) + rolling_min(l, n)) / 2
    t, k = don(conv), don(base)
    a, b = (t + k) / 2, don(lead)
    # the cloud plotted at bar i was computed disp-1 bars earlier (no lookahead)
    sh = lambda x: np.r_[np.full(disp - 1, NAN), x[:len(x) - disp + 1]]
    return t, k, sh(a), sh(b)


def obv(c, v):
    d = np.sign(np.diff(c, prepend=c[0]))
    return np.cumsum(d * v)


def mfi(h, l, c, v, n=14):
    tp = (h + l + c) / 3; d = np.diff(tp, prepend=NAN)
    pos = np.where(d > 0, tp * v, 0.0); neg = np.where(d < 0, tp * v, 0.0)
    sp, sn = sma(pos, n) * n, sma(neg, n) * n
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 - 100 / (1 + sp / sn)


def cmf(h, l, c, v, n=20):
    with np.errstate(divide="ignore", invalid="ignore"):
        mfm = np.where(h > l, ((c - l) - (h - c)) / (h - l), 0.0)
        return sma(mfm * v, n) / sma(v, n)


def rvol(v, n=20):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.asarray(v, float) / np.r_[NAN, sma(v, n)[:-1]]


def pct_rank(x, n=500):
    """Share of the previous n values below x (ta.percentrank)."""
    from numpy.lib.stride_tricks import sliding_window_view as swv
    out = np.full(len(x), NAN)
    if len(x) > n:
        w = swv(np.asarray(x, float), n + 1)
        out[n:] = 100 * (w[:, :-1] < w[:, -1:]).sum(1) / n
    return out


def cross_up(a, b):
    a, b = np.asarray(a, float), np.broadcast_to(np.asarray(b, float), np.shape(a))
    pa, pb = np.r_[NAN, a[:-1]], np.r_[NAN, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a > b) & (pa <= pb)


def cross_dn(a, b):
    a, b = np.asarray(a, float), np.broadcast_to(np.asarray(b, float), np.shape(a))
    pa, pb = np.r_[NAN, a[:-1]], np.r_[NAN, b[:-1]]
    with np.errstate(invalid="ignore"):
        return (a < b) & (pa >= pb)
