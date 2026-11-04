"""
run_backtest.py — Master orchestration for the Volume Profile backtest.

Runs the three stages in order and prints total runtime:

    1. fetch_data.py     (SKIPPED if all three data CSVs already exist)
    2. backtest_vp.py    (runs all four configurations)
    3. analyze_results.py (comparison table, equity curves, text report)

Stage 1 needs a running MetaTrader 5 terminal; stages 2–3 are pure-DataFrame and
need no MT5. If fetch fails (e.g. MT5 not running) and no cached CSVs exist, the
run aborts before the backtest with a clear message.

────────────────────────────────────────────────────────────────────────────
REQUIREMENTS (install if missing):
    pip install pandas numpy ta matplotlib scipy MetaTrader5
    (scipy is optional; the engines fall back to numpy where possible.)
────────────────────────────────────────────────────────────────────────────

Usage:
    python research/vp_backtest/run_backtest.py            # full pipeline
    python research/vp_backtest/run_backtest.py --refetch  # force re-download
"""

import sys
import time
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))

_DATA_DIR = _THIS.parent / "data"
_DATA_FILES = ["xauusd_h1.csv", "xauusd_h4.csv", "xauusd_d1.csv"]


def _data_present():
    """
    True if all three timeframe CSVs already exist and are non-empty.

    Returns:
        bool: whether the fetch stage can be skipped.
    """
    return all((_DATA_DIR / f).exists() and (_DATA_DIR / f).stat().st_size > 0
               for f in _DATA_FILES)


def main():
    """
    Orchestrate fetch -> backtest -> analyze and print total runtime.

    Returns:
        int: 0 on success, non-zero if a stage fails.
    """
    refetch = "--refetch" in sys.argv
    t0 = time.time()

    # ── Stage 1: fetch ──
    if refetch or not _data_present():
        print("[run_backtest] Stage 1/3: fetching data from MT5 ...")
        import fetch_data
        rc = fetch_data.fetch_all()
        if rc != 0:
            if _data_present():
                print("[run_backtest] Fetch failed but cached CSVs exist — "
                      "continuing with existing data.")
            else:
                print("[run_backtest] Fetch failed and no cached data — aborting.")
                return rc
    else:
        print("[run_backtest] Stage 1/3: data CSVs present — skipping fetch.")

    # ── Stage 2: backtest ──
    print("[run_backtest] Stage 2/3: running backtest (4 configs) ...")
    import backtest_vp
    rc = backtest_vp.main()
    if rc != 0:
        print("[run_backtest] Backtest failed — aborting.")
        return rc

    # ── Stage 3: analyze ──
    print("[run_backtest] Stage 3/3: analysing results ...")
    import analyze_results
    rc = analyze_results.main()

    elapsed = time.time() - t0
    mins, secs = divmod(elapsed, 60)
    print(f"\n[run_backtest] TOTAL RUNTIME: {int(mins)}m {secs:.1f}s")
    return rc


if __name__ == "__main__":
    sys.exit(main())
