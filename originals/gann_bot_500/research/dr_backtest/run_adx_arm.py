"""
Arm C5 — ADX≥25 gate ON (research-only; live is ADX_THRESHOLD=0 i.e. OFF).

Question (from the audit directive): does an ADX>25 H4 filter help or hurt,
and does it asymmetrically starve BUY signals given gold's slow bullish grind?

Method: identical to Run A baseline, EXCEPT entries are kept only when pure
Wilder ADX(14) on completed H4 bars is >= 25 at entry time. We record ADX per
entry so the report can ALSO show what the baseline population's ADX
distribution looks like (i.e., the filter's counterfactual effect computed on
one run rather than re-running the engine twice).

Implementation trick: we re-use Run A's recorded trades and CANNOT — ADX
wasn't recorded then. So this re-runs the engine once per profile with ADX
computed and recorded per entry, gate NOT enforced (record-only). The C5
result is then computed by filtering the recorded population at adx >= 25.
This gives BOTH the baseline-with-adx-recorded AND the C5 arm from one run,
and lets us test other thresholds descriptively (15/20/25/30) without
re-running. Thresholds other than 25 are DESCRIPTIVE ONLY (the directive's
pre-specified test is 25).
"""
from __future__ import annotations

import json
import sys
import time
import logging
from pathlib import Path

import numpy as np
import pandas as pd

for _name in ("levels", "signal", "signals", "structure"):
    logging.getLogger(_name).setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

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
from research.dr_backtest.polarity_pure import PolarityAdapter       # noqa: E402
from research.dr_backtest.backtest import profile_D, profile_R       # noqa: E402
from research.dr_backtest.adx_pure import adx_from_bars              # noqa: E402

OUT = REPO / "research" / "dr_backtest"
BT_START = pd.Timestamp("2016-01-01T00:00:00Z")
BT_END   = pd.Timestamp("2026-12-31T23:59:00Z")   # clamped by data
LOAD_BUFFER_DAYS = 45


def run_profile(prof, h1, h4, d1, m1, atr_h1, start, end):
    for k, v in [
        ("SYMBOL", prof.symbol), ("GANN_DEGREES", prof.gann_degrees),
        ("FIB_LEVELS", prof.fib_levels),
        ("ATR_ZONE_WIDTH_MULT", prof.atr_zone_mult),
        ("CONFLUENCE_ATR_MULT", prof.confluence_atr_mult),
        ("SWING_LOOKBACK_H4", prof.swing_lookback_h4),
    ]:
        setattr(live_config, k, v)

    polarity = PolarityAdapter(h4)
    if prof.use_polarity:
        _orig = structure_mod.check_zone_polarity
        structure_mod.check_zone_polarity = polarity.check_zone_polarity
    try:
        entries = []
        opens = h1.index[(h1.index + pd.Timedelta(hours=1) >= start) &
                         (h1.index + pd.Timedelta(hours=1) <= end)]
        total = len(opens); checked = 0
        for this_bar_open in opens:
            checked += 1
            cursor = this_bar_open + pd.Timedelta(hours=1)
            if checked % 5000 == 0:
                assert_no_h1_leak(h1, h4, cursor)
                print(f"    [C5·{prof.name}] {checked:>7,}/{total:,} "
                      f"({100*checked/total:5.1f}%) — entries {len(entries)}",
                      flush=True)
            atr = float(atr_h1.get(this_bar_open, np.nan))
            if not np.isfinite(atr) or atr <= 0:
                continue
            bars_h4 = bars_to_dicts(completed_h4_before(h4, cursor).tail(250))
            if len(bars_h4) < 50:
                continue
            closed_h1 = h1[h1.index <= this_bar_open].tail(10)
            bars_h1_list = bars_to_dicts(closed_h1)
            if len(bars_h1_list) < 2:
                continue
            last = bars_h1_list[-1]
            bars_h1_list.append({"time": int(cursor.timestamp()),
                                 "open": last["close"], "high": last["close"],
                                 "low": last["close"], "close": last["close"],
                                 "volume": 0.0})
            today_open_ts = pd.Timestamp(cursor.floor("D"))
            d1_upto = d1[d1.index <= today_open_ts]
            if len(d1_upto) < 2:
                continue
            prev_d1 = d1_upto.iloc[-2]
            daily_open = float(d1_upto.iloc[-1]["open"])
            price = float(h1.loc[this_bar_open]["close"])

            gann_l  = levels_mod.gann_levels(daily_open, prof.gann_degrees)
            piv_l   = levels_mod.fibonacci_pivots(prev_d1["high"], prev_d1["low"], prev_d1["close"])
            sh, sl, sdir = structure_mod.find_swing(bars_h4)
            fib_l   = levels_mod.fib_retracements(sh, sl, sdir)
            zones = levels_mod.build_zones({**gann_l, **piv_l, **fib_l}, atr,
                                           prof.atr_zone_mult, price,
                                           fib_swing_dir=sdir)
            h4_bias = structure_mod.get_h4_bias(bars_h4)
            if prof.use_polarity:
                polarity.set_now(cursor)
            reason = {}
            sig = signals_mod.evaluate_signal(price, zones, h4_bias,
                                              bars_h1_list, atr,
                                              use_polarity=prof.use_polarity,
                                              reason=reason)
            if sig is None:
                continue
            # record ADX (gate NOT enforced — record-only run)
            adx_val = adx_from_bars(bars_h4, 14)
            r = simulate_trade(sig["direction"], price, cursor, atr, m1,
                               tp_fixed_points=prof.tp_fixed_points,
                               sl_atr_mult=prof.sl_atr_mult,
                               partial_enabled=prof.partial_enabled,
                               partial_atr_mult=prof.partial_atr_mult)
            entries.append({
                "profile": prof.name, "entry_ts": cursor.isoformat(),
                "direction": sig["direction"], "entry_price": price,
                "atr": atr, "adx_h4": adx_val, "h4_bias": h4_bias,
                "zone_source": sig["zone_hit"]["source"],
                "outcome_status": r["status"], "pnl_points": r["pnl_points"],
            })
        return entries
    finally:
        if prof.use_polarity:
            structure_mod.check_zone_polarity = _orig


def main():
    print("[data] loading M1 ...", flush=True)
    m1 = load_m1(BT_START - pd.Timedelta(days=LOAD_BUFFER_DAYS), BT_END)
    end_eff = m1.index.max()
    print(f"[data] {len(m1):,} bars → end {end_eff}", flush=True)
    h1 = resample_ohlc(m1, "1h"); h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1); atr_h1 = wilder_atr(h1, 14)

    for prof_fn in (profile_D, profile_R):
        prof = prof_fn()
        t0 = time.time()
        print(f"\n--- C5 record-only ADX run · Profile {prof.name} ---", flush=True)
        entries = run_profile(prof, h1, h4, d1, m1, atr_h1, BT_START, end_eff)
        print(f"    → {len(entries)} entries in {time.time()-t0:.0f}s", flush=True)
        p = OUT / f"trades_variants_C5adx_{prof.name}.jsonl"
        with open(p, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        print(f"    wrote {p.name}", flush=True)


if __name__ == "__main__":
    main()
