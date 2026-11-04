import importlib.util
import os
from datetime import datetime, timezone

import numpy as np
import pytest

from src import clock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ep(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())


@pytest.mark.parametrize("when,want", [
    ((2017, 1, 10, 12), False),   # US winter
    ((2017, 7, 3, 12), True),     # US summer
    ((2018, 3, 20, 12), True),    # After the US switch, before the EU one, US rule applies through 2018
    ((2018, 10, 30, 12), True),   # After the EU switch back, before the US one
    ((2019, 3, 20, 12), False),   # Same date a year later, EU rule applies from 2019
    ((2019, 4, 5, 12), True),
    ((2019, 10, 30, 12), False),  # After the EU switch back
    ((2011, 7, 1, 12), True),     # ASSUMED-CLOCK year follows the US rule
])
def test_shift_by_date(when, want):
    assert bool(clock.shifted(np.array([ep(*when)]))[0]) is want


def test_true_utc_moves_only_shifted_bars():
    s = np.array([ep(2017, 1, 10, 12), ep(2017, 7, 3, 12)])
    assert (s - clock.true_utc(s)).tolist() == [0, 3600]


def test_switch_edges_are_exact():
    a, b = clock.eu_bounds(2024)
    assert a == ep(2024, 3, 31, 1) and b == ep(2024, 10, 27, 1)
    a, b = clock.us_dst_bounds(2016)
    assert a == ep(2016, 3, 13, 2) and b == ep(2016, 11, 6, 2)
    s = np.array([a - 1, a, b - 1, b])
    assert clock.shifted(s).tolist() == [False, True, True, False]


def test_equal_to_the_audit_copy():
    p = os.path.join(ROOT, "audit", "phaseC", "clockfix.py")
    sp = importlib.util.spec_from_file_location("clockfix", p)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    s = np.arange(ep(2010, 1, 3), ep(2026, 6, 20), 3607 * 11)
    assert (clock.true_utc(s) == m.true_utc(s)).all()
