"""Triple-barrier engine — label generator AND exit engine, single source of
truth. Merges the labelsizing_core labeler contract with the validated Sim5
exit stack (fable-backtesting/bail_exit_v5.py:77-119).

Semantics (parity-verified against Sim5):
  * entry = OPEN of the first M1 bar at/after the signal timestamp
    (next-bar-open; the signal timestamp is a bar CLOSE, so no lookahead);
  * per bar, SL is checked BEFORE TP: a bar touching both barriers resolves
    conservatively as a stop and is counted (`ambiguous`);
  * fill modes:
      barrier_level — fills exactly at the barrier price (Sim5 parity mode);
      gap_open      — if the bar OPENS through a barrier, fill at the open
                      (honest gap handling; worse on SL gaps, better on TP
                      gaps, both are what a live order would get);
  * regime bail overlay (validated v5.1 stack), evaluated on M1 CLOSES after
    the barrier checks of the same bar, exactly Sim5's order:
      hivol -> close HALF at the first close <= -hivol_half_x*ATR adverse;
      lovol -> close ALL at a close <= -lovol_bail_x*ATR adverse once age
               >= lovol_bail_h hours;
  * vertical barrier: mark-to-market at the close of the last bar before
    entry_bar_time + time_stop_h.

Returns GROSS P&L per 1.0 lot ($1 price move = $100/lot). Sim5 baked a flat
20pt cost into every trade; goldbot instead nets costs downstream
(goldbot.backtest.net_trades) so one trade set prices under every regime.

With bail disabled this is a pure triple-barrier labeler (TP/SL/TIMEOUT).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

USD_PER_PRICE_PER_LOT = 100.0


def run_exits(m1: pd.DataFrame, events: pd.DataFrame, *,
              k_tp_atr: float | None = None, k_sl_atr: float | None = None,
              tp_usd: float | None = None, sl_usd: float | None = None,
              time_stop_h: int = 24, fill_mode: str = "gap_open",
              bail_enabled: bool = False, hivol_half_x: float = 1.2,
              lovol_bail_h: int = 8, lovol_bail_x: float = 1.0) -> pd.DataFrame:
    """Run every event through the exit stack. ATR-multiple barriers when
    k_tp_atr/k_sl_atr given, else fixed-dollar tp_usd/sl_usd."""
    assert fill_mode in ("gap_open", "barrier_level"), fill_mode
    # Each barrier is resolved INDEPENDENTLY: give exactly one of the ATR
    # multiple or the fixed dollar distance, per barrier. Passing both ATR
    # (the `final` variant) or both USD (the `base` variant) behaves exactly as
    # before, so every prior result still reproduces bit-for-bit. Mixing them
    # is what a fixed-lot account forces: the STOP is pinned in dollars by
    # volume_min while the target stays volatility-scaled.
    assert (k_tp_atr is None) != (tp_usd is None), \
        "give exactly one of k_tp_atr / tp_usd"
    assert (k_sl_atr is None) != (sl_usd is None), \
        "give exactly one of k_sl_atr / sl_usd"

    t = m1.index.values
    o = m1["open"].to_numpy(float)
    h = m1["high"].to_numpy(float)
    l = m1["low"].to_numpy(float)
    c = m1["close"].to_numpy(float)
    one_min = np.timedelta64(1, "m")
    horizon = np.timedelta64(time_stop_h, "h")
    bail_dt = np.timedelta64(lovol_bail_h, "h")

    out = []
    for ev in events.itertuples(index=False):
        side = int(ev.side)
        atr = float(ev.atr)
        ev_ts = pd.Timestamp(ev.event_ts)
        if ev_ts.tzinfo is not None:            # t is naive-UTC datetime64
            ev_ts = ev_ts.tz_convert("UTC").tz_localize(None)
        i0 = t.searchsorted(ev_ts.to_datetime64())
        if i0 >= len(t):
            continue                                    # Sim5: event skipped
        entry = o[i0]
        tp_d = k_tp_atr * atr if k_tp_atr is not None else tp_usd
        sl_d = k_sl_atr * atr if k_sl_atr is not None else sl_usd
        tp = entry + side * tp_d
        sl = entry - side * sl_d

        i_end = min(t.searchsorted(t[i0] + horizon), len(t))
        i_end = max(i_end, i0 + 1)

        use_half = bail_enabled and bool(ev.hivol)
        use_bail = bail_enabled and not bool(ev.hivol)
        half_px = entry - side * hivol_half_x * atr
        bail_px = entry - side * lovol_bail_x * atr
        i_bail = t.searchsorted(t[i0] + bail_dt) if use_bail else None

        bank = 0.0            # realized from the half-close, in price units
        frac = 1.0
        halved = False
        ambiguous = False
        mae = 0.0             # most adverse excursion, price units (<= 0)
        resolution, exit_px, exit_i = None, None, None

        for i in range(i0, i_end):
            hi, lo, cl = h[i], l[i], c[i]
            mae = min(mae, side * ((lo if side > 0 else hi) - entry))
            hit_sl = (lo <= sl) if side > 0 else (hi >= sl)
            hit_tp = (hi >= tp) if side > 0 else (lo <= tp)
            if hit_sl:                                  # SL first: conservative
                ambiguous = hit_tp
                exit_px = sl
                if fill_mode == "gap_open" and \
                        ((o[i] <= sl) if side > 0 else (o[i] >= sl)):
                    exit_px = o[i]
                resolution, exit_i = "SL", i
                break
            if hit_tp:
                exit_px = tp
                if fill_mode == "gap_open" and \
                        ((o[i] >= tp) if side > 0 else (o[i] <= tp)):
                    exit_px = o[i]
                resolution, exit_i = "TP", i
                break
            if use_half and not halved and \
                    ((cl <= half_px) if side > 0 else (cl >= half_px)):
                bank += 0.5 * side * (cl - entry)
                frac = 0.5
                halved = True
            if use_bail and i >= i_bail and \
                    ((cl <= bail_px) if side > 0 else (cl >= bail_px)):
                resolution, exit_px, exit_i = "BAIL", cl, i
                break

        if resolution is None:
            resolution, exit_px, exit_i = "TIMEOUT", c[i_end - 1], i_end - 1

        gross = (bank + frac * side * (exit_px - entry)) * USD_PER_PRICE_PER_LOT
        signal_hr = int(pd.Timestamp(ev.event_ts).value // 3_600_000_000_000)
        out.append({
            "event_ts": pd.Timestamp(ev.event_ts), "side": side,
            "entry_ts": pd.Timestamp(t[i0], tz="UTC"), "entry_px": float(entry),
            "exit_ts": pd.Timestamp(t[exit_i] + one_min, tz="UTC"),
            "exit_px": float(exit_px), "resolution": resolution,
            "derisked": halved, "ambiguous": ambiguous,
            "mae_usd": float(mae * USD_PER_PRICE_PER_LOT),
            "gross_usd": float(gross),
            "atr": atr, "hivol": bool(ev.hivol),
            "signal_hr": signal_hr,
            "label_horizon_end_hr": signal_hr + time_stop_h,
        })
    return pd.DataFrame(out)


def label_signals(trades: pd.DataFrame) -> pd.DataFrame:
    """Labeler-contract view of a run_exits result (labelsizing_core style):
    one row per signal with ternary resolution and the purge horizon key."""
    return pd.DataFrame({
        "signal_idx": trades["signal_hr"],
        "side": trades["side"],
        "resolution_type": trades["resolution"],
        "realized_usd": trades["gross_usd"],
        "label_horizon_end": trades["label_horizon_end_hr"],
    })
