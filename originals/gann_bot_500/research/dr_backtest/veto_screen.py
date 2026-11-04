"""
Veto screen against the backtest trade population.

Reuses research/market_context/ (LiquidityLevel + MarketContext + veto rule).
For each backtest trade, at its entry ts and price, build MarketContext from
completed M1 bars/sessions and apply the veto for K in {0.5, 1.0, 1.5, 2.0}.
Report per profile.

Same-K sample-size labelling: n<15 -> NO CONCLUSION, n<100 -> directional only.
"""
from __future__ import annotations
from pathlib import Path
import sys

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.market_context.context import MarketContext, veto  # noqa: E402


K_GRID = [0.5, 1.0, 1.5, 2.0]


def compute_veto_per_trade(trades: list[dict], m1: pd.DataFrame) -> list[dict]:
    """Attach opposing-level info to each trade. Uses each trade's own recorded
    entry_ts / direction / entry_price / atr."""
    ctx = MarketContext(m1)
    out = []
    for tr in trades:
        rec = dict(tr)
        if tr.get("outcome_status") not in ("TP", "SL", "PARTIAL_THEN_TP",
                                            "PARTIAL_THEN_BE"):
            rec["distance_atr"] = None
            rec["opposing"] = None
            out.append(rec)
            continue
        ts = pd.Timestamp(tr["entry_ts"])
        ctx.refresh(ts)
        lv, dist = ctx.nearest_opposing_unswept(tr["direction"], tr["entry_price"])
        atr = tr["atr"]
        dist_atr = None if (lv is None or atr <= 0 or dist is None) else dist / atr
        rec["opposing"] = None if lv is None else {
            "source": lv.source, "side": lv.side, "price": lv.price,
            "formed_at": lv.formed_at.isoformat(), "swept": lv.swept,
        }
        rec["distance_price"] = None if dist is None else round(dist, 3)
        rec["distance_atr"] = None if dist_atr is None else round(dist_atr, 3)
        out.append(rec)
    return out
