"""Variant B ("elitrade basic"): break of previous-session 15m levels on the 5m chart."""
import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import sessions as S

LEVELS = ("session_hl", "fractal", "pivot")


def trading_dates_ny(m):
    ts = pd.to_datetime(m["t"] * 60, unit="s", utc=True).tz_convert(S.NY)
    return sorted({d for d in ts.date if d.weekday() < 5})


def _fractals(h, l, n=2):
    """Indices of swing highs / lows: strictly beyond the n bars on each side."""
    sh, sl = [], []
    for j in range(n, len(h) - n):
        if h[j] > h[j - n:j].max() and h[j] > h[j + 1:j + n + 1].max():
            sh.append(j)
        if l[j] < l[j - n:j].min() and l[j] < l[j + 1:j + n + 1].min():
            sl.append(j)
    return np.array(sh, int), np.array(sl, int)


def build_sessions(m, b15, dates, session, window_max=60):
    """One row per (date, session): levels of every type, marked 5 minutes before the open.

    Only 15m bars that have CLOSED by open-5min are used; the reference price for picking
    the nearest level is the last 1m close before open-5min.
    """
    t = m["t"]
    rows = []
    for d in dates:
        T = S.variant_b_times(d, session, window_max)
        j0 = np.searchsorted(b15["t"], T["prev_start"])
        j1 = np.searchsorted(b15["t"], T["prev_end"] - 15, side="right")   # bars closed by prev_end
        io, ie = np.searchsorted(t, [T["open"], T["exit"]])
        iref = np.searchsorted(t, T["open"] - 5) - 1
        if j1 - j0 < 4 or io >= len(t) or t[io] >= T["open"] + 5 or ie <= io or iref < 0:
            rows.append(dict(date=d, ok=False))
            continue
        H, L, C = b15["h"][j0:j1], b15["l"][j0:j1], b15["c"][j0:j1]
        ref = m["c"][iref]
        r = dict(date=d, ok=True, open_t=T["open"], exit_t=T["exit"], i_open=io, i_exit=ie, ref=ref)
        r["session_hl_up"], r["session_hl_dn"] = H.max(), L.min()
        sh, sl = _fractals(H, L)
        up = H[sh][H[sh] > ref] if sh.size else np.array([])
        dn = L[sl][L[sl] < ref] if sl.size else np.array([])
        r["fractal_up"] = up.min() if up.size else np.nan
        r["fractal_dn"] = dn.max() if dn.size else np.nan
        hh, ll, cc = H.max(), L.min(), C[-1]
        P = (hh + ll + cc) / 3
        piv = np.array([P, 2 * P - ll, 2 * P - hh, P + (hh - ll), P - (hh - ll)])
        r["pivot_up"] = piv[piv > ref].min() if (piv > ref).any() else np.nan
        r["pivot_dn"] = piv[piv < ref].max() if (piv < ref).any() else np.nan
        rows.append(r)
    return pd.DataFrame(rows).set_index("date")


@dataclass(frozen=True)
class SigB:
    session: str = "london"
    level: str = "session_hl"
    window: int = 30
    vol_k: float = 0.0
    buffer_atr: float = 0.0


def signals(m, b5, vr5, sess, cfg: SigB):
    """All 5m bars in the first `window` minutes that close beyond a level, in time order."""
    ok = sess.ok.values.astype(bool)
    up_all = sess[f"{cfg.level}_up"].values if ok.any() else None
    dn_all = sess[f"{cfg.level}_dn"].values if ok.any() else None
    pos = np.flatnonzero(ok)
    cols = ["day", "dir", "i_entry", "planned", "sig_h", "sig_l", "atr", "kind"]
    if pos.size == 0:
        return pd.DataFrame(columns=cols)
    open_t = sess.open_t.values[pos].astype(np.int64)
    js = np.searchsorted(b5["t"], open_t)
    je = np.searchsorted(b5["t"], open_t + cfg.window - 5, side="right")
    cnt = np.maximum(je - js, 0)
    if cnt.sum() == 0:
        return pd.DataFrame(columns=cols)
    idx = np.concatenate([np.arange(a, b) for a, b in zip(js, je)])
    drow = np.repeat(pos, cnt)
    C, A = b5["c"][idx], b5["atr"][idx]
    up_l, dn_l = up_all[drow].astype(float), dn_all[drow].astype(float)
    buf = cfg.buffer_atr * A
    with np.errstate(invalid="ignore"):
        lo = C > up_l + buf
        sh = C < dn_l - buf
        if cfg.vol_k > 0:
            v = vr5[idx] >= cfg.vol_k
            lo &= v
            sh &= v
    q = np.flatnonzero(lo | sh)
    i_entry = np.searchsorted(m["t"], b5["t"][idx[q]] + 5)
    out = pd.DataFrame(dict(day=drow[q], dir=np.where(lo[q], 1, -1), i_entry=i_entry,
                            sig_h=b5["h"][idx[q]], sig_l=b5["l"][idx[q]], atr=A[q], kind="market"))
    out = out[out.i_entry < sess.i_exit.values[out.day.values]]
    out["planned"] = m["o"][out.i_entry.values]
    return out.reset_index(drop=True)[cols]
