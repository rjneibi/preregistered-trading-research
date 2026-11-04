"""
Run:  pytest test_modules.py -v
"""

import numpy as np
import pandas as pd
import pytest

from regime import (
    MEAN_REVERSION,
    MOMENTUM,
    NEUTRAL,
    RegimeGate,
    Thresholds,
    calibrate_thresholds,
    classify_series,
    efficiency_ratio,
    flip_count,
)
from sizing import XAUUSD_TYPICAL, SymbolSpec, _floor_to_step, atr, position_size

RNG = np.random.default_rng(7)


# ---------------------------------------------------------------- sizing

def test_sizing_known_answer():
    # equity 10k, risk 1% -> $100 budget
    # ATR 5.0 * mult 1.5 -> stop 7.5 price units
    # XAUUSD typical: $100 per unit per lot -> risk/lot = $750
    # raw = 0.1333 -> floored to step 0.01 -> 0.13 lots
    lots = position_size(10_000, 0.01, 7.5, XAUUSD_TYPICAL)
    assert lots == pytest.approx(0.13)
    # and 0.13 lots really respects the budget
    assert lots * 7.5 * XAUUSD_TYPICAL.value_per_unit_per_lot <= 100 + 1e-9


def test_sizing_never_exceeds_budget_randomised():
    for _ in range(500):
        equity = RNG.uniform(500, 1_000_000)
        risk = RNG.uniform(0.001, 0.02)
        stop = RNG.uniform(0.5, 25.0)
        lots = position_size(equity, risk, stop, XAUUSD_TYPICAL)
        budget = equity * risk
        loss_at_stop = lots * stop * XAUUSD_TYPICAL.value_per_unit_per_lot
        assert loss_at_stop <= budget + 1e-6
        assert lots == 0.0 or lots >= XAUUSD_TYPICAL.volume_min


def test_sizing_skips_when_min_lot_breaks_budget():
    # $300 account, 0.5% risk = $1.50 budget; stop 7.5 units means even
    # 0.01 lots risks $7.50 -> must skip, never clamp up to min lot
    assert position_size(300, 0.005, 7.5, XAUUSD_TYPICAL) == 0.0


def test_sizing_respects_volume_max():
    tiny_max = SymbolSpec(0.01, 1.0, 0.01, 0.01, volume_max=0.5)
    assert position_size(1_000_000, 0.02, 1.0, tiny_max) == 0.5


def test_sizing_garbage_inputs_return_zero():
    for eq, rf, sd in [(-1, 0.01, 5), (1000, 0, 5), (1000, 0.01, 0)]:
        assert position_size(eq, rf, sd, XAUUSD_TYPICAL) == 0.0


def test_floor_to_step_float_noise():
    assert _floor_to_step(0.1333333, 0.01) == 0.13
    assert _floor_to_step(0.13, 0.01) == 0.13          # exact stays exact
    assert _floor_to_step(0.9999999999, 0.1) == 1.0    # 1e-9 guard works
    assert str(_floor_to_step(0.06 + 0.07, 0.01)) == "0.13"


def test_atr_basic_shape():
    df = pd.DataFrame(
        {
            "high": np.linspace(101, 120, 60),
            "low": np.linspace(99, 118, 60),
            "close": np.linspace(100, 119, 60),
        }
    )
    a = atr(df, n=14)
    assert a.iloc[:14].isna().all()
    assert (a.iloc[20:] > 0).all()


# ---------------------------------------------------------------- ER

def test_er_straight_line_is_one():
    close = pd.Series(np.arange(100.0, 200.0))
    er = efficiency_ratio(close, 14)
    assert er.iloc[20:].round(9).eq(1.0).all()


def test_er_pure_chop_is_zero():
    close = pd.Series(100.0 + np.tile([0.0, 1.0], 50))
    er = efficiency_ratio(close, 14)  # even window: net change 0
    assert er.iloc[20:].max() < 1e-9


def test_er_warmup_is_nan():
    close = pd.Series(np.arange(100.0, 130.0))
    assert efficiency_ratio(close, 14).iloc[:14].isna().all()


# ---------------------------------------------------------------- gate

T = Thresholds(enter_mr=0.25, exit_mr=0.35, exit_mom=0.45, enter_mom=0.60)


def test_threshold_ordering_enforced():
    with pytest.raises(ValueError):
        Thresholds(enter_mr=0.4, exit_mr=0.3, exit_mom=0.45, enter_mom=0.6)


def test_hysteresis_holds_state_between_exit_and_enter():
    g = RegimeGate(T, confirm_bars=1)
    seq = [0.50, 0.65, 0.50, 0.44, 0.30, 0.20, 0.30, 0.40]
    got = [g.update(v) for v in seq]
    assert got == [
        NEUTRAL,          # 0.50 inside dead zone
        MOMENTUM,         # 0.65 >= enter_mom
        MOMENTUM,         # 0.50 > exit_mom -> retained (naive gate flips here)
        NEUTRAL,          # 0.44 <= exit_mom -> released
        NEUTRAL,          # 0.30 not <= enter_mr yet
        MEAN_REVERSION,   # 0.20 <= enter_mr
        MEAN_REVERSION,   # 0.30 < exit_mr -> retained
        NEUTRAL,          # 0.40 >= exit_mr -> released
    ]


def test_direct_flip_momentum_to_mr_allowed():
    g = RegimeGate(T, confirm_bars=1)
    assert g.update(0.7) == MOMENTUM
    assert g.update(0.1) == MEAN_REVERSION  # crash through both bands


def test_confirm_bars_delays_and_filters_fakeouts():
    g = RegimeGate(T, confirm_bars=3)
    assert g.update(0.7) == NEUTRAL   # 1st bar of evidence
    assert g.update(0.7) == NEUTRAL   # 2nd
    assert g.update(0.7) == MOMENTUM  # 3rd confirms
    # a single-bar fakeout must not flip a confirmed state
    g2 = RegimeGate(T, confirm_bars=2)
    g2.update(0.7); g2.update(0.7)
    assert g2.state == MOMENTUM
    assert g2.update(0.10) == MOMENTUM  # one bar of MR evidence: ignored
    assert g2.update(0.70) == MOMENTUM  # evidence gone, counter reset


def test_nan_resets_to_neutral():
    g = RegimeGate(T, confirm_bars=1)
    g.update(0.7)
    assert g.update(float("nan")) == NEUTRAL


def test_hysteresis_reduces_flips_vs_naive():
    er = pd.Series(0.55 + 0.10 * np.sign(np.sin(np.arange(300))))  # noise
    naive = pd.Series(np.where(er >= 0.60, MOMENTUM, NEUTRAL))
    hyst = classify_series(er, T, confirm_bars=2)
    assert flip_count(hyst) < flip_count(naive)


def test_classify_series_matches_stateful_gate():
    er = pd.Series(RNG.uniform(0, 1, 200))
    g = RegimeGate(T, confirm_bars=2)
    manual = [g.update(v) for v in er]
    vector = classify_series(er, T, confirm_bars=2)
    assert manual == vector.tolist()


def test_calibrate_thresholds_orders_correctly():
    er = pd.Series(RNG.beta(2, 3, 5000))  # skewed like real ER dists
    t = calibrate_thresholds(er)
    assert t.enter_mr < t.exit_mr <= t.exit_mom < t.enter_mom
