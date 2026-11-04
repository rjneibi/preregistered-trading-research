"""
Three-run variant backtest orchestrator.
  Run A — baseline (current live D and R config).
  Run B — T1 wick-on-trend-days variant.
  Run C — four ablations (C1 Gann off · C2 fib retr off · C3 pivots off · C4 bias off).

Design constraints:
  * NO live-code edits. All variant logic lives in variants.py + this file.
  * All variant knobs applied via (a) data-shaping filters, (b) two-shot bias
    override for C4, or (c) monkey-patching structure.h1_close_confirmed inside
    a try/finally for Run B.
  * IS window: 2016-01-01 → 2022-12-31.
    OOS window: 2023-01-01 → HistData end (clamped, reported honestly).
  * OOS is broken out PER CALENDAR YEAR so regime dependence is visible.
  * Run B: split by trend-day flag (closed-bar directionality > 0.6).
  * Run C4: split by direction (long PF vs short PF).
"""
from __future__ import annotations

import json
import os
import sys
import time
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# silence live-module loggers at scale (must precede live imports)
for _name in ("levels", "signal", "signals", "structure"):
    logging.getLogger(_name).setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# live modules — imported and CALLED but NEVER modified
import levels as levels_mod                                          # noqa: E402
import signals as signals_mod                                        # noqa: E402
import structure as structure_mod                                    # noqa: E402
import config as live_config                                         # noqa: E402

from research.dr_backtest.data_prep import (                         # noqa: E402
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
    completed_h4_before, completed_d1_before, bars_to_dicts,
    assert_no_h1_leak,
)
from research.dr_backtest.exit_sim import simulate_trade             # noqa: E402
from research.dr_backtest.metrics import basic_stats, size_label     # noqa: E402
from research.dr_backtest.polarity_pure import PolarityAdapter       # noqa: E402
from research.dr_backtest.backtest import profile_D, profile_R       # noqa: E402
from research.dr_backtest.variants import (                          # noqa: E402
    Arm, ARMS, drop_family, is_trend_day,
    h1_confirmed_wick_variant, TREND_LOOKBACK_H1_BARS,
    TREND_DIRECTIONALITY_THRESHOLD,
)

OUT = REPO / "research" / "dr_backtest"

# ─────────────────────────────────────────────────────────────
# Window — per user brief
# ─────────────────────────────────────────────────────────────
BT_IS_START  = pd.Timestamp("2016-01-01T00:00:00Z")
BT_IS_END    = pd.Timestamp("2022-12-31T23:59:00Z")
BT_OOS_START = pd.Timestamp("2023-01-01T00:00:00Z")
BT_OOS_END   = pd.Timestamp("2026-12-31T23:59:00Z")   # clamp to actual data
LOAD_BUFFER_DAYS = 45


# ─────────────────────────────────────────────────────────────
# Thread the trend-flag through the monkey-patch (Run B only)
# ─────────────────────────────────────────────────────────────
_TREND_STATE = {"is_trend": False}


def _set_trend(flag: bool) -> None:
    _TREND_STATE["is_trend"] = flag


def _patched_h1_close_confirmed(bars_h1, level, direction):
    """Drop-in for structure.h1_close_confirmed: baseline body-close-through
    always, plus wick rejection on trend days. Reads the trend flag from
    module-level state set immediately before each evaluate_signal call."""
    return h1_confirmed_wick_variant(bars_h1, level, direction,
                                     _TREND_STATE["is_trend"])


# ─────────────────────────────────────────────────────────────
# One-arm-one-profile runner
# ─────────────────────────────────────────────────────────────
def run_arm_profile(arm: Arm, prof, h1: pd.DataFrame, h4: pd.DataFrame,
                    d1: pd.DataFrame, m1: pd.DataFrame, atr_h1: pd.Series,
                    start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
    """Iterate every H1 close in [start, end] with `arm`'s variant logic
    applied; simulate exits; return trade records."""
    # per-arm live-config alignment (SYMBOL/GANN_DEGREES etc.)
    for k, v in [
        ("SYMBOL", prof.symbol),
        ("GANN_DEGREES", prof.gann_degrees),
        ("FIB_LEVELS", prof.fib_levels),
        ("ATR_ZONE_WIDTH_MULT", prof.atr_zone_mult),
        ("CONFLUENCE_ATR_MULT", prof.confluence_atr_mult),
        ("SWING_LOOKBACK_H4", prof.swing_lookback_h4),
    ]:
        setattr(live_config, k, v)

    # polarity adapter (D only; monkey-patch structure.check_zone_polarity)
    polarity = PolarityAdapter(h4)
    if prof.use_polarity:
        _orig_polarity = structure_mod.check_zone_polarity
        structure_mod.check_zone_polarity = polarity.check_zone_polarity
    if arm.wick_on_trend:
        _orig_h1_confirm = structure_mod.h1_close_confirmed
        structure_mod.h1_close_confirmed = _patched_h1_close_confirmed

    try:
        entries: list[dict] = []
        # opens in window
        window_opens = h1.index[
            (h1.index + pd.Timedelta(hours=1) >= start) &
            (h1.index + pd.Timedelta(hours=1) <= end)
        ]
        total = len(window_opens); checked = 0; last_leak_ok = None
        for this_bar_open in window_opens:
            checked += 1
            cursor = this_bar_open + pd.Timedelta(hours=1)
            if checked % 5000 == 0:
                pct = 100 * checked / total
                print(f"    [{arm.key}·{prof.name}] {checked:>7,}/{total:,} "
                      f"({pct:5.1f}%) — entries {len(entries)}", flush=True)
                assert_no_h1_leak(h1, h4, cursor)

            atr = float(atr_h1.get(this_bar_open, np.nan))
            if not np.isfinite(atr) or atr <= 0:
                continue

            # completed bar snapshots
            bars_h4 = bars_to_dicts(completed_h4_before(h4, cursor).tail(250))
            if len(bars_h4) < 50:
                continue
            closed_h1 = h1[h1.index <= this_bar_open].tail(10)
            bars_h1_list = bars_to_dicts(closed_h1)
            if len(bars_h1_list) < 2:
                continue
            # dummy trailing bar to mimic live "forming" indexing
            last = bars_h1_list[-1]
            bars_h1_list.append({"time": int(cursor.timestamp()),
                                 "open": last["close"], "high": last["close"],
                                 "low": last["close"], "close": last["close"],
                                 "volume": 0.0})
            # D1: today's still-forming bar + yesterday's completed
            today_open_ts = pd.Timestamp(cursor.floor("D"))
            d1_upto = d1[d1.index <= today_open_ts]
            if len(d1_upto) < 2:
                continue
            prev_d1 = d1_upto.iloc[-2]
            today_d1 = d1_upto.iloc[-1]
            daily_open = float(today_d1["open"])

            this_h1 = h1.loc[this_bar_open]
            price = float(this_h1["close"])

            # ── LEVELS ─── with ablation filter for C1-C3
            gann_lvls   = levels_mod.gann_levels(daily_open, prof.gann_degrees)
            pivot_lvls  = levels_mod.fibonacci_pivots(prev_d1["high"], prev_d1["low"], prev_d1["close"])
            swing_h, swing_l, sdir = structure_mod.find_swing(bars_h4)
            fib_lvls    = levels_mod.fib_retracements(swing_h, swing_l, sdir)
            all_levels  = {**gann_lvls, **pivot_lvls, **fib_lvls}
            all_levels  = drop_family(all_levels, arm.drop_family)
            zones = levels_mod.build_zones(all_levels, atr,
                                           prof.atr_zone_mult, price,
                                           fib_swing_dir=sdir)

            # H4 bias (live implementation)
            h4_bias = structure_mod.get_h4_bias(bars_h4)

            # polarity cursor
            if prof.use_polarity:
                polarity.set_now(cursor)

            # trend flag for Run B (look-ahead safe assertion inside helper)
            trend = False
            if arm.wick_on_trend:
                trend = is_trend_day(h1, cursor)
                _set_trend(trend)

            # ── SIGNAL ─── with C4 two-shot bias override
            def _call_sig(bias):
                reason = {}
                return signals_mod.evaluate_signal(
                    price, zones, bias, bars_h1_list, atr,
                    use_polarity=prof.use_polarity, reason=reason,
                )
            if arm.bias_off:
                # try both biases; take whichever fires (equivalent to removing
                # the bias filter — signals still enforces zone/polarity/H1)
                sig = _call_sig("bullish") or _call_sig("bearish")
            else:
                sig = _call_sig(h4_bias)
            if sig is None:
                continue

            rec = {
                "arm": arm.key, "profile": prof.name,
                "entry_ts": cursor.isoformat(),
                "direction": sig["direction"],
                "entry_price": price, "atr": atr,
                "h4_bias": h4_bias, "trend_day": bool(trend),
                "zone_source": sig["zone_hit"]["source"],
                "zone_level": sig["zone_hit"]["level"],
                "confluence": sig["confluence"],
                "polarity_flipped": sig["polarity_flipped"],
            }
            # exit sim with THIS profile's actual TP/SL/partial config
            r = simulate_trade(
                sig["direction"], price, cursor, atr, m1,
                tp_fixed_points=prof.tp_fixed_points,
                sl_atr_mult=prof.sl_atr_mult,
                partial_enabled=prof.partial_enabled,
                partial_atr_mult=prof.partial_atr_mult,
            )
            rec["outcome_status"] = r["status"]
            rec["pnl_points"]     = r["pnl_points"]
            rec["exit_ts_final"]  = r["exit_ts_final"]
            rec["partial_hit"]    = r["partial_hit"]
            entries.append(rec)
        return entries
    finally:
        if prof.use_polarity:
            structure_mod.check_zone_polarity = _orig_polarity
        if arm.wick_on_trend:
            structure_mod.h1_close_confirmed = _orig_h1_confirm


# ─────────────────────────────────────────────────────────────
# Load + orchestrate
# ─────────────────────────────────────────────────────────────
def main():
    print(f"=== window request: IS {BT_IS_START.date()} → {BT_IS_END.date()} · "
          f"OOS {BT_OOS_START.date()} → {BT_OOS_END.date()} ===", flush=True)
    print(f"[data] loading M1 ...", flush=True)
    load_start = BT_IS_START - pd.Timedelta(days=LOAD_BUFFER_DAYS)
    load_end   = BT_OOS_END
    m1 = load_m1(load_start, load_end)
    real_start = m1.index.min()
    real_end   = m1.index.max()
    # clamp end to what's actually there
    bt_end_effective = min(BT_OOS_END, real_end)
    print(f"[data] M1 bars: {len(m1):,}  actual coverage: {real_start} → {real_end}",
          flush=True)
    print(f"[data] EFFECTIVE OOS end (clamped to data): {bt_end_effective}", flush=True)

    print(f"[data] resample H1 / H4 / D1 ...", flush=True)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    print(f"[data] H1={len(h1):,}  H4={len(h4):,}  D1={len(d1):,}  "
          f"ATR non-nan={atr_h1.notna().sum():,}", flush=True)

    # store per-arm-per-profile trades
    all_trades: dict[tuple, list[dict]] = {}
    total_start = time.time()
    for arm in ARMS:
        for prof_fn, prof_name in [(profile_D, "D"), (profile_R, "R")]:
            prof = prof_fn()
            t0 = time.time()
            print(f"\n--- Arm {arm.key} · Profile {prof.name} — {arm.label} ---",
                  flush=True)
            trades = run_arm_profile(arm, prof, h1, h4, d1, m1, atr_h1,
                                     BT_IS_START, bt_end_effective)
            all_trades[(arm.key, prof.name)] = trades
            elapsed = time.time() - t0
            print(f"    → {len(trades)} entries in {elapsed:.0f}s", flush=True)

    total_elapsed = time.time() - total_start
    print(f"\n=== all arms done in {total_elapsed:.0f}s ===", flush=True)

    # persist raw trades per arm-profile
    for (arm_key, prof_name), trades in all_trades.items():
        p = OUT / f"trades_variants_{arm_key}_{prof_name}.jsonl"
        with open(p, "w") as f:
            for e in trades:
                f.write(json.dumps(e) + "\n")

    # write the report
    from research.dr_backtest.variants_report import write_report        # noqa: E402
    write_report(all_trades, real_start, real_end, bt_end_effective)


if __name__ == "__main__":
    main()
