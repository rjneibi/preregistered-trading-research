import datetime as dt

import numpy as np
import pandas as pd

from lbo import sessions as S
from lbo.robustness import cost_breakeven, deflated_sharpe, reality_check, walk_forward


def utc(emin):
    return pd.Timestamp(emin * 60, unit="s", tz="UTC")


def test_london_open_utc_across_dst():
    # winter: 08:00 London = 08:00 UTC; summer: 07:00 UTC
    assert utc(S.variant_a_times(dt.date(2024, 1, 15), "utc0007", 60)["open"]).hour == 8
    assert utc(S.variant_a_times(dt.date(2024, 7, 15), "utc0007", 60)["open"]).hour == 7
    # UK switched on 2024-03-31; Monday 2024-04-01 is summer time
    assert utc(S.variant_a_times(dt.date(2024, 3, 29), "utc0007", 60)["open"]).hour == 8
    assert utc(S.variant_a_times(dt.date(2024, 4, 1), "utc0007", 60)["open"]).hour == 7


def test_ny_box_truncated_at_london_open_and_us_uk_mismatch_weeks():
    # 2024-03-11..28: US on EDT, UK still GMT -> 04:00 NY = 08:00 UTC = London open
    T = S.variant_a_times(dt.date(2024, 3, 13), "ny1904", 60)
    assert T["box_end"] == T["open"]
    assert utc(T["box_start"]).hour == 23          # 19:00 EDT previous day
    # deep winter: 04:00 NY = 09:00 UTC, after the 08:00 UTC London open -> truncated
    T = S.variant_a_times(dt.date(2024, 1, 10), "ny1904", 60)
    assert T["box_end"] == T["open"] and utc(T["box_start"]).hour == 0


def test_fixed_utc_box_leaves_gap_in_winter_only():
    w = S.variant_a_times(dt.date(2024, 1, 10), "utc0007", 60)
    s = S.variant_a_times(dt.date(2024, 7, 10), "utc0007", 60)
    assert w["open"] - w["box_end"] == 60 and s["open"] - s["box_end"] == 0


def test_variant_b_sessions_ny_clock():
    T = S.variant_b_times(dt.date(2024, 7, 10), "london", 30)
    assert utc(T["open"]).hour == 7                 # 03:00 EDT
    assert T["prev_end"] == T["open"] - 5           # Asia still open -> cut 5 min before
    T = S.variant_b_times(dt.date(2024, 1, 8), "asia", 30)   # Monday
    assert utc(T["open"]) == pd.Timestamp("2024-01-08 00:00", tz="UTC")   # Sunday 19:00 EST
    assert utc(T["prev_start"]).date() == dt.date(2024, 1, 5)            # Friday NY session


def test_reality_check_noise_not_significant():
    rng = np.random.default_rng(1)
    X = rng.normal(0, 1, (200, 500))
    r = reality_check(X, B=300, seed=2)
    assert r["p_white_rc"] > 0.05 and r["p_hansen_spa"] > 0.05


def test_reality_check_detects_real_edge():
    rng = np.random.default_rng(1)
    X = rng.normal(0, 1, (50, 1500))
    X[7] += 0.25
    assert reality_check(X, B=300, seed=2)["p_hansen_spa"] < 0.01


def test_deflated_sharpe_penalises_many_trials():
    rng = np.random.default_rng(3)
    r = rng.normal(0.05, 1, 1000)
    trials = rng.normal(0, 0.03, 1000)
    p_few, _, _ = deflated_sharpe(r, trials[:5], 5)
    p_many, _, _ = deflated_sharpe(r, trials, 1000)
    assert p_many < p_few


def test_walk_forward_picks_best_train_config():
    dates = pd.bdate_range("2015-01-01", "2019-12-31").date
    T = len(dates)
    S_ = np.zeros((3, T))
    N_ = np.ones((3, T))
    S_[1] = 0.1                                       # config 1 always best
    r, n, picks = walk_forward(S_, N_, dates, 24, 6, 10)
    assert all(p["cfg"] == 1 for p in picks) and np.isclose(r.sum() / n.sum(), 0.1)


def test_cost_breakeven():
    assert np.isclose(cost_breakeven([0, 0.5, 1, 2], [0.1, 0.05, 0.0, -0.1]), 1.0)
    assert cost_breakeven([0, 1], [-0.1, -0.2]) == 0.0
