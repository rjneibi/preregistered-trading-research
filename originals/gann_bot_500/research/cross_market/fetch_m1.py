"""Deep M1 history in yearly chunks (needs MaxBars raised).  data/{SYM}_M1.npz"""
import time, numpy as np, MetaTrader5 as mt5
from datetime import datetime, timezone
mt5.initialize(path="<mt5-terminal-path>")
for n in ["US500", "USTEC", "US30"]:
    mt5.symbol_select(n, True); i = mt5.symbol_info(n)
    parts = []
    for y in range(2026, 2009, -1):
        a, b = datetime(y, 1, 1, tzinfo=timezone.utc), datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        r = None
        for k in range(6):
            r = mt5.copy_rates_range(n, mt5.TIMEFRAME_M1, a, b)
            if r is not None and len(r): break
            time.sleep(5)
        if r is None or not len(r):
            print(n, y, "none", mt5.last_error(), flush=True)
            if parts: break
            continue
        parts.append(r); print(n, y, len(r), flush=True)
    r = np.sort(np.concatenate(parts), order="time")
    np.savez(f"data/{n}_M1.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"], c=r["close"], sp=r["spread"] * i.point)
    print("SAVED", n, len(r), time.strftime('%Y-%m-%d', time.gmtime(r[0]['time'])), flush=True)
mt5.shutdown()
