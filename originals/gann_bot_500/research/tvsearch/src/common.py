"""Dataset catalogue shared by both phases: which base series feeds which timeframe, and per-bar arrays."""
import numpy as np

import data
import ind

TFS = [1, 2, 3, 5, 10, 15, 30, 45, 60, 120, 240, "D"]
ASSETS = ["XAU", "SPY", "QQQ"]
_BASE = {}


def base(asset, kind):
    key = (asset, kind)
    if key not in _BASE:
        if asset == "XAU":
            df = data.load_xau(kind)
            df = data.trim_partial(df, 1300)
        else:
            df = data.load_us(asset, kind)
            if kind != "1d":
                df = data.trim_partial(df, 385 if kind == "1m" else 380 if kind == "5m" else 300)
        _BASE[key] = df
    return _BASE[key]


def source_for(asset, tf, horizon):
    """horizon 'primary' (last 30 days) or 'long'. Returns (base kind, note)."""
    if asset == "XAU":
        if horizon == "primary":
            return ("m1", "broker M1") if tf != "D" else ("m5", "broker M5 -> D")
        return ("m1", "broker M1 (from 2026-07-15)") if tf in (1, 2, 3) else ("m5", "broker M5 (from 2025-05-29)")
    if tf == "D":
        return "1d", "Yahoo daily"
    if horizon == "primary":
        return "1m", "Yahoo 1m (30 days)"
    if tf in (1, 2, 3):
        return "1m", "Yahoo 1m (30 days only - no longer 1m history is free)"
    if tf in (5, 10, 15, 30, 45):
        return "5m", "Yahoo 5m (57 days)"
    return "1h", "Yahoo 1h (2 years)"


def dataset(asset, tf, horizon):
    kind, note = source_for(asset, tf, horizon)
    df = base(asset, kind)
    native = {"m1": 1, "m5": 5, "1m": 1, "5m": 5, "1h": 60, "1d": "D"}[kind]
    if tf != native:
        df = data.resample(df, tf)
    D = data.arrays(df, tf)
    D["asset"], D["note"], D["kind"] = asset, note, kind
    D["atr14"] = ind.atr(D["h"], D["l"], D["c"], 14)
    D["ohlc4"] = (D["o"] + D["h"] + D["l"] + D["c"]) / 4
    return D


def window(D, horizon, days=30):
    t = D["t"]
    return (t[-1] - days * 86400, None) if horizon == "primary" else (None, None)


def random_masks(rng, D, nL, nS, t0):
    """Random-entry baseline: same number of long and short signals, at uniformly random bars inside the window."""
    lo = 0 if t0 is None else int(np.searchsorted(D["t"], t0))
    N = D["N"]
    L = np.zeros(N, bool); S = np.zeros(N, bool)
    k = min(nL + nS, max(N - 1 - lo, 0))
    if k <= 0:
        return L, S
    pos = rng.choice(np.arange(lo, N - 1), size=k, replace=False)
    L[pos[:min(nL, k)]] = True; S[pos[min(nL, k):]] = True
    return L, S
