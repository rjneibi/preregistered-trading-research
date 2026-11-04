"""M1 loading and resampling. Times are int64 epoch MINUTES, UTC. A resampled bar is
known only at t_close = t_open + tf; nothing downstream may read it before then."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class Bars:
    tf: int
    t_open: np.ndarray
    t_close: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    i0: np.ndarray       # index of the first M1 bar inside each bar

    def __len__(self):
        return len(self.t_open)


def load_m1(npz_dir, symbol, start=None, end=None):
    z = np.load(Path(npz_dir) / f"{symbol}.npz")
    m = {k: z[k] for k in ("t", "o", "h", "l", "c", "sp")}
    keep = np.ones(len(m["t"]), bool)
    if start:
        keep &= m["t"] >= pd.Timestamp(start, tz="UTC").value // 60_000_000_000
    if end:
        keep &= m["t"] < pd.Timestamp(end, tz="UTC").value // 60_000_000_000
    return {k: v[keep] for k, v in m.items()}


def truncate(m, t_cut):
    """M1 data as it existed just before minute t_cut (used by the no-look-ahead tests)."""
    keep = m["t"] < t_cut
    return {k: v[keep] for k, v in m.items()}


def resample(m, tf, offset_min=0):
    """UTC-aligned bars of tf minutes (offset_min shifts the grid, e.g. for broker-aligned 4H).
    The trailing bar is dropped when the data stops before it closes, so a bar's existence
    never depends on minutes that have not happened yet."""
    t = m["t"]
    key = (t - offset_min) // tf
    st = np.flatnonzero(np.diff(key, prepend=key[0] - 1))
    en = np.r_[st[1:], len(t)]
    t_open = key[st] * tf + offset_min
    b = Bars(tf, t_open, t_open + tf, m["o"][st], np.maximum.reduceat(m["h"], st),
             np.minimum.reduceat(m["l"], st), m["c"][en - 1], st)
    if len(b) and t[-1] + 1 < b.t_close[-1]:
        b = Bars(tf, *(a[:-1] for a in (b.t_open, b.t_close, b.o, b.h, b.l, b.c, b.i0)))
    return b


def atr(b, n=14):
    """Wilder ATR; value at i uses bars <= i only."""
    pc = np.r_[b.c[0], b.c[:-1]]
    tr = np.maximum(b.h - b.l, np.maximum(np.abs(b.h - pc), np.abs(b.l - pc)))
    out = np.empty(len(tr))
    w = min(n, len(tr))
    out[:w] = np.cumsum(tr[:w]) / np.arange(1, w + 1)
    for i in range(n, len(tr)):
        out[i] = out[i - 1] + (tr[i] - out[i - 1]) / n
    return out


def ema(x, n):
    out = np.empty(len(x))
    a = 2.0 / (n + 1)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out
