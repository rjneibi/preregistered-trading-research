"""Combinatorial Purged Cross-Validation splitter (adapted from
research/labelsizing_core/cpcv.py; Config dependency replaced by explicit
constructor args, rows keyed by epoch-hour instead of bar index).

N_GROUPS=6 contiguous time groups, K_TEST=2 test groups per split ->
C(6,2)=15 splits and phi(6,2)=5 backtest paths.

Purge + embargo are applied to the TRAINING set. With each row keyed by its
signal time ``t`` (epoch-hours) and a test span ``[test_start, test_end]``, a
train row is purged iff

    test_start - tau_max  <=  t  <=  test_end + max(embargo, l_feature_max)

Left bound: label horizon (a row entered up to tau_max before the test could
still be resolving inside it). Right bound: feature lookback + embargo.
Every split MUST retain non-empty train and test sets.
"""

from __future__ import annotations

from itertools import combinations
from typing import Iterator

import numpy as np
import pandas as pd


class CombinatorialPurgedCV:
    """Yield (train_idx, test_idx, split_id) over rows keyed by signal time."""

    def __init__(self, n_groups: int = 6, k_test: int = 2,
                 tau_max: int = 24, embargo: int = 24,
                 l_feature_max: int = 40) -> None:
        assert 0 < k_test < n_groups
        self.n_groups = n_groups
        self.k_test = k_test
        self.tau_max = tau_max
        self.embargo = embargo
        self.l_feature_max = l_feature_max

    def _group_bounds(self, t_values: np.ndarray) -> list[tuple[int, int]]:
        """Partition the signal-time range into N contiguous groups."""
        lo, hi = int(t_values.min()), int(t_values.max())
        edges = np.linspace(lo, hi + 1, self.n_groups + 1).astype(int)
        return [(int(edges[g]), int(edges[g + 1]) - 1)
                for g in range(self.n_groups)]

    def split(self, labels: pd.DataFrame
              ) -> Iterator[tuple[np.ndarray, np.ndarray, int]]:
        """``labels`` must carry ``signal_idx``. Yields positional indices."""
        t = labels["signal_idx"].to_numpy()
        bounds = self._group_bounds(t)
        right_margin = max(self.embargo, self.l_feature_max)

        split_id = 0
        for test_groups in combinations(range(self.n_groups), self.k_test):
            test_mask = np.zeros(len(labels), dtype=bool)
            spans: list[tuple[int, int]] = []
            for g in test_groups:
                g_lo, g_hi = bounds[g]
                spans.append((g_lo, g_hi))
                test_mask |= (t >= g_lo) & (t <= g_hi)

            purge_mask = np.zeros(len(labels), dtype=bool)
            for g_lo, g_hi in spans:
                left = g_lo - self.tau_max
                right = g_hi + right_margin
                purge_mask |= (t >= left) & (t <= right)

            train_mask = (~test_mask) & (~purge_mask)
            train_idx = np.where(train_mask)[0]
            test_idx = np.where(test_mask)[0]

            if len(train_idx) == 0 or len(test_idx) == 0:
                raise RuntimeError(
                    f"CPCV split {split_id} (test groups {test_groups}) "
                    f"collapsed after purge: train={len(train_idx)}, "
                    f"test={len(test_idx)}"
                )

            yield train_idx, test_idx, split_id
            split_id += 1

    def split_test_groups(self) -> list[tuple[int, ...]]:
        """Split-ordered list of test-group tuples (split_id = position)."""
        return list(combinations(range(self.n_groups), self.k_test))

    def paths(self) -> list[dict[int, int]]:
        """The phi(N,K) backtest paths: each path maps every group to the
        split whose test fold supplies that group's out-of-sample stretch;
        each group is tested exactly K times across all splits, giving K
        appearances -> K paths per the AFML ch.12 construction (phi(6,2)=5)."""
        groups_splits: dict[int, list[int]] = {g: [] for g in range(self.n_groups)}
        for sid, tg in enumerate(self.split_test_groups()):
            for g in tg:
                groups_splits[g].append(sid)
        n_paths = len(groups_splits[0])
        for g, sids in groups_splits.items():
            assert len(sids) == n_paths, "unbalanced group/test coverage"
        return [{g: groups_splits[g][k] for g in range(self.n_groups)}
                for k in range(n_paths)]
