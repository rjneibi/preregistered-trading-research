"""
probe_symbols.py — read-only MT5 reconnaissance for the FX backtest task.

Connects to the Account-A terminal (read-only), resolves the real broker symbol
names for the EUR/GBP/AUD-vs-USD majors (suffixes like .a / m are common),
prints the full sizing-relevant symbol_info per candidate, and measures how much
D1/H4/H1 history is actually available per symbol. Nothing is traded.
"""
import sys
from datetime import datetime, timedelta

import MetaTrader5 as mt5

TERMINAL_PATH = "<mt5-terminal-path>"
WANT = ["EURUSD", "GBPUSD", "AUDUSD"]


def main():
    if not mt5.initialize(path=TERMINAL_PATH):
        print("ERROR initialize:", mt5.last_error())
        sys.exit(1)
    ai = mt5.account_info()
    print(f"Connected. login={getattr(ai,'login','?')} server={getattr(ai,'server','?')} "
          f"balance={getattr(ai,'balance','?')} currency={getattr(ai,'currency','?')}")

    allsyms = mt5.symbols_get()
    print(f"Total symbols on server: {len(allsyms)}")

    # Find every symbol whose name contains one of the bases (to catch suffixes).
    for base in WANT:
        matches = [s.name for s in allsyms if base in s.name.upper()]
        print(f"\n=== candidates containing {base}: {matches}")

    print("\n" + "=" * 70)
    now = datetime.now()
    far = now - timedelta(days=int(8 * 365.25))
    for base in WANT:
        matches = [s.name for s in allsyms if base in s.name.upper()]
        # Prefer exact, then shortest (fewest suffix chars).
        matches.sort(key=lambda n: (n.upper() != base, len(n)))
        if not matches:
            print(f"\n{base}: NO MATCH")
            continue
        name = matches[0]
        mt5.symbol_select(name, True)
        info = mt5.symbol_info(name)
        tick = mt5.symbol_info_tick(name)
        print(f"\n##### {base} -> using '{name}'")
        if info is None:
            print("  symbol_info None:", mt5.last_error())
            continue
        print(f"  digits={info.digits} point={info.point} "
              f"contract_size={info.trade_contract_size}")
        print(f"  tick_value={info.trade_tick_value} tick_size={info.trade_tick_size}")
        print(f"  volume_min={info.volume_min} volume_max={info.volume_max} "
              f"volume_step={info.volume_step}")
        print(f"  spread(points,current)={info.spread} "
              f"spread_float={info.spread_float}")
        print(f"  swap_long={info.swap_long} swap_short={info.swap_short}")
        if tick:
            cur_spread_pts = round((tick.ask - tick.bid) / info.point, 1)
            print(f"  live bid={tick.bid} ask={tick.ask} "
                  f"spread={cur_spread_pts} points")
        # History depth per timeframe.
        for tf_name, tf in (("D1", mt5.TIMEFRAME_D1),
                            ("H4", mt5.TIMEFRAME_H4),
                            ("H1", mt5.TIMEFRAME_H1)):
            rates = mt5.copy_rates_from(name, tf, now, 200000)
            if rates is None or len(rates) == 0:
                print(f"  {tf_name}: NO DATA ({mt5.last_error()})")
                continue
            t0 = datetime.utcfromtimestamp(int(rates[0]["time"]))
            t1 = datetime.utcfromtimestamp(int(rates[-1]["time"]))
            yrs = (t1 - t0).days / 365.25
            print(f"  {tf_name}: {len(rates)} bars {t0.date()} -> {t1.date()} ({yrs:.2f}y)")

    mt5.shutdown()


if __name__ == "__main__":
    main()
