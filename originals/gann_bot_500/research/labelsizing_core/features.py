"""Module C — strictly causal (backward-looking) feature set at bar t.

Every column is computable from data at or before ``t``. The HMM regime is fit on
a rolling 63*24 = 1512-bar window (this is what sets ``L_FEATURE_MAX``) at fixed
absolute stride boundaries, then carried forward — causal *and* prefix-stable.

``assert_no_forward_leak`` empirically verifies causality: it recomputes the
feature frame on truncated prefixes and asserts the last row is identical to the
full-series computation at the same index. Any forward reference would break that
equality and raise.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config
from hmm_regime import GaussianHMM2
from indicators import atr

_HMM_STRIDE = 168  # refit weekly (in H1 bars); boundaries are absolute multiples


def _hmm_regime_series(df: pd.DataFrame, cfg: Config) -> pd.Series:
    """Rolling-window HMM regime, assigned forward from each refit boundary.

    Boundaries are absolute multiples of ``_HMM_STRIDE`` with at least
    ``L_FEATURE_MAX`` bars of history. The window [b - L, b) is fit (deterministic,
    no RNG) and its terminal regime is applied to bars [b, next_boundary). This is
    causal (the window ends strictly before the bars it labels) and prefix-stable
    (truncating at any index reproduces the same boundary fits).
    """
    log_ret = np.log(df["close"]).diff().fillna(0.0)
    feat = np.column_stack([log_ret.to_numpy(), np.abs(log_ret.to_numpy())])
    n = len(df)
    regime = np.zeros(n, dtype=np.int8)

    win = cfg.L_FEATURE_MAX
    boundaries = range(((win + _HMM_STRIDE - 1) // _HMM_STRIDE) * _HMM_STRIDE,
                       n, _HMM_STRIDE)
    last_b = None
    last_state = 0
    for b in boundaries:
        window = feat[b - win:b]
        # Standardise within window for numerical stability (deterministic).
        mu = window.mean(axis=0)
        sd = window.std(axis=0)
        sd[sd == 0] = 1.0
        model = GaussianHMM2().fit((window - mu) / sd)
        last_state = model.last_state((window - mu) / sd)
        regime[b:] = last_state  # forward-fill until overwritten by next b
        last_b = b
    return pd.Series(regime, index=df.index, name="hmm_regime")


def compute_features(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Build the causal feature frame aligned to ``df``'s index."""
    atr14 = atr(df, 14)
    body = (df["close"] - df["open"]).abs()

    # Scale-invariant displacement on the *previous* bar's body.
    med_body = body.rolling(100, min_periods=20).median()
    floor = np.maximum(med_body, 1e-4 * atr14)
    displacement = (body.shift(1) / floor.replace(0, np.nan))

    # Wick-based FVG (3-candle): BISI (bullish) / SIBI (bearish), ATR-normalised.
    high2 = df["high"].shift(2)
    low2 = df["low"].shift(2)
    bisi = (df["low"] - high2).clip(lower=0.0) / atr14   # buyside imbalance
    sibi = (low2 - df["high"]).clip(lower=0.0) / atr14   # sellside imbalance

    # Bar close location.
    bcl = (df["close"] - df["low"]) / (df["high"] - df["low"]).clip(lower=1e-8)

    # ATR-margin structure break using retrospectively-confirmed swings.
    w = 3
    roll_max = df["high"].rolling(2 * w + 1, center=True).max()
    roll_min = df["low"].rolling(2 * w + 1, center=True).min()
    is_swing_high = df["high"] >= roll_max
    is_swing_low = df["low"] <= roll_min
    # A swing at k is only confirmed at k+w; shift the level forward so no future
    # data is used, then forward-fill the most recent confirmed swing.
    prior_swing_high = df["high"].where(is_swing_high).shift(w).ffill()
    prior_swing_low = df["low"].where(is_swing_low).shift(w).ffill()
    sb_up = ((df["close"] - prior_swing_high) / atr14 >= 0.15).astype(float)
    sb_down = ((prior_swing_low - df["close"]) / atr14 >= 0.15).astype(float)

    out = pd.DataFrame(
        {
            "atr14": atr14,
            "displacement": displacement,
            "fvg_bisi": bisi,
            "fvg_sibi": sibi,
            "bcl": bcl,
            "sb_up": sb_up,
            "sb_down": sb_down,
        },
        index=df.index,
    )

    if cfg.USE_HMM_REGIME:
        out["hmm_regime"] = _hmm_regime_series(df, cfg).astype(float)

    return out


def assert_no_forward_leak(
    df: pd.DataFrame, cfg: Config, sample_indices: list[int]
) -> None:
    """Empirical causality check: prefix recomputation must match the full run.

    For each sampled index i we recompute features on ``df.iloc[:i+1]`` and assert
    the row at i equals the full-series feature row at i (within tolerance). A
    forward-looking column would differ and raise here.
    """
    full = compute_features(df, cfg)
    for i in sample_indices:
        if i < cfg.L_FEATURE_MAX + _HMM_STRIDE:
            continue  # not enough history for a meaningful HMM comparison
        prefix = compute_features(df.iloc[: i + 1], cfg)
        a = full.iloc[i]
        b = prefix.iloc[-1]
        both = pd.concat([a, b], axis=1).dropna()
        if both.empty:
            continue
        diff = (both.iloc[:, 0] - both.iloc[:, 1]).abs()
        assert (diff < 1e-8).all(), (
            f"forward leak detected at index {i}: columns "
            f"{list(diff[diff >= 1e-8].index)}"
        )
