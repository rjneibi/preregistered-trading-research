"""
structure.py — Market structure analysis for gann_bot.

Provides:
  * find_swing()        — detect H4 swing high/low and trend direction
  * h1_close_confirmed() — body-close confirmation of a level break on H1
  * get_h4_bias()       — EMA50-based H4 trend bias (bullish/bearish)

Bars are dicts with keys: time, open, high, low, close, volume (most recent
last), as produced by broker.get_ohlc().
"""

import MetaTrader5 as mt5

import config
from logsetup import get_logger

log = get_logger("structure")


# ── 3A. H4 Swing Detection ────────────────────────────────
def find_swing(bars_h4: list) -> tuple:
    """
    Detect the swing high, swing low, and trend direction from H4 bars.

    Params:
        bars_h4 (list): H4 OHLC bar dicts, most recent last.

    Returns:
        tuple: (swing_high (float), swing_low (float), direction (str))
               direction is "up" if the last close is above the midpoint of the
               swing range, else "down".
    """
    if not bars_h4:
        log.warning("find_swing called with empty H4 bars")
        return (0.0, 0.0, "down")

    lookback = config.SWING_LOOKBACK_H4
    window = bars_h4[-lookback:] if len(bars_h4) > lookback else bars_h4

    swing_high = max(b["high"] for b in window)
    swing_low = min(b["low"] for b in window)
    mid = (swing_high + swing_low) / 2.0
    direction = "up" if window[-1]["close"] > mid else "down"

    log.info(
        "Swing(H4): high=%.2f low=%.2f mid=%.2f dir=%s (lookback=%d)",
        swing_high, swing_low, mid, direction, len(window),
    )
    return (swing_high, swing_low, direction)


# ── 3B. H1 Close Confirmation ─────────────────────────────
def h1_close_confirmed(bars_h1: list, level: float, direction: str) -> bool:
    """
    Confirm a level break using the body of the last CLOSED H1 candle.

    Uses index -2 (the last fully closed bar; -1 is still forming). Wicks do not
    count — only the body (open/close) must straddle the level.

    Params:
        bars_h1 (list): H1 OHLC bar dicts, most recent last (>= 2 bars).
        level (float): the price level being tested.
        direction (str): "above" (bullish break up) or "below" (bearish break down).

    Returns:
        bool: True if the last closed H1 body fully crossed the level.
    """
    if len(bars_h1) < 2:
        log.warning("h1_close_confirmed needs >=2 bars, got %d", len(bars_h1))
        return False

    bar = bars_h1[-2]  # last fully closed H1 bar
    o, c = bar["open"], bar["close"]

    if direction == "above":
        confirmed = c > level and o < level
    elif direction == "below":
        confirmed = c < level and o > level
    else:
        log.error("h1_close_confirmed bad direction: %s", direction)
        return False

    log.info(
        "H1 confirm dir=%s level=%.2f open=%.2f close=%.2f -> %s",
        direction, level, o, c, confirmed,
    )
    return confirmed


# ── 3C. H4 Bias ───────────────────────────────────────────
def _ema(values: list, period: int) -> float:
    """
    Compute the final EMA value of a series.

    Params:
        values (list): list of floats (oldest first).
        period (int): EMA period.

    Returns:
        float: the most recent EMA value (falls back to simple mean if short).
    """
    if not values:
        return 0.0
    if len(values) < period:
        return sum(values) / len(values)

    k = 2.0 / (period + 1.0)
    ema = sum(values[:period]) / period  # seed with SMA of first `period`
    for v in values[period:]:
        ema = v * k + ema * (1.0 - k)
    return ema


# Requires ≥150 post-seed bars (200 total) for a converged EMA50. Do not reduce
# the caller's fetch window without re-validating — with only period+5 bars the
# result is effectively an SMA50, which flips later than a true EMA50.
def get_h4_bias(bars_h4: list) -> str:
    """
    Determine H4 trend bias using EMA50 of H4 closes.

    STRATEGY CHANGE 2026-06-12: callers now feed ≥200 bars so the EMA50 is
    properly converged (previously 55 bars → ~SMA50). Re-validate before
    trusting bias-gate statistics gathered before this change.

    Params:
        bars_h4 (list): H4 OHLC bar dicts, most recent last (≥200 for a
            converged EMA50).

    Returns:
        str: "bullish" if last close > EMA50, else "bearish".
    """
    if not bars_h4:
        log.warning("get_h4_bias called with empty H4 bars")
        return "bearish"

    closes = [b["close"] for b in bars_h4]
    ema50 = _ema(closes, 50)
    last_close = closes[-1]
    bias = "bullish" if last_close > ema50 else "bearish"

    log.info("H4 bias: close=%.2f ema50=%.2f -> %s", last_close, ema50, bias)
    return bias


# ── 3D. ADX Trend Strength ────────────────────────────────
def _wilder_rma(values: list, period: int) -> list:
    """
    Wilder's smoothing (running moving average) of a series.

    Seed = simple average of the first `period` values, then
    rma[i] = (rma[i-1] * (period - 1) + value) / period. This keeps the result
    on the same scale as the inputs (so +DI/-DI stay 0..100 and the final ADX is
    a conventional 0..100 reading the ADX_THRESHOLD can be compared against).

    Params:
        values (list): input series (oldest first).
        period (int): smoothing period.

    Returns:
        list: smoothed series (empty if fewer than `period` values).
    """
    if len(values) < period:
        return []
    rma = [sum(values[:period]) / period]
    for v in values[period:]:
        rma.append((rma[-1] * (period - 1) + v) / period)
    return rma


def get_adx(symbol: str, timeframe: str, period: int = 14):
    """
    Compute the H4 ADX (Average Directional Index) via the standard Wilder method.

    ADX measures trend strength independent of direction. Fetches the last
    period × 3 H4 candles directly from MT5 (same H4 timeframe used for the
    EMA50 bias) and returns the most recent ADX value.

    Params:
        symbol (str): trading symbol.
        timeframe (str): kept for signature symmetry; H4 candles are always used,
                         matching the H4 EMA50 bias calculation.
        period (int): ADX period (default 14).

    Returns:
        float or None: latest ADX value, or None if data/calculation is insufficient.
    """
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, period * 3)
        if rates is None or len(rates) < period * 2 + 1:
            log.warning("ADX calculation failed — insufficient data")
            return None

        highs = [float(r["high"]) for r in rates]
        lows = [float(r["low"]) for r in rates]
        closes = [float(r["close"]) for r in rates]

        trs, plus_dms, minus_dms = [], [], []
        for i in range(1, len(rates)):
            high, low = highs[i], lows[i]
            prev_high, prev_low, prev_close = highs[i - 1], lows[i - 1], closes[i - 1]

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))

            up_move = high - prev_high
            down_move = prev_low - low
            plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
            minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0

            trs.append(tr)
            plus_dms.append(plus_dm)
            minus_dms.append(minus_dm)

        sm_tr = _wilder_rma(trs, period)
        sm_plus = _wilder_rma(plus_dms, period)
        sm_minus = _wilder_rma(minus_dms, period)
        if not sm_tr:
            log.warning("ADX calculation failed — insufficient data")
            return None

        dx_list = []
        for tr_v, plus_v, minus_v in zip(sm_tr, sm_plus, sm_minus):
            if tr_v == 0:
                dx_list.append(0.0)
                continue
            plus_di = 100.0 * plus_v / tr_v
            minus_di = 100.0 * minus_v / tr_v
            di_sum = plus_di + minus_di
            dx = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum != 0 else 0.0
            dx_list.append(dx)

        adx_series = _wilder_rma(dx_list, period)
        if not adx_series:
            log.warning("ADX calculation failed — insufficient data")
            return None

        return float(round(adx_series[-1], 2))
    except Exception as e:  # noqa: BLE001 - never let an indicator crash the loop
        log.warning("ADX calculation failed — insufficient data (%s)", e)
        return None


# ── 3D-bis. M5 RSI overextension (Fix C) ──────────────────
def get_m5_rsi(symbol: str, period: int = 14):
    """
    Compute RSI(period) on the M5 timeframe using the standard Wilder method
    (same smoothing family as get_adx's _wilder_rma above).

    Fetches period+2 M5 candles and uses the last period+1 CLOSES (→ exactly
    `period` price changes for the Wilder seed; any extra change smooths it).
    Used by bot.py as a final overextension gate before entry: a BUY into an
    overbought M5 (RSI > OB) or a SELL into an oversold M5 (RSI < OS) is skipped.

    Params:
        symbol (str): trading symbol.
        period (int): RSI period (default 14).

    Returns:
        float or None: latest RSI value (0..100), or None on a data/calc error
                       (the caller FAILS OPEN — a None must never block a trade).
    """
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, period + 2)
        if rates is None or len(rates) < period + 1:
            log.warning("M5 RSI failed — insufficient data (%s bars)",
                        0 if rates is None else len(rates))
            return None
        closes = [float(r["close"]) for r in rates][-(period + 1):]
        gains, losses = [], []
        for i in range(1, len(closes)):
            ch = closes[i] - closes[i - 1]
            gains.append(max(ch, 0.0))
            losses.append(max(-ch, 0.0))
        # Wilder seed = simple average of the first `period` gains/losses, then
        # smooth any remaining change(s).
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        for g, l in zip(gains[period:], losses[period:]):
            avg_gain = (avg_gain * (period - 1) + g) / period
            avg_loss = (avg_loss * (period - 1) + l) / period
        if avg_loss == 0:
            # No downside over the window: fully overbought if there was upside,
            # otherwise a flat series → neutral 50 (never block on a flat tape).
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return round(rsi, 2)
    except Exception as e:  # noqa: BLE001 - never let an indicator crash the loop
        log.warning("M5 RSI calculation failed (%s)", e)
        return None


# ── 3E. Zone Polarity Flip ────────────────────────────────
def check_zone_polarity(zone: dict, symbol: str) -> str:
    """
    Re-evaluate a zone's polarity for the current session from recent H4 closes.

    A support level that price has already CLOSED below on H4 has flipped to
    resistance; a resistance level price has CLOSED above has flipped to support.
    Inspects the last 10 CLOSED H4 candles (positions 1..10, excluding the
    forming candle at 0). The underlying zone dict is never modified.

    Params:
        zone (dict): zone with at least "level" and a side ("side" or "kind").
        symbol (str): trading symbol.

    Returns:
        str: the current polarity ("support" or "resistance"); the original side
             is returned unchanged on insufficient data or a non-directional side.
    """
    side = zone.get("side", zone.get("kind"))
    level = zone["level"]
    try:
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 1, 10)
        if rates is None or len(rates) == 0:
            log.warning("Polarity check failed for %s — using original side",
                        zone.get("source"))
            return side

        closes = [float(r["close"]) for r in rates]

        if side == "support":
            return "resistance" if any(c < level for c in closes) else "support"
        if side == "resistance":
            return "support" if any(c > level for c in closes) else "resistance"
        return side
    except Exception as e:  # noqa: BLE001 - never let the check crash the loop
        log.warning("Polarity check failed for %s — using original side (%s)",
                    zone.get("source"), e)
        return side
