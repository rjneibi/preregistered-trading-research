"""A compact, fully-deterministic 2-state diagonal-Gaussian HMM.

``hmmlearn`` is intentionally NOT a dependency (it is not in the locked library
set), so we implement just enough Baum-Welch here in numpy/scipy to fit a
two-regime (calm / turbulent) emission model on a rolling window.

Determinism matters: the regime feature must be both causal *and* prefix-stable
(recomputing on a truncated prefix yields the identical value), otherwise the
leakage assert in features.py would false-positive. We get that by:
  * a deterministic, RNG-free initialisation (median split of |return|), and
  * fitting only on the window's own data with a fixed iteration count.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


class GaussianHMM2:
    """Two-state diagonal-Gaussian HMM fit by a fixed number of EM iterations."""

    def __init__(self, n_iter: int = 15, var_floor: float = 1e-6) -> None:
        self.n_iter = n_iter
        self.var_floor = var_floor
        self.startprob_ = np.array([0.5, 0.5])
        self.transmat_ = np.array([[0.95, 0.05], [0.05, 0.95]])
        self.means_: np.ndarray | None = None
        self.vars_: np.ndarray | None = None

    def _log_emission(self, x: np.ndarray) -> np.ndarray:
        """Return (T, 2) log-likelihood of each obs under each state."""
        logb = np.zeros((x.shape[0], 2))
        for k in range(2):
            comp = norm.logpdf(
                x, loc=self.means_[k], scale=np.sqrt(self.vars_[k])
            )
            logb[:, k] = comp.sum(axis=1)
        return logb

    def _init(self, x: np.ndarray) -> None:
        # Deterministic split: low-energy vs high-energy bars by |second feature|.
        energy = np.abs(x[:, -1])
        thr = np.median(energy)
        low = x[energy <= thr]
        high = x[energy > thr]
        if len(low) == 0:
            low = x
        if len(high) == 0:
            high = x
        self.means_ = np.vstack([low.mean(axis=0), high.mean(axis=0)])
        self.vars_ = np.vstack(
            [
                np.maximum(low.var(axis=0), self.var_floor),
                np.maximum(high.var(axis=0), self.var_floor),
            ]
        )

    def fit(self, x: np.ndarray) -> "GaussianHMM2":
        self._init(x)
        t_len = x.shape[0]
        for _ in range(self.n_iter):
            logb = self._log_emission(x)
            log_alpha, log_beta = self._forward_backward(logb)
            log_gamma = log_alpha + log_beta
            log_gamma -= _logsumexp_rows(log_gamma)[:, None]
            gamma = np.exp(log_gamma)

            # Pairwise posteriors xi summed over time.
            log_xi_sum = np.full((2, 2), -np.inf)
            log_trans = np.log(self.transmat_ + 1e-300)
            for t in range(t_len - 1):
                m = (
                    log_alpha[t][:, None]
                    + log_trans
                    + logb[t + 1][None, :]
                    + log_beta[t + 1][None, :]
                )
                m -= _logsumexp(m.ravel())
                log_xi_sum = np.logaddexp(log_xi_sum, m)
            xi_sum = np.exp(log_xi_sum)

            # M-step.
            self.startprob_ = gamma[0] / gamma[0].sum()
            denom = xi_sum.sum(axis=1, keepdims=True)
            denom[denom == 0] = 1.0
            self.transmat_ = xi_sum / denom
            w = gamma.sum(axis=0)
            w[w == 0] = 1.0
            self.means_ = (gamma.T @ x) / w[:, None]
            for k in range(2):
                diff = x - self.means_[k]
                self.vars_[k] = np.maximum(
                    (gamma[:, k][:, None] * diff ** 2).sum(axis=0) / w[k],
                    self.var_floor,
                )
        return self

    def _forward_backward(self, logb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        t_len = logb.shape[0]
        log_start = np.log(self.startprob_ + 1e-300)
        log_trans = np.log(self.transmat_ + 1e-300)
        log_alpha = np.empty((t_len, 2))
        log_beta = np.empty((t_len, 2))

        log_alpha[0] = log_start + logb[0]
        for t in range(1, t_len):
            for k in range(2):
                log_alpha[t, k] = _logsumexp(
                    log_alpha[t - 1] + log_trans[:, k]
                ) + logb[t, k]

        log_beta[-1] = 0.0
        for t in range(t_len - 2, -1, -1):
            for k in range(2):
                log_beta[t, k] = _logsumexp(
                    log_trans[k, :] + logb[t + 1] + log_beta[t + 1]
                )
        return log_alpha, log_beta

    def last_state(self, x: np.ndarray) -> int:
        """Posterior-argmax regime at the final observation of ``x``.

        States are canonicalised so 0 = calmer (lower mean |energy|), 1 =
        turbulent, making the label comparable across refits.
        """
        logb = self._log_emission(x)
        log_alpha, log_beta = self._forward_backward(logb)
        log_gamma = log_alpha[-1] + log_beta[-1]
        state = int(np.argmax(log_gamma))
        # Canonicalise by emission energy on the last feature dim.
        energy_means = np.abs(self.means_[:, -1])
        order = np.argsort(energy_means)  # order[0] = calmer state index
        canonical = {int(order[0]): 0, int(order[1]): 1}
        return canonical[state]


def _logsumexp(v: np.ndarray) -> float:
    m = np.max(v)
    if not np.isfinite(m):
        return float(m)
    return float(m + np.log(np.sum(np.exp(v - m))))


def _logsumexp_rows(a: np.ndarray) -> np.ndarray:
    m = np.max(a, axis=1)
    return m + np.log(np.sum(np.exp(a - m[:, None]), axis=1))
