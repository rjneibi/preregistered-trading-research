"""Per-symbol spread + ATR statistics over the 7y backtest window (read-only).

The MT5 rates 'spread' field is the average spread (in points) recorded for that
bar. We summarise it (median / mean / p90) per symbol on H1 and H4, plus typical
ATR, so the backtest spread-cost and the proposed per-symbol MAX_SPREAD threshold
are data-driven rather than gold-inherited.
"""
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime, timedelta

mt5.initialize(path="<mt5-terminal-path>")
now = datetime.now()
start = now - timedelta(days=int(7 * 365.25))
for name in ["EURUSD", "GBPUSD", "AUDUSD"]:
    mt5.symbol_select(name, True)
    info = mt5.symbol_info(name)
    print("=====", name, "point=", info.point)
    for tfn, tf in (("H1", mt5.TIMEFRAME_H1), ("H4", mt5.TIMEFRAME_H4)):
        r = mt5.copy_rates_range(name, tf, start, now)
        if r is None or len(r) == 0:
            print(f"  {tfn}: no data"); continue
        sp = np.array([x["spread"] for x in r], dtype=float)
        sp = sp[sp > 0]
        # ATR(14) rough: mean of (high-low) in points
        rng_pts = (np.array([x["high"] for x in r]) -
                   np.array([x["low"] for x in r])) / info.point
        print(f"  {tfn}: bars={len(r)} spread(pts) median={np.median(sp):.0f} "
              f"mean={np.mean(sp):.1f} p90={np.percentile(sp,90):.0f} "
              f"max={np.max(sp):.0f} | bar_range(pts) median={np.median(rng_pts):.0f}")
mt5.shutdown()
