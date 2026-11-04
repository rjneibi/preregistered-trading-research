"""Module E — per-split, side-conditioned R-bar_timeout estimate.

R-bar_timeout[side] is the mean realized return of TIMEOUT-resolved rows, computed
ONLY from the purged TRAINING rows of a given CPCV split and conditioned on side
(pooling long and short neutralises directional edge). If a side has no timeout
training rows in a split, we fall back to 0.0 and log it.

These rows are, by construction of cpcv.py, already outside the purge zone — this
module never reads rows inside it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def estimate_timeout_means(
    labels: pd.DataFrame, train_idx: np.ndarray, split_id: int
) -> dict[int, float]:
    """Return {+1: R-bar_long, -1: R-bar_short} from purged train TIMEOUT rows."""
    train = labels.iloc[train_idx]
    timeouts = train[train["resolution_type"] == "TIMEOUT"]
    out: dict[int, float] = {}
    for side in (1, -1):
        rows = timeouts[timeouts["side"] == side]
        if len(rows) == 0:
            out[side] = 0.0
            print(
                f"[timeout_baseline] split {split_id} side {side:+d}: "
                f"0 timeout train rows -> R-bar fallback 0.0"
            )
        else:
            out[side] = float(rows["realized_return"].mean())
    return out
