"""
Pure replacement for structure.check_zone_polarity, which in the live module
calls MetaTrader5 directly (structure.py:314). Semantics mirror the live
function 1:1: read the last 10 CLOSED H4 candles (positions 1..10, skipping
the still-forming position 0), and flip the zone side if any close breached
the level.

This is the ONE mirrored function required to run signals.evaluate_signal
outside a live terminal. Everything else in signals/levels/structure is pure
and imported directly. Drift risk to flag on any structure.py edit.
"""
from __future__ import annotations
import pandas as pd


class PolarityAdapter:
    """Bind an H4 DataFrame + current backtest time so the callable this class
    exposes has the exact signature check_zone_polarity(zone, symbol) — which
    lets us monkey-patch structure.check_zone_polarity for the duration of a
    backtest without changing signals.py."""

    def __init__(self, h4_completed_df: pd.DataFrame):
        # h4_completed_df must be indexed by BAR-END timestamps in UTC.
        if h4_completed_df.index.tz is None:
            raise ValueError("h4_completed_df must be tz-aware (UTC)")
        self.h4 = h4_completed_df
        self.now: pd.Timestamp | None = None
        self._last_closes_cache: tuple[pd.Timestamp, list[float]] | None = None

    def set_now(self, now_utc: pd.Timestamp) -> None:
        """Set the backtest cursor. Only H4 bars ending strictly before this
        instant are considered 'closed' for polarity purposes."""
        self.now = now_utc

    def _last_10_closed(self) -> list[float]:
        assert self.now is not None, "PolarityAdapter.set_now(...) must be called"
        if self._last_closes_cache and self._last_closes_cache[0] == self.now:
            return self._last_closes_cache[1]
        # bar-end < now => fully closed. bar_end == now still counts as closed
        # only if the caller has advanced past the boundary; live semantics use
        # "position 1" i.e. skipping the forming bar, so strictly '<' is safe.
        sub = self.h4[self.h4.index < self.now]
        closes = sub["close"].tail(10).tolist()
        self._last_closes_cache = (self.now, closes)
        return closes

    def check_zone_polarity(self, zone: dict, symbol: str) -> str:
        """Signature-compatible with structure.check_zone_polarity."""
        side = zone.get("side", zone.get("kind"))
        level = zone["level"]
        closes = self._last_10_closed()
        if not closes:
            return side
        if side == "support":
            return "resistance" if any(c < level for c in closes) else "support"
        if side == "resistance":
            return "support" if any(c > level for c in closes) else "resistance"
        return side
