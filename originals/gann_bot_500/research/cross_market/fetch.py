"""Pull D1 + H1 history from the PC broker demo feed terminal into data/{SYM}_{TF}.npz (server time)."""
import sys, time
import numpy as np
import MetaTrader5 as mt5
mt5.initialize(path="<mt5-terminal-path>")
S = ["USTEC", "US500", "US30", "USDX", "XAUUSD", "XAGUSD", "TLT", "EURUSD", "USDJPY"]
for n in S:
    mt5.symbol_select(n, True)
    i = mt5.symbol_info(n)
    for tfn, tf in (("D1", mt5.TIMEFRAME_D1), ("H1", mt5.TIMEFRAME_H1)):
        r = None
        for cnt in (200000, 100000, 50000, 20000):
            r = mt5.copy_rates_from_pos(n, tf, 0, cnt)
            if r is not None and len(r): break
            time.sleep(3)
        if r is None or not len(r):
            print(n, tfn, "none", mt5.last_error(), flush=True); continue
        np.savez(f"data/{n}_{tfn}.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"],
                 c=r["close"], sp=r["spread"] * i.point, swl=i.swap_long, sws=i.swap_short, swm=i.swap_mode,
                 cs=i.trade_contract_size)
        print(f"{n:7s} {tfn} {len(r):7d} {time.strftime('%Y-%m-%d', time.gmtime(r[0]['time']))} -> "
              f"{time.strftime('%Y-%m-%d', time.gmtime(r[-1]['time']))} med spread {np.median(r['spread'])*i.point:.4f} "
              f"swap L/S {i.swap_long}/{i.swap_short} mode {i.swap_mode}", flush=True)
mt5.shutdown()
