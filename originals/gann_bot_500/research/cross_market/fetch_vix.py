import time, numpy as np, MetaTrader5 as mt5
mt5.initialize(path="<mt5-terminal-path>")
print("init ok", flush=True)
c = ["VIXY", "VIXM"]
print("candidates:", c, flush=True)
for n in c:
    mt5.symbol_select(n, True)
    r = None
    for k in range(6):
        r = mt5.copy_rates_from_pos(n, mt5.TIMEFRAME_D1, 0, 20000)
        if r is not None and len(r) > 50: break
        time.sleep(3)
    if r is None or not len(r): print(n, "none"); continue
    np.savez(f"data/{n}_D1.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"], c=r["close"], sp=r["spread"] * mt5.symbol_info(n).point)
    print(n, mt5.symbol_info(n).description, len(r), time.strftime('%Y-%m-%d', time.gmtime(r[0]['time'])), "->", time.strftime('%Y-%m-%d', time.gmtime(r[-1]['time'])), "last", r[-1]["close"], flush=True)
mt5.shutdown()
