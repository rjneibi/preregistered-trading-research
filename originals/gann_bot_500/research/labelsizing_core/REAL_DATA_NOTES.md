# REAL_DATA_NOTES — running labelsizing_core on real XAUUSD H1

This is a **research run on real history with NO live path**. Nothing here imports
MetaTrader5, dispatches orders, or touches a live profile. It reads a local H1 OHLC
file and a precomputed signals file, then runs the same labeling → CPCV →
calibration → sizing → walk-forward core that was validated on synthetic data.

## Why signals come from a CSV (the fidelity decision)

The live entry rule is `signals.evaluate_signal`. It is **not** a pure function of
H1 OHLC: it imports `structure`, which does `import MetaTrader5` at module load and
fetches **live H4 data via the broker** (`structure.check_zone_polarity` →
`mt5.copy_rates_from_pos`), plus `levels.build_zones` (multi-timeframe zone
structure) and H4 EMA50 bias. So it cannot run inside this MT5-free quarantine, and
re-implementing it here would risk a clean-but-wrong number that does not transfer
to the live profiles.

Decision (Option 2): the **real** `evaluate_signal` is run **outside** this folder
(with MT5), and its output — `(bar t, side)` — is exported to a CSV that
`run_real.py` ingests. The authoritative rule stays authoritative; only the
labeling + sizing core lives in the quarantine. No rule is reinvented here.

## Files this run expects

1. **H1 OHLC** — a local CSV/parquet with columns `time`/`datetime`, `open`,
   `high`, `low`, `close`, and `tick_volume` if present. Example present in this
   repo: `research/vp_backtest/data/xauusd_h1.csv` (~25.9k bars, 2022→2026 — enough
   history for the 1512-bar feature lookback). `real_data.load` coerces a tz-naive
   H1 `DatetimeIndex` and **reports + asserts OHLC coherence** (it never silently
   repairs bad bars).

2. **Signals CSV** — produced by the export step below. Schema:

   | column     | required | meaning                                             |
   |------------|----------|-----------------------------------------------------|
   | `datetime` | yes\*    | tz-naive H1 bar timestamp of the signal bar `t`     |
   | `side`     | yes      | `+1`/`BUY`/`long` or `-1`/`SELL`/`short`            |
   | `profile`  | no       | `D` or `R`; filter with `run_real.py --profile D`   |

   \* `datetime` may be replaced by epoch-seconds `time`, or by a positional
   integer `bar_idx`. Timestamps that do not match an H1 bar are reported and
   dropped — never snapped. One signal per bar (duplicates dropped, first kept).

## Producing the signals CSV (run OUTSIDE the quarantine, with MT5)

This export must live and run **outside** `research/labelsizing_core/` because it
imports `MetaTrader5` and the live `signals`/`structure`/`levels` stack. The
natural host is an existing live-faithful backtester (e.g.
`research/backtest_live_replica.py` / `research/backtest.py`), which already
replays the live gates over history via `mt5.copy_rates_*`. Add a hook that, each
time `evaluate_signal` (or the backtester's gate equivalent) fires a fresh signal,
records one row:

```python
# sketch — runs in the LIVE environment, NOT in research/labelsizing_core/
rows = []
for t, bar in enumerate(h1_history):           # walk H1 bars chronologically
    zones  = levels.build_zones(...)            # built from the live multi-TF stack
    h4_bias = ...                               # H4 EMA50 bias as the live bot computes
    sig = signals.evaluate_signal(price, zones, h4_bias, h1_window, atr,
                                   use_polarity=True)   # True=Profile D, False=Profile R
    if sig is not None:
        rows.append({"datetime": bar.time, "side": 1 if sig["direction"] == "BUY" else -1,
                     "profile": "D"})
pd.DataFrame(rows).drop_duplicates("datetime").to_csv("xauusd_h1_signals.csv", index=False)
```

Export D and R separately (the `use_polarity` flag is their only difference) and
run `run_real.py` once per profile with `--profile`.

## Running

```
research/labelsizing_core/.venv/Scripts/python research/labelsizing_core/run_real.py \
    research/vp_backtest/data/xauusd_h1.csv  path/to/xauusd_h1_signals.csv  --profile D
```

**Runtime caveat:** `USE_HMM_REGIME=True` with `L_FEATURE_MAX=1512` over ~25k bars
runs the rolling Gaussian-HMM refits plus 15 XGBoost/Venn-Abers splits — expect
**several minutes**, dominated by the feature build and the causality probe.

## Read the output in this order

1. **Signal sanity first.** Before trusting any downstream number, check the
   ingested signal count, BUY/SELL split, signals-per-year cadence, and the
   TP/SL/TIMEOUT label distribution. If real XAUUSD produces wildly more/fewer
   signals than your live D/R profiles' actual trade frequency, the export or the
   alignment is off — fix that before reading calibration.
2. **Purge cost.** Section 3 prints each split's surviving train fraction and warns
   loudly if any split's train count drops below 200 (the 1512-bar purge can starve
   folds on short histories — that is a data-budget signal, not a verdict).
3. **Gating asserts.** Coherence, `entry_idx == t + N_CONFIRM`, non-empty CPCV
   folds, and the zero-violation leakage probe must all pass.
4. **Walk-forward read.** Section 8 prints the raw rule edge (path-independent) and
   the per-CPCV-path sized edge, plus sign agreement and spread across the 5 paths.
   The script **declares no go/no-go** — judge the path spread against your gate.

## Suggested scoped commit (run it yourself after review)

```
git add research/labelsizing_core/real_data.py research/labelsizing_core/run_real.py research/labelsizing_core/REAL_DATA_NOTES.md
git commit -m "research(labelsizing_core): real-data adapter + walk-forward harness (CSV signals, no MT5)"
```
