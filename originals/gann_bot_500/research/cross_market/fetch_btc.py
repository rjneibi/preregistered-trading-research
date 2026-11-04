import time, numpy as np, MetaTrader5 as mt5
mt5.initialize(path="<mt5-terminal-path>")
names = [s.name for s in mt5.symbols_get(group="*BTC*,*ETH*,*Crypto*")]
print("crypto-ish symbols:", names[:40], flush=True)
for n in ["BTCUSD", "ETHUSD"]:
    if not mt5.symbol_select(n, True): print(n, "not on server", flush=True); continue
    i = mt5.symbol_info(n)
    for tfn, tf in (("D1", mt5.TIMEFRAME_D1), ("H1", mt5.TIMEFRAME_H1), ("M1", mt5.TIMEFRAME_M1)):
        r = None
        for k in range(6):
            r = mt5.copy_rates_from_pos(n, tf, 0, 3000000 if tfn == "M1" else 200000)
            if r is not None and len(r) > 50: break
            time.sleep(4)
        if r is None or not len(r): print(n, tfn, "none", mt5.last_error(), flush=True); continue
        np.savez(f"data/{n}_{tfn}.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"], c=r["close"], sp=r["spread"] * i.point)
        print(n, tfn, len(r), time.strftime('%Y-%m-%d', time.gmtime(r[0]['time'])), "->", time.strftime('%Y-%m-%d', time.gmtime(r[-1]['time'])),
              f"med spread {np.median(r['spread'])*i.point:.2f} swap L/S {i.swap_long}/{i.swap_short} mode {i.swap_mode} trade_mode {i.trade_mode}", flush=True)
mt5.shutdown()
