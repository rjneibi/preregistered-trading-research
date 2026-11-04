"""
fetch_data.py — Download XAUUSD history from MetaTrader 5 for the VP backtest.

Connects to MT5 using the SAME credential pattern as bot.py/broker.py (imports
CONFIG values from the project's config.py) and pulls ~3 years of H1, H4 and D1
OHLCV bars (including tick_volume), saving each timeframe to a CSV under
research/vp_backtest/data/.

This is the ONLY file in the VP backtest that touches MT5 or config.py. The
volume-profile and signal engines downstream are pure-DataFrame and never import
the live bot.

Run standalone:  python research/vp_backtest/fetch_data.py
If MT5 is not running / cannot connect, the script prints a clear message and
exits with a non-zero status instead of crashing.
"""

import sys
from pathlib import Path

# ── Make the project root importable so `import config` resolves the live config
#    (credentials only). We do NOT import bot.py / broker.py / signals.py here. ──
_THIS = Path(__file__).resolve()
_PROJECT_ROOT = _THIS.parents[2]          # research/vp_backtest -> research -> root
sys.path.insert(0, str(_PROJECT_ROOT))

_DATA_DIR = _THIS.parent / "data"

# Years of history to request (calendar years; broker availability may trim this).
_YEARS = 3
# Bars-per-year upper bounds (gold trades ~24h x 5d). Over-requesting is safe:
# copy_rates_from_pos simply returns fewer rows when history is shorter.
_BARS_PER_YEAR = {
    "H1": 24 * 6 * 60,    # generous H1 upper bound
    "H4": 6 * 6 * 60,     # generous H4 upper bound
    "D1": 7 * 60,         # generous D1 upper bound
}

_CSV_COLUMNS = ["time", "open", "high", "low", "close",
                "tick_volume", "spread", "real_volume"]


def _connect_mt5():
    """
    Initialize and log in to MT5 using config.py credentials (same pattern as
    broker.connect, re-implemented locally so we do not import the live broker).

    Returns:
        module or None: the imported MetaTrader5 module on success, else None.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[fetch_data] ERROR: MetaTrader5 package is not installed "
              "(pip install MetaTrader5).")
        return None

    try:
        import config
    except Exception as e:  # noqa: BLE001
        print(f"[fetch_data] ERROR: could not import project config.py: {e}")
        return None

    init_kwargs = {
        "login": config.LOGIN,
        "password": config.PASSWORD,
        "server": config.SERVER,
    }
    terminal_path = getattr(config, "TERMINAL_PATH", None)
    if terminal_path:
        init_kwargs["path"] = terminal_path
        if getattr(config, "PORTABLE", False):
            init_kwargs["portable"] = True

    if not mt5.initialize(**init_kwargs):
        print(f"[fetch_data] ERROR: mt5.initialize() failed: {mt5.last_error()}")
        print("[fetch_data] Is the MetaTrader 5 terminal installed/running and "
              "the account reachable? Aborting.")
        return None

    if not mt5.login(login=config.LOGIN, password=config.PASSWORD,
                     server=config.SERVER):
        print(f"[fetch_data] ERROR: mt5.login() failed: {mt5.last_error()}")
        mt5.shutdown()
        return None

    acct = mt5.account_info()
    bal = acct.balance if acct else float("nan")
    print(f"[fetch_data] Connected to {config.SERVER} as {config.LOGIN} "
          f"| balance={bal:.2f}")
    return mt5


def _fetch_timeframe(mt5, symbol, tf_const, count):
    """
    Pull up to `count` recent bars for one timeframe into a DataFrame.

    Params:
        mt5: the imported MetaTrader5 module (already initialized).
        symbol (str): trading symbol.
        tf_const (int): an mt5.TIMEFRAME_* constant.
        count (int): number of bars to request.

    Returns:
        pandas.DataFrame or None: bars with _CSV_COLUMNS, oldest first.
    """
    import pandas as pd

    rates = mt5.copy_rates_from_pos(symbol, tf_const, 0, count)
    if rates is None or len(rates) == 0:
        print(f"[fetch_data] WARNING: no data returned for tf_const={tf_const}: "
              f"{mt5.last_error()}")
        return None

    df = pd.DataFrame(rates)
    # Ensure every expected column exists (older terminals may omit real_volume).
    for col in _CSV_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    df = df[_CSV_COLUMNS].copy()
    # Add a human-readable UTC timestamp column alongside the raw epoch `time`.
    df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def fetch_all():
    """
    Fetch H1/H4/D1 history for the configured symbol and write three CSVs.

    Returns:
        int: 0 on success, non-zero on any failure (suitable for sys.exit()).
    """
    import config

    mt5 = _connect_mt5()
    if mt5 is None:
        return 1

    symbol = config.SYMBOL
    # Make sure the symbol is selected/visible before requesting history.
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"[fetch_data] ERROR: symbol_info({symbol}) is None: "
              f"{mt5.last_error()}")
        mt5.shutdown()
        return 1
    if not info.visible:
        mt5.symbol_select(symbol, True)

    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    tf_map = {
        "H1": (mt5.TIMEFRAME_H1, _DATA_DIR / "xauusd_h1.csv"),
        "H4": (mt5.TIMEFRAME_H4, _DATA_DIR / "xauusd_h4.csv"),
        "D1": (mt5.TIMEFRAME_D1, _DATA_DIR / "xauusd_d1.csv"),
    }

    exit_code = 0
    for tf_name, (tf_const, out_path) in tf_map.items():
        count = _BARS_PER_YEAR[tf_name] * _YEARS
        df = _fetch_timeframe(mt5, symbol, tf_const, count)
        if df is None or len(df) == 0:
            print(f"[fetch_data] {tf_name}: FAILED (no rows)")
            exit_code = 1
            continue
        df.to_csv(out_path, index=False)
        start = df["datetime"].iloc[0]
        end = df["datetime"].iloc[-1]
        print(f"[fetch_data] {tf_name}: {len(df):>6d} rows  "
              f"{start} -> {end}  saved {out_path.name}")

    mt5.shutdown()
    print("[fetch_data] MT5 connection shut down.")
    return exit_code


if __name__ == "__main__":
    sys.exit(fetch_all())
