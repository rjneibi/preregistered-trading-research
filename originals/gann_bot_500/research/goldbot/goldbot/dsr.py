"""Deflated Sharpe Ratio + PBO/CSCV — HCRT prereg harness prerequisite.

DSR per Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", JPM
40(5): the observed (best-of-N) Sharpe is tested against SR0 = E[max SR]
under the null of N zero-edge trials, with the PSR variance adjustment for
non-Normal per-trade returns (skew gamma1, RAW kurtosis gamma2; Normal=3).

PBO per Bailey, Borwein, López de Prado & Zhu (2017) CSCV: S contiguous
blocks, C(S, S/2) IS/OOS combinations, rank-logit of the IS-best trial's
OOS standing. PBO = fraction of combinations where the IS winner lands
below the OOS median.

Conventions pinned by HCRT_PREREGISTRATION.md:
- SR and DSR are computed on PER-TRADE NET returns and are NOT annualized
  (matches goldbot/backtest.py's honesty labeling).
- SR0 uses the exact expected-max formula with the Euler–Mascheroni mix;
  N=1 => SR0=0 and DSR reduces to PSR.
- CSCV uses S=8 blocks; when trade timestamps are supplied, IS rows within
  the embargo horizon (24h = one event horizon) of any OOS span are purged,
  mirroring goldbot/cpcv.py's purge direction (train-side only).
"""

from __future__ import annotations

import math
from itertools import combinations
from statistics import NormalDist

import numpy as np

EULER_GAMMA = 0.5772156649015329
_N01 = NormalDist()


def sharpe(returns) -> float:
    """Per-trade Sharpe (mean/sd, ddof=1). Zero-variance series -> 0.0."""
    r = np.asarray(returns, dtype=float)
    if len(r) < 2:
        return 0.0
    sd = float(r.std(ddof=1))
    return 0.0 if sd == 0.0 else float(r.mean()) / sd


def skew_kurt(returns) -> tuple[float, float]:
    """Sample skewness g1 and RAW kurtosis g2 (Normal -> 3.0)."""
    r = np.asarray(returns, dtype=float)
    m = r.mean()
    d = r - m
    m2 = float((d ** 2).mean())
    if m2 == 0.0:
        return 0.0, 3.0
    g1 = float((d ** 3).mean()) / m2 ** 1.5
    g2 = float((d ** 4).mean()) / m2 ** 2
    return g1, g2


def expected_max_sharpe(n_trials: int, var_trial_sr: float) -> float:
    """SR0 = E[max of n_trials null Sharpes] with cross-trial variance
    var_trial_sr. n_trials <= 1 or degenerate variance -> 0.0 (so a single
    pre-registered trial is tested undeflated, i.e. plain PSR)."""
    if n_trials <= 1 or var_trial_sr <= 0.0:
        return 0.0
    z1 = _N01.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = _N01.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trial_sr) * ((1.0 - EULER_GAMMA) * z1
                                      + EULER_GAMMA * z2)


def psr(sr: float, sr_ref: float, n_obs: int,
        skew: float, kurt: float) -> float:
    """Probabilistic Sharpe Ratio: P(true SR > sr_ref | observed sr).
    kurt is RAW kurtosis (Normal = 3). Degenerate variance adjustments are
    clamped to a tiny positive value (extreme skew*SR combinations)."""
    if n_obs < 2:
        return 0.0
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    denom = max(denom, 1e-12)
    z = (sr - sr_ref) * math.sqrt(n_obs - 1.0) / math.sqrt(denom)
    return _N01.cdf(z)


def dsr(returns, trial_srs) -> dict:
    """Deflated Sharpe of the SELECTED trial's per-trade net returns.

    ``trial_srs`` is the full vector of Sharpes across ALL selectable trials
    of the frozen prereg (HCRT: exactly [SR_E1, SR_E2]); N and the
    cross-trial variance are taken from it, never passed loose. Returns a
    dict so the runner can disclose every intermediate in results JSON.
    """
    srs = [float(s) for s in trial_srs]
    n_trials = len(srs)
    assert n_trials >= 1, "trial_srs must contain at least the selected trial"
    r = np.asarray(returns, dtype=float)
    sr = sharpe(r)
    g1, g2 = skew_kurt(r)
    var_trials = float(np.var(srs, ddof=1)) if n_trials > 1 else 0.0
    sr0 = expected_max_sharpe(n_trials, var_trials)
    return {
        "sr": sr, "sr0": sr0, "n_trials": n_trials,
        "var_trial_sr": var_trials, "n_obs": int(len(r)),
        "skew": g1, "kurt_raw": g2,
        "dsr": psr(sr, sr0, len(r), g1, g2),
    }


def pbo_cscv(trial_returns: np.ndarray, s: int = 8,
             times=None, embargo_h: float = 24.0) -> dict:
    """Probability of Backtest Overfitting via CSCV.

    ``trial_returns``: T x N matrix, one column per trial of the frozen
    matrix, rows time-ordered. ``times`` (optional): epoch-hours per row;
    when given, IS rows within embargo_h of any contiguous OOS span are
    purged before ranking (train-side purge only, as in cpcv.py).
    """
    m = np.asarray(trial_returns, dtype=float)
    assert m.ndim == 2 and m.shape[1] >= 2, "need a T x N matrix, N >= 2"
    t_rows, n_trials = m.shape
    assert s % 2 == 0 and s >= 2, "S must be even"
    assert t_rows >= 2 * s, f"too few rows ({t_rows}) for S={s} blocks"
    if times is not None:
        times = np.asarray(times, dtype=float)
        assert len(times) == t_rows, "times must align with rows"
        assert np.all(np.diff(times) >= 0), "rows must be time-ordered"

    edges = np.linspace(0, t_rows, s + 1).astype(int)
    blocks = [np.arange(edges[i], edges[i + 1]) for i in range(s)]

    def col_sharpes(rows: np.ndarray) -> np.ndarray:
        sub = m[rows]
        mu = sub.mean(axis=0)
        sd = sub.std(axis=0, ddof=1)
        out = np.zeros(n_trials)
        nz = sd > 0
        out[nz] = mu[nz] / sd[nz]
        return out

    lambdas = []
    for is_blocks in combinations(range(s), s // 2):
        oos_blocks = [b for b in range(s) if b not in is_blocks]
        is_rows = np.concatenate([blocks[b] for b in is_blocks])
        oos_rows = np.concatenate([blocks[b] for b in oos_blocks])

        if times is not None:
            purge = np.zeros(t_rows, dtype=bool)
            for b_lo, b_hi in _contiguous_spans(oos_blocks):
                t_lo = times[blocks[b_lo][0]] - embargo_h
                t_hi = times[blocks[b_hi][-1]] + embargo_h
                purge |= (times >= t_lo) & (times <= t_hi)
            is_rows = is_rows[~purge[is_rows]]
            assert len(is_rows) >= 2, "IS collapsed after embargo purge"

        best = int(np.argmax(col_sharpes(is_rows)))
        oos_sr = col_sharpes(oos_rows)
        # average rank of the IS winner among OOS Sharpes, in (0, 1)
        rank = 1.0 + float(np.sum(oos_sr < oos_sr[best])) \
            + 0.5 * float(np.sum(oos_sr == oos_sr[best]) - 1)
        omega = rank / (n_trials + 1.0)
        lambdas.append(math.log(omega / (1.0 - omega)))

    lambdas = np.asarray(lambdas)
    return {
        "pbo": float(np.mean(lambdas <= 0.0)),
        "n_combinations": int(len(lambdas)),
        "lambda_mean": float(lambdas.mean()),
        "s_blocks": s,
        "purged": times is not None,
    }


def _contiguous_spans(sorted_blocks: list[int]) -> list[tuple[int, int]]:
    """Group sorted block ids into (first, last) contiguous runs."""
    spans, lo, prev = [], sorted_blocks[0], sorted_blocks[0]
    for b in sorted_blocks[1:]:
        if b != prev + 1:
            spans.append((lo, prev))
            lo = b
        prev = b
    spans.append((lo, prev))
    return spans
