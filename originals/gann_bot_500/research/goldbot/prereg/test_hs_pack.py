#!/usr/bin/env python3
"""H-S pack self-checks. Run: python test_hs_pack.py — all asserts must pass."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scalp_lab import (breakeven_frontier, dollar_barrier, momo_burst_events,
                       move_vs_cost, permutation_best_of, pf_net,
                       zscore_fade_events)


def _walk(n_min=40_000, sd=0.15, seed=11, p0=2400.0):
    rng = np.random.default_rng(seed)
    close = p0 + np.cumsum(rng.normal(0, sd, n_min))
    open_ = np.empty(n_min); open_[0] = p0; open_[1:] = close[:-1]
    wig = np.abs(rng.normal(0, sd * 0.5, n_min))
    idx = pd.date_range("2024-01-01", periods=n_min, freq="1min", tz="UTC")
    return pd.DataFrame({"open": open_, "high": np.maximum(open_, close) + wig,
                         "low": np.minimum(open_, close) - wig, "close": close},
                        index=idx)


def test_frontier_hand_math():
    f = breakeven_frontier(costs=(0.62,), geometries=((0.5, 0.5), (2.0, 1.0)))
    r1 = f.iloc[0]["required_winrate"]; r2 = f.iloc[1]["required_winrate"]
    assert abs(r1 - (0.5 + 0.62) / 1.0) < 1e-12        # 112% — impossible
    assert abs(r2 - (1.0 + 0.62) / 3.0) < 1e-12        # 54%
    assert r1 > 1.0, "symmetric $0.50 scalp at $0.62 cost must be impossible"
    print(f"frontier ok: (0.5,0.5)@$0.62 needs {r1:.0%} (impossible); (2,1) needs {r2:.0%}")


def test_ambiguity_is_a_loss():
    bars = [(100.0, 100.1, 99.9, 100.0),
            (100.0, 100.8, 99.3, 100.2)]      # both barriers (±0.5) inside one bar
    df = pd.DataFrame(bars, columns=["open", "high", "low", "close"])
    t, amb = dollar_barrier(df, np.array([0]), np.array([1]), 0.5, 0.5, horizon=5)
    assert amb == 1 and t.iloc[0]["exit_reason"] == "ambiguous->sl"
    assert t.iloc[0]["exit_price"] == 99.5
    print("pessimism ok: dual-touch bar resolves to stop-loss")


def test_signals_no_lookahead():
    df = _walk()
    for fn in (zscore_fade_events, momo_burst_events):
        e1, s1 = fn(df)
        df2 = df.copy()
        cut = 30_000
        for col in ("open", "high", "low", "close"):
            df2.iloc[cut:, df2.columns.get_loc(col)] *= 3.0
        e2, s2 = fn(df2)
        k = np.searchsorted(e1, cut - 2)
        assert np.array_equal(e1[:k], e2[:k]) and np.array_equal(s1[:k], s2[:k]), fn.__name__
    print("signal lookahead probes ok: past events invariant to future perturbation")


def test_noise_cannot_pass_at_cost():
    """Edge-free entries on a driftless walk at realistic cost must lose, and even
    the best-of-12 selection must sit well under the PF gate. This proves the
    harness cannot hallucinate a passing scalper from noise + selection."""
    df = _walk()
    configs = [{"tp": tp, "sl": sl, "horizon": 30}
               for tp, sl in ((0.5, 0.5), (1.0, 1.0), (1.5, 0.75))] * 4  # 12 arms
    counts = [400] * len(configs)
    best = permutation_best_of(df, configs, counts, n_perm=60,
                               cost_per_oz=0.62, seed=5)
    med, p95 = float(np.median(best)), float(np.percentile(best, 95))
    assert med < 1.0, f"median best-of-12 on noise should lose at cost (got {med:.2f})"
    assert p95 < 1.30, f"even selection luck must sit under the PF gate (got {p95:.2f})"
    print(f"noise control ok: best-of-12 median PF {med:.2f}, p95 {p95:.2f} (< 1.30 gate)")


def test_move_vs_cost_shape():
    df = _walk(sd=0.15)
    ex = move_vs_cost(df, cost_usd_oz=0.62, horizons=(1, 30))
    r1, r30 = ex.iloc[0], ex.iloc[1]
    assert r30["median_abs_move"] > r1["median_abs_move"]
    assert r1["cost_over_median_move"] > r30["cost_over_median_move"]
    print(f"move-vs-cost ok: cost is {r1['cost_over_median_move']:.1f}x the median 1-min move, "
          f"{r30['cost_over_median_move']:.2f}x the 30-min move (toll shrinks with horizon)")


if __name__ == "__main__":
    test_frontier_hand_math()
    test_ambiguity_is_a_loss()
    test_signals_no_lookahead()
    test_noise_cannot_pass_at_cost()
    test_move_vs_cost_shape()
    print("\nALL H-S PACK TESTS PASSED")
