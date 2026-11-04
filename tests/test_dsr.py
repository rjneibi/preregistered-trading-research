import numpy as np
import pytest

from src.dsr import dsr


def sample(t, n=1000, seed=7):
    """Normal returns set to an exact t-statistic."""
    r = np.random.default_rng(seed).standard_normal(n)
    r = (r - r.mean()) / r.std(ddof=1)
    return r + t / np.sqrt(n)


def test_gate_needs_a_t_near_six_at_the_full_ledger():
    assert dsr(sample(5.0), 179000) < 0.95 < dsr(sample(7.5), 179000)
    assert dsr(sample(6.2), 179000) == pytest.approx(0.95, abs=0.04)


def test_more_trials_lower_the_score():
    r = sample(4.0)
    assert dsr(r, 34) > dsr(r, 569) > dsr(r, 179000)


def test_degenerate_input():
    assert dsr([1.0, 1.0, 1.0, 1.0], 10) is None
    assert dsr([1.0, 2.0], 10) is None
