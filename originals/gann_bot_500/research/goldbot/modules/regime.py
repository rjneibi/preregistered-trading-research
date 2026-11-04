"""
Kaufman Efficiency Ratio regime gate with hysteresis.

ER = |close_t - close_{t-window}| / sum(|close_i - close_{i-1}|)
-> 1.0 for straight-line trends, -> 0.0 for pure chop.

Why hysteresis: a single-threshold gate flips state on every noise
crossing and bleeds spread. This gate uses separate ENTER and EXIT
thresholds per regime plus an optional N-bar confirmation, so a state
is only left when evidence actually deteriorates.

Threshold discipline (pre-registration):
- The default numbers below are PLACEHOLDERS. Calibrate on IN-SAMPLE
  data only via calibrate_thresholds(), write the chosen values into
  your pre-reg doc as named parameters, then freeze them.
- These four numbers are exactly the kind of knobs that overfit
  silently. Treat any post-hoc change as a new experiment.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

MOMENTUM = "MOMENTUM"
MEAN_REVERSION = "MEAN_REVERSION"
NEUTRAL = "NEUTRAL"


def efficiency_ratio(close: pd.Series, window: int = 14) -> pd.Series:
    """Rolling Kaufman ER in [0, 1]. NaN during warmup and dead markets
    are returned as NaN (caller should treat NaN as NEUTRAL / no trade).
    """
    if window < 2:
        raise ValueError("window must be >= 2")
    net = (close - close.shift(window)).abs()
    path = close.diff().abs().rolling(window).sum()
    er = net / path.replace(0.0, np.nan)
    return er.clip(0.0, 1.0)


@dataclass(frozen=True)
class Thresholds:
    """enter_mr < exit_mr <= exit_mom < enter_mom must hold."""

    enter_mr: float
    exit_mr: float
    exit_mom: float
    enter_mom: float

    def __post_init__(self) -> None:
        ok = self.enter_mr < self.exit_mr <= self.exit_mom < self.enter_mom
        if not ok:
            raise ValueError(
                "require enter_mr < exit_mr <= exit_mom < enter_mom, "
                f"got {self}"
            )


# Placeholder values - see module docstring. Calibrate before use.
PLACEHOLDER_THRESHOLDS = Thresholds(
    enter_mr=0.25, exit_mr=0.35, exit_mom=0.45, enter_mom=0.60
)


def calibrate_thresholds(
    er_in_sample: pd.Series,
    mr_enter_q: float = 0.20,
    mr_exit_q: float = 0.35,
    mom_exit_q: float = 0.55,
    mom_enter_q: float = 0.75,
) -> Thresholds:
    """Quantile-based thresholds from IN-SAMPLE ER distribution only.

    Never feed out-of-sample data through this. Record both the
    quantile choices and the resulting values in the pre-reg doc.
    """
    q = er_in_sample.dropna().quantile
    return Thresholds(
        enter_mr=float(q(mr_enter_q)),
        exit_mr=float(q(mr_exit_q)),
        exit_mom=float(q(mom_exit_q)),
        enter_mom=float(q(mom_enter_q)),
    )


class RegimeGate:
    """Stateful hysteresis gate. Feed one ER value per closed bar.

    confirm_bars=1 switches immediately on threshold cross;
    2-3 is more sensible on M1 to avoid single-bar fakeouts.
    """

    def __init__(self, thresholds: Thresholds, confirm_bars: int = 1):
        if confirm_bars < 1:
            raise ValueError("confirm_bars must be >= 1")
        self.t = thresholds
        self.confirm_bars = confirm_bars
        self.state = NEUTRAL
        self._pending: str | None = None
        self._pending_count = 0

    def _raw_target(self, er: float) -> str:
        t = self.t
        # retention first: stay in a regime until its EXIT is crossed
        if self.state == MOMENTUM and er > t.exit_mom:
            return MOMENTUM
        if self.state == MEAN_REVERSION and er < t.exit_mr:
            return MEAN_REVERSION
        # entries
        if er >= t.enter_mom:
            return MOMENTUM
        if er <= t.enter_mr:
            return MEAN_REVERSION
        return NEUTRAL

    def update(self, er: float) -> str:
        """Advance one bar. NaN resets to NEUTRAL (warmup / dead tape)."""
        if er is None or (isinstance(er, float) and np.isnan(er)):
            self.state = NEUTRAL
            self._pending, self._pending_count = None, 0
            return self.state

        target = self._raw_target(float(er))
        if target == self.state:
            self._pending, self._pending_count = None, 0
            return self.state

        if target == self._pending:
            self._pending_count += 1
        else:
            self._pending, self._pending_count = target, 1

        if self._pending_count >= self.confirm_bars:
            self.state = target
            self._pending, self._pending_count = None, 0
        return self.state


def classify_series(
    er: pd.Series, thresholds: Thresholds, confirm_bars: int = 1
) -> pd.Series:
    """Vectorised-interface wrapper for backtests: ER series -> state
    series, using the same stateful logic bar by bar (no lookahead).
    """
    gate = RegimeGate(thresholds, confirm_bars)
    values = er.to_numpy(dtype=float)
    out = np.empty(len(values), dtype=object)
    for i, v in enumerate(values):
        out[i] = gate.update(v)
    return pd.Series(out, index=er.index, name="regime")


def flip_count(states: pd.Series) -> int:
    """Diagnostic: number of state changes. Compare hysteresis settings
    with this before committing thresholds - fewer flips = less spread
    paid to the regime router.
    """
    s = states.dropna()
    return int((s != s.shift(1)).sum() - 1) if len(s) else 0
