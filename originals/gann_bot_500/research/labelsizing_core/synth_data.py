"""Module A — coherent synthetic H1 OHLC for a gold-like series.

The price path is a geometric random walk whose per-bar volatility is driven by a
two-state (calm / turbulent) Markov regime *and* a GARCH(1,1)-style innovation
term, so the regime feature in features.py has a genuine signal to detect.

OHLC coherence is guaranteed by construction: each H1 bar is simulated as a small
intrabar sub-path, and open/high/low/close are read off that single path. We never
draw the four prices independently, so ``low <= min(open, close)`` and
``high >= max(open, close)`` hold for every bar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import Config


def _simulate_regimes(n: int, rng: np.random.Generator) -> np.ndarray:
    """Two-state Markov vol regime: 0 = calm, 1 = turbulent."""
    # Sticky transition matrix so regimes persist (detectable by an HMM).
    p_stay = np.array([0.985, 0.97])
    states = np.empty(n, dtype=np.int8)
    s = 0
    for i in range(n):
        states[i] = s
        if rng.random() > p_stay[s]:
            s = 1 - s
    return states


def generate_synthetic_ohlc(cfg: Config) -> pd.DataFrame:
    """Generate ``cfg.N_SYNTH_BARS`` of coherent synthetic H1 OHLC.

    Returns a DataFrame indexed by an hourly DatetimeIndex with columns
    ``open, high, low, close, tick_volume``.
    """
    rng = np.random.default_rng(cfg.RANDOM_SEED)
    n = cfg.N_SYNTH_BARS
    sub_steps = 6  # intrabar resolution used purely to build coherent H/L

    regimes = _simulate_regimes(n, rng)
    # Per-regime baseline hourly vol (gold-like, ~0.3% calm / ~0.9% turbulent).
    base_vol = np.array([0.0030, 0.0090])

    # GARCH(1,1)-ish multiplier so vol clusters within a regime as well.
    omega, alpha, beta = 0.02, 0.08, 0.90
    h = 1.0  # variance multiplier state
    prev_shock = 0.0

    price = 2000.0  # starting gold-like level
    opens = np.empty(n)
    highs = np.empty(n)
    lows = np.empty(n)
    closes = np.empty(n)
    volumes = np.empty(n)

    for i in range(n):
        h = omega + alpha * (prev_shock ** 2) + beta * h
        sigma_bar = base_vol[regimes[i]] * np.sqrt(h)
        # Slight upward drift, regime-independent.
        mu_bar = 0.00002

        # Build a coherent intrabar path of log-returns.
        step_sigma = sigma_bar / np.sqrt(sub_steps)
        step_mu = mu_bar / sub_steps
        increments = rng.normal(step_mu, step_sigma, size=sub_steps)
        log_path = np.cumsum(increments)
        path = price * np.exp(log_path)
        path = np.insert(path, 0, price)  # open == prior close level

        o = path[0]
        c = path[-1]
        hi = path.max()
        lo = path.min()

        opens[i] = o
        highs[i] = hi
        lows[i] = lo
        closes[i] = c
        # Volume rises with realised intrabar range; turbulent bars trade more.
        rng_frac = (hi - lo) / o
        volumes[i] = max(1.0, rng.normal(1500.0, 200.0) * (1.0 + 40.0 * rng_frac))

        prev_shock = (c - o) / o
        price = c

    idx = pd.date_range("2018-01-01", periods=n, freq="h")
    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "tick_volume": volumes.astype(np.int64),
        },
        index=idx,
    )
    df.index.name = "time"
    return df


def assert_ohlc_coherent(df: pd.DataFrame) -> None:
    """Raise AssertionError unless every bar satisfies OHLC ordering."""
    lo_ok = (df["low"] <= df[["open", "close"]].min(axis=1) + 1e-9).all()
    hi_ok = (df["high"] >= df[["open", "close"]].max(axis=1) - 1e-9).all()
    rng_ok = (df["high"] >= df["low"]).all()
    assert lo_ok, "OHLC incoherent: low above min(open, close) on some bar"
    assert hi_ok, "OHLC incoherent: high below max(open, close) on some bar"
    assert rng_ok, "OHLC incoherent: high below low on some bar"
