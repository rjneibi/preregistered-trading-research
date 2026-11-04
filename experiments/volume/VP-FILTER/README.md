# VP-FILTER

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-06-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Volume-profile POC/VA/LVN filter improves D and R.

Family: volume. Market: XAUUSD. Timeframe: H1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author asked whether a volume-profile filter improves gold profiles D and R. A signal is kept only if three conditions hold: its zone is near the point of control, price is outside the value area, and a low-volume node lies between entry and target. Four configurations were run: D and R, each with and without the filter. The filter rejected every eligible signal, so the filtered runs have 0 trades. The baselines here are a reconstruction of the gate logic and differ from the live D/R profiles. Sources: [backtest_vp.py](../../../originals/gann_bot_500/research/vp_backtest/backtest_vp.py) lines 1-29; [all_summaries.csv](../../../originals/gann_bot_500/research/vp_backtest/results/all_summaries.csv).

## Instruments and data
- Instruments: XAUUSD (backtest_vp.py line 47).
- Timeframe(s): H1 for decisions, fills and exits; H4 for ATR, EMA50, ADX and fib structure; D1 for day sessions (backtest_vp.py lines 110-119, 167-177 of the run loop; [signal_engine.py](../../../originals/gann_bot_500/research/vp_backtest/signal_engine.py) lines 30-183).
- Data source and file(s): broker MT5 bars with tick volume, `research/vp_backtest/data/xauusd_{h1,h4,d1}.csv` (manifest group `broker_mt5`, not published; [data/manifest.csv](../../../data/manifest.csv) lines 524-526). Fetched by [fetch_data.py](../../../originals/gann_bot_500/research/vp_backtest/fetch_data.py), which asks for 3 calendar years (line 30); "broker availability may trim this".
- Period: the run loaded H1 = 25,920, H4 = 6,480 and D1 = 1,260 bars ([recorded.vp.log](../../../audit/phaseC/logs_L1/recorded.vp.log) line 4). Baseline trades run from 2022-04-19 to 2026-05-28 (first and last rows of [Profile_D_Baseline.csv](../../../originals/gann_bot_500/research/vp_backtest/results/Profile_D_Baseline.csv) and [Profile_R_Baseline.csv](../../../originals/gann_bot_500/research/vp_backtest/results/Profile_R_Baseline.csv)). That is longer than the 3 years in fetch_data.py; the published files do not explain the difference.
- In-sample / out-of-sample: none. One full-history run per configuration.

## Rules
- Entry: on each closed H1 bar, the gate stack is: price in a confluence zone; H4 EMA50 bias; H4 fib structure; ADX > 25; polarity flip (D only); H1 body-close confirmation. Fill at the next H1 open (backtest_vp.py lines 12-14, 51; the run loop from line 259). The gates are "reconstructed in signal_engine, NOT imported from the live bot" (line 12). Zones are recomputed each calendar day. Each zone is taken at most once per day. One trade at a time.
- Exit (stop, target, time): D SL 1.0 x ATR, TP 3.0 x ATR; R SL 1.5 x ATR, TP 2.5 x ATR (lines 60-63). The ATR is the H4 ATR (filter docstring, "current H4 ATR"). If one bar touches both SL and TP, the SL is taken. There is no time stop: a trade still open at the end of the data closes at the last close (lines 112-169).
- Filters (VP configs only; all three must pass) (lines 16-19, 188-255):
  - POC proximity: |zone - POC| <= 1.0 x ATR, with the POC taken from H1 bars of the last 20 D1 sessions.
  - Value area: price must not be inside the 70% value area.
  - LVN path: the nearest LVN (of the 5 lowest-volume buckets) in the trade direction lies strictly between price and TP.
  - If no profile can be built, the signal is rejected.
- Position sizing: fixed 0.01 lot "for comparability" (line 50). Results in points.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | H4, 14, Wilder with SMA seed | signal_engine.py lines 30-62 |
| EMA | H4, 50, SMA seed | signal_engine.py lines 66-91 |
| ADX | H4, 14, threshold > 25 for both profiles | signal_engine.py line 94; backtest_vp.py line 51 |
| Zone half-width | 0.3 x ATR | backtest_vp.py line 52 |
| Confluence radius | 0.5 x ATR | line 53 |
| H4 swing lookback | 50 bars | line 54; signal_engine.py line 169 |
| D SL / TP | 1.0 / 3.0 x ATR, polarity on | lines 60-63 |
| R SL / TP | 1.5 / 2.5 x ATR, polarity off | lines 60-63 |
| VP window | 20 D1 sessions of H1 bars | line 55 |
| POC proximity | 1.0 x ATR | line 56 |
| Value area | 70% | filter code, `va_pct=0.70` |
| LVN candidates | 5 lowest buckets | filter code, `n_bottom=5` |
| Price bucket | $0.50 | line 57 |
| Lot | 0.01 | line 50 |

## Costs
Every entry is worsened by 40 points ($0.40), the live `MAX_SPREAD_POINTS` cap, used here as the spread cost (backtest_vp.py lines 49, 172-185). There is no commission, swap or slippage.

## Tuning and selection
- Search: none. Four fixed configurations (backtest_vp.py lines 5-10).
- Configurations run (counted from the code/results): 4 (all_summaries.csv). Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row VP-FILTER, n_variants): 2. The ledger counts the two VP variants, not the two baselines.
- How the reported variant was chosen: not applicable; all four are reported.
- Preregistered: no.

## Results
From [all_summaries.csv](../../../originals/gann_bot_500/research/vp_backtest/results/all_summaries.csv) and [vp_analysis_report.txt](../../../originals/gann_bot_500/research/vp_backtest/results/vp_analysis_report.txt). The audit rerun reproduced all_summaries exactly ([VERDICTS.md](../../../audit/VERDICTS.md) line 16).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| D baseline | 66 | PF 1.025, win 22.7%, expectancy 49.2 pts (INSUFFICIENT SAMPLE) | all_summaries.csv |
| R baseline | 32 | PF 1.027, win 46.9%, expectancy 46.3 pts (INSUFFICIENT SAMPLE) | all_summaries.csv |
| D with VP filter | 0 (104 eligible signals, 0 passed) | no trades | all_summaries.csv |
| R with VP filter | 0 (48 eligible, 0 passed) | no trades | all_summaries.csv |
| D rejected signals, hypothetical | 104 | win 18.3%, avg -439.5 pts; removed by POC 63, VA 80, LVN 75 (overlapping) | vp_analysis_report.txt |
| R rejected signals, hypothetical | 48 | win 50.0%, avg +287.5 pts; removed by POC 33, VA 36, LVN 35 (overlapping) | vp_analysis_report.txt |

Raw signal and ADX-pass counts differ between each baseline and its VP run (D 304/66 vs 363/104; R 127/32 vs 147/48). Because the slot is held by open trades, the two runs see different signals (all_summaries.csv columns RawSignals, ADXPassed).

## Code and how to rerun
- Code: [run_backtest.py](../../../originals/gann_bot_500/research/vp_backtest/run_backtest.py) (entry point: fetch, backtest, analyse), [backtest_vp.py](../../../originals/gann_bot_500/research/vp_backtest/backtest_vp.py), [signal_engine.py](../../../originals/gann_bot_500/research/vp_backtest/signal_engine.py), [volume_profile.py](../../../originals/gann_bot_500/research/vp_backtest/volume_profile.py), [analyze_results.py](../../../originals/gann_bot_500/research/vp_backtest/analyze_results.py), [fetch_data.py](../../../originals/gann_bot_500/research/vp_backtest/fetch_data.py).
- Audit rerun stage: none in [run_all.sh](../../../audit/tools/run_all.sh) or [CLEAN_RUN_stages.txt](../../../audit/tools/CLEAN_RUN_stages.txt). The folder is copied into the research sandbox ([sandbox_research.py](../../../audit/phaseC/sandbox_research.py) line 16), and a stored rerun log exists ([recorded.vp.log](../../../audit/phaseC/logs_L1/recorded.vp.log)), but no listed stage regenerates it.
- Public data enough? No. It needs `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv) lines 524-526).

## Corrections from the release review
- README "baseline D PF 1.025 n=66, R PF 1.027 n=32". Misleading. These baselines are not the live D and R. backtest_vp.py hard-codes an ADX > 25 gate "for BOTH profiles" (line 51) and rebuilds the gates instead of importing them (line 12). The live config has ADX off (`ADX_THRESHOLD = 0`, [config.py](../../../originals/gann_bot_500/config.py) lines 136, 73). Both baselines also have fewer than 100 trades and must be labelled INSUFFICIENT SAMPLE.
- README "Costs: see backtest_vp.py". The cost is the 40-point spread cap charged on every entry. There is no commission (lines 49, 172-185).
- README "Data: MT5 tick-volume" gives no window. The fetch asks for 3 years (fetch_data.py line 30), but the trades run from 2022-04-19 to 2026-05-28.
- README "Rules" gives no parameters. They are 20 sessions, POC within 1.0 x ATR, 70% value area, 5 LVN candidates and $0.50 buckets (lines 55-57).
- README "Variants counted in the ledger: 2". Four configurations were run; the two baselines are not counted.
- README "Provenance" links the report but not the code or the rerun log, although both are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Filter passed 0% of signals, so 0 trades survived; baseline D PF 1.025 n=66, R PF 1.027 n=32 |
| Rerun, recorded clock | Baselines 1.025 / 1.027 |
| Rerun, true UTC | not on the SUSPECT list; not rerun on true UTC |

## Verdict
VERIFIED. all_summaries identical.

## Audit caveats
All-veto result is a filter definition failure, not evidence about volume profile. Spot volume is a broker tick count.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/research/vp_backtest/results/vp_analysis_report.txt](../../../originals/gann_bot_500/research/vp_backtest/results/vp_analysis_report.txt)
