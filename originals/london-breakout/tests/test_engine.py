"""Hand-computed reference cases for the fill logic in lbo.engine."""
import numpy as np
import pytest

from lbo.engine import simulate, simulate_managed


def bars(rows, sp=0.0):
    a = np.array(rows, dtype=float)
    return dict(o=a[:, 0], h=a[:, 1], l=a[:, 2], c=a[:, 3], sp=np.full(len(a), sp))


def test_long_target_hit_gross():
    # entry at bar0 open 100, stop 99 (1R = 1), target 2R = 102 reached on bar 2
    m = bars([[100, 100.5, 99.5, 100.2], [100.2, 101, 100, 100.8], [100.8, 102.1, 100.5, 102]])
    r, ei, why = simulate(m, 0, 3, +1, 100, 99, [2], 0, 0, 0)
    assert r[0] == pytest.approx(2.0) and ei[0] == 2 and why[0] == 1


def test_same_bar_stop_and_target_is_stop():
    m = bars([[100, 100.2, 99.9, 100], [100, 102.5, 98.5, 101]])
    r, ei, why = simulate(m, 0, 2, +1, 100, 99, [2], 0, 0, 0)
    assert r[0] == pytest.approx(-1.0) and why[0] == -1 and ei[0] == 1


def test_stop_gap_fills_at_open():
    m = bars([[100, 100.2, 99.9, 100], [98, 98.5, 97.5, 98]])
    r, _, why = simulate(m, 0, 2, +1, 100, 99, [3], 0, 0, 0)
    assert r[0] == pytest.approx(-2.0) and why[0] == -1


def test_time_exit_at_forced_bar_open():
    m = bars([[100, 100.5, 99.5, 100], [100, 100.6, 99.6, 100.3], [100.4, 100.9, 100, 100.5]])
    r, ei, why = simulate(m, 0, 2, +1, 100, 99, [5], 0, 0, 0)
    assert r[0] == pytest.approx(0.4) and why[0] == 0 and ei[0] == 2


def test_short_mirror():
    m = bars([[100, 100.5, 99.5, 99.8], [99.8, 100, 97.9, 98]])
    r, _, why = simulate(m, 0, 2, -1, 100, 101, [2], 0, 0, 0)
    assert r[0] == pytest.approx(2.0) and why[0] == 1


def test_costs_spread_slippage_commission():
    # spread 0.2 -> buy at 100.1; slip 0.05 -> 100.15; target limit at 102 (bid must reach it:
    # mid high 102.2 -> bid high 102.1 >= 102). commission 0.1. R = (102-100.15-0.1)/1
    m = bars([[100, 100.2, 99.95, 100], [100, 102.2, 99.95, 102]], sp=0.2)
    r, _, why = simulate(m, 0, 2, +1, 100, 99, [2], 1, 0.05, 0.1)
    assert why[0] == 1 and r[0] == pytest.approx(1.75)
    # double costs: buy at 100 + 0.2 + 0.1 = 100.3; bid high = 102.0 -> still touches 102
    r2, _, _ = simulate(m, 0, 2, +1, 100, 99, [2], 2, 0.05, 0.1)
    assert r2[0] == pytest.approx(102 - 100.3 - 0.2)


def test_stop_entry_fill_bar_ignores_target_but_not_stop():
    # buy stop at 100.5; bar0 trades 100.4 -> 103 -> 99.0: stop hit on fill bar, no target credit
    m = bars([[100.4, 103, 99.0, 100], [100, 104, 100, 104]])
    r, _, why = simulate(m, 0, 2, +1, 100.5, 99.5, [2], 0, 0, 0, kind="stop")
    assert why[0] == -1 and r[0] == pytest.approx(-1.0)
    m2 = bars([[100.4, 103, 100.3, 100], [100, 104, 100, 104]])
    r, ei, why = simulate(m2, 0, 2, +1, 100.5, 99.5, [2], 0, 0, 0, kind="stop")
    assert why[0] == 1 and ei[0] == 1      # target only counted from bar 1


def test_multi_rr_vector_matches_individual():
    rng = np.random.default_rng(0)
    c = 100 + np.cumsum(rng.normal(0, 0.3, 300))
    o = np.r_[100, c[:-1]]
    h = np.maximum(o, c) + 0.1
    l = np.minimum(o, c) - 0.1
    m = dict(o=o, h=h, l=l, c=c, sp=np.full(300, 0.05))
    rrs = [1, 1.5, 2, 3, np.inf]
    rv, _, _ = simulate(m, 5, 250, +1, o[5], o[5] - 1.0, rrs, 1, 0.02, 0)
    for rr, want in zip(rrs, rv):
        got, _, _ = simulate_managed(m, 5, 250, +1, o[5], o[5] - 1.0, rr, 1, 0.02, 0)
        assert got == pytest.approx(want)


def test_break_even_then_stop_at_entry():
    # +1R reached on bar1, then price falls back to entry on bar2 -> exit at 0R (gross)
    m = bars([[100, 100.2, 99.8, 100], [100, 101.2, 100.1, 101], [101, 101, 99.5, 99.6]])
    r, _, why = simulate_managed(m, 0, 3, +1, 100, 99, 3, 0, 0, 0, be_at=1.0)
    assert why == -1 and r == pytest.approx(0.0)


def test_partial_take_profit():
    # 50% off at 1R (101), rest stopped at break-even? no BE -> rest stopped at 99: 0.5*1 + 0.5*-1
    m = bars([[100, 100.2, 99.8, 100], [100, 101.2, 100.1, 101], [101, 101, 98.5, 98.6]])
    r, _, _ = simulate_managed(m, 0, 3, +1, 100, 99, 3, 0, 0, 0, partial_at=1.0)
    assert r == pytest.approx(0.0)
