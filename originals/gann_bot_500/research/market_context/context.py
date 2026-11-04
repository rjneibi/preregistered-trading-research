"""
MarketContext: aggregates LiquidityLevel objects from all sources, tracks which
have been swept in the M1 stream between formation and as_of_ts, and answers
nearest-opposing queries used by the veto rule.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
import pandas as pd

from .levels import LiquidityLevel, BUYSIDE, SELLSIDE
from .sources import ALL_SOURCES


def _mark_swept(levels: List[LiquidityLevel], m1_df: pd.DataFrame,
                as_of_ts: pd.Timestamp) -> None:
    """Set level.swept = True if price traded through the level between
    formation and as_of_ts. Only completed bars are considered."""
    cutoff = as_of_ts - pd.Timedelta(minutes=1)
    for lv in levels:
        window = m1_df[(m1_df.index > lv.formed_at) & (m1_df.index <= cutoff)]
        if window.empty:
            continue
        if lv.side == BUYSIDE and float(window["high"].max()) >= lv.price:
            lv.swept = True
        elif lv.side == SELLSIDE and float(window["low"].min()) <= lv.price:
            lv.swept = True


class MarketContext:
    def __init__(self, m1_df: pd.DataFrame):
        """m1_df: UTC-tz-aware DatetimeIndex, columns open/high/low/close."""
        if m1_df.index.tz is None:
            raise ValueError("m1_df must be tz-aware")
        self.m1_df = m1_df
        self.levels: List[LiquidityLevel] = []
        self.as_of_ts: Optional[pd.Timestamp] = None

    def refresh(self, as_of_ts: pd.Timestamp) -> None:
        """Rebuild levels from all sources as-of `as_of_ts`, then mark sweeps
        from level formation up to as_of_ts."""
        levels: List[LiquidityLevel] = []
        for src in ALL_SOURCES:
            levels.extend(src.get_levels(self.m1_df, as_of_ts))
        _mark_swept(levels, self.m1_df, as_of_ts)
        self.levels = levels
        self.as_of_ts = as_of_ts

    def active_unswept(self) -> List[LiquidityLevel]:
        return [lv for lv in self.levels if not lv.swept]

    def nearest_opposing_unswept(
        self, direction: str, price: float
    ) -> Tuple[Optional[LiquidityLevel], Optional[float]]:
        """
        Returns (level, absolute_price_distance) — distance is positive.
        LONG (BUY)  candidate: opposing = nearest UNSWEPT SELLSIDE below price.
        SHORT (SELL) candidate: opposing = nearest UNSWEPT BUYSIDE above price.
        """
        direction = direction.upper()
        candidates: List[LiquidityLevel] = []
        if direction == "BUY":
            candidates = [lv for lv in self.active_unswept()
                          if lv.side == SELLSIDE and lv.price < price]
            if not candidates:
                return None, None
            best = max(candidates, key=lambda lv: lv.price)     # closest below
            return best, price - best.price
        elif direction == "SELL":
            candidates = [lv for lv in self.active_unswept()
                          if lv.side == BUYSIDE and lv.price > price]
            if not candidates:
                return None, None
            best = min(candidates, key=lambda lv: lv.price)     # closest above
            return best, best.price - price
        else:
            raise ValueError(f"direction must be BUY or SELL, got {direction!r}")


def veto(direction: str, price: float, atr: float, K: float,
         ctx: MarketContext) -> Tuple[bool, Optional[LiquidityLevel], Optional[float]]:
    """
    Apply the veto rule.

    Returns (vetoed, level_or_none, distance_in_atr_or_none).
    - vetoed=True  if an opposing unswept pool sits within K*ATR of the entry
      (the "pool is likely drawn on first" logic).
    - level_or_none: the level that triggered the veto (or the nearest opposing
      if not vetoed).
    - distance_in_atr_or_none: (P-L)/A for LONG, (L-P)/A for SHORT.
    """
    lv, dist = ctx.nearest_opposing_unswept(direction, price)
    if lv is None or dist is None:
        return False, None, None
    if atr <= 0:
        return False, lv, None
    dist_atr = dist / atr
    return (dist_atr <= K), lv, dist_atr
