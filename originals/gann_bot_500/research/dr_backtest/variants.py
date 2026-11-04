"""
Research-only variant hooks for the D/R backtest — Runs B and C1-C4.

Design rule: NO live-module edits. Everything here is either a data-shaping
filter (level-family drop for C1-C3, bias override for C4) or a monkey-patch
applied for the duration of a backtest and restored in a `try/finally`.

The only monkey-patch in the harness that reaches into a live module is
`structure.check_zone_polarity` (already used in the baseline as a
research-only pure replacement — see `polarity_pure.py`). This file adds ONE
more monkey-patch on request: `structure.h1_close_confirmed` for Run B's
wick-rejection acceptance. Both are restored at the end of every run.

LOOK-AHEAD SAFETY: the trend-day regime flag reads ONLY H1 bars whose CLOSE
time is `<= cursor` (i.e., strictly closed at or before the current entry
bar). Never reads the not-yet-closed current bar or any future data. There is
an explicit assertion in the helper and it must be true for Run B to be valid.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd


# ─────────────────────────────────────────────────────────────────
# Level family classification (used by C1, C2, C3)
# ─────────────────────────────────────────────────────────────────
def _num_suffix(key: str) -> Optional[int]:
    if not (key.startswith("R") or key.startswith("S")):
        return None
    try:
        return int(key[1:])
    except ValueError:
        return None


def is_gann_key(key: str) -> bool:
    """Gann rotational levels: R{deg} / S{deg} where deg ∈ {45,90,...,360}."""
    n = _num_suffix(key)
    return n is not None and n >= 45


def is_pivot_key(key: str) -> bool:
    """Fibonacci pivots: PP + R1..R3 + S1..S3."""
    if key == "PP":
        return True
    n = _num_suffix(key)
    return n is not None and 1 <= n <= 3


def is_fib_retr_key(key: str) -> bool:
    """Fibonacci retracements off the H4 swing."""
    return key.startswith("fib_")


LEVEL_FILTER: dict[str, Callable[[str], bool]] = {
    "gann":  is_gann_key,
    "pivot": is_pivot_key,
    "fib":   is_fib_retr_key,
}


def drop_family(all_levels: dict, family: Optional[str]) -> dict:
    """Return `all_levels` with all keys belonging to `family` removed.
    family ∈ {None, 'gann', 'pivot', 'fib'}."""
    if family is None:
        return all_levels
    pred = LEVEL_FILTER[family]
    return {k: v for k, v in all_levels.items() if not pred(k)}


# ─────────────────────────────────────────────────────────────────
# Trend-day regime detector (Run B only) — look-ahead-safe
# ─────────────────────────────────────────────────────────────────
TREND_LOOKBACK_H1_BARS = 24     # 1 day of H1 context
TREND_DIRECTIONALITY_THRESHOLD = 0.6


def is_trend_day(h1_df: pd.DataFrame, cursor: pd.Timestamp,
                 lookback: int = TREND_LOOKBACK_H1_BARS,
                 threshold: float = TREND_DIRECTIONALITY_THRESHOLD) -> bool:
    """Trend-day flag based ONLY on CLOSED H1 bars strictly before `cursor`.

    Directionality = |close_last - close_first| / (max_high - min_low) over
    the last `lookback` closed H1 bars. > threshold → trend day.

    LOOK-AHEAD ASSERTION: the last bar considered must have bar-CLOSE time
    <= cursor. bar-close = bar-open + 1h. So bar-open must be <= cursor - 1h.
    """
    # bar-open <= cursor - 1h  ⇔  bar-close <= cursor
    last_valid_open = cursor - pd.Timedelta(hours=1)
    closed = h1_df[h1_df.index <= last_valid_open]
    if len(closed) < lookback:
        return False
    sub = closed.iloc[-lookback:]
    # explicit assertion
    last_bar_close = sub.index[-1] + pd.Timedelta(hours=1)
    assert last_bar_close <= cursor, (
        f"trend regime look-ahead: last H1 bar close {last_bar_close} > cursor {cursor}"
    )
    closes = sub["close"].to_numpy()
    highs  = sub["high"].to_numpy()
    lows   = sub["low"].to_numpy()
    net = abs(float(closes[-1]) - float(closes[0]))
    rng = float(highs.max() - lows.min())
    if rng <= 0:
        return False
    return (net / rng) > threshold


# ─────────────────────────────────────────────────────────────────
# H1 confirmation variant: wick rejection on trend days (Run B)
# ─────────────────────────────────────────────────────────────────
def h1_confirmed_wick_variant(bars_h1: list, level: float, direction: str,
                              is_trend: bool) -> bool:
    """Baseline body-close-through PLUS: on trend days, accept ICT-style
    wick rejection candles.

    Baseline rule (matches structure.h1_close_confirmed live semantics):
      * bars_h1[-2] is the last CLOSED H1 bar (bars_h1[-1] is treated by the
        live code as still forming — our backtest snapshot uses the same
        indexing convention via a dummy trailing bar).
      * direction == "above" (BUY confirmation, break UP through the level):
            confirmed if bar.close > level AND bar.open < level  (body straddles)
      * direction == "below" (SELL confirmation, break DOWN through):
            confirmed if bar.close < level AND bar.open > level

    Wick-rejection additions (trend days only):
      * direction == "above" (BUY at support): confirmed if
            bar.low < level      (wick reached DOWN into support)
        AND bar.close > level    (body closed back ABOVE support)
        AND bar.close > bar.open (bullish body — actual rejection)
      * direction == "below" (SELL at resistance): confirmed if
            bar.high > level     (wick reached UP into resistance)
        AND bar.close < level    (body closed back BELOW resistance)
        AND bar.close < bar.open (bearish body)

    Both patterns are the standard ICT "rejection candle" pattern. They fire
    ONLY on `is_trend=True` days per the T1 pre-registration.
    """
    if len(bars_h1) < 2:
        return False
    bar = bars_h1[-2]
    o = float(bar["open"]); h = float(bar["high"])
    lo = float(bar["low"]); c = float(bar["close"])

    if direction == "above":
        body = c > level and o < level
        if body:
            return True
        if is_trend:
            wick_rej = (lo < level) and (c > level) and (c > o)
            if wick_rej:
                return True
        return False
    elif direction == "below":
        body = c < level and o > level
        if body:
            return True
        if is_trend:
            wick_rej = (h > level) and (c < level) and (c < o)
            if wick_rej:
                return True
        return False
    else:
        return False


# ─────────────────────────────────────────────────────────────────
# Arm spec
# ─────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Arm:
    key: str                     # 'A' / 'B' / 'C1' / 'C2' / 'C3' / 'C4'
    label: str
    drop_family: Optional[str] = None       # 'gann' | 'pivot' | 'fib' | None
    wick_on_trend: bool = False             # Run B
    bias_off: bool = False                  # Run C4


ARMS: list[Arm] = [
    Arm("A",  "baseline (live config)"),
    Arm("B",  "T1: wick on trend days",     wick_on_trend=True),
    Arm("C1", "ablate Gann family off",      drop_family="gann"),
    Arm("C2", "ablate Fib retracement off",  drop_family="fib"),
    Arm("C3", "ablate Fib pivot family off", drop_family="pivot"),
    Arm("C4", "ablate H4 bias gate off",     bias_off=True),
]
