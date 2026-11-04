"""
Pure (MT5-free) Wilder ADX on the H4 frame — research-only mirror of
structure.get_adx (structure.py:171-240), which fetches its own H4 rates from
MT5 and therefore can't run in the backtest.

Semantics mirrored 1:1:
  * period=14, H4 bars, last `period*3` bars
  * Wilder RMA smoothing (seed = simple mean of first `period`, then
    rma = (prev*(period-1) + x) / period)
  * +DM/-DM standard rules; DX = 100*|+DI - -DI| / (+DI + -DI); ADX = RMA(DX)
  * returns the most recent ADX value, or None on insufficient data

DRIFT RISK: if structure.get_adx changes, re-verify this mirror.
"""
from __future__ import annotations
from typing import Optional


def _wilder_rma(values: list, period: int) -> list:
    if len(values) < period:
        return []
    rma = [sum(values[:period]) / period]
    for v in values[period:]:
        rma.append((rma[-1] * (period - 1) + v) / period)
    return rma


def adx_from_bars(bars_h4: list[dict], period: int = 14) -> Optional[float]:
    """bars_h4: list of {'high','low','close'} dicts, oldest first (completed
    bars only — caller guarantees look-ahead safety). Uses the last period*3
    bars to match live's fetch window."""
    rates = bars_h4[-(period * 3):]
    if len(rates) < period * 2 + 1:
        return None
    highs  = [float(r["high"]) for r in rates]
    lows   = [float(r["low"]) for r in rates]
    closes = [float(r["close"]) for r in rates]

    trs, plus_dms, minus_dms = [], [], []
    for i in range(1, len(rates)):
        high, low = highs[i], lows[i]
        prev_high, prev_low, prev_close = highs[i-1], lows[i-1], closes[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm = down_move if (down_move > up_move and down_move > 0) else 0.0
        trs.append(tr); plus_dms.append(plus_dm); minus_dms.append(minus_dm)

    sm_tr = _wilder_rma(trs, period)
    sm_plus = _wilder_rma(plus_dms, period)
    sm_minus = _wilder_rma(minus_dms, period)
    if not sm_tr:
        return None
    dx_list = []
    for tr_v, plus_v, minus_v in zip(sm_tr, sm_plus, sm_minus):
        if tr_v == 0:
            dx_list.append(0.0); continue
        plus_di = 100.0 * plus_v / tr_v
        minus_di = 100.0 * minus_v / tr_v
        di_sum = plus_di + minus_di
        dx = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum else 0.0
        dx_list.append(dx)
    adx_series = _wilder_rma(dx_list, period)
    if not adx_series:
        return None
    return float(round(adx_series[-1], 2))
