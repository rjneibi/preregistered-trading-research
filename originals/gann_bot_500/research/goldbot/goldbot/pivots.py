"""Daily R3/S3 pivot levels on the previous trading day, shifted to kill
lookahead, plus the baseline dead-level check.

Formula (ported from the validated live logic, flip_bot.py:160-162 /
levels.py::fibonacci_pivots with the 1.000 multiplier):

    PP = (H + L + C) / 3          # UNROUNDED pp feeds R3/S3
    R3 = round(PP + (H - L), 2)
    S3 = round(PP - (H - L), 2)

Note this is the Fibonacci-style R3/S3 (PP +/- 1.0*range), NOT the classic
floor-trader R3 = H + 2*(PP - L). Only R3/S3 carry edge — R1/R2/S1/S2 and fib
retracements were tested and rejected (STRATEGY_SPECIFICATION.md §3).

The 2dp rounding is kept deliberately for parity with the live bot; levels are
computed from unrounded PP so rounding is applied exactly once.
"""

from __future__ import annotations

import pandas as pd


def daily_pivots(d1: pd.DataFrame) -> pd.DataFrame:
    """Per-trading-day pivot frame, indexed like d1 (bar-open = day start).

    Row for day D holds levels computed from day D-1's OHLC (`.shift(1)` —
    the lookahead kill). First row is NaN. d1 must contain only real trading
    days (weekend gaps already dropped by the resampler), so shift(1) is the
    previous TRADING day, matching the live bot's prev-D1-bar convention.
    """
    h, l, c = d1["high"], d1["low"], d1["close"]
    rng = h - l
    pp = (h + l + c) / 3.0
    out = pd.DataFrame({
        "pp": pp.round(2),
        "r3": (pp + rng).round(2),
        "s3": (pp - rng).round(2),
    }, index=d1.index)
    return out.shift(1)


def dead_levels(h4: pd.DataFrame, day_open: pd.Timestamp,
                r3: float, s3: float, n: int = 10) -> tuple[bool, bool, int]:
    """Baseline dead-check: a level already breached by any of the last `n`
    UTC-H4 closes fully completed BEFORE day_open is dead for the day.

    Uses the backtest-harness convention (closes before day_open), which is
    what every validated number was produced with. The live bot's variant
    (last 10 H4 closes before *now*, flip_bot.py:170-176) can additionally
    kill a level intraday — documented divergence, not ported.

    Returns (r3_dead, s3_dead, n_completed_h4).
    """
    closed = h4[h4.index + pd.Timedelta(hours=4) <= day_open]
    base = closed["close"].tail(n)
    r3_dead = bool((base > r3).any())    # resistance: any close above -> dead
    s3_dead = bool((base < s3).any())    # support: any close below -> dead
    return r3_dead, s3_dead, len(closed)


def r3s3_fade_events(*args, **kwargs):
    """Documented placeholder from the goldbot spec — intentionally NOT
    implemented. Fading R3/S3 was tested against 11 years of XAUUSD and
    REJECTED (the edge is the BREAKOUT: close beyond the level, level
    polarity flips — see STRATEGY_SPECIFICATION.md §2). The validated event
    generators live in goldbot.events:

        generate_events_final  — conviction dual-arm H1+H4 (live spec)
        generate_events_base   — H4-close ancestor (fixed-$ exits)
    """
    raise NotImplementedError(
        "r3s3_fade_events is the spec's placeholder; the validated rules are "
        "breakout generators in goldbot.events (fade was tested and rejected)"
    )
