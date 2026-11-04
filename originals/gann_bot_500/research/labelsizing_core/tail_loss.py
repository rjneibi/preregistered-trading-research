"""Module G — tail-aware effective stop distance via a GPD slippage model.

The effective stop loss is

    D-bar_SL = D_SL + E[slippage | SL breached]

where the conditional slippage tail is modelled with a Generalised Pareto
Distribution (``scipy.stats.genpareto``) fit to historical SL-breach overshoots
(the amount by which price gapped through the stop level). The shape parameter is
clamped to ``xi <= GPD_XI_CLAMP`` for a finite, well-behaved mean. If the number
of exceedances is below ``GPD_MIN_EXCEEDANCES`` the GPD is suspended and a flat
multiplier fallback ``D-bar_SL = GPD_FALLBACK_MULT * D_SL`` is used instead.

For a GPD(xi, sigma) with threshold 0 the mean is ``sigma / (1 - xi)`` (requires
``xi < 1``); we additionally guard ``1 - xi > 0``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import genpareto

from config import Config


@dataclass
class TailLossResult:
    xi_hat: float
    xi_clamped: float
    sigma: float
    n_exceedances: int
    used_gpd: bool
    expected_slippage: float
    d_bar_sl: float


def fit_tail_loss(
    overshoots: np.ndarray, d_sl: float, cfg: Config
) -> TailLossResult:
    """Fit the GPD slippage tail and return the effective stop distance.

    ``overshoots`` are non-negative SL-breach amounts (price units). ``d_sl`` is
    the nominal stop distance to add the expected slippage onto.
    """
    exceedances = np.asarray(overshoots, dtype=float)
    exceedances = exceedances[exceedances > 0.0]
    n_exc = int(len(exceedances))

    if n_exc < cfg.GPD_MIN_EXCEEDANCES:
        # Too few tail points to trust a GPD fit — use the flat fallback.
        d_bar = cfg.GPD_FALLBACK_MULT * d_sl
        return TailLossResult(
            xi_hat=float("nan"),
            xi_clamped=float("nan"),
            sigma=float("nan"),
            n_exceedances=n_exc,
            used_gpd=False,
            expected_slippage=float(d_bar - d_sl),
            d_bar_sl=float(d_bar),
        )

    # Fit GPD with threshold (loc) fixed at 0 — overshoots are exceedances.
    xi_hat, _loc, sigma = genpareto.fit(exceedances, floc=0.0)
    xi_clamped = min(xi_hat, cfg.GPD_XI_CLAMP)

    one_minus_xi = 1.0 - xi_clamped
    if one_minus_xi <= 0.0:
        # Mean undefined; fall back to the multiplier rather than emit inf.
        d_bar = cfg.GPD_FALLBACK_MULT * d_sl
        return TailLossResult(
            xi_hat=float(xi_hat),
            xi_clamped=float(xi_clamped),
            sigma=float(sigma),
            n_exceedances=n_exc,
            used_gpd=False,
            expected_slippage=float(d_bar - d_sl),
            d_bar_sl=float(d_bar),
        )

    expected_slip = sigma / one_minus_xi
    d_bar = d_sl + expected_slip
    return TailLossResult(
        xi_hat=float(xi_hat),
        xi_clamped=float(xi_clamped),
        sigma=float(sigma),
        n_exceedances=n_exc,
        used_gpd=True,
        expected_slippage=float(expected_slip),
        d_bar_sl=float(d_bar),
    )
