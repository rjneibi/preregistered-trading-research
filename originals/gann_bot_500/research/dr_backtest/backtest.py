"""
Multi-timeframe backtest engine.

Strategy: iterate every H1 CLOSE time in the backtest window. At each close:
  * take the profile's fully-completed D1 / H4 / H1 views (look-ahead-safe),
  * build zones exactly like the live bot (levels.gann_levels + fibonacci_pivots
    + fib_retracements + build_zones),
  * compute H4 bias via structure.get_h4_bias,
  * call signals.evaluate_signal(price, zones, h4_bias, h1_bars, atr_h1,
    use_polarity=use_polarity, reason=reason) — this is the LIVE gate function.

The live modules are imported directly. The only mirrored piece is
structure.check_zone_polarity (D-only), which live calls MT5; the pure
replacement (PolarityAdapter in polarity_pure.py) reads the pre-loaded H4
DataFrame instead.

UNTHROTTLED per Step 3: an entry is recorded every H1 close where all gates
pass. NO _fired_zones (1/zone/day), NO MAX_OPEN_TRADES, NO re-entry gating,
NO trade cooldown. This measures ENTRY-SIGNAL edge and inflates sample size
for the veto screen — it is NOT live D/R system P&L.

Skipped vs live:
  * Spread gate — HistData has no bid/ask; broker spread is verified live-side
    (13 pts current, <40 pt cap in config). Assumed OK across the backtest.
  * ADX gate      — ADX_THRESHOLD=0 for D and R, so this is already OFF live.
  * M5 RSI gate   — RSI_FILTER_ENABLED=False for D and R.
  * OPTION C M1 pullback (D-only) — an entry-timing improvement, not one of
    the six gates; we backtest the IMMEDIATE entry which is D's primary path
    and R's only path. Documented in the report.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# --- silence the live loggers (levels.py / signals.py / structure.py) at scale ---
for name in ("levels", "signal", "signals", "structure"):
    logging.getLogger(name).setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

# Live modules imported DIRECTLY — single source of truth for gate logic.
import levels as levels_mod                                 # noqa: E402
import signals as signals_mod                               # noqa: E402
import structure as structure_mod                           # noqa: E402

from research.dr_backtest.data_prep import (                # noqa: E402
    wilder_atr, completed_h4_before, completed_d1_before, bars_to_dicts,
    assert_no_h1_leak,
)
from research.dr_backtest.polarity_pure import PolarityAdapter  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────
# Config bundle used at each H1 close
# ─────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ProfileConf:
    name: str
    symbol: str
    use_polarity: bool
    tp_fixed_points: float
    sl_atr_mult: float
    partial_enabled: bool
    partial_atr_mult: float
    swing_lookback_h4: int
    atr_zone_mult: float
    confluence_atr_mult: float
    gann_degrees: list
    fib_levels: list


def profile_D() -> ProfileConf:
    return ProfileConf(
        name="D", symbol="XAUUSD",
        use_polarity=True,
        tp_fixed_points=900.0,
        sl_atr_mult=1.0,
        partial_enabled=True, partial_atr_mult=1.0,
        swing_lookback_h4=50,
        atr_zone_mult=0.3,
        confluence_atr_mult=0.5,
        gann_degrees=[45, 90, 135, 180, 225, 270, 315, 360],
        fib_levels=[0.382, 0.500, 0.618, 0.786],
    )


def profile_R() -> ProfileConf:
    return ProfileConf(
        name="R", symbol="XAUUSD",
        use_polarity=False,
        tp_fixed_points=1000.0,
        sl_atr_mult=1.5,
        partial_enabled=True,   # per config_R.py:PARTIAL_CLOSE_ENABLED=True
        partial_atr_mult=1.0,
        swing_lookback_h4=50,
        atr_zone_mult=0.3,
        confluence_atr_mult=0.5,
        gann_degrees=[45, 90, 135, 180, 225, 270, 315, 360],
        fib_levels=[0.382, 0.500, 0.618, 0.786],
    )


# ─────────────────────────────────────────────────────────────────────────
# Per-H1-close evaluator
# ─────────────────────────────────────────────────────────────────────────
class Backtester:
    def __init__(self, prof: ProfileConf,
                 h1: pd.DataFrame, h4: pd.DataFrame, d1: pd.DataFrame,
                 m1: pd.DataFrame, atr_h1: pd.Series,
                 assert_no_leak_every: int = 5000):
        self.prof = prof
        self.h1 = h1     # index = bar OPEN (UTC)
        self.h4 = h4     # index = bar OPEN (UTC)
        self.d1 = d1     # index = bar OPEN (UTC)
        self.m1 = m1
        self.atr_h1 = atr_h1
        self.assert_no_leak_every = assert_no_leak_every

        # Pure polarity adapter — monkey-patched onto structure module while
        # this backtester runs. Restored in a context manager.
        self._polarity_adapter = PolarityAdapter(self.h4)
        # cheat-safe live config for the modules that read `config.` values
        import config as live_config
        for k, v in [
            ("SYMBOL", prof.symbol),
            ("GANN_DEGREES", prof.gann_degrees),
            ("FIB_LEVELS", prof.fib_levels),
            ("ATR_ZONE_WIDTH_MULT", prof.atr_zone_mult),
            ("CONFLUENCE_ATR_MULT", prof.confluence_atr_mult),
            ("SWING_LOOKBACK_H4", prof.swing_lookback_h4),
        ]:
            setattr(live_config, k, v)

    # ------------------------------------------------------------------
    def _bars_h4_snapshot(self, cursor: pd.Timestamp) -> list[dict]:
        """H4 bars fully closed before cursor (last 200 for EMA50 convergence,
        also enough for find_swing over SWING_LOOKBACK_H4)."""
        closed = completed_h4_before(self.h4, cursor)
        # get_h4_bias needs ≥200 for a converged EMA50 (per bot.py comment);
        # we'll take the last 250 for safety.
        return bars_to_dicts(closed.tail(250))

    def _bars_h1_snapshot(self, cursor: pd.Timestamp,
                          this_bar_open: pd.Timestamp) -> list[dict]:
        """Return last 10 completed H1 bars + a DUMMY forming-bar so that
        h1_close_confirmed's bars[-2] indexes the just-closed bar.

        cursor = the H1 close time (= this_bar_open + 1h).
        this_bar_open = the just-closed bar's open time = cursor - 1h.
        """
        closed = self.h1[self.h1.index <= this_bar_open].tail(10)
        bars = bars_to_dicts(closed)
        if bars:
            # dummy 'forming' bar with the same close as the just-closed bar so
            # any accidental use of bars[-1] doesn't crash and doesn't leak.
            last = bars[-1]
            bars.append({"time": int(cursor.timestamp()),
                         "open": last["close"], "high": last["close"],
                         "low": last["close"], "close": last["close"],
                         "volume": 0.0})
        return bars

    def _bars_d1_snapshot(self, cursor: pd.Timestamp) -> list[dict]:
        """D1: previous full day + today (still forming). bars[-1].open is the
        one bot.py reads for daily_open; bars[-2] is prev day for HLC pivots."""
        completed = completed_d1_before(self.d1, cursor)
        if completed.empty:
            return []
        # 'today' = the D1 bar whose open <= cursor but whose close > cursor.
        # If cursor is exactly on a UTC midnight boundary, the just-closed D1
        # is a fully-completed bar — treat that as "today" (its open is fresh).
        today_open_ts = pd.Timestamp(cursor.floor("D"))
        # slice all D1 bars with open <= today_open_ts (weekend gaps handled)
        d1_upto = self.d1[self.d1.index <= today_open_ts]
        if d1_upto.empty or len(d1_upto) < 2:
            return []
        prev = d1_upto.iloc[-2]
        today = d1_upto.iloc[-1]
        return [
            {"time": int(d1_upto.index[-2].timestamp()),
             "open": float(prev["open"]), "high": float(prev["high"]),
             "low": float(prev["low"]), "close": float(prev["close"]),
             "volume": 0.0},
            {"time": int(d1_upto.index[-1].timestamp()),
             "open": float(today["open"]), "high": float(today["high"]),
             "low": float(today["low"]), "close": float(today["close"]),
             "volume": 0.0},
        ]

    # ------------------------------------------------------------------
    def evaluate_close(self, this_bar_open: pd.Timestamp) -> Optional[dict]:
        """Evaluate the six-gate pipeline as of the H1 close = this_bar_open + 1h.

        Returns an entry-record dict or None.
        """
        cursor = this_bar_open + pd.Timedelta(hours=1)
        atr = float(self.atr_h1.get(this_bar_open, np.nan))
        if not np.isfinite(atr) or atr <= 0:
            return None

        bars_h4 = self._bars_h4_snapshot(cursor)
        if len(bars_h4) < 50:
            return None
        bars_h1 = self._bars_h1_snapshot(cursor, this_bar_open)
        if len(bars_h1) < 3:
            return None
        bars_d1 = self._bars_d1_snapshot(cursor)
        if len(bars_d1) < 2:
            return None

        # look-ahead assertion (periodic — cheap to check but not needed every bar)
        # ... a compile-time sanity check happens in main() before the loop.

        # price = this bar's close (the just-closed H1 bar)
        this = self.h1.loc[this_bar_open]
        price = float(this["close"])

        # daily open (matches bot.py logic)
        daily_open = bars_d1[-1]["open"]
        prev = bars_d1[-2]

        gann = levels_mod.gann_levels(daily_open, self.prof.gann_degrees)
        pivots = levels_mod.fibonacci_pivots(prev["high"], prev["low"], prev["close"])
        swing_h, swing_l, sdir = structure_mod.find_swing(bars_h4)
        fibs = levels_mod.fib_retracements(swing_h, swing_l, sdir)
        all_levels = {**gann, **pivots, **fibs}
        zones = levels_mod.build_zones(all_levels, atr,
                                       self.prof.atr_zone_mult, price,
                                       fib_swing_dir=sdir)

        # bind the polarity adapter to the cursor and monkey-patch for THIS call
        if self.prof.use_polarity:
            self._polarity_adapter.set_now(cursor)
            _orig = structure_mod.check_zone_polarity
            structure_mod.check_zone_polarity = self._polarity_adapter.check_zone_polarity

        try:
            h4_bias = structure_mod.get_h4_bias(bars_h4)
            reason = {}
            sig = signals_mod.evaluate_signal(
                price, zones, h4_bias, bars_h1, atr,
                use_polarity=self.prof.use_polarity, reason=reason,
            )
        finally:
            if self.prof.use_polarity:
                structure_mod.check_zone_polarity = _orig

        if sig is None:
            return None
        return {
            "profile": self.prof.name,
            "entry_ts": cursor.isoformat(),           # H1 close time (entry moment)
            "h1_bar_open": this_bar_open.isoformat(),
            "direction": sig["direction"],
            "entry_price": price,
            "atr": atr,
            "h4_bias": h4_bias,
            "zone_source": sig["zone_hit"]["source"],
            "zone_level": sig["zone_hit"]["level"],
            "target_source": sig["target_zone"]["source"] if sig["target_zone"] else None,
            "confluence": sig["confluence"],
            "polarity_flipped": sig["polarity_flipped"],
        }

    # ------------------------------------------------------------------
    def run(self, start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
        entries: list[dict] = []
        # iterate every H1 whose CLOSE time is within [start, end]
        # this_bar_open = close - 1h ; keep only bars whose close is <= end
        window_opens = self.h1.index[
            (self.h1.index + pd.Timedelta(hours=1) >= start) &
            (self.h1.index + pd.Timedelta(hours=1) <= end)
        ]
        total = len(window_opens)
        checked = 0
        for open_ts in window_opens:
            checked += 1
            if checked % self.assert_no_leak_every == 0:
                cursor = open_ts + pd.Timedelta(hours=1)
                assert_no_h1_leak(self.h1, self.h4, cursor)
                pct = 100 * checked / total
                print(f"  [{self.prof.name}] {checked:>7,}/{total:,} "
                      f"({pct:5.1f}%) — entries so far: {len(entries)}",
                      flush=True)
            rec = self.evaluate_close(open_ts)
            if rec is not None:
                entries.append(rec)
        return entries
