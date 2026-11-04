"""
Three look-ahead-safe liquidity sources for the first-pass measurement:

  1. PriorDay        — high/low of the prior COMPLETED NY-calendar day.
  2. PriorSession    — high/low of the prior COMPLETED London (03:00-08:00 NY)
                       and NY (08:00-17:00 NY) sessions.
  3. AsianRange      — high/low of the prior COMPLETED Asian window (19:00 NY
                       previous day → 00:00 NY current day). This is a first-
                       principles reimplementation because research/asian_range/
                       does not exist in this repo.

All three take a UTC-indexed M1 DataFrame (`time, open, high, low, close`) and a
tz-aware `as_of_ts`, then look strictly BACKWARDS from as_of_ts.
"""
from __future__ import annotations

from datetime import time, timedelta
from typing import List, Optional, Tuple
import pandas as pd

from .levels import LiquidityLevel, LiquiditySource, BUYSIDE, SELLSIDE

NY_TZ = "America/New_York"


def _to_ny(df: pd.DataFrame) -> pd.DataFrame:
    """Return the same M1 df with a tz-aware NY index. Idempotent."""
    if df.index.tz is None:
        raise ValueError("df must have a tz-aware index (expected UTC)")
    if str(df.index.tz) == NY_TZ:
        return df
    return df.tz_convert(NY_TZ)


def _completed_before(df: pd.DataFrame, as_of_ts: pd.Timestamp) -> pd.DataFrame:
    """Slice to bars whose bar-open time is strictly BEFORE as_of_ts.

    Convention: M1 bar labelled 09:00:00 covers [09:00, 09:01). It is
    "completed" only once wall-time has reached 09:01. To be safe we require
    bar_open + 1min <= as_of_ts, i.e. bar_open <= as_of_ts - 1min.
    """
    cutoff = as_of_ts - pd.Timedelta(minutes=1)
    return df[df.index <= cutoff]


def _window_high_low(
    df_ny: pd.DataFrame,
    start_ny: pd.Timestamp,
    end_ny: pd.Timestamp,
) -> Optional[Tuple[float, float]]:
    """High/low of bars whose bar-open falls in [start_ny, end_ny). Returns
    None if the window has no bars (weekend/holiday)."""
    sub = df_ny[(df_ny.index >= start_ny) & (df_ny.index < end_ny)]
    if sub.empty:
        return None
    return float(sub["high"].max()), float(sub["low"].min())


# ─────────────────────────────────────────────────────────────────────────
# Source 1: PriorDay
# ─────────────────────────────────────────────────────────────────────────
class PriorDaySource:
    name = "PriorDay"

    def get_levels(self, df_completed, as_of_ts):
        df_ny = _to_ny(_completed_before(df_completed, as_of_ts))
        if df_ny.empty:
            return []
        as_of_ny = as_of_ts.tz_convert(NY_TZ)
        today_ny = as_of_ny.normalize()  # 00:00 NY
        # scan back up to 3 calendar days for the most recent completed day
        for back in range(1, 4):
            start = today_ny - pd.Timedelta(days=back)
            end = start + pd.Timedelta(days=1)
            hl = _window_high_low(df_ny, start, end)
            if hl is None:
                continue
            hi, lo = hl
            formed = end.tz_convert("UTC")
            return [
                LiquidityLevel(hi, BUYSIDE, "PriorDayHigh", formed,
                               meta={"day": str(start.date())}),
                LiquidityLevel(lo, SELLSIDE, "PriorDayLow", formed,
                               meta={"day": str(start.date())}),
            ]
        return []


# ─────────────────────────────────────────────────────────────────────────
# Source 2: PriorSession (London + NY)
# ─────────────────────────────────────────────────────────────────────────
LONDON_OPEN = time(3, 0)
LONDON_CLOSE = time(8, 0)
NY_OPEN = time(8, 0)
NY_CLOSE = time(17, 0)


def _last_completed_window(df_ny, as_of_ny, open_t, close_t, max_back_days=4):
    """Most recent [open_t, close_t) NY window whose end is <= as_of_ny.

    Returns (formed_at_utc, high, low) or None.
    """
    today_ny = as_of_ny.normalize()
    for back in range(0, max_back_days + 1):
        day = today_ny - pd.Timedelta(days=back)
        start = day + pd.Timedelta(hours=open_t.hour, minutes=open_t.minute)
        end = day + pd.Timedelta(hours=close_t.hour, minutes=close_t.minute)
        if end > as_of_ny:
            continue  # not yet completed
        hl = _window_high_low(df_ny, start, end)
        if hl is None:
            continue
        hi, lo = hl
        return end.tz_convert("UTC"), hi, lo
    return None


class PriorSessionSource:
    name = "PriorSession"

    def get_levels(self, df_completed, as_of_ts):
        df_ny = _to_ny(_completed_before(df_completed, as_of_ts))
        if df_ny.empty:
            return []
        as_of_ny = as_of_ts.tz_convert(NY_TZ)
        out: List[LiquidityLevel] = []
        for label, ot, ct in (
            ("London", LONDON_OPEN, LONDON_CLOSE),
            ("NY", NY_OPEN, NY_CLOSE),
        ):
            res = _last_completed_window(df_ny, as_of_ny, ot, ct)
            if not res:
                continue
            formed_utc, hi, lo = res
            out.append(LiquidityLevel(hi, BUYSIDE, f"Prior{label}High", formed_utc,
                                      meta={"session": label}))
            out.append(LiquidityLevel(lo, SELLSIDE, f"Prior{label}Low", formed_utc,
                                      meta={"session": label}))
        return out


# ─────────────────────────────────────────────────────────────────────────
# Source 3: AsianRange (19:00 prev NY day → 00:00 NY current day)
# ─────────────────────────────────────────────────────────────────────────
class AsianRangeSource:
    """Prior completed Asian window. Window is [19:00 NY day D-1, 00:00 NY day D).

    "Prior completed" = the most recent such window whose end (00:00 NY of day
    D) is <= as_of_ny. If as_of_ny is 15:00 on day D, prior completed window is
    day D's [19:00 D-1, 00:00 D]. If as_of_ny is 22:00 (during current Asia),
    prior completed is day (D-1)'s.
    """
    name = "AsianRange"

    def get_levels(self, df_completed, as_of_ts):
        df_ny = _to_ny(_completed_before(df_completed, as_of_ts))
        if df_ny.empty:
            return []
        as_of_ny = as_of_ts.tz_convert(NY_TZ)
        today_ny = as_of_ny.normalize()
        for back in range(0, 4):
            end = today_ny - pd.Timedelta(days=back)      # 00:00 NY
            start = end - pd.Timedelta(hours=5)           # 19:00 NY prev day
            if end > as_of_ny:
                continue
            hl = _window_high_low(df_ny, start, end)
            if hl is None:
                continue
            hi, lo = hl
            formed = end.tz_convert("UTC")
            return [
                LiquidityLevel(hi, BUYSIDE, "AsianRangeHigh", formed,
                               meta={"day": str((end - pd.Timedelta(seconds=1)).date())}),
                LiquidityLevel(lo, SELLSIDE, "AsianRangeLow", formed,
                               meta={"day": str((end - pd.Timedelta(seconds=1)).date())}),
            ]
        return []


ALL_SOURCES: List[LiquiditySource] = [
    PriorDaySource(),
    PriorSessionSource(),
    AsianRangeSource(),
]
