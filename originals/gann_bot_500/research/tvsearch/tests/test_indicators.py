"""Indicator + engine checks. RSI uses the published Wilder/StockCharts worked example (same seed and smoothing as
TradingView's ta.rsi); EMA/ATR/VWAP are checked against direct loop implementations of the Pine reference code."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import ind  # noqa: E402
import engine  # noqa: E402

CLOSE = [44.3389, 44.0902, 44.1497, 43.6124, 44.3278, 44.8264, 45.0955, 45.4245, 45.8433, 46.0826, 45.8931, 46.0328,
         45.6140, 46.2820, 46.2820, 46.0028, 46.0328, 46.4116, 46.2222, 45.6439]


def test_rsi_stockcharts_example():
    r = ind.rsi(np.array(CLOSE), 14)
    assert np.isnan(r[:14]).all()
    assert r[14] == pytest.approx(70.53, abs=0.01)
    assert r[15] == pytest.approx(66.32, abs=0.01)


def test_ema_matches_pine_loop():
    rng = np.random.default_rng(1); x = 100 + rng.normal(0, 1, 300).cumsum(); n = 9
    a = 2 / (n + 1); ref = np.full(len(x), np.nan); ref[n - 1] = x[:n].mean()
    for i in range(n, len(x)):
        ref[i] = a * x[i] + (1 - a) * ref[i - 1]
    np.testing.assert_allclose(ind.ema(x, n), ref, rtol=1e-12, equal_nan=True)


def test_atr_matches_wilder_loop():
    rng = np.random.default_rng(2); c = 100 + rng.normal(0, 1, 200).cumsum()
    h = c + rng.uniform(0, 1, 200); l = c - rng.uniform(0, 1, 200)
    t = [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, 200)]
    ref = np.full(200, np.nan); ref[13] = np.mean(t[:14])
    for i in range(14, 200):
        ref[i] = (ref[i - 1] * 13 + t[i]) / 14
    np.testing.assert_allclose(ind.atr(h, l, c, 14), ref, rtol=1e-12, equal_nan=True)


def test_vwap_ohlc4_session_reset():
    o = np.array([10, 11, 12, 20, 21.]); h = o + 1; l = o - 1; c = o + 0.5; v = np.array([100, 200, 300, 50, 150.])
    src = (o + h + l + c) / 4
    vw, sd = ind.vwap(src, v, np.array([1, 1, 1, 2, 2]))
    assert vw[0] == pytest.approx(src[0])
    assert vw[2] == pytest.approx((src[:3] * v[:3]).sum() / v[:3].sum())
    assert vw[3] == pytest.approx(src[3])                      # new session -> reset
    assert vw[4] == pytest.approx((src[3:] * v[3:]).sum() / v[3:].sum())
    m = vw[2]; assert sd[2] == pytest.approx(np.sqrt((v[:3] * (src[:3] - m) ** 2).sum() / v[:3].sum()))


def test_cross_helpers():
    a = np.array([1, 2, 3, 2, 1.]); b = np.full(5, 2.0)
    assert ind.cross_up(a, b).tolist() == [False, False, True, False, False]
    assert ind.cross_dn(a, b).tolist() == [False, False, False, False, True]


def test_supertrend_follows_trend():
    x = np.r_[np.linspace(100, 150, 100), np.linspace(150, 100, 100)]
    d, _ = ind.supertrend(x + 0.5, x - 0.5, x, 10, 3)
    assert d[60] == 1 and d[180] == -1


def _D(o, h, l, c, sess=None):
    N = len(o); sess = np.zeros(N, int) if sess is None else np.asarray(sess)
    D = dict(t=np.arange(N) * 60, o=np.asarray(o, float), h=np.asarray(h, float), l=np.asarray(l, float),
             c=np.asarray(c, float), sp=np.zeros(N), sess=sess, N=N, tf=1)
    last = np.r_[np.flatnonzero(sess[1:] != sess[:-1]), N - 1]
    sid = np.cumsum(np.r_[1, sess[1:] != sess[:-1]]) - 1
    D["sid"] = sid; D["sess_last"] = last[sid]
    return D


NOCOST = dict(slip=0.0, comm=0.0)


def test_engine_next_open_fill_and_tp():
    D = _D([10, 10, 11, 12, 13], [10, 10.5, 11.5, 15.5, 13], [10, 9.5, 10.5, 11.5, 12], [10, 10, 11, 12, 13])
    L = np.array([True, 0, 0, 0, 0], bool); S = np.zeros(5, bool)
    tr = engine.simulate(D, L, S, dict(tp=5.0), NOCOST)
    assert tr["e"][0] == 1 and tr["x"][0] == 3 and tr["pnl"][0] == pytest.approx(5.0) and tr["why"][0] == "tp"


def test_engine_stop_wins_when_both_in_bar():
    D = _D([10, 10, 10], [10, 10, 16], [10, 10, 4], [10, 10, 10])
    tr = engine.simulate(D, np.array([1, 0, 0], bool), np.zeros(3, bool), dict(tp=5.0, sl=5.0), NOCOST)
    assert tr["why"][0] == "sl" and tr["pnl"][0] == pytest.approx(-5.0)


def test_engine_stop_and_reverse():
    D = _D([10, 10, 11, 12, 11, 10], [10] * 6, [10] * 6, [10, 10, 11, 12, 11, 10])
    D["h"] = np.maximum(D["o"], D["c"]); D["l"] = np.minimum(D["o"], D["c"])
    L = np.array([1, 0, 0, 0, 0, 0], bool); S = np.array([0, 0, 0, 1, 0, 0], bool)
    tr = engine.simulate(D, L, S, dict(tp=50.0, opp=True), NOCOST)
    assert tr["d"].tolist() == [1, -1]
    assert tr["x"][0] == 4 and tr["e"][1] == 4 and tr["pnl"][0] == pytest.approx(11 - 10)


def test_engine_eos_flat_and_no_cross_session_entry():
    D = _D([10, 10, 11, 12, 12, 12], [10, 10, 11, 12, 12, 12], [10, 10, 11, 12, 12, 12], [10, 10, 11, 12, 12, 12],
           sess=[0, 0, 0, 1, 1, 1])
    L = np.array([1, 0, 1, 0, 0, 0], bool)
    tr = engine.simulate(D, L, np.zeros(6, bool), dict(tp=50.0, eos=True), NOCOST)
    assert len(tr["e"]) == 1 and tr["x"][0] == 2 and tr["why"][0] == "eos" and tr["pnl"][0] == pytest.approx(1.0)
