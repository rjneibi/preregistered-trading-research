"""
ATR risk-normalized position sizing for XAUUSD (or any MT5 symbol).

Design decisions (deliberate, do not "fix" silently):
- Lot size is floored to the broker volume step, never rounded up.
  Rounding up can exceed the per-trade dollar risk budget.
- If the floored size is below the broker minimum lot, the function
  returns 0.0 (skip the trade). Clamping up to min-lot silently takes
  more risk than the budget allows on small accounts / wide stops.
- Contract math is pulled from a SymbolSpec, not hardcoded, because
  brokers differ (100 oz vs 10 oz gold contracts, different tick values).
  Populate it once from the live terminal with SymbolSpec.from_mt5()
  or construct it manually for backtests.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SymbolSpec:
    """Broker/contract parameters needed for sizing.

    tick_size:  minimum price increment (e.g. 0.01 for XAUUSD)
    tick_value: account-currency value of one tick per 1.0 lot
    volume_step / volume_min / volume_max: broker lot constraints
    """

    tick_size: float
    tick_value: float
    volume_step: float
    volume_min: float
    volume_max: float

    @property
    def value_per_unit_per_lot(self) -> float:
        """Account-currency value of a 1.0 price-unit move for 1.0 lot.

        Example: XAUUSD with tick_size=0.01, tick_value=$1.00 (100 oz
        contract) -> $100 per $1.00 of price movement per lot.
        """
        return self.tick_value / self.tick_size

    @classmethod
    def from_mt5(cls, symbol: str) -> "SymbolSpec":
        """Build the spec from a live MetaTrader 5 terminal connection.

        Requires `mt5.initialize()` to have been called already.
        """
        import MetaTrader5 as mt5  # lazy import: backtests don't need it

        info = mt5.symbol_info(symbol)
        if info is None:
            raise RuntimeError(f"symbol_info({symbol!r}) returned None - "
                               "is the terminal connected and the symbol "
                               "in Market Watch?")
        return cls(
            tick_size=info.trade_tick_size,
            tick_value=info.trade_tick_value,
            volume_step=info.volume_step,
            volume_min=info.volume_min,
            volume_max=info.volume_max,
        )


# Typical retail XAUUSD spec (100 oz contract, USD account).
# VERIFY against your broker with SymbolSpec.from_mt5("XAUUSD") before
# trusting backtest cost math - do not assume this matches your account.
XAUUSD_TYPICAL = SymbolSpec(
    tick_size=0.01,
    tick_value=1.0,
    volume_step=0.01,
    volume_min=0.01,
    volume_max=100.0,
)


def _floor_to_step(value: float, step: float) -> float:
    """Floor `value` to a multiple of `step`, robust to float error."""
    if step <= 0:
        raise ValueError("volume_step must be positive")
    stepped = math.floor((value / step) + 1e-9) * step
    # normalise float noise like 0.13000000000000003
    decimals = max(0, -int(math.floor(math.log10(step))))
    return round(stepped, decimals)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder ATR from columns high/low/close. NaN during warmup."""
    h, l, c = df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    tr = pd.concat(
        [(h - l), (h - prev_c).abs(), (l - prev_c).abs()], axis=1
    ).max(axis=1)
    out = tr.ewm(alpha=1.0 / n, adjust=False).mean()
    out.iloc[: n] = np.nan  # don't trust the seed period
    return out


def position_size(
    equity: float,
    risk_fraction: float,
    stop_distance: float,
    spec: SymbolSpec,
) -> float:
    """Lots such that (stop hit) loses <= equity * risk_fraction.

    stop_distance is in PRICE UNITS (e.g. dollars per oz for XAUUSD),
    typically atr_value * atr_multiplier from the caller.

    Returns 0.0 when the trade cannot be taken within budget
    (stop too wide for the account at broker min lot).
    """
    if equity <= 0 or risk_fraction <= 0 or stop_distance <= 0:
        return 0.0

    dollar_risk = equity * risk_fraction
    risk_per_lot = stop_distance * spec.value_per_unit_per_lot
    raw_lots = dollar_risk / risk_per_lot

    lots = _floor_to_step(raw_lots, spec.volume_step)
    if lots < spec.volume_min:
        return 0.0  # skip: min lot would exceed the risk budget
    return min(lots, spec.volume_max)
