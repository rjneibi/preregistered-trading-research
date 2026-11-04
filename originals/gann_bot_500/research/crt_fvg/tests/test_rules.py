"""Hand-built cases for swings, CRT, streaks, FVGs and fills, plus the no-look-ahead proofs."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from crt_fvg.data import load_m1, resample, truncate
from crt_fvg.engine import simulate
from crt_fvg.rules import crt_events, fvgs, signals, streak_flags, swings, INF

CFG = yaml.safe_load(open(Path(__file__).resolve().parents[1] / "config.yaml"))
MON = pd.Timestamp("2026-10-26 08:00", tz="UTC").value // 60_000_000_000   # a Monday


def m1(l, h=None, c=None, o=None, t0=MON, sp=0.0):
    l = np.asarray(l, float)
    h = l + 1 if h is None else np.asarray(h, float)
    c = l + 0.5 if c is None else np.asarray(c, float)
    o = l + 0.5 if o is None else np.asarray(o, float)
    return dict(t=t0 + np.arange(len(l)), o=o, h=h, l=l, c=c, sp=np.full(len(l), sp))


# ---------------------------------------------------------------- swings / CRT
def test_swing_needs_n_strict_bars_each_side():
    b = resample(m1([5, 4, 3, 4, 5, 6, 5, 2.5, 4]), 1)
    hi, lo = swings(b, 2)
    assert list(lo) == [2]                       # bar 6 (l=5) ties bar 4 on the left -> no pivot
    assert list(hi) == [5]


def test_bull_crt_close_back_on_sweep_bar():
    c = np.array([5, 4, 3, 4, 5, 6, 5, 3.5, 4]) + 0.5
    c[7] = 3.5                                   # sweep bar trades to 2.5, closes back above 3
    b = resample(m1([5, 4, 3, 4, 5, 6, 5, 2.5, 4], c=c), 1)
    ev = crt_events(b, 2, 1)
    bull = ev[ev.dir == 1]
    assert len(bull) == 1
    e = bull.iloc[0]
    assert (e.level, e.ext, e.sweep_i, e.conf_i) == (3, 2.5, 7, 7)
    assert e.known == b.t_close[7]               # observable only when the sweep bar closes
    assert e.known > b.t_close[2 + 2]            # pivot known at bar j+N, sweep strictly later


def test_failed_sweep_consumes_level_and_k_window():
    l = [5, 4, 3, 4, 5, 6, 5, 2.5, 4]
    c = np.array(l) + 0.5
    c[7] = 2.8                                   # closes below the level
    c[8] = 3.6                                   # one bar later closes back above
    b = resample(m1(l, c=c), 1)
    assert (crt_events(b, 2, 1).dir == 1).sum() == 0          # K=1: no CRT, level consumed
    e = crt_events(b, 2, 2).query("dir == 1").iloc[0]         # K=2: CRT confirmed on bar 8
    assert (e.sweep_i, e.conf_i, e.ext) == (7, 8, 2.5)


def test_bear_crt_mirrors_bull():
    l = np.array([5, 4, 3, 4, 5, 6, 5, 2.5, 4.0])
    c = np.array(l) + 0.5
    c[7] = 3.5
    bull = crt_events(resample(m1(l, c=c), 1), 2, 1).query("dir == 1")
    mir = crt_events(resample(m1(-l - 1, h=-l, c=-c, o=-l - 0.5), 1), 2, 1).query("dir == -1")
    assert len(bull) == len(mir) == 1
    assert mir.iloc[0].level == -3 and mir.iloc[0].ext == -2.5


def test_streak_requires_same_direction_and_higher_lows():
    ev = pd.DataFrame({"dir": [1, 1, -1, 1, 1, 1], "ext": [2, 3, 9, 4, 3, 5]})
    ok = streak_flags(ev, 2, True)
    assert list(ok[1]) == [False, True, False, False, False, True]
    assert list(streak_flags(ev, 2, False)[1]) == [False, True, False, False, True, True]


# ---------------------------------------------------------------- FVG
def test_bull_fvg_zone_and_close_through_invalidation():
    h = [10, 12, 13, 12, 11]
    l = [9, 10, 11, 9.95, 9.5]
    c = [9.5, 11.5, 12.5, 10.5, 9.9]
    b = resample(m1(l, h=h, c=c), 1)
    f = fvgs(b, 0.0, 14, "close_through").query("dir == 1").iloc[0]
    assert (f.bottom, f.top, f.known) == (10, 11, b.t_close[2])
    assert f.invalid == b.t_close[4]             # bar 3 only wicks through, bar 4 closes below 10
    g = fvgs(b, 0.0, 14, "full_fill").query("dir == 1").iloc[0]
    assert g.invalid == b.t_close[3]
    assert fvgs(b, 5.0, 14, "close_through").query("dir == 1").empty   # size filter vs ATR


# ---------------------------------------------------------------- engine fills
SYM = dict(spread=0.0, comm=0.0, tick=0.01)
COST = dict(slip_ticks=1, spread_mode="fixed")


def sig(k, d, stop, liq=np.nan):
    return pd.DataFrame([dict(k=k, dir=d, stop=stop, liq=liq)])


def test_stop_first_when_both_hit_in_one_bar():
    m = m1(l=[99.5, 98.9], h=[100.2, 101.5], o=[100, 100], c=[100, 100])
    tr = simulate(m, sig(0, 1, 99.0), 1.0, SYM, COST, 20 * 60 + 45)
    entry = 100.01
    assert tr.why[0] == "stop"
    assert tr.R[0] == pytest.approx((99.0 - 0.01 - entry) / (entry - 99.0))


def test_gap_through_stop_fills_at_open_and_target_has_no_slippage():
    m = m1(l=[99.5, 98.0], h=[100.2, 98.6], o=[100, 98.5], c=[100, 98.2])
    tr = simulate(m, sig(0, 1, 99.0), 1.0, SYM, COST, 20 * 60 + 45)
    assert tr.exit[0] == pytest.approx(98.49)
    m = m1(l=[99.5, 99.8], h=[100.2, 102.5], o=[100, 100], c=[100, 101])
    tr = simulate(m, sig(0, 1, 99.0), 2.0, dict(SYM, comm=0.02), COST, 20 * 60 + 45)
    assert tr.why[0] == "target" and tr.R[0] == pytest.approx(2.0 - 0.02 / 1.01)


def test_short_with_spread_and_liquidity_target():
    m = m1(l=[99.5, 97.0], h=[100.2, 100.05], o=[100, 99], c=[100, 98], sp=0.0)
    tr = simulate(m, sig(0, -1, 101.0, liq=98.0), "liq", dict(SYM, spread=0.2), COST, 20 * 60 + 45)
    entry = 100 - 0.1 - 0.01
    assert tr.entry[0] == pytest.approx(entry)
    assert tr.why[0] == "target" and tr.exit[0] == 98.0      # ask low 97.1 <= 98; ask high 100.15 < 101
    assert tr.R[0] == pytest.approx((entry - 98.0) / (101.0 - entry))


def test_friday_exit_and_one_open_trade():
    fri = pd.Timestamp("2026-10-30 20:40", tz="UTC").value // 60_000_000_000
    m = m1(l=[99.9] * 10, h=[100.1] * 10, o=[100] * 10, c=[100] * 10, t0=fri)
    s = pd.concat([sig(0, 1, 99.0), sig(2, 1, 99.0)])
    tr = simulate(m, s, 3.0, SYM, COST, 20 * 60 + 45)
    assert len(tr) == 1 and tr.why[0] == "friday"
    assert tr.t_exit[0] == fri + 5 + 1 and tr.exit[0] == 100.0


# ---------------------------------------------------------------- no look-ahead
def synthetic(days=260, seed=1):
    """24/5 random-walk M1 with weekends removed, gold-like scale."""
    rng = np.random.default_rng(seed)
    t = []
    d0 = MON // 1440
    for d in range(int(days * 7 / 5)):
        if (d0 + d + 3) % 7 < 5:
            t.append((d0 + d) * 1440 + np.arange(1440))
    t = np.concatenate(t)
    c = 2000 + np.cumsum(rng.normal(0, 0.35, len(t)))
    o = np.r_[2000, c[:-1]]
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.12, len(t)))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.12, len(t)))
    return dict(t=t, o=o, h=h, l=l, c=c, sp=np.full(len(t), 0.3))


def rules(**kw):
    return dict(CFG["rules"], **kw)


def _same_past(full, part, cut):
    a = full[full.t_entry < cut].reset_index(drop=True)
    b = part[part.t_entry < cut].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    return len(a)


@pytest.mark.parametrize("entry_tf", [5, 15])
def test_truncating_the_future_does_not_change_past_signals(entry_tf):
    m = synthetic()
    R = rules()
    full = signals(m, R, entry_tf)
    assert len(full) >= 5, "synthetic data too quiet to test anything"
    for frac in (0.3, 0.55, 0.8):
        cut = int(m["t"][int(len(m["t"]) * frac)]) + 7       # deliberately not on a bar boundary
        n = _same_past(full, signals(truncate(m, cut), R, entry_tf), cut)
        assert n > 0


def test_truncation_with_loose_rules_and_every_option_switched():
    """More signals and the non-default branches (K=2, 1H bias, HTF close, full_fill, ages)."""
    m = synthetic(seed=3)
    R = rules(min_streak=1, crt_k=2, bias_tf=60, bias_price="htf_close", fvg_before_sweep=False,
              fvg_invalidate="full_fill", fvg_max_age_bars=48, setup_max_age_min=240)
    full = signals(m, R, 5)
    assert len(full) >= 30
    for frac in (0.4, 0.7):
        cut = int(m["t"][int(len(m["t"]) * frac)]) + 2
        assert _same_past(full, signals(truncate(m, cut), R, 5), cut) > 5


def test_rewriting_the_future_does_not_change_past_signals():
    m = synthetic(seed=2)
    R = rules(bias_tf=60)
    full = signals(m, R, 5)
    rng = np.random.default_rng(99)
    cut_i = int(len(m["t"]) * 0.5)
    cut = int(m["t"][cut_i])
    alt = {k: v.copy() for k, v in m.items()}
    step = rng.normal(0, 0.8, len(m["t"]) - cut_i)               # a different, wilder future
    alt["c"][cut_i:] = m["c"][cut_i - 1] + np.cumsum(step)
    alt["o"][cut_i:] = np.r_[m["c"][cut_i - 1], alt["c"][cut_i:-1]]
    alt["h"][cut_i:] = np.maximum(alt["o"][cut_i:], alt["c"][cut_i:]) + 0.5
    alt["l"][cut_i:] = np.minimum(alt["o"][cut_i:], alt["c"][cut_i:]) - 0.5
    assert _same_past(full, signals(alt, R, 5), cut) > 0
    assert not full[full.t_entry >= cut].reset_index(drop=True).equals(
        signals(alt, R, 5).query("t_entry >= @cut").reset_index(drop=True))


def test_signals_are_causal_on_real_gold_data():
    p = Path(CFG["data"]["npz_dir"]) / "XAUUSD.npz"
    if not p.exists():
        pytest.skip("cached Dukascopy data not present")
    m = load_m1(CFG["data"]["npz_dir"], "XAUUSD", "2016-01-01", "2017-01-01")   # signals only, no P&L
    full = signals(m, rules(), 5)
    for frac in (0.5, 0.75):
        cut = int(m["t"][int(len(m["t"]) * frac)]) + 3
        assert _same_past(full, signals(truncate(m, cut), rules(), 5), cut) > 0
