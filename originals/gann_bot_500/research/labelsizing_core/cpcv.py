"""Module D — Combinatorial Purged Cross-Validation splitter.

N_GROUPS=6 contiguous time groups, K_TEST=2 test groups per split -> C(6,2)=15
splits and phi(6,2)=C(5,1)=5 backtest paths.

Purge + embargo around each test fold are applied to the TRAINING set. A train
row is dropped when *either* its label horizon ``[entry_idx, label_horizon_end]``
*or* its feature lookback window ``[t - L_FEATURE_MAX, t]`` overlaps the test
span. Concretely, with each row keyed by its signal bar ``t`` and the test span
running ``[test_start, test_end]``, a train row is purged iff

    test_start - TAU_MAX  <=  t  <=  test_end + max(EMBARGO, L_FEATURE_MAX)

The left bound is governed by the label horizon (a row entered up to TAU_MAX
before the test could still be resolving inside it); the right bound by feature
lookback + embargo (a row after the test whose 1512-bar window reaches back into
it). After purging, every split MUST retain a non-empty train and test set.
"""

from __future__ import annotations

from itertools import combinations
from typing import Iterator

import numpy as np
import pandas as pd

from config import Config


class CombinatorialPurgedCV:
    """Yield (train_idx, test_idx, split_id) over rows keyed by signal bar t."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.n_groups = cfg.N_GROUPS
        self.k_test = cfg.K_TEST

    def _group_bounds(self, t_values: np.ndarray) -> list[tuple[int, int]]:
        """Partition the *bar-index* range into N contiguous groups."""
        lo, hi = int(t_values.min()), int(t_values.max())
        edges = np.linspace(lo, hi + 1, self.n_groups + 1).astype(int)
        return [(int(edges[g]), int(edges[g + 1]) - 1) for g in range(self.n_groups)]

    def split(self, labels: pd.DataFrame) -> Iterator[tuple[np.ndarray, np.ndarray, int]]:
        """Generate purged train/test positional indices into ``labels``.

        ``labels`` must carry ``signal_idx`` (the bar ``t``) and
        ``label_horizon_end``. Yields positional row indices.
        """
        cfg = self.cfg
        t = labels["signal_idx"].to_numpy()
        bounds = self._group_bounds(t)
        right_margin = max(cfg.EMBARGO, cfg.L_FEATURE_MAX)

        split_id = 0
        for test_groups in combinations(range(self.n_groups), self.k_test):
            # Test span = union of the selected groups (they may be disjoint).
            test_mask = np.zeros(len(labels), dtype=bool)
            spans: list[tuple[int, int]] = []
            for g in test_groups:
                g_lo, g_hi = bounds[g]
                spans.append((g_lo, g_hi))
                test_mask |= (t >= g_lo) & (t <= g_hi)

            # Purge train rows overlapping ANY test span (+ asymmetric margins).
            purge_mask = np.zeros(len(labels), dtype=bool)
            for g_lo, g_hi in spans:
                left = g_lo - cfg.TAU_MAX
                right = g_hi + right_margin
                purge_mask |= (t >= left) & (t <= right)

            train_mask = (~test_mask) & (~purge_mask)
            train_idx = np.where(train_mask)[0]
            test_idx = np.where(test_mask)[0]

            if len(train_idx) == 0 or len(test_idx) == 0:
                raise RuntimeError(
                    f"CPCV split {split_id} (test groups {test_groups}) collapsed "
                    f"after purge: train={len(train_idx)}, test={len(test_idx)}"
                )

            yield train_idx, test_idx, split_id
            split_id += 1
