"""
fx_common.py — shared symbol config, data fetch, and cost model for the FX
transfer-test backtests (EURUSD / GBPUSD / AUDUSD).

This module is research-only. It is never imported by the live bot and changes
nothing about Profiles D/R/S as they run. It centralises:

  * the verified broker symbol names + sizing fields (read live from MT5),
  * a DATA-DRIVEN per-symbol spread cost (from 7y of recorded bar spreads),
  * the realistic cost model (spread + commission) shared by all 9 runs,
  * the 7-year fetch window and the 70/30 chronological IS/OOS split.

Symbol-aware sizing note (Step 2): all three majors verified identical on this
feed — digits=5, point=1e-5, trade_tick_value=$1.0, trade_tick_size=1e-5,
contract_size=100000 → point value V = tick_value*(point/tick_size) = $1.0 per
point per lot, i.e. $100000 P&L per 1.0 lot per 1.0 price move. risk.py's
calculate_lot_size already reads all of these from symbol_info(), so it is fully
symbol-agnostic and needs no change (confirmed by audit).
"""
import os
import sys
from datetime import datetime, timedelta

import numpy as np
import MetaTrader5 as mt5

TERMINAL_PATH = "<mt5-terminal-path>"
YEARS_BACK = 7
IN_SAMPLE_PCT = 0.70

# Verified bare names on broker demo feed (no broker suffix — probed 2026-06-14).
SYMBOLS = ["EURUSD", "GBPUSD", "AUDUSD"]

# ── Per-symbol cost & filter config (Step 2) ──────────────────────────────────
# spread_pts : round-trip spread COST charged once per trade, in points (1e-5).
#   Set to ~2x the 7y recorded mean H1 spread (EUR 3.4 / GBP 5.9 / AUD 5.5 pts),
#   a conservative retail markup over this tight institutional demo feed.
# max_spread_pts : PROPOSED live spread filter replacing gold's MAX_SPREAD_POINTS
#   =40 (which on FX is ~10x typical spread = effectively disabled). Set to roughly
#   the 7y H1 p90 + buffer so it blocks only genuine news-spike spreads. Report-only
#   here — no live config.py change is made (task guardrail).
SYMCFG = {
    "EURUSD": {"point": 1e-5, "V": 1.0, "spread_pts": 8,  "max_spread_pts": 15,
               "pip": 1e-4},
    "GBPUSD": {"point": 1e-5, "V": 1.0, "spread_pts": 12, "max_spread_pts": 30,
               "pip": 1e-4},
    "AUDUSD": {"point": 1e-5, "V": 1.0, "spread_pts": 11, "max_spread_pts": 25,
               "pip": 1e-4},
}

# Commission: $7 / lot round trip (matches the gold validation cost model). With
# V=$1/pt/lot this is 7 points of price, charged once per trade.
COMMISSION_USD = 7.0

# $ P&L per 1.0 lot per 1.0 unit of price move (= contract_size for xxxUSD majors).
USD_PER_LOT_PER_PRICE = 100000.0

# ── D/R price scaling (engine-rounding adapter) ───────────────────────────────
# research/backtest.py reuses the LIVE levels.py, whose pivot/fib/gann/zone math
# rounds to 2 decimals — gold's $0.01 tick. On native FX prices (~1.16, 5dp) that
# rounding collapses every level and forces ATR to 0, so nothing evaluates. We
# multiply all D/R OHLC by DR_SCALE so 1 FX point (1e-5) maps onto one engine
# "cent" (0.01) — exactly how the engine treats a gold point — keeping every
# production formula byte-identical at full precision. All reported metrics
# (R-multiple, win%, PF, expectancy in R, MaxDD%) are scale-invariant.
#   point_scaled = 1e-5 * DR_SCALE = 0.1 ; spread/commission are charged in points
#   so they scale consistently. Profile S needs no scaling (its engine uses raw
#   numpy floats with no 2dp rounding).
# Caveat: the Gann Square-of-9 is price-magnitude-sensitive; zone-source
# composition is reported so its contribution per pair is transparent.
DR_SCALE = 10000.0


def scale_bars(bars, scale=DR_SCALE):
    """Return a copy of bars with OHLC multiplied by `scale` (spread/time kept)."""
    out = []
    for b in bars:
        nb = dict(b)
        for k in ("open", "high", "low", "close"):
            nb[k] = b[k] * scale
        out.append(nb)
    return out

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def connect():
    if not mt5.initialize(path=TERMINAL_PATH):
        print("ERROR: mt5.initialize failed:", mt5.last_error())
        sys.exit(1)
    return True


def window():
    """Return (start_dt, end_dt) for the 7-year fetch window."""
    end = datetime.now()
    start = end - timedelta(days=int(YEARS_BACK * 365.25))
    return start, end


def fetch_rates(symbol, timeframe, start, end):
    """copy_rates_range -> structured array (oldest first). Exits on hard failure."""
    mt5.symbol_select(symbol, True)
    r = mt5.copy_rates_range(symbol, timeframe, start, end)
    if r is None or len(r) == 0:
        print(f"ERROR: no {timeframe} data for {symbol}: {mt5.last_error()}")
        sys.exit(1)
    return r


def rates_to_bars(rates):
    """MT5 structured array -> list of OHLC dicts (the shape research/backtest.py
    and backtest_s.py both consume)."""
    out = []
    for r in rates:
        out.append({"time": int(r["time"]), "open": float(r["open"]),
                    "high": float(r["high"]), "low": float(r["low"]),
                    "close": float(r["close"]), "volume": float(r["tick_volume"]),
                    "spread": int(r["spread"])})
    return out


def split_date(bars):
    """70/30 chronological split: the UTC date at IN_SAMPLE_PCT of the time span."""
    t0 = datetime.utcfromtimestamp(bars[0]["time"])
    t1 = datetime.utcfromtimestamp(bars[-1]["time"])
    span = (t1 - t0).total_seconds()
    return t0 + timedelta(seconds=span * IN_SAMPLE_PCT)


def coverage(bars):
    t0 = datetime.utcfromtimestamp(bars[0]["time"])
    t1 = datetime.utcfromtimestamp(bars[-1]["time"])
    return t0, t1, (t1 - t0).days / 365.25


def max_drawdown_pct(r_series, risk_frac=0.01, start_equity=10000.0):
    """Fixed-fractional (1% risk/trade, compounding) equity curve over a
    chronological realized-R series -> max drawdown %. Same basis the gold D/R
    and Profile S reports use, so MaxDD% is comparable across all profiles."""
    eq = peak = start_equity
    maxdd = 0.0
    for r in r_series:
        eq += r * (risk_frac * eq)
        peak = max(peak, eq)
        if peak > 0:
            maxdd = max(maxdd, (peak - eq) / peak * 100.0)
    return maxdd
