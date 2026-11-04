"""Module B — ternary triple-barrier labeler (THE CRITICAL MODULE).

For each candidate signal bar ``t`` with a ``side`` in {+1 long, -1 short}:

    entry_idx   = t + N_CONFIRM
    entry_price = Close[entry_idx]
    atr_e       = ATR(14) at entry_idx
    D_TP        = K_TP_ATR * atr_e
    D_SL        = K_SL_ATR * atr_e

The barrier window STARTS at ``entry_idx`` (= t + N_CONFIRM), NOT at t. Scanning
runs over ``j in [entry_idx + 1, entry_idx + TAU_MAX]``. Intrabar ties (both TP
and SL touched on the same bar) resolve PESSIMISTICALLY to SL. If no barrier is
touched within TAU_MAX the row is a TIMEOUT and the realized return is recorded.

The label therefore uses future data up to ``t + N_CONFIRM + TAU_MAX``. That end
index is carried forward as ``label_horizon_end`` so the CPCV purge can excise it.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from config import Config
from indicators import atr


def label_signals(
    df: pd.DataFrame,
    signal_idx: Sequence[int],
    sides: Sequence[int],
    cfg: Config,
) -> pd.DataFrame:
    """Label a set of candidate signals with the ternary triple-barrier scheme.

    Parameters
    ----------
    df : OHLC frame (integer-positional access used throughout).
    signal_idx : positional bar indices ``t`` of each candidate signal.
    sides : matching direction in {+1, -1} for each signal.
    cfg : locked configuration.

    Returns
    -------
    DataFrame with one row per resolvable signal and columns:
    ``signal_idx, side, entry_idx, resolution_type, realized_return,
    label_horizon_end, D_TP, D_SL, entry_price``.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    close = df["close"].to_numpy()
    atr_arr = atr(df, 14).to_numpy()
    n = len(df)

    rows: list[dict] = []
    for t, side in zip(signal_idx, sides):
        side = int(side)
        entry_idx = t + cfg.N_CONFIRM
        horizon_end = entry_idx + cfg.TAU_MAX
        # Need the full barrier window to exist inside the series.
        if horizon_end >= n:
            continue
        atr_e = atr_arr[entry_idx]
        if not np.isfinite(atr_e) or atr_e <= 0.0:
            continue  # insufficient ATR history at entry -> not labelable

        entry_price = close[entry_idx]
        d_tp = cfg.K_TP_ATR * atr_e
        d_sl = cfg.K_SL_ATR * atr_e
        if side == 1:
            tp_level = entry_price + d_tp
            sl_level = entry_price - d_sl
        else:
            tp_level = entry_price - d_tp
            sl_level = entry_price + d_sl

        resolution = "TIMEOUT"
        realized_return = 0.0
        # Scan strictly AFTER entry_idx, through entry_idx + TAU_MAX inclusive.
        for j in range(entry_idx + 1, horizon_end + 1):
            if side == 1:
                tp_hit = high[j] >= tp_level
                sl_hit = low[j] <= sl_level
            else:
                tp_hit = low[j] <= tp_level
                sl_hit = high[j] >= sl_level

            if tp_hit and sl_hit:
                resolution = "SL"  # PESSIMISTIC same-bar tie
                break
            if sl_hit:
                resolution = "SL"
                break
            if tp_hit:
                resolution = "TP"
                break

        if resolution == "TIMEOUT":
            exit_price = close[horizon_end]
            realized_return = side * (exit_price - entry_price) / entry_price

        rows.append(
            {
                "signal_idx": int(t),
                "side": side,
                "entry_idx": int(entry_idx),
                "resolution_type": resolution,
                "realized_return": float(realized_return),
                "label_horizon_end": int(horizon_end),
                "D_TP": float(d_tp),
                "D_SL": float(d_sl),
                "entry_price": float(entry_price),
            }
        )

    out = pd.DataFrame(rows)
    if not out.empty:
        # Sanity: the entry must be exactly N_CONFIRM bars after the signal.
        assert (out["entry_idx"] - out["signal_idx"] == cfg.N_CONFIRM).all(), (
            "entry_idx must equal signal_idx + N_CONFIRM"
        )
    return out
