# DR-EDGE-SCREEN

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-01. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Unthrottled D/R entry signals carry edge.

Family: support/resistance. Market: XAUUSD. Timeframe: H1 / M1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author's live bots run two support/resistance profiles, D and R, built on Gann, pivot and Fibonacci zones. This screen asked whether their entry signals have edge. Every H1 close where all live entry gates pass was recorded as a separate entry, with no live throttles, and exits were simulated on M1. Follow-up runs tried a per-zone throttle, a different TP, and six variant arms. No spread was charged.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): signals at each H1 close; H4 for bias and polarity; D1 for pivots; M1 for exits ([backtest.py](../../../originals/gann_bot_500/research/dr_backtest/backtest.py) lines 1-15).
- Data source and file(s): HistData XAUUSD M1, `research/data/xauusd_m1_histdata.csv` ([data_prep.py](../../../originals/gann_bot_500/research/dr_backtest/data_prep.py) line 28).
- Period: base run 2021-06-19 to 2026-06-19 17:57 UTC ([run.py](../../../originals/gann_bot_500/research/dr_backtest/run.py) lines 37-38). Variant runs: IS 2016-01-01 to 2022-12-31, OOS 2023-01-01 to 2026-06-19 ([run_variants.py](../../../originals/gann_bot_500/research/dr_backtest/run_variants.py) docstring; [variants_report.md](../../../originals/gann_bot_500/research/dr_backtest/variants_report.md) lines 45-50).
- In-sample / out-of-sample: base run split chronologically by trade count, first 70% IS (run.py line 122). For D this put the boundary at 2025-02-27 21:00 UTC; for R at 2025-03-20 18:00 UTC ([backtest_1perzone_report.md](../../../originals/gann_bot_500/research/dr_backtest/backtest_1perzone_report.md) lines 4-5).

## Rules
- Entry: at each H1 close, zones are built with the live functions `levels.gann_levels`, `fibonacci_pivots`, `fib_retracements` and `build_zones`; the live `signals.evaluate_signal` is then called (backtest.py lines 4-10). In code, a signal needs: price inside a confluence zone; a side from the zone (for D, re-evaluated from recent H4 closes by the polarity check); agreement with the H4 bias; and an H1 close confirming the level ([signals.py](../../../originals/gann_bot_500/signals.py) lines 155-274). The published files say "six gates" but do not list them. Entry at the H1 close price ([variants_report.md](../../../originals/gann_bot_500/research/dr_backtest/variants_report.md) line 35). Unthrottled: no one-per-zone-per-day rule, no max open trades, no cooldown (backtest.py lines 17-20).
- Exit (stop, target, time): SL = 1.0 x ATR (D) or 1.5 x ATR (R); TP fixed at 900 points = $9/oz (D) or 1000 points = $10/oz (R); half the position closes at 1.0 x ATR in profit and the rest moves to breakeven; horizon 30 days; if one M1 bar touches both TP and SL it is flagged ambiguous, resolved as SL, and left out of PF ([backtest.py](../../../originals/gann_bot_500/research/dr_backtest/backtest.py) lines 82-110; [exit_sim.py](../../../originals/gann_bot_500/research/dr_backtest/exit_sim.py) lines 31-60, 77-114; variants_report.md line 36).
- Filters: live spread gate, ADX gate (threshold 0 live), M5 RSI filter (off live) and D's M1 pullback entry are skipped (backtest.py lines 22-30).
- Position sizing: none. Results are in points ($0.01/oz) per trade (exit_sim.py line 24).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Polarity flip | D on, R off | backtest.py lines 85, 100 |
| Gann degrees | 45, 90, 135, 180, 225, 270, 315, 360 | backtest.py lines 92, 108 |
| Fibonacci levels | 0.382, 0.500, 0.618, 0.786 | backtest.py lines 93, 109 |
| Zone width | 0.3 x ATR | backtest.py lines 90, 106 |
| Confluence distance | 0.5 x ATR | backtest.py lines 91, 107 |
| Swing lookback | 50 H4 bars | backtest.py lines 89, 105 |
| ATR | Wilder 14 on H1 | run.py line 55 |
| SL | D 1.0 x ATR, R 1.5 x ATR | backtest.py lines 87, 102 |
| TP | D 900 pts, R 1000 pts | backtest.py lines 86, 101 |
| Partial | 50% at 1.0 x ATR, then breakeven | exit_sim.py; backtest.py lines 88, 103-104 |
| IS fraction | 0.70 by count | run.py line 122 |
| Veto K (opposing unswept level within K x ATR) | 0.5, 1.0 (headline), 1.5, 2.0 | [backtest_report.md](../../../originals/gann_bot_500/research/dr_backtest/backtest_report.md) lines 46-68 |
| Variant B trend-day flag | closed-bar directionality > 0.6 | run_variants.py docstring |
| Variant C5 ADX | Wilder ADX(14) on H4 >= 25 | [run_adx_arm.py](../../../originals/gann_bot_500/research/dr_backtest/run_adx_arm.py) docstring |

## Costs
None. No spread, commission or slippage is deducted (variants_report.md line 37; backtest_report.md line 14). The audit later applied the goldbot cost matrix to the stored trades (median and p90 spread, slippage 0.5 x spread per side, $7 per lot) in [dr_matrix.py](../../../audit/phaseC/dr_matrix.py); average cost about 105 points per trade at the median ([dr_matrix.json](../../../audit/phaseC/dr_matrix.json)).

## Tuning and selection
- Search: (1) base D and R; (2) 1-per-zone-per-day throttle on D and R ([backtest_1perzone_report.md](../../../originals/gann_bot_500/research/dr_backtest/backtest_1perzone_report.md)); (3) TP 1000 for D and R ([backtest_tp10_report.md](../../../originals/gann_bot_500/research/dr_backtest/backtest_tp10_report.md)); (4) variant arms on both profiles: A baseline, B wick acceptance on trend days, C1 Gann levels off, C2 Fibonacci retracements off, C3 Fibonacci pivots off, C4 H4 bias off (variants_report.md lines 54-67; [run_variants.py](../../../originals/gann_bot_500/research/dr_backtest/run_variants.py)); (5) C5 ADX >= 25 on both profiles, with thresholds 15/20/30 descriptive only ([run_adx_arm.py](../../../originals/gann_bot_500/research/dr_backtest/run_adx_arm.py)); (6) veto screen at four K values on both profiles.
- Configurations run (counted from the code/results): 20 profile runs (one trade file each in the folder; R at TP 1000 reproduced base R trade for trade) and 8 veto cells. Ledger count (registry/trial_ledger.csv n_variants): 8. They differ; the ledger basis is "minimum, see entry".
- How the reported variant was chosen: the headline figures are the base run with the live configuration, not a selected variant. The veto K = 1.0 was declared as the headline before results (backtest_report.md line 46). Variant B had a written four-condition go/no-go rule (variants_report.md lines 82-92).
- Preregistered: no (registry). Only the veto headline K and the variant B rule were fixed in advance inside the reports.

## Results
Points per trade, no costs unless stated.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored D, all / IS / OOS | 1,351 / 946 / 405 | PF 1.326 / 1.409 / 1.241; report flags none | [backtest_report.md](../../../originals/gann_bot_500/research/dr_backtest/backtest_report.md) lines 28-38 |
| Stored R, all / IS / OOS | 1,012 / 708 / 304 | PF 1.06 / 1.078 / 1.042; flagged below 1.20 IS and OOS | backtest_report.md lines 31-42 |
| Stored D, 1 per zone per day | 1,112 | PF 1.368 | backtest_1perzone_report.md |
| Stored R, 1 per zone per day | 791 | PF 1.018 | backtest_1perzone_report.md |
| Stored D at TP 1000 | 1,351 | PF 1.312 | backtest_tp10_report.md |
| Variant A (2016-2026), D OOS / R OOS | 949 / 704 | PF 1.316 / 1.061 | variants_report.md line 56-57 |
| Variant B, D and R | see report | NO-GO on its own rule for both | variants_report.md lines 90-92 |
| Veto K = 1.0, D vetoed / R vetoed | 77 / 125 | PF 1.043 (INSUFFICIENT SAMPLE) / 1.189 | backtest_report.md lines 55, 66 |
| Audit rerun, recorded clock | D 1,353 / R 1,013 entries | matches stored | [logs_L1/recorded.run.log](../../../audit/phaseC/logs_L1/recorded.run.log) |
| Audit rerun, true UTC | D 1,308 / R 1,026 entries | PF not in any published output | [logs_L1/true.run.log](../../../audit/phaseC/logs_L1/true.run.log) |
| Audit, D with matrix median cost, recorded / true | 1,352 / 1,308 | PF 0.974 / 1.099 | [dr_matrix.json](../../../audit/phaseC/dr_matrix.json) |
| Audit, D with p90 cost, true | 1,308 | PF 1.001 | dr_matrix.json |
| Audit, R with matrix median cost, recorded / true | 1,013 / 1,026 | PF 0.819 / 0.78 | dr_matrix.json |

## Code and how to rerun
- Code: [run.py](../../../originals/gann_bot_500/research/dr_backtest/run.py), [backtest.py](../../../originals/gann_bot_500/research/dr_backtest/backtest.py), [exit_sim.py](../../../originals/gann_bot_500/research/dr_backtest/exit_sim.py), [polarity_pure.py](../../../originals/gann_bot_500/research/dr_backtest/polarity_pure.py), [veto_screen.py](../../../originals/gann_bot_500/research/dr_backtest/veto_screen.py), [run_1pz.py](../../../originals/gann_bot_500/research/dr_backtest/run_1pz.py), [run_tp10.py](../../../originals/gann_bot_500/research/dr_backtest/run_tp10.py), [run_variants.py](../../../originals/gann_bot_500/research/dr_backtest/run_variants.py), [variants.py](../../../originals/gann_bot_500/research/dr_backtest/variants.py), [run_adx_arm.py](../../../originals/gann_bot_500/research/dr_backtest/run_adx_arm.py). Live modules it imports: [levels.py](../../../originals/gann_bot_500/levels.py), [signals.py](../../../originals/gann_bot_500/signals.py), [structure.py](../../../originals/gann_bot_500/structure.py), [config.py](../../../originals/gann_bot_500/config.py). Audit: [run_dr_flip.sh](../../../audit/phaseC/run_dr_flip.sh), [dr_matrix.py](../../../audit/phaseC/dr_matrix.py).
- Audit rerun stage: `dr_flip` (run.py on both clocks) and `c_dr_matrix` (costs) ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)). The variant, throttle, TP 1000 and ADX runs are not rerun by any stage.
- Public data enough? Yes for run.py: manifest group `histdata_xau`.

## Corrections from the release review
- README "Original verdict: FAILED" is wrong as a record of the original. The original report found no flags for D (IS PF 1.409, OOS 1.241, both above its 1.20 threshold) and called D "real edge"; only R was flagged (backtest_report.md lines 35-42, 80-81). FAILED is the audit's later verdict, based on the missing spread.
- README "Rerun, true UTC: D n=1307 PF 1.505; R n=1025 PF 1.014" had no saved evidence when the review began: [dr_flip.out](../../../audit/phaseC/dr_flip.out) is empty and the stage logs give only signal counts (1,308 and 1,026). The true-UTC run's own report is now saved as [true.dr_backtest_report.md](../../../audit/phaseC/logs_L1/true.dr_backtest_report.md) and confirms n=1,307 PF 1.505 and n=1,025 PF 1.014, after one ambiguous trade per profile is dropped (audit DECISIONS 63). The figure is unchanged.
- README "Parameters and tuning: 2 profiles, variants A/B/C1-C4" omits the throttle runs, the TP 1000 runs, the C5 ADX arm and the four veto K values. 20 profile runs exist (trade files in the folder). The ledger counts 8.
- README "Rules: Every H1 close passing six gates is one entry" does not define the gates. The code checks zone membership, zone side (with polarity for D), H4 bias and H1 close confirmation (signals.py lines 180-274); the "six gates" are never listed in a published file.
- README "Data: HistData M1 2021-06-19 to 2026-06-19" holds only for the base run. The variant runs use 2016-01-01 to 2026-06-19 (variants_report.md lines 45-50).
- README gives no exit rules. Exits are SL 1.0/1.5 x ATR, TP $9/$10 fixed, 50% partial at 1 x ATR then breakeven (backtest.py lines 82-110).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | D ALL n=1351 PF 1.326; R ALL n=1012 PF 1.06 |
| Rerun, recorded clock | D n=1351 PF 1.326; R n=1012 PF 1.06 |
| Rerun, true UTC | D n=1307 PF 1.505; R n=1025 PF 1.014 |

## Verdict
VERIFIED-WITH-CORRECTIONS. No spread in the original. D at matrix cost: 0.974 recorded, 1.099 true, 1.001 true at p90. Unthrottled and overlapping, so not a strategy. Remains FAILED.

## Audit caveats
No spread modelled and fixed-point TPs calibrated to the current regime. Superseded by D-REVIVAL.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/research/dr_backtest/backtest_report.md](../../../originals/gann_bot_500/research/dr_backtest/backtest_report.md)
- [originals/gann_bot_500/research/dr_backtest/variants_report.md](../../../originals/gann_bot_500/research/dr_backtest/variants_report.md)
