#!/usr/bin/env python3
"""Pack self-checks. Run: python test_prereg_pack.py -- all asserts must pass."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cost_matrix import CostMatrix, build_matrix, save_matrix
from regime import event_regime_mask, mechanism_control, trailing_pct_rank


def _two_regime_bars(n_days=400, lo=2e-5, hi=2e-4, seed=3):
    """Geometric returns: dollar vol scales with price, so relATR is level-invariant
    (an arithmetic walk with fixed dollar vol injects a spurious relATR trend via
    the denominator -- exactly the artifact relative ATR exists to avoid)."""
    rng = np.random.default_rng(seed)
    n = n_days * 1440
    sd = np.where(np.arange(n) < n // 2, lo, hi)
    close = 2000.0 * np.exp(np.cumsum(rng.normal(0, sd)))
    open_ = np.empty(n); open_[0] = close[0]; open_[1:] = close[:-1]
    wig = np.abs(rng.normal(0, sd * 0.4)) * close
    idx = pd.date_range("2022-01-01", periods=n, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + wig,
                         "low": np.minimum(open_, close) - wig, "close": close},
                        index=idx)


def test_regime_two_state():
    df = _two_regime_bars()
    events = np.array([d * 1440 + 720 for d in range(400)])   # one noon event/day
    mask = event_regime_mask(df, events, threshold=0.5, pct_window=100, atr_window=14)
    # Deterministic contracts:
    assert not mask[:114].any(), "warmup must be conservative (False)"
    trans = mask[205:245]            # 10x vol jump vs still-low-vol trailing window
    assert trans.mean() > 0.90, f"expansion must pass ({trans.mean():.2f})"
    # Statistical contracts -- WIDE bands over LONG windows on purpose: ATR(14) is
    # heavily autocorrelated, so a 65-day stretch holds only ~4 effective samples
    # and its pass rate is seed-lottery. Do NOT tighten these bands.
    era1 = mask[120:199]             # steady low-vol era, post-warmup
    era2 = mask[250:399]             # steady high-vol era, post-renormalization
    assert 0.10 < era1.mean() < 0.90, f"filter must not fence off the low-vol era ({era1.mean():.2f})"
    assert 0.10 < era2.mean() < 0.90, f"filter must re-normalize in high-vol era ({era2.mean():.2f})"
    print(f"regime contract ok: warmup 0.00, expansion {trans.mean():.2f}, "
          f"era pass rates {era1.mean():.2f}/{era2.mean():.2f} (adaptive, not a date fence)")


def test_regime_no_lookahead():
    df = _two_regime_bars()
    events = np.array([d * 1440 + 720 for d in range(400)])
    m1 = event_regime_mask(df, events, threshold=0.5, pct_window=100)
    df2 = df.copy()
    cut = 250 * 1440
    for c in ("open", "high", "low", "close"):
        df2.iloc[cut:, df2.columns.get_loc(c)] *= 7.0        # violent future change
    m2 = event_regime_mask(df2, events, threshold=0.5, pct_window=100)
    assert (m1[:248] == m2[:248]).all(), "future data changed past filter values!"
    print("regime lookahead probe ok: past mask invariant to future perturbation")


def test_pct_rank_edges():
    s = pd.Series(np.ones(300))
    p = trailing_pct_rank(s, window=100)
    assert np.nanmax(p.to_numpy()) == 0.0, "constant series: strictly-below rank must be 0 -> no trade"
    print("pct-rank edge ok: constant series is conservatively excluded")


def test_cost_matrix_recovery(tmp="/tmp/cm_test.json"):
    rows = []
    for day in (1, 2, 3):
        for hour in range(24):
            base = 0.60 if hour == 13 else 0.20
            for k in range(50):
                t = pd.Timestamp(f"2016-03-0{day} {hour:02d}:{k % 60:02d}:00", tz="UTC")
                rows.append((int(t.value // 10**6), 2000.0, 2000.0 + base))
    for day in (1, 2):
        for hour in range(24):
            base = 0.90 if hour == 13 else 0.30
            for k in range(50):
                t = pd.Timestamp(f"2020-03-0{day} {hour:02d}:{k % 60:02d}:00", tz="UTC")
                rows.append((int(t.value // 10**6), 1700.0, 1700.0 + base))
    df = pd.DataFrame(rows, columns=["time", "bid", "ask"])
    p = "/tmp/ticks_test.csv"; df.to_csv(p, index=False)

    m = build_matrix([p], time_unit="ms", bucket_cap=500)
    save_matrix(m, tmp)
    cm = CostMatrix.load(tmp, k_slip=0.5, commission_per_lot_rt=7.0)
    assert abs(cm.spread_usd(pd.Timestamp("2016-03-01 13:30", tz="UTC")) - 0.60) < 1e-9
    assert abs(cm.spread_usd(pd.Timestamp("2016-03-01 05:00", tz="UTC")) - 0.20) < 1e-9
    assert abs(cm.spread_usd(pd.Timestamp("2020-03-01 13:05", tz="UTC")) - 0.90) < 1e-9
    _ = cm.spread_usd(pd.Timestamp("2030-01-01 10:00", tz="UTC"))   # global fallback
    assert cm.fallback_hits.get("_global", 0) == 1
    # hand math: entry 2016 h05 (0.20), exit h13 (0.60), k=0.5, 1 lot, $7 comm
    cost = cm.trade_cost_usd(pd.Timestamp("2016-03-01 05:10", tz="UTC"),
                             pd.Timestamp("2016-03-01 13:10", tz="UTC"))
    assert abs(cost - 87.0) < 1e-6, cost      # (0.4 + 0.4)*100 + 7
    print("cost matrix ok: bucket recovery exact, fallback counted, hand-math $87.00")


def test_mechanism_control():
    net = np.array([100.0, -50, 120, -60, -80, -90, -70, 30])
    mask = np.array([True, True, True, True, False, False, False, False])
    r = mechanism_control(net, mask, min_n_in=3)
    assert r["n_in"] == 4 and r["sufficient"]
    assert r["pf_in"] == 2.0 and abs(r["pf_out"] - 30 / 240) < 1e-9
    print("mechanism control ok: conditional PFs computed as specified")


if __name__ == "__main__":
    test_regime_two_state()
    test_regime_no_lookahead()
    test_pct_rank_edges()
    test_cost_matrix_recovery()
    test_mechanism_control()
    print("\nALL PACK TESTS PASSED")
