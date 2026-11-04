# VWAP/EMA video strategy + TradingView indicator search

Research only. Nothing here connects to a broker for trading or touches the live bots.

## Run everything

```
.venv\Scripts\python src\run_all.py              # fetch SPY/QQQ, tests, phase 1, phase 2, Pine, report
.venv\Scripts\python src\run_all.py --no-fetch   # same on the data already in data/
```

Output: `reports/report.html`, `results/*.csv(.gz)/.json`, `pine/*.pine`. Phase 2 takes roughly 15–30 min on 9 cores.

Single stages: `src/phase1.py`, `src/phase2.py`, `src/pine.py`, `src/report.py`, `python -m pytest -q tests`.

## Environment

* **Python:** system Python 3.11. `.venv` is created with `--system-site-packages` and adds only **optuna**, which is pure Python. `requirements.txt` pins the versions.
* **Why not the usual stack:** Windows Application Control on the author's machine blocks any newly downloaded native DLL.
  * A fresh pandas wheel failed to load.
  * vectorbt, numba, pyarrow and yfinance (through curl_cffi) all need native code, so none of them are used.
  * Do not try to bypass the policy.
* **Engine:** a small numpy simulator, `src/engine.py`, replaces vectorbt.
* **SPY/QQQ data:** `src/fetch_yf.py` calls Yahoo's chart endpoint directly instead of using yfinance.
* **Results format:** CSV/gzip instead of parquet.

## Data

| file | what | how to refresh |
|---|---|---|
| `data/SPY_1m.csv` etc. | Yahoo bars, regular hours only (1m 30 days, 5m 57 days, 1h 2 years, 1d 10 years) | `src/fetch_yf.py` |
| `data/xau_tv.npz` | broker XAUUSD M1 (last 99,999 bars) and M5 (last 99,999 bars), bid prices, with spread and tick volume | Pulled read-only from a broker demo terminal by `src/vm_xau_tv.py` and `src/vm_xau_tv.ps1`. Not published. |

**Swapping in new data:**
* **Another ticker:** drop `<TICKER>_1m.csv` (and `_5m`, `_1h`, `_1d`) into `data/` with columns `time,open,high,low,close,volume`. `time` is UTC epoch seconds. Add the ticker to `common.ASSETS` and `engine.COST`.
* **TradingView export ("Export chart data"):** rename the columns to match and convert time to epoch seconds.
* **Every timeframe** is resampled from one base series. `common.source_for` decides which base feeds which timeframe and horizon.

## Rules baked in

* **Timing:** signals are read on bar close and filled at the next bar's open. Indicators use only past bars.
* **Same bar hits stop and target:** the stop is assumed (worst case). A bar that opens past the stop or target fills at that open.
* **XAU costs:** bars are bid, so longs pay the recorded spread on entry and shorts pay it on exit (minimum $0.22).
* **SPY/QQQ costs:** $0.01 per share per side. Edit `engine.COST` to change this.
* **Sizing:** one share or one ounce per trade. Multiply XAU by 100 for 1 lot.
* **Phase 2 anti-overfit rules:**
  * Ranking is by out-of-sample results only.
  * At least 30 out-of-sample trades are needed to rank.
  * Every config tested is logged and counted in the deflated Sharpe ratio.
  * Each candidate is compared with buy-and-hold and with random entries.
  * Bootstrap and walk-forward checks.
  * Parameter-neighbour stability check.

## Indicator fidelity

`tests/test_indicators.py` checks:
* **RSI:** against the published Wilder/StockCharts worked example (70.53, 66.32).
* **EMA and ATR:** against loop versions of the Pine reference code. Both are SMA-seeded, as TradingView's built-ins are.
* **VWAP:** OHLC4 source with a session reset, and its standard-deviation band.
* **Engine:** fill timing, worst-case same-bar handling, stop-and-reverse, and end-of-session rules.

`src/ind.py` lists the Pine formula each function follows.

## Pine scripts

The `pine/` folder holds:
* `top_1..3.pine`: the three best Phase 2 configs.
* `video_ema9_vwap_a|b|c.pine`: the video rule with each of its exit variants.

They have not been compiled inside TradingView from here. Each file's header explains why TradingView's results will differ a little (feed, same-bar fill order, costs, session).
