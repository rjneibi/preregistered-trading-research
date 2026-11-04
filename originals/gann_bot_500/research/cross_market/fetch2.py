import time, numpy as np, MetaTrader5 as mt5
mt5.initialize(path="<mt5-terminal-path>")
for n in ["SPY", "DIA", "IWM", "QQQ", "MDY", "EWA", "EWO"]:
    if not mt5.symbol_select(n, True): print(n, "no symbol"); continue
    r = None
    for k in range(8):
        r = mt5.copy_rates_from_pos(n, mt5.TIMEFRAME_D1, 0, 20000)
        if r is not None and len(r) > 300: break
        time.sleep(4)
    if r is None or not len(r): print(n, "none", mt5.last_error()); continue
    i = mt5.symbol_info(n)
    np.savez(f"data/{n}_D1.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"], c=r["close"],
             sp=r["spread"] * i.point, swl=i.swap_long, sws=i.swap_short, swm=i.swap_mode, cs=i.trade_contract_size)
    print(n, len(r), time.strftime('%Y-%m-%d', time.gmtime(r[0]['time'])), "->", time.strftime('%Y-%m-%d', time.gmtime(r[-1]['time'])), flush=True)
mt5.shutdown()
