"""Shared causal indicators (ATR) used by both the labeler and the feature set.

Everything here is strictly backward-looking: the value at bar ``t`` uses only
data at or before ``t``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def true_range(df: pd.DataFrame) -> pd.Series:
    """Wilder true range. TR[t] uses high/low at t and close at t-1 only."""
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Causal ATR via Wilder smoothing (EWM). ATR[t] depends only on TR<=t."""
    tr = true_range(df)
    # adjust=False reproduces Wilder's recursive average; min_periods enforces
    # that early bars (insufficient history) are NaN rather than leaking.
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
