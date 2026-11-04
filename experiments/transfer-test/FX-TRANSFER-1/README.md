# FX-TRANSFER-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-06-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Gold profiles D/R/S transfer to FX majors with locked parameters.

Family: transfer test. Market: EURUSD/GBPUSD/AUDUSD. Timeframe: H1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author ran the three live gold profiles D, R and S on three FX majors with their gold parameters locked. No gate was re-tuned per pair. The test asked whether any profile reached the gold benchmark of PF 1.20. None did. The six D/R trade files were later recomputed by the audit and matched exactly. Source: [FX_BACKTEST_REPORT.md](../../../originals/gann_bot_500/research/fx_backtest/results/FX_BACKTEST_REPORT.md) lines 1-11, 65-71.

## Instruments and data
- Instruments: EURUSD, GBPUSD, AUDUSD ([fx_common.py](../../../originals/gann_bot_500/research/fx_backtest/fx_common.py) line 33).
- Timeframe(s): D and R on H1 bars with an H4 bias ([config.py](../../../originals/gann_bot_500/config.py) lines 129-130). S is a "Daily/H4 swing system" (report line 58).
- Data source and file(s): broker MT5 demo feed, fetched live with `copy_rates_range` (report line 7; fx_common.py lines 22-25). The bars were not cached. No file is in [data/manifest.csv](../../../data/manifest.csv).
- Period: a 7-year window back from the run date (fx_common.py lines 29, 16-18). Trades run from 2019-06-28 to 2026-06-12 (first and last rows of the trade CSVs). S in-sample is 2019-06-17 to 2024-05-07 and out-of-sample 2024-05-07 to 2026-06-12 for EURUSD ([summaries_S.json](../../../originals/gann_bot_500/research/fx_backtest/results/summaries_S.json)).
- In-sample / out-of-sample: 70/30 chronological split by time span per symbol (fx_common.py lines 30, 44-47). D EURUSD split date 2024-05-08 ([summary_D_EURUSD.json](../../../originals/gann_bot_500/research/fx_backtest/results/summary_D_EURUSD.json)).

## Rules
- Entry: the live six-gate zone logic of `research/backtest.py`, imported unchanged ([fx_dr_backtest.py](../../../originals/gann_bot_500/research/fx_backtest/fx_dr_backtest.py) lines 3-7, 39). That file is not in the repo, so the exact gate sequence cannot be checked. Parameters in the published live config: Fibonacci pivots; Gann degrees 45-360; fib levels 0.382/0.5/0.618/0.786; zone = level ± 0.3 x ATR(H1); H1 close confirmation; H4 bias; confluence within 0.5 x ATR; ADX threshold 0 (off) ([config.py](../../../originals/gann_bot_500/config.py) lines 122-136, 231). D/R prices are multiplied by 10,000 so the engine's 2-decimal rounding does not collapse FX levels (fx_common.py lines 58-72). S uses `backtest_s.py`, also imported unchanged and also not in the repo ([fx_s_backtest.py](../../../originals/gann_bot_500/research/fx_backtest/fx_s_backtest.py) lines 1-8).
- Exit (stop, target, time):
  - D ("Core + Polarity"): TP 3.0 x ATR, SL 1.0 x ATR (fx_dr_backtest.py lines 11, 43-46).
  - R ("Pure Core"): TP 2.5 x ATR, SL 1.5 x ATR (lines 12, 43-46).
  - S: phase trail, breakeven/trailing and weekend-gap control inside backtest_s.py (fx_s_backtest.py lines 4-6). Values: Not recorded in the published files.
  - Time exit for D/R: inside `bt.simulate_trade`, not published.
- Filters: D polarity flip on, R off (fx_dr_backtest.py lines 43-46). S adds a news blackout: NFP on the first Friday 12:00-15:00 UTC on all pairs, and RBA on the first Tuesday 03:00-06:00 UTC on AUDUSD; it blocked 0 entries (fx_s_backtest.py lines 17-22; report line 63).
- Position sizing: results in R, net of costs (fx_dr_backtest.py lines 61-64). MaxDD% is on a 1%-fixed-fractional equity curve (report line 27).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| D TP / SL | 3.0 / 1.0 x ATR(H1) | fx_dr_backtest.py lines 43-46 |
| R TP / SL | 2.5 / 1.5 x ATR(H1) | fx_dr_backtest.py lines 43-46 |
| Polarity flip | D on, R off, S mandatory | fx_dr_backtest.py lines 43-46; report line 27 |
| Pivot type | Fibonacci | config.py line 122 |
| Gann degrees | 45, 90, ... 360 | config.py line 123 |
| Fib levels | 0.382, 0.5, 0.618, 0.786 | config.py line 124 |
| Zone width | ± 0.3 x ATR(H1) | config.py line 126 |
| Confluence radius | 0.5 x ATR | config.py line 231 |
| ADX threshold | 0 (off) | config.py line 136 |
| D/R price scale | x10,000 | fx_common.py line 72 |
| IS share | 0.70 | fx_common.py line 30 |

## Costs
- D/R: per-symbol spread charged once per trade, plus $7 per lot round-trip commission ([fx_dr_backtest.py](../../../originals/gann_bot_500/research/fx_backtest/fx_dr_backtest.py) lines 14-15, 54-61). Spread cost in points: EURUSD 8, GBPUSD 12, AUDUSD 11, about 2x the 7-year recorded mean H1 spread (fx_common.py lines 35-50; report lines 17-23). At $1 per point per lot, the commission is 7 points.
- S: spread plus commission folded into one points figure (EURUSD 15), plus nightly swap read from `symbol_info` (EURUSD -0.7 long, -1.0 short points) ([fx_s_backtest.py](../../../originals/gann_bot_500/research/fx_backtest/fx_s_backtest.py) lines 12-15; summaries_S.json).
- No separate slippage.

## Tuning and selection
- Search: none. "No per-pair re-optimisation of any gate" (report line 8).
- Configurations run (counted from the code/results): 9 (3 profiles x 3 pairs; nine trade files in [results/](../../../originals/gann_bot_500/research/fx_backtest/results/)). Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row FX-TRANSFER-1, n_variants): 9. They agree.
- How the reported variant was chosen: not applicable. All nine runs are reported against the gold PF 1.20 bar. The report adds a new data floor for S after seeing the counts: at least 30 OOS trades (report lines 58-61).
- Preregistered: no. The parameters were locked from earlier gold work.

## Results
From the report's table (lines 29-39), recomputed from the trade files by the audit ([l2_more.json](../../../audit/phaseC/l2_more.json) `fx`; S in [l2_recompute.json](../../../audit/phaseC/l2_recompute.json)).

| Slice | Trades (n) full / OOS | Result PF full / OOS | Source file |
|---|---|---|---|
| D EURUSD | 710 / 203 | 0.721 / 0.631 | l2_more.json |
| D GBPUSD | 673 / 195 | 0.799 / 0.813 | l2_more.json |
| D AUDUSD | 765 / 233 | 0.731 / 0.681 | l2_more.json |
| R EURUSD | 1,140 / 372 | 0.902 / 1.03 (OOS +0.019R/trade) | l2_more.json; report line 68 |
| R GBPUSD | 1,220 / 386 | 0.884 / 0.839 | l2_more.json |
| R AUDUSD | 1,150 / 327 | 0.842 / 0.764 | l2_more.json |
| S EURUSD | 24 / 5 | 0.41 / 0.00 (INSUFFICIENT SAMPLE) | report line 37; l2_recompute.json |
| S GBPUSD | 41 / 16 | 0.54 / 0.15 (INSUFFICIENT SAMPLE) | report line 38 |
| S AUDUSD | 31 / 12 | 0.40 / 0.53 (INSUFFICIENT SAMPLE) | report line 39 |
| Gold reference, D XAUUSD OOS | 162 | PF 1.20 | report line 40 |

Verdict: 0 of 9 meet PF 1.20. The audit counts all six D/R files as exact: recomputed n and PF equal the stored summaries.

## Code and how to rerun
- Code: [fx_common.py](../../../originals/gann_bot_500/research/fx_backtest/fx_common.py), [fx_dr_backtest.py](../../../originals/gann_bot_500/research/fx_backtest/fx_dr_backtest.py), [fx_s_backtest.py](../../../originals/gann_bot_500/research/fx_backtest/fx_s_backtest.py), [fx_report.py](../../../originals/gann_bot_500/research/fx_backtest/fx_report.py). The engines they import, `research/backtest.py` and `backtest_s.py`, are not in the repo. Audit recompute: [l2_more.py](../../../audit/phaseC/l2_more.py), [l2_recompute.py](../../../audit/phaseC/l2_recompute.py) lines 100-111.
- Audit rerun stage: `c_l2_more` and `c_l2_recompute` ([run_all.sh](../../../audit/tools/run_all.sh) line 50). These recompute statistics from the stored trade files. They do not rerun the backtest.
- Public data enough? No. The backtest needs the unpublished engines and live MT5 bars that were never cached; no manifest group covers them. The recompute stages need only the trade CSVs, which are published.

## Corrections from the release review
- README "Rules: Live gates unchanged, no per-pair tuning." It does not define D, R or S. D is TP 3.0 / SL 1.0 ATR with polarity on; R is TP 2.5 / SL 1.5 ATR with polarity off (fx_dr_backtest.py lines 10-12). Note: the published live config.py now sets D's TP to a fixed $9.00, not 3.0 ATR (config.py lines 57-75). "Profile D" on this page means the 3.0 ATR version.
- README does not say the backtest cannot be rerun. Both engines, `research/backtest.py` and `backtest_s.py`, are imported but not published, and the MT5 bars were not cached. Only the statistics were recomputed, from the stored trades (l2_more.py line 1).
- README "Costs: per-symbol spread + $7/lot". Incomplete. The spread costs are 8 / 12 / 11 points, about 2x the recorded mean. S also pays nightly swap (fx_common.py lines 35-50; fx_s_backtest.py line 14).
- README "Data: broker demo feed 2019-06 to 2026-06" gives no source for the window. The source is fx_common.py lines 16-18 and 29 (7 years back from the run date).
- README results give PF without n. Add n: D EURUSD 710/203, R EURUSD 1,140/372. The S cells have n = 24 to 41 and must be labelled INSUFFICIENT SAMPLE.
- README "Provenance" links only the report. The code and the audit recompute files are published and should be linked.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0/9 pass; best full PF 0.90 (R EURUSD); D EURUSD 0.72/0.63 |
| Rerun, recorded clock | 0/9; best 0.90, all 6 D/R files exact |
| Rerun, true UTC | no gold clock |

## Verdict
VERIFIED. Recomputed from stored trades. R EURUSD OOS PF 1.03 is a single cell.

## Audit caveats
The gold reference it compares to was later overturned.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/research/fx_backtest/results/FX_BACKTEST_REPORT.md](../../../originals/gann_bot_500/research/fx_backtest/results/FX_BACKTEST_REPORT.md)
