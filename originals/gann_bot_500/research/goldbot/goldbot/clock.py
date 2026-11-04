"""Trading-day clocks. TWO independent clocks by construction:

1. Pivot day-cut (`day_key`): which calendar day a bar belongs to for pivot
   construction. The VALIDATED convention across every historical result in
   this repo is `utc00` (UTC midnight). `ny17` (5 PM New York rollover —
   22:00 UTC winter, 21:00 UTC summer, automatically via zoneinfo) is offered
   because most brokers cut their daily candle there; switching it CHANGES
   every pivot level and invalidates parity with the validated numbers.

2. Rollover/fee clock (`nights_held`, `in_flatten_window`): always 5 PM NY,
   regardless of the pivot day-cut. Used only for Islamic admin-fee accrual
   (Phase 1) and the live flatten window (Phase 2).
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

import pandas as pd

NY = ZoneInfo("America/New_York")
_ROLL_SHIFT = pd.Timedelta(hours=7)   # 17:00 NY + 7h = next NY midnight


def day_key(ts: pd.Timestamp, boundary: str = "utc00") -> pd.Timestamp:
    """Trading-day label (tz-naive midnight Timestamp) for a UTC instant."""
    assert ts.tzinfo is not None, "day_key needs a tz-aware timestamp"
    if boundary == "utc00":
        return ts.tz_convert("UTC").normalize().tz_localize(None)
    if boundary == "ny17":
        # the trading day STARTING at 17:00 NY belongs to the NEXT NY date
        return (ts.tz_convert(NY) + _ROLL_SHIFT).normalize().tz_localize(None)
    raise ValueError(f"unknown day boundary {boundary!r}")


def nights_held(entry_ts: pd.Timestamp, exit_ts: pd.Timestamp) -> int:
    """Number of 17:00-NY rollover crossings in (entry, exit].

    This counts every crossing including weekends; whether the broker bills
    weekend nights (or triple-swaps one day) is a T&C question — adjust in
    costs config once verified, not here.
    """
    assert entry_ts.tzinfo is not None and exit_ts.tzinfo is not None
    assert exit_ts >= entry_ts, "exit before entry"
    # compare calendar DATES (tz stripped): tz-aware subtraction measures
    # absolute duration and silently drops a day across a DST spring-forward
    a = (entry_ts.tz_convert(NY) + _ROLL_SHIFT).normalize().tz_localize(None)
    b = (exit_ts.tz_convert(NY) + _ROLL_SHIFT).normalize().tz_localize(None)
    return max(0, (b - a).days)


def in_flatten_window(ts: pd.Timestamp, minutes_before: int = 10) -> bool:
    """True inside the pre-rollover flatten window [17:00 NY - N min, 17:00 NY).

    Phase 2 live-layer check; Phase 1 only unit-tests it (incl. across DST —
    zoneinfo moves the window between 21:00/22:00 UTC automatically)."""
    local = ts.tz_convert(NY)
    roll = local.normalize() + pd.Timedelta(hours=17)
    if local >= roll:                       # after today's 17:00 -> next roll is tomorrow
        return False
    return roll - pd.Timedelta(minutes=minutes_before) <= local < roll
