"""
Exit simulation for the two live exit models.

D — Core+Polarity, PARTIAL_CLOSE_ENABLED, TP_FIXED_POINTS=900 (fixed +$9 above
entry / below entry). Full lot enters. When price hits entry ± 1.0×ATR (the
partial trigger, in DIRECTION OF THE TRADE), half the position closes and the
stop moves to entry (BE). The remaining 50% then continues to fixed-TP or the
BE stop, whichever comes first. Points P&L is a 50/50 blend of the two legs.

R — Pure Core, PARTIAL_CLOSE_ENABLED, TP_FIXED_POINTS=1000, SL=1.5×ATR.
CONFIG says PARTIAL_CLOSE_ENABLED is TRUE for R too — same partial-to-BE model.
(Contradicts the task's "R has no partials" assumption; config wins.)

Points convention: XAUUSD 1 dollar = 100 pts. Positive pts = winner.

Same-M1-bar SL+TP collisions are flagged AMBIGUOUS_SAME_BAR and resolved
CONSERVATIVELY (assume SL first). Counts of these are reported.
"""
from __future__ import annotations

from typing import Optional
import pandas as pd

POINT_PER_DOLLAR = 100.0


def _dir_sign(direction: str) -> int:
    return 1 if direction == "BUY" else -1


def simulate_trade(direction: str, entry_price: float, entry_ts: pd.Timestamp,
                   atr_at_entry: float, m1_df: pd.DataFrame, *,
                   tp_fixed_points: float,
                   sl_atr_mult: float,
                   partial_enabled: bool,
                   partial_atr_mult: float = 1.0,
                   max_hours: int = 24 * 30) -> dict:
    """Bar-by-bar M1 simulation.

    Returns dict with:
      status ∈ {'TP','SL','PARTIAL_THEN_TP','PARTIAL_THEN_BE','OPEN_AT_HORIZON',
                'AMBIGUOUS_SAME_BAR','OUT_OF_HISTDATA'}
      pnl_points   — blended points P&L (float) or None
      exit_ts_final — timestamp of the final leg exit
      partial_hit  — bool (did the partial trigger fire?)
      partial_ts, bar-count fields for auditability
    """
    sign = _dir_sign(direction)
    sl_price = entry_price - sign * (sl_atr_mult * atr_at_entry)
    tp_price = entry_price + sign * (tp_fixed_points / POINT_PER_DOLLAR)
    partial_price = entry_price + sign * (partial_atr_mult * atr_at_entry)

    fwd = m1_df[m1_df.index > entry_ts]
    if fwd.empty:
        return {"status": "OUT_OF_HISTDATA", "pnl_points": None,
                "exit_ts_final": None, "partial_hit": False,
                "sl_price": sl_price, "tp_price": tp_price,
                "partial_price": partial_price}
    horizon_end = entry_ts + pd.Timedelta(hours=max_hours)
    fwd = fwd[fwd.index <= horizon_end]

    partial_hit = False
    partial_ts = None
    stop = sl_price  # will move to entry (BE) once partial fires

    for ts, row in fwd.iterrows():
        hi = float(row["high"]); lo = float(row["low"])

        hit_tp = (hi >= tp_price) if sign > 0 else (lo <= tp_price)
        hit_sl = (lo <= stop) if sign > 0 else (hi >= stop)
        hit_partial = ((hi >= partial_price) if sign > 0
                       else (lo <= partial_price)) and partial_enabled and not partial_hit

        # Same-bar SL+TP → ambiguous. Resolve conservatively as SL.
        if hit_tp and hit_sl:
            leg1_pts = sign * (stop - entry_price) * POINT_PER_DOLLAR
            pnl = leg1_pts * (0.5 if partial_hit else 1.0)
            if partial_hit:
                partial_leg_pts = sign * (partial_price - entry_price) * POINT_PER_DOLLAR
                pnl += 0.5 * partial_leg_pts
            return {"status": "AMBIGUOUS_SAME_BAR", "pnl_points": round(pnl, 1),
                    "exit_ts_final": ts.isoformat(),
                    "partial_hit": partial_hit,
                    "partial_ts": partial_ts.isoformat() if partial_ts else None,
                    "sl_price": sl_price, "tp_price": tp_price,
                    "partial_price": partial_price}

        if hit_partial and not hit_tp and not hit_sl:
            partial_hit = True
            partial_ts = ts
            stop = entry_price  # move remaining leg's stop to BE
            continue

        if hit_tp:
            leg_final_pts = sign * (tp_price - entry_price) * POINT_PER_DOLLAR
            if partial_hit:
                partial_leg_pts = sign * (partial_price - entry_price) * POINT_PER_DOLLAR
                pnl = 0.5 * partial_leg_pts + 0.5 * leg_final_pts
                status = "PARTIAL_THEN_TP"
            else:
                pnl = leg_final_pts
                status = "TP"
            return {"status": status, "pnl_points": round(pnl, 1),
                    "exit_ts_final": ts.isoformat(),
                    "partial_hit": partial_hit,
                    "partial_ts": partial_ts.isoformat() if partial_ts else None,
                    "sl_price": sl_price, "tp_price": tp_price,
                    "partial_price": partial_price}

        if hit_sl:
            leg_final_pts = sign * (stop - entry_price) * POINT_PER_DOLLAR
            if partial_hit:
                partial_leg_pts = sign * (partial_price - entry_price) * POINT_PER_DOLLAR
                pnl = 0.5 * partial_leg_pts + 0.5 * leg_final_pts
                status = "PARTIAL_THEN_BE"
            else:
                pnl = leg_final_pts
                status = "SL"
            return {"status": status, "pnl_points": round(pnl, 1),
                    "exit_ts_final": ts.isoformat(),
                    "partial_hit": partial_hit,
                    "partial_ts": partial_ts.isoformat() if partial_ts else None,
                    "sl_price": sl_price, "tp_price": tp_price,
                    "partial_price": partial_price}

    # 30 days without SL or TP is extremely unusual — flag OPEN.
    return {"status": "OPEN_AT_HORIZON", "pnl_points": None,
            "exit_ts_final": None,
            "partial_hit": partial_hit,
            "partial_ts": partial_ts.isoformat() if partial_ts else None,
            "sl_price": sl_price, "tp_price": tp_price,
            "partial_price": partial_price}
