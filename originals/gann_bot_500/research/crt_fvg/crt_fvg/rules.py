"""CRT + HTF FVG rules. Every object carries `known`, the minute it becomes observable
(the close of the bar that completes it); every query at decision time T only uses objects
with known <= T (or < T where stated). Directions: +1 bull / long, -1 bear / short."""
import numpy as np
import pandas as pd

from .data import atr, ema, resample

INF = np.iinfo(np.int64).max


# ---------------------------------------------------------------- swings
def swings(b, n):
    """Fractal pivots. Bar j is a swing high if h[j] is strictly above the highs of the n bars
    on each side (swing low mirrors). Returns (high_idx, low_idx); pivot j is known at
    t_close[j + n], so the earliest bar that may use it is j + n + 1."""
    N = len(b)
    if N < 2 * n + 1:
        return np.empty(0, int), np.empty(0, int)
    j = np.arange(n, N - n)
    hi = np.ones(len(j), bool)
    lo = np.ones(len(j), bool)
    for k in range(1, n + 1):
        hi &= (b.h[j] > b.h[j - k]) & (b.h[j] > b.h[j + k])
        lo &= (b.l[j] < b.l[j - k]) & (b.l[j] < b.l[j + k])
    return j[hi], j[lo]


# ---------------------------------------------------------------- CRT
def _crt_bull(low, close, piv, n, k):
    """Bullish CRT on one bar series. Reference level = the most recent confirmed swing low
    (a newer confirmed pivot replaces it). The first bar trading below the reference is the
    sweep; the reference is consumed then, whatever happens next. CRT = a close back above the
    reference within k bars counting the sweep bar. ext = lowest low from sweep to confirm."""
    nb = len(low)
    out = []
    for p in range(len(piv)):
        lvl = low[piv[p]]
        a = piv[p] + n + 1                                   # first bar allowed to use the pivot
        e = piv[p + 1] + n + 1 if p + 1 < len(piv) else nb   # replaced by the next confirmed pivot
        if a >= e:
            continue
        hit = np.flatnonzero(low[a:e] < lvl)
        if not len(hit):
            continue
        i = a + int(hit[0])
        back = np.flatnonzero(close[i:min(i + k, nb)] > lvl)
        if len(back):
            q = i + int(back[0])
            out.append((lvl, low[i:q + 1].min(), i, q, piv[p]))
    return out


def crt_events(b, n, k):
    """All CRT models on bar series b, sorted by the minute they are known."""
    hi, lo = swings(b, n)
    rows = [(1, lvl, ext, i, q, j) for lvl, ext, i, q, j in _crt_bull(b.l, b.c, lo, n, k)]
    rows += [(-1, -lvl, -ext, i, q, j) for lvl, ext, i, q, j in _crt_bull(-b.h, -b.c, hi, n, k)]
    ev = pd.DataFrame(rows, columns=["dir", "level", "ext", "sweep_i", "conf_i", "pivot_i"])
    ev["t_sweep"] = b.t_open[ev.sweep_i.values] if len(ev) else []
    ev["known"] = b.t_close[ev.conf_i.values] if len(ev) else []
    return ev.sort_values(["known", "dir"], kind="stable").reset_index(drop=True)


def streak_flags(ev, min_streak, monotonic):
    """ok[d][e] = the last `min_streak` events ending at e are all direction d, each sweep
    extreme beyond the previous one (higher lows for bull, lower highs for bear)."""
    d = ev.dir.values
    x = ev.ext.values
    ok = {}
    for s in (1, -1):
        f = np.zeros(len(ev), bool)
        for e in range(min_streak - 1, len(ev)):
            w = slice(e - min_streak + 1, e + 1)
            if np.all(d[w] == s) and (not monotonic or np.all(s * np.diff(x[w]) > 0)):
                f[e] = True
        ok[s] = f
    return ok


# ---------------------------------------------------------------- FVG
def _first_after(arr, start, pred_val, below):
    """first index >= start with arr < pred_val (below) / arr > pred_val, else -1."""
    step = 256
    while start < len(arr):
        seg = arr[start:start + step]
        hit = np.flatnonzero(seg < pred_val) if below else np.flatnonzero(seg > pred_val)
        if len(hit):
            return start + int(hit[0])
        start += step
        step *= 4
    return -1


def fvgs(b, min_atr, atr_n, invalidate):
    """Bull FVG at i: low[i] > high[i-2], zone [high[i-2], low[i]]; bear mirrors. Known at the
    close of bar i. Invalidated at the close of the first later bar that closes beyond the far
    edge (close_through) or trades beyond it (full_fill)."""
    if len(b) < 3:
        return pd.DataFrame(columns=["dir", "bottom", "top", "i", "known", "invalid"])
    a = atr(b, atr_n)
    i = np.arange(2, len(b))
    rows = []
    for s, gap in ((1, b.l[i] > b.h[i - 2]), (-1, b.h[i] < b.l[i - 2])):
        for ii in i[gap]:
            bot, top = (b.h[ii - 2], b.l[ii]) if s == 1 else (b.h[ii], b.l[ii - 2])
            if top - bot < min_atr * a[ii]:
                continue
            if s == 1:
                probe = b.c if invalidate == "close_through" else b.l
                k = _first_after(probe, ii + 1, bot, below=True)
            else:
                probe = b.c if invalidate == "close_through" else b.h
                k = _first_after(probe, ii + 1, top, below=False)
            rows.append((s, bot, top, ii, b.t_close[ii], b.t_close[k] if k >= 0 else INF))
    f = pd.DataFrame(rows, columns=["dir", "bottom", "top", "i", "known", "invalid"])
    return f.sort_values("known", kind="stable").reset_index(drop=True)


# ---------------------------------------------------------------- liquidity targets
def liquidity_pools(b, n, m):
    """Swing highs (for longs) and lows (for shorts) on b with the minute they become known and
    the minute they are swept (close of the first M1 bar after `known` that trades beyond)."""
    hi, lo = swings(b, n)
    out = {}
    for s, piv, lvls, arr in ((1, hi, b.h, m["h"]), (-1, lo, b.l, m["l"])):
        known = b.t_close[piv + n]
        swept = np.full(len(piv), INF, np.int64)
        for r, (j, kn) in enumerate(zip(piv, known)):
            st = int(np.searchsorted(m["t"], kn))
            x = _first_after(arr, st, lvls[j], below=(s == -1))
            if x >= 0:
                swept[r] = m["t"][x] + 1
        df = pd.DataFrame({"level": lvls[piv], "known": known, "swept": swept})
        out[s] = df.sort_values("known", kind="stable").reset_index(drop=True)
    return out


# ---------------------------------------------------------------- pipeline
def _hhmm(s):
    h, mm = s.split(":")
    return int(h) * 60 + int(mm)


def signals(m, R, entry_tf, cache=None):
    """Entry signals for one rule set R (dict, see config.yaml `rules`). Returns one row per
    signal: decision minute T (close of the entry CRT confirming bar), M1 entry index k (open of
    the next bar), direction, sweep extreme, stop, the FVG used and the liquidity target."""
    cache = {} if cache is None else cache

    def get(key, fn):
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    n, k = R["swing_n"], R["crt_k"]
    E = get(("bars", entry_tf), lambda: resample(m, entry_tf))
    S = get(("bars", R["setup_tf"]), lambda: resample(m, R["setup_tf"]))
    B = get(("bars", R["bias_tf"]), lambda: resample(m, R["bias_tf"]))
    F = get(("bars", R["fvg_tf"]), lambda: resample(m, R["fvg_tf"]))
    L = get(("bars", R["liq_tf"]), lambda: resample(m, R["liq_tf"]))
    ev = get(("crt", entry_tf, n, k), lambda: crt_events(E, n, k))
    sev = get(("crt", R["setup_tf"], n, k), lambda: crt_events(S, n, k))
    bev = get(("crt", R["bias_tf"], n, k), lambda: crt_events(B, n, k))
    streak = get(("streak", R["setup_tf"], n, k, R["min_streak"], R["streak_monotonic"]),
                 lambda: streak_flags(sev, R["min_streak"], R["streak_monotonic"]))
    bema = get(("ema", R["bias_tf"], R["bias_ema"]), lambda: ema(B.c, R["bias_ema"]))
    fv = get(("fvg", R["fvg_tf"], R["fvg_min_atr"], R["atr_n"], R["fvg_invalidate"]),
             lambda: fvgs(F, R["fvg_min_atr"], R["atr_n"], R["fvg_invalidate"]))
    pools = get(("liq", R["liq_tf"], n), lambda: liquidity_pools(L, n, m))
    eatr = get(("atr", entry_tf, R["atr_n"]), lambda: atr(E, R["atr_n"]))

    cols = ["T", "k", "t_entry", "dir", "ext", "stop", "level", "fvg_bottom", "fvg_top",
            "fvg_known", "liq"]
    if not len(ev):
        return pd.DataFrame(columns=cols)
    T = ev.known.values
    d = ev.dir.values

    # Bias: last CRT on the bias TF (known <= T) has direction d, and price is beyond the EMA
    # of the last CLOSED bias bar.
    be = np.searchsorted(bev.known.values, T, side="right") - 1
    bdir = np.where(be >= 0, bev.dir.values[np.maximum(be, 0)], 0)
    kb = np.searchsorted(B.t_close, T, side="right") - 1
    warm = kb >= R["bias_ema"]
    price = E.c[ev.conf_i.values] if R["bias_price"] == "entry_close" else B.c[np.maximum(kb, 0)]
    above = price > bema[np.maximum(kb, 0)]
    ok = warm & (bdir == d) & np.where(d == 1, above, ~above)

    # Rule 1: setup-TF streak among CRTs known strictly before T (so a 15m entry CRT is "new").
    se = np.searchsorted(sev.known.values, T, side="left") - 1
    sdir_ok = np.where(d == 1, streak[1][np.maximum(se, 0)], streak[-1][np.maximum(se, 0)])
    ok &= (se >= 0) & sdir_ok
    if R.get("setup_max_age_min"):
        ok &= T - sev.known.values[np.maximum(se, 0)] <= R["setup_max_age_min"]

    # Entry at the open of the next bar; session and weekend checks on the entry minute.
    kk = np.searchsorted(m["t"], T)
    has = kk < len(m["t"])
    kk = np.minimum(kk, len(m["t"]) - 1)
    t_entry = m["t"][kk]
    ok &= has & (t_entry - T <= R["max_entry_gap_min"])
    mod = t_entry % 1440
    s0, s1 = _hhmm(R["session_utc"][0]), _hhmm(R["session_utc"][1])
    ok &= (mod >= s0) & (mod < s1)
    dow = ((t_entry // 1440) + 3) % 7                       # 0 = Monday (1970-01-01 was a Thursday)
    ok &= ~((dow == 4) & (mod >= _hhmm(R["friday_exit_utc"]))) & (dow < 5)

    # Rule 2 + 3: the entry sweep extreme lies inside a live HTF FVG of the same direction.
    out = []
    fk, finv = fv.known.values, fv.invalid.values
    fdir, fbot, ftop, fi = fv.dir.values, fv.bottom.values, fv.top.values, fv.i.values
    for r in np.flatnonzero(ok):
        t_ref = ev.t_sweep.values[r] if R["fvg_before_sweep"] else T[r]
        hi_idx = np.searchsorted(fk, t_ref, side="right")
        x = ev.ext.values[r]
        cand = (fdir[:hi_idx] == d[r]) & (finv[:hi_idx] > T[r]) & (fbot[:hi_idx] <= x) & (x <= ftop[:hi_idx])
        if R.get("fvg_max_age_bars"):
            cur = np.searchsorted(F.t_close, T[r], side="right") - 1
            cand &= cur - fi[:hi_idx] <= R["fvg_max_age_bars"]
        c = np.flatnonzero(cand)
        if not len(c):
            continue
        f = c[-1]                                              # the most recent qualifying FVG
        ci = ev.conf_i.values[r]
        stop = x - d[r] * R["sl_buffer_atr"] * eatr[ci]
        # liquidity target: nearest opposing swing known by T, unswept at T, beyond the entry open
        P = pools[d[r]]
        pe = np.searchsorted(P.known.values, T[r], side="right")
        lv = P.level.values[:pe]
        live = (P.swept.values[:pe] > T[r]) & (d[r] * (lv - m["o"][kk[r]]) > 0)
        liq = (lv[live].min() if d[r] == 1 else lv[live].max()) if live.any() else np.nan
        out.append((T[r], kk[r], t_entry[r], d[r], x, stop, ev.level.values[r],
                    fbot[f], ftop[f], fk[f], liq))
    return pd.DataFrame(out, columns=cols)
