"""EDGE-1 universe: every D1 history broker demo feed has among a broad multi-asset list."""
import time, numpy as np, MetaTrader5 as mt5, os
mt5.initialize(path="<mt5-terminal-path>")
WANT = ("EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF NZDUSD EURJPY GBPJPY AUDJPY EURGBP EURCHF USDMXN USDZAR USDTRY USDNOK USDSEK "
        "XAUUSD XAGUSD XPTUSD XPDUSD XBRUSD XTIUSD XNGUSD UKOIL USOIL BRENT WTI NATGAS "
        "US500 US30 USTEC US2000 DE40 GER40 UK100 FRA40 JP225 AUS200 HK50 STOXX50 EU50 ESP35 "
        "SPY QQQ DIA IWM MDY TLT IEF SHY LQD HYG TIP GLD SLV USO UNG DBA DBC VNQ EFA EEM FXI EWJ EWG EWU EWZ EWA EWC INDA "
        "XLE XLF XLK XLU XLV XLP XLI XLB XLY XLC SMH XBI GDX UUP FXE FXY FXA").split()
have = {s.name for s in mt5.symbols_get()}
os.makedirs("data_edge", exist_ok=True)
for n in WANT:
    if os.path.exists(f"data_edge/{n}_D1.npz"): continue
    if n not in have: continue
    mt5.symbol_select(n, True)
    r = None
    for k in range(6):
        r = mt5.copy_rates_from_pos(n, mt5.TIMEFRAME_D1, 0, 6000)
        if r is not None and len(r) > 500: break
        time.sleep(3)
    if r is None or len(r) < 500: print(n, "short/none"); continue
    i = mt5.symbol_info(n)
    np.savez(f"data_edge/{n}_D1.npz", t=r["time"].astype(np.int64), o=r["open"], h=r["high"], l=r["low"], c=r["close"],
             sp=r["spread"] * i.point, swl=i.swap_long, sws=i.swap_short, swm=i.swap_mode, cs=i.trade_contract_size)
    print(n, len(r), time.strftime('%Y-%m-%d', time.gmtime(r[0]['time'])), flush=True)
print("missing:", [w for w in WANT if w not in have])
mt5.shutdown()
