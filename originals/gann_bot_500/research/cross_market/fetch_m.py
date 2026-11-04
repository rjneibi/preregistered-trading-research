import time, numpy as np, MetaTrader5 as mt5
mt5.initialize(path="<mt5-terminal-path>")
for n in ["US500", "USTEC", "US30", "XAUUSD"]:
    mt5.symbol_select(n, True); i = mt5.symbol_info(n)
    for tfn, tf in (("M5", mt5.TIMEFRAME_M5), ("M1", mt5.TIMEFRAME_M1)):
        r = None
        for cnt in (1000000, 500000, 200000, 99999):
            for k in range(3):
                r = mt5.copy_rates_from_pos(n, tf, 0, cnt)
                if r is not None and len(r): break
                time.sleep(4)
            if r is not None and len(r): break
        if r is None or not len(r): print(n, tfn, "none", mt5.last_error(), flush=True); continue
        np.savez(f"data/{n}_{tfn}.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"], c=r["close"], sp=r["spread"] * i.point)
        print(n, tfn, len(r), time.strftime('%Y-%m-%d', time.gmtime(r[0]['time'])), "->", time.strftime('%Y-%m-%d', time.gmtime(r[-1]['time'])), flush=True)
mt5.shutdown()
