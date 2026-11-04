import MetaTrader5 as mt5
from datetime import datetime, timedelta

mt5.initialize(path="<mt5-terminal-path>")
now = datetime.now()
for name in ["EURUSD", "GBPUSD", "AUDUSD"]:
    mt5.symbol_select(name, True)
    print("=====", name, flush=True)
    for tfn, tf, cnt in (("D1", mt5.TIMEFRAME_D1, 3000),
                         ("H4", mt5.TIMEFRAME_H4, 40000),
                         ("H1", mt5.TIMEFRAME_H1, 90000)):
        r = mt5.copy_rates_from_pos(name, tf, 0, cnt)
        if r is None or len(r) == 0:
            print(f"  {tfn} from_pos: none {mt5.last_error()}")
        else:
            t0 = datetime.utcfromtimestamp(int(r[0]['time']))
            t1 = datetime.utcfromtimestamp(int(r[-1]['time']))
            print(f"  {tfn} from_pos: {len(r)} {t0.date()}->{t1.date()} "
                  f"{(t1-t0).days/365.25:.2f}y")
mt5.shutdown()
