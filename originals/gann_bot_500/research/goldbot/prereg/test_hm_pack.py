#!/usr/bin/env python3
"""H-M pack self-checks — SYNTHETIC data only (no real market data, no gate
peeking). Run: python test_hm_pack.py — all asserts must pass."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from meta_lab import (FEATURES, build_context, cpcv_meta_run, evaluate_gates,
                      wilder_adx_d1)


def _synth_events(n=1200, seed=7, edge_feature=False):
    """Synthetic event set shaped like the real one: ~12h spacing, 73% base
    win rate, wins +$300 / losses -$700. If edge_feature, vol_pctile truly
    predicts the outcome (win prob 0.60 vs 0.88)."""
    rng = np.random.default_rng(seed)
    t_hr = np.arange(n) * 12 + rng.integers(0, 4, n)
    X = pd.DataFrame({
        "hour": rng.choice([12, 13, 14, 15, 16, 17, 18, 19, 20], n),
        "weekday": rng.integers(1, 5, n),
        "tie_entry": rng.integers(0, 2, n),
        "hivol": rng.integers(0, 2, n),
        "vol_pctile_prevday": rng.uniform(0, 1, n),
        "adx_d1": rng.uniform(10, 50, n),
        "news_day": (rng.uniform(0, 1, n) < 0.08).astype(int),
        "overshoot_atr": rng.uniform(0, 1.5, n),
    })[list(FEATURES)]
    if edge_feature:
        pwin = np.where(X["vol_pctile_prevday"] > 0.55, 0.88, 0.60)
    else:
        pwin = np.full(n, 0.73)
    y = (rng.uniform(0, 1, n) < pwin).astype(int)
    net = np.where(y == 1, 300.0, -700.0) + rng.normal(0, 40, n)
    era_new = t_hr > np.median(t_hr)
    return X, y, net, net - 60.0, t_hr, era_new


def test_no_edge_control_fails_gates():
    X, y, net, net90, t, era = _synth_events(edge_feature=False, seed=3)
    res = cpcv_meta_run(X, y, net, net90, t, era)
    g = evaluate_gates(res)
    up = res["pooled"]["uplift"]
    assert not (g["1_filtered_pf_ge_1.40"] and g["2_uplift_ge_0.15"]), \
        f"edge-free data passed profit gates (uplift {up:.3f})"
    assert abs(up) < 0.30 if np.isfinite(up) else True, \
        f"edge-free uplift suspiciously large: {up:.3f}"
    print(f"no-edge control ok: uplift {up:+.3f}, gates not passable from noise")


def test_planted_edge_is_detected():
    X, y, net, net90, t, era = _synth_events(edge_feature=True, seed=5)
    res = cpcv_meta_run(X, y, net, net90, t, era)
    p = res["pooled"]
    assert p["uplift"] > 0.15, f"planted edge not detected (uplift {p['uplift']:.3f})"
    assert p["pf_filtered"] > p["pf_unfiltered"]
    print(f"planted-edge ok: PF {p['pf_unfiltered']:.2f} -> {p['pf_filtered']:.2f} "
          f"(uplift {p['uplift']:+.2f}, retention {p['retention_unique']:.0%})")


def test_shuffled_label_control_kills_planted_edge():
    X, y, net, net90, t, era = _synth_events(edge_feature=True, seed=5)
    res = cpcv_meta_run(X, y, net, net90, t, era, shuffle_labels=True)
    up = res["pooled"]["uplift"]
    assert not np.isfinite(up) or up < 0.15, \
        f"shuffled labels still show uplift {up:.3f} — leakage in pipeline"
    print(f"shuffled-label control ok: uplift {up:+.3f} (edge destroyed)")


def test_threshold_chosen_on_train_only():
    X, y, net, net90, t, era = _synth_events(edge_feature=True, seed=9)
    r1 = cpcv_meta_run(X, y, net, net90, t, era)
    # corrupt outcomes ONLY inside the last time-sixth (test-fold territory
    # for splits containing group 5); taus of those splits must not move
    hi = t.max()
    zone = t > hi - (hi - t.min()) // 6
    net_c = net.copy(); net_c[zone] = -9999.0
    y_c = y.copy()  # labels unchanged; only TEST-fold nets corrupted
    r2 = cpcv_meta_run(X, y_c, net_c, net90, t, era)
    from itertools import combinations
    for (a, b) in zip(r1["splits"], r2["splits"]):
        if a.get("skipped") or b.get("skipped"):
            continue
        tg = list(combinations(range(6), 2))[a["split"]]
        if 5 in tg:                      # corrupted zone sits in the TEST fold
            assert a["tau"] == b["tau"], \
                f"split {a['split']}: tau moved with test-fold data!"
    print("train-only threshold ok: test-fold corruption cannot move tau")


def test_context_builders_causal():
    rng = np.random.default_rng(1)
    n_days, per_day = 320, 24
    n = n_days * per_day
    close = 2000 + np.cumsum(rng.normal(0, 0.5, n))
    open_ = np.empty(n); open_[0] = close[0]; open_[1:] = close[:-1]
    wig = np.abs(rng.normal(0, 0.3, n))
    idx = pd.date_range("2023-01-01", periods=n, freq="1h", tz="UTC")
    m1 = pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + wig,
                       "low": np.minimum(open_, close) - wig, "close": close},
                      index=idx)
    c1 = build_context(m1)
    m2 = m1.copy()
    cut = (n_days - 40) * per_day
    for col in m2.columns:
        m2.iloc[cut:, m2.columns.get_loc(col)] *= 5.0
    c2 = build_context(m2)
    safe = c1.index < m1.index[cut].normalize().tz_localize(None)
    a, b = c1[safe], c2[safe]
    assert np.allclose(a["adx_d1"].fillna(-1), b["adx_d1"].fillna(-1)), "ADX leaks"
    assert np.allclose(a["vol_pctile_prevday"].fillna(-1),
                       b["vol_pctile_prevday"].fillna(-1)), "vol pctile leaks"
    # and the day the perturbation starts must NOT yet see it (prev-day shift)
    d0 = m1.index[cut].normalize().tz_localize(None)
    if d0 in c1.index:
        assert np.isclose(c1.loc[d0, "adx_d1"], c2.loc[d0, "adx_d1"],
                          equal_nan=True), "same-day ADX leak (shift missing)"
    print("context causality ok: future perturbation invisible to past features")


def test_adx_sane():
    rng = np.random.default_rng(2)
    n = 400
    trend = np.cumsum(np.full(n, 2.0) + rng.normal(0, 0.5, n))
    chop = 2000 + rng.normal(0, 2.0, n)
    for name, px, want_high in (("trend", 2000 + trend, True), ("chop", chop, False)):
        d1 = pd.DataFrame({"open": px, "high": px + 3.0, "low": px - 3.0,
                           "close": px + rng.normal(0, 0.5, n)},
                          index=pd.date_range("2020-01-01", periods=n, tz="UTC"))
        adx = wilder_adx_d1(d1).iloc[-50:].mean()
        assert (adx > 30) == want_high, f"{name}: ADX {adx:.1f}"
    print("adx sanity ok: trending >30, chop <30")


if __name__ == "__main__":
    test_adx_sane()
    test_context_builders_causal()
    test_no_edge_control_fails_gates()
    test_planted_edge_is_detected()
    test_shuffled_label_control_kills_planted_edge()
    test_threshold_chosen_on_train_only()
    print("\nALL H-M PACK TESTS PASSED (synthetic only — no real data touched)")
