"""Module H — CVXPY sizing optimizer with a CVaR cap and a cash fallback.

For M candidate setups we choose weights ``w`` maximising expected net edge

    E[R_i] = p_TP_i * D_TP_i  -  p_SL_i * D-bar_SL_i  +  p_timeout_i * R-bar_timeout_i

minus transaction cost and a big-M penalty on the soft turnover slack.

HARD constraints (never relaxed to soft):
  * exposure        : sum|w| <= MAX_EXPOSURE
  * CVaR (R-U form) : beta + mean(u)/(1-alpha) <= CVAR_LIMIT,
                      u_k >= 0, u_k >= loss_k - beta
SOFT constraint:
  * turnover        : |w_i - w0_i| <= MAX_TURNOVER + s_i, s_i >= 0, penalised.

FALLBACK — De-Risk-to-Cash LP: if the primary solve is not optimal (exposure or
CVaR cannot be met), minimise sum|w| subject ONLY to the turnover band. Exposure
and CVaR are never silently relaxed; we move toward cash instead.
"""

from __future__ import annotations

from dataclasses import dataclass

import cvxpy as cp
import numpy as np

from config import Config

_BIG_M = 1.0e3  # turnover-slack penalty


@dataclass
class Setups:
    """Per-setup calibrated probabilities and barrier distances (length M)."""

    p_tp: np.ndarray
    p_sl: np.ndarray
    p_to: np.ndarray
    d_tp: np.ndarray
    dbar_sl: np.ndarray
    rbar_to: np.ndarray

    @property
    def m(self) -> int:
        return len(self.p_tp)

    def expected_edge(self) -> np.ndarray:
        return self.p_tp * self.d_tp - self.p_sl * self.dbar_sl + self.p_to * self.rbar_to


@dataclass
class SizingResult:
    mode: str            # "primary" or "derisk_to_cash"
    status: str
    w: np.ndarray
    scenarios: np.ndarray  # (N_SCENARIOS, M) outcome draws used for CVaR
    cvar_value: float | None


def _draw_scenarios(setups: Setups, cfg: Config) -> np.ndarray:
    """Draw (N_SCENARIOS, M) outcomes from each setup's calibrated mixture."""
    rng = np.random.default_rng(cfg.RANDOM_SEED + 7)
    n, m = cfg.N_SCENARIOS, setups.m
    out = np.empty((n, m))
    for i in range(m):
        probs = np.array([setups.p_tp[i], setups.p_sl[i], setups.p_to[i]])
        probs = probs / probs.sum()
        vals = np.array([setups.d_tp[i], -setups.dbar_sl[i], setups.rbar_to[i]])
        choice = rng.choice(3, size=n, p=probs)
        out[:, i] = vals[choice]
    return out


def _cvar_of_loss(loss: np.ndarray, alpha: float) -> float:
    """Empirical CVaR_alpha of a loss sample (mean of worst (1-alpha) tail)."""
    var = np.quantile(loss, alpha)
    tail = loss[loss >= var]
    return float(tail.mean()) if len(tail) else float(var)


def _derisk_to_cash(w0: np.ndarray, cfg: Config, scenarios: np.ndarray) -> SizingResult:
    """Fallback LP: minimise gross exposure subject only to the turnover band."""
    m = len(w0)
    w = cp.Variable(m)
    constraints = [cp.abs(w - w0) <= cfg.MAX_TURNOVER]
    prob = cp.Problem(cp.Minimize(cp.norm1(w)), constraints)
    prob.solve()
    w_val = np.asarray(w.value).ravel() if w.value is not None else np.zeros(m)
    loss = -(scenarios @ w_val)
    return SizingResult(
        mode="derisk_to_cash",
        status=str(prob.status),
        w=w_val,
        scenarios=scenarios,
        cvar_value=_cvar_of_loss(loss, cfg.CVAR_ALPHA),
    )


def solve_sizing(
    setups: Setups,
    w0: np.ndarray,
    cfg: Config,
    turnover_hard: bool = False,
) -> SizingResult:
    """Solve the primary CVaR-constrained problem, falling back to cash.

    With the locked model ``turnover_hard=False`` the turnover band is soft (slack
    + big-M penalty), so ``w = 0`` is always feasible and exposure/CVaR are met by
    de-risking inside the primary. The ``turnover_hard=True`` variant is used ONLY
    by the infeasibility demonstration: it models a locked book (|w - w0| bounded
    hard), so dropping MAX_EXPOSURE below sum|w0| genuinely cannot be satisfied and
    the De-Risk-to-Cash fallback must engage — without ever relaxing exposure/CVaR.
    """
    m = setups.m
    scenarios = _draw_scenarios(setups, cfg)
    edge = setups.expected_edge()

    w = cp.Variable(m)
    up = cp.Variable(m, nonneg=True)
    un = cp.Variable(m, nonneg=True)
    s = cp.Variable(m, nonneg=True)
    beta = cp.Variable()
    u = cp.Variable(cfg.N_SCENARIOS, nonneg=True)

    loss = -(scenarios @ w)  # portfolio loss per scenario
    cost = (cfg.C_SPREAD + cfg.C_COMM) * cp.sum(up + un)

    constraints = [
        w - w0 == up - un,
        cp.norm1(w) <= cfg.MAX_EXPOSURE,                       # exposure (hard)
        u >= loss - beta,                                       # R-U CVaR (hard)
        beta + cp.sum(u) / (cfg.N_SCENARIOS * (1.0 - cfg.CVAR_ALPHA))
        <= cfg.CVAR_LIMIT,
    ]
    if turnover_hard:
        constraints.append(cp.abs(w - w0) <= cfg.MAX_TURNOVER)  # locked book
        penalty = 0.0
    else:
        constraints.append(cp.abs(w - w0) <= cfg.MAX_TURNOVER + s)  # soft
        penalty = _BIG_M * cp.sum(s)

    objective = cp.Maximize(edge @ w - cost - penalty)
    prob = cp.Problem(objective, constraints)
    try:
        prob.solve()
    except cp.error.SolverError:
        return _derisk_to_cash(w0, cfg, scenarios)

    if prob.status not in ("optimal", "optimal_inaccurate") or w.value is None:
        # Exposure or CVaR could not be met — de-risk rather than relax them.
        return _derisk_to_cash(w0, cfg, scenarios)

    w_val = np.asarray(w.value).ravel()
    loss_val = -(scenarios @ w_val)
    return SizingResult(
        mode="primary",
        status=str(prob.status),
        w=w_val,
        scenarios=scenarios,
        cvar_value=_cvar_of_loss(loss_val, cfg.CVAR_ALPHA),
    )
