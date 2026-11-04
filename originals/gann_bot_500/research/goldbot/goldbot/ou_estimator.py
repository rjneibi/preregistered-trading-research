"""Exact AR(1) <-> Ornstein-Uhlenbeck fit with validity gates.

Discrete observations x_0..x_n at spacing dt of an OU process
    dX = theta*(mu - X) dt + sigma dW
follow an exact AR(1):
    x_{t+1} = c + phi1 * x_t + eps_t,   eps ~ N(0, s_eps^2)
with
    phi1  = exp(-theta*dt)
    c     = mu * (1 - phi1)
    s_eps^2 = sigma^2 * (1 - phi1^2) / (2*theta)

Inversion (the fit) therefore requires ALL of:
  * 0 < phi1 < 1  — phi1 <= 0 is anti-persistent noise, phi1 >= 1 is a random
    walk/explosive process; neither has a finite OU half-life. This is the
    condition careless treatments omit: fitting a random walk "succeeds"
    numerically and reports a meaningless multi-year half-life.
  * the sigma-recovery term (1 - phi1^2) bounded away from 0, else
    sigma = sqrt(s_eps^2 * 2*theta / (1 - phi1^2)) blows up on noise.
  * a stationarity t-gate: (1 - phi1) / se(phi1) >= min_t (default 3), with
    se(phi1) ~ sqrt((1 - phi1^2)/n). A finite-sample random walk fits to
    phi1 just BELOW 1 (negative bias), sails through the 0<phi1<1 check, and
    reports a huge-but-finite half-life; the t-gate catches exactly that.
    (Normal-approximation flavor of a Dickey-Fuller test — a research gate,
    not a rigorous unit-root test; DF critical values are ~2.9 at 5%.)

No trading conclusion may be drawn from a fit with valid=False.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_TINY_RECOVERY = 1e-10


@dataclass(frozen=True)
class OUFit:
    valid: bool
    reason: str
    n: int
    phi1: float = float("nan")
    c: float = float("nan")
    eps_var: float = float("nan")
    theta: float = float("nan")
    mu: float = float("nan")
    sigma: float = float("nan")
    half_life: float = float("nan")   # in units of dt's time unit


def fit_ou(x: np.ndarray, dt: float = 1.0, min_obs: int = 100,
           min_t: float = 3.0) -> OUFit:
    """Exact AR(1) OLS fit mapped to OU parameters, with validity gates."""
    x = np.asarray(x, dtype=float)
    assert dt > 0, "dt must be positive"
    n = len(x)
    if n < min_obs:
        return OUFit(False, f"n={n} < min_obs={min_obs}", n)
    if not np.all(np.isfinite(x)):
        return OUFit(False, "non-finite values in series", n)

    xlag, y = x[:-1], x[1:]
    vx = np.var(xlag)
    if vx <= 0:
        return OUFit(False, "constant series", n)
    phi1 = float(np.cov(xlag, y, bias=True)[0, 1] / vx)
    c = float(np.mean(y) - phi1 * np.mean(xlag))
    eps = y - c - phi1 * xlag
    eps_var = float(np.sum(eps ** 2) / max(1, len(eps) - 2))   # ddof=2 (two params)

    if phi1 <= 0.0:
        return OUFit(False, f"phi1={phi1:.4f} <= 0 (anti-persistent, not OU)",
                     n, phi1, c, eps_var)
    if phi1 >= 1.0:
        return OUFit(False, f"phi1={phi1:.6f} >= 1 (random walk/explosive)",
                     n, phi1, c, eps_var)
    recovery = 1.0 - phi1 ** 2
    if recovery < _TINY_RECOVERY:
        return OUFit(False, f"sigma-recovery term 1-phi1^2={recovery:.2e} ~ 0 "
                            f"(indistinguishable from random walk)",
                     n, phi1, c, eps_var)
    se_phi1 = float(np.sqrt(recovery / max(1, n - 1)))
    t_stat = (1.0 - phi1) / se_phi1 if se_phi1 > 0 else 0.0
    if t_stat < min_t:
        return OUFit(False,
                     f"stationarity t-gate failed: (1-phi1)/se={t_stat:.2f} "
                     f"< {min_t} (cannot reject random walk at this n)",
                     n, phi1, c, eps_var)

    theta = -np.log(phi1) / dt
    mu = c / (1.0 - phi1)
    sigma = float(np.sqrt(eps_var * 2.0 * theta / recovery))
    half_life = float(np.log(2.0) / theta)
    return OUFit(True, "ok", n, phi1, c, eps_var,
                 float(theta), float(mu), sigma, half_life)


def simulate_ou(theta: float, mu: float, sigma: float, x0: float,
                n: int, dt: float = 1.0, seed: int = 42) -> np.ndarray:
    """Exact-transition OU simulator (no Euler discretization error):

        x_{t+1} = mu + (x_t - mu)*e^{-theta dt}
                  + sigma * sqrt((1 - e^{-2 theta dt}) / (2 theta)) * z_t
    """
    assert theta > 0 and sigma >= 0 and n >= 1 and dt > 0
    rng = np.random.default_rng(seed)
    phi = np.exp(-theta * dt)
    step_sd = sigma * np.sqrt((1.0 - phi ** 2) / (2.0 * theta))
    x = np.empty(n, dtype=float)
    x[0] = x0
    z = rng.standard_normal(n - 1)
    for i in range(1, n):
        x[i] = mu + (x[i - 1] - mu) * phi + step_sd * z[i - 1]
    return x
