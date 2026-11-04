"""Phase B known-answer tests for the audit engine. Must pass before any cross-check uses it."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from nbe import closed_resample, lots_for_risk, simulate

N = math.nan


def run(bars, side=1, stop=1.0, tgt=2.0, mb=10, sp=0.0, **kw):
    o, h, l, c = map(np.array, zip(*bars))
    return simulate(o.astype(float), h.astype(float), l.astype(float), c.astype(float), sp, np.array([0]), np.array([side]), np.array([stop]), np.array([tgt]), mb, **kw)


def test_long_target_to_the_cent():
    r = run([(100, 100.5, 99.5, 100), (100, 102.5, 99.5, 102)])
    assert r.pnl[0] == pytest.approx(2.0) and r.reason[0] == 1


def test_long_stop_to_the_cent():
    r = run([(100, 100.5, 98.5, 99)])
    assert r.pnl[0] == pytest.approx(-1.0) and r.reason[0] == 0


def test_short_with_spread_uses_ask_for_all_checks():
    # short fills at bid 100, stop is 101 on the ASK. Bid high 100.8 + 0.3 spread = 101.1 is a stop-out.
    r = run([(100, 100.8, 99.9, 100)], side=-1, sp=0.3)
    assert r.reason[0] == 0 and r.pnl[0] == pytest.approx(-1.0)


def test_long_pays_spread_at_entry():
    r = run([(100, 103, 99.8, 103)], sp=0.5)
    assert r.entry[0] == 100.5 and r.exit[0] == pytest.approx(102.5)


def test_same_bar_both_barriers_is_a_stop():
    r = run([(100, 103, 98, 100)])
    assert r.reason[0] == 0 and r.ambiguous[0]


def test_gap_through_stop_fills_at_gap():
    r = run([(100, 100.2, 99.9, 100), (95, 96, 94, 95)])
    assert r.exit[0] == 95 and r.pnl[0] == pytest.approx(-5.0)


def test_gap_through_target_fills_at_gap():
    r = run([(100, 100.2, 99.9, 100), (105, 106, 104, 105)])
    assert r.exit[0] == 105


def test_stop_slippage_is_against_the_trader():
    r = run([(100, 100.5, 98.5, 99)], slip=0.1)
    assert r.entry[0] == pytest.approx(100.1) and r.pnl[0] == pytest.approx(-1.1)


def test_time_stop_at_last_close():
    r = run([(100, 100.2, 99.9, 100.1)] * 3, mb=3, stop=N, tgt=N)
    assert r.reason[0] == 2 and r.exit_i[0] == 2 and r.pnl[0] == pytest.approx(0.1)


def walk(n, seed, sub=8):
    rng = np.random.default_rng(seed)
    x = 1000 + np.cumsum(rng.normal(0, 0.05, n * sub))
    x = x.reshape(n, sub)
    return x[:, 0], x.max(1), x.min(1), x[:, -1]


def test_zero_edge_random_entries_lose_the_cost():
    o, h, l, c = walk(300_000, 1)
    rng = np.random.default_rng(2)
    i = np.sort(rng.choice(299_000, 8000, replace=False))
    s = rng.choice([-1, 1], len(i))
    d = np.full(len(i), 1.0)
    cost = 0.05
    r = simulate(o, h, l, c, cost, i, s, d, d, 5000)
    se = r.pnl.std() / math.sqrt(len(r.pnl))
    assert abs(r.pnl.mean() + cost) < 4 * se


def test_buy_and_hold_is_price_change_minus_costs():
    o, h, l, c = walk(5000, 3)
    r = simulate(o, h, l, c, 0.2, np.array([0]), np.array([1]), np.array([N]), np.array([N]), 5000, slip=0.05, comm=0.07)
    assert r.pnl[0] == pytest.approx(c[-1] - o[0] - 0.2 - 2 * 0.05 - 0.07)


def test_doubling_costs_changes_pnl_by_the_cost():
    o, h, l, c = walk(40_000, 4)
    i = np.arange(0, 39_000, 40)
    s = np.where(i % 80 == 0, 1, -1)
    d = np.full(len(i), 5000.0)
    a = simulate(o, h, l, c, 0.1, i, s, d, d, 30, comm=0.05)
    b = simulate(o, h, l, c, 0.2, i, s, d, d, 30, comm=0.10)
    assert (b.pnl - a.pnl).mean() == pytest.approx(-0.15, abs=1e-9)


def test_mirror_symmetry():
    o, h, l, c = walk(40_000, 5)
    i = np.arange(0, 39_000, 37)
    s = np.ones(len(i), int)
    d = np.full(len(i), 1.0)
    a = simulate(o, h, l, c, 0.0, i, s, d, d, 400)
    K = 2000.0
    b = simulate(K - o, K - l, K - h, K - c, 0.0, i, -s, d, d, 400)
    assert np.allclose(a.pnl, b.pnl) and np.array_equal(a.exit_i, b.exit_i)


@pytest.mark.parametrize("eq,stop", [(10_000, 5.0), (7_333, 3.7), (2_000, 20.0), (123_456, 11.1)])
def test_stop_out_never_exceeds_budget(eq, stop):
    lots = lots_for_risk(eq, 0.01, stop, 100, 0.01, 0.01)
    assert lots * stop * 100 <= eq * 0.01 + 1e-9
    assert (lots + 0.01) * stop * 100 > eq * 0.01


def test_below_min_lot_refuses():
    assert lots_for_risk(500, 0.01, 20.0, 100, 0.01, 0.01) == 0.0


def test_resample_drops_forming_bar_and_uses_closed_data():
    t = np.arange(0, 7200 + 600, 60)
    o = h = l = c = (t / 60.0).astype(float)
    T, O, H, L, C = closed_resample(t, o, h, l, c, 3600)
    assert list(T) == [0, 3600] and O[1] == 60 and C[1] == 119 and H[1] == 119 and L[1] == 60
