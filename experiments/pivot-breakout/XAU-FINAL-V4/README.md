# XAU-FINAL-V4

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-02. A verdict grades the stored claim, not the strategy.

**Hypothesis:** H1 close beyond an unflipped R3/S3 in 12-20 UTC, no Mondays, 1/day, has edge.

Family: pivot/breakout. Market: XAUUSD. Timeframe: H1. Idea source: own + Fable optimisation. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
FINAL_v4 is the "high-win-rate arm" of the author's zone-flip programme on gold. It buys on the first H1 close above the prior UTC day's R3, or sells on the first H1 close below S3, between 12:00 and 20:00 UTC, with no Mondays and at most one trade a day. Exits are a small ATR target, a wide ATR stop and a 24 h time stop ([MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md) lines 7-17). The audit rebuilt the trades on the recorded clock and on true UTC.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): H1 closes for signals. H4 closes for the dead-check. Daily bars cut at UTC 00:00 for pivots. M1 for exit simulation ([audit/phaseC/fable_both.py](../../../audit/phaseC/fable_both.py) lines 37-38, 62-92).
- Data source and file(s): HistData M1 XAUUSD, `gann_bot_500/research/data/xauusd_m1_histdata.csv` ([data/manifest.csv](../../../data/manifest.csv) line 428, group `histdata_xau`). The true-UTC run uses a clock-corrected copy ([audit/phaseC/sandbox_fable.py](../../../audit/phaseC/sandbox_fable.py) line 9; [audit/findings/CLOCK_BUG.md](../../../audit/findings/CLOCK_BUG.md)).
- Period: 2015-06-19 to 2026-06-19 17:57 UTC, in two eras ([fable_both.py](../../../audit/phaseC/fable_both.py) line 20). M1 is loaded from 60 days before each era start (line 36). The 2010-15 window was a separate probe (ledger row 35 in [PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md)), not part of these results.
- In-sample / out-of-sample: tuning era "new" = 2021-06-19 to 2026-06-19. Validation era "old" = 2015-06-19 to 2021-06-18 ([bimodal_v4.py](../../../originals/gann_bot_500/fable-backtesting/bimodal_v4.py) docstring lines 2-8 and lines 37-43). MASTER_SUMMARY says "eras consulted repeatedly" (methodology section). The old era is therefore not a clean holdout.

## Rules
- Entry: zones are built at each UTC day open with the live zone builder. Only the R3 and S3 zones are kept, and only if none of the last 10 H4 closes before the day breached them. Each H1 bar whose close time falls between 12:00 and 20:00 UTC is checked. A close above R3 is BUY. A close below S3 is SELL. Mondays are skipped. Only the first hit of the day is traded. The fill is at the open of the first M1 bar at or after the H1 close ([h1_2026_test.py](../../../originals/gann_bot_500/fable-backtesting/h1_2026_test.py) lines 31-69; [fable_both.py](../../../audit/phaseC/fable_both.py) lines 62-92; [innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py) `SimX.run`).
- Exit (stop, target, time): TP = entry ± 0.8 × ATR. SL = entry ∓ 2.4 × ATR. Close at market at 24 h. If the stop and target fall in the same M1 bar, the stop is taken first ([innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py) `SimX._leg`, "conservative: stop first"). ATR is the H1 value at the day build.
- Filters: no Mondays; 12-20 UTC H1 closes; 1 trade per day; dead-level check.
- Position sizing: fixed 1.00 lot. P&L = price move × 100 minus cost ([innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py) `_leg`; MASTER_SUMMARY "+$21,768/lot"). The bail exits, ADX, news and equity-% sizing in [spec.md](../../../experiments/pivot-breakout/XAU-FINAL-V4/spec.md) §3 belong to the later v5.1 system. They are not part of FINAL_v4.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Pivot | PP = (H+L+C)/3 of the prior UTC day | [levels.py](../../../originals/gann_bot_500/levels.py) lines 65-91 |
| R3 / S3 | PP ± 1.000 × (H − L) | levels.py lines 84, 87 |
| ATR | Wilder ATR(14) on H1, last bar closed before the day open | [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) lines 134-138; [data_prep.py](../../../originals/gann_bot_500/research/dr_backtest/data_prep.py) `wilder_atr` |
| Dead-level check | 10 H4 closes before the day | run_flip_scalp.py line 152 |
| Session | H1 close hour 12-20 UTC inclusive | h1_2026_test.py line 46 |
| TP / SL multiples | 0.8 / 2.4 × ATR | MASTER_SUMMARY.md line 14; bimodal_v4.py line 27 |
| Time stop | 24 h (simulator horizon 120 h) | innovate_r3s3.py `ts_h=24`, `HORIZON_H = 120` (line 37) |
| Vol regime (tuning only) | ATR vs trailing 90-day median of H1 ATR (24 × 90 bars, min 200) | bimodal_v4.py line 51 |
| Zone width (live builder) | 0.3 × ATR | run_flip_scalp.py line 88 |

## Costs
A flat 20 points ($0.20) per round trip at 1 lot ([innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py) line 36, `COST = 20.0`). This is 13 points of spread plus 7 of commission ([run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) lines 40-41). No slippage. The audit also costed the true-UTC trades with an approximate per-hour spread matrix (entry hour used for both sides) and its p90 ([audit/stats/gate_table.py](../../../audit/stats/gate_table.py) line 48).

## Tuning and selection
- Search (round 7, [bimodal_v4.py](../../../originals/gann_bot_500/fable-backtesting/bimodal_v4.py)): four (TP, SL) ATR geometries, (1.4, 2.1), (1.0, 1.5), (1.0, 2.5) and (0.8, 2.4), each read on ALL, HIVOL and LOVOL in both eras, plus a 2025 line in the new era (lines 26-27, 97-107). The entry rule came from earlier rounds: R3/S3 only (ledger row 9), skip Monday (rows 4, 15), session filter (row 16), H1 granularity (row 13, [h1_flip_test.py](../../../originals/gann_bot_500/fable-backtesting/h1_flip_test.py)), ATR exits (row 25), all in [PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md).
- Configurations run (counted from the code/results): 4 geometries in the final round. The bimodal_v4.py output is not saved in the published files. Earlier rounds include the ~22-variant train grid in tune_r3s3 (ledger row 22) and others. Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 64, n_variants): 37. That 37 is the number of rows in the pre-July Trials Ledger. Those rows have "inner variants uncounted" (trial_ledger.csv GB rows), and several came after FINAL_v4 (for example the conviction rows 14 and 36). [audit/DECISIONS.md](../../../audit/DECISIONS.md) item 48 calls the family count (41) "a floor".
- How the reported variant was chosen: [bimodal_v4.py](../../../originals/gann_bot_500/fable-backtesting/bimodal_v4.py) line 7: "Tuning on NEW era per user; OLD era = validation". The stated goal was max win rate and few losers (line 3). The new era contains 2025, the headline year. The choice among the four geometries was made by hand from printed output. No written criterion is published.
- Preregistered: no ([experiments/pivot-breakout/XAU-FINAL-V4/README.md](../../../experiments/pivot-breakout/XAU-FINAL-V4/README.md)). No gate was set for V4. The audit applied the programme gate PF ≥ 1.20 ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 98).

## Results
All rows: 1 lot. The flat 20-point cost applies unless stated.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored 2025 | 51 | 86.3% win, PF 2.90, +$21,768. INSUFFICIENT SAMPLE | [MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md) lines 15-17 |
| Stored 2021-26 | n not stated in the stored file (rerun: 247) | 79.4% win, PF 1.40, $30,448 | same |
| Stored 2015-21 | n not stated in the stored file (rerun: 318) | 78.6% win, PF 1.21, $9,427 | same |
| Rerun, recorded clock, pooled | 565 | PF 1.331, net $39,875, max DD $10,992 | [audit/phaseC/fable_recorded.json](../../../audit/phaseC/fable_recorded.json) |
| Rerun, recorded clock, old / new | 318 / 247 | PF 1.212 / 1.400 | same |
| Rerun, recorded clock, 2025 | 51 | 86.3% win, PF 2.901. INSUFFICIENT SAMPLE | same |
| Rerun, true UTC, pooled | 577 | PF 1.145, win 76.9%, net $20,185, max DD $13,015 | [audit/phaseC/fable_true.json](../../../audit/phaseC/fable_true.json) |
| Rerun, true UTC, old / new | 322 / 255 | PF 1.053 / 1.196 | same |
| Rerun, true UTC, 2025 | 52 | 76.9% win, PF 1.128. INSUFFICIENT SAMPLE | same |
| True UTC, approximate matrix cost | 577 | PF 0.899 (p90: 0.843) | [audit/stats/gate_table.json](../../../audit/stats/gate_table.json); [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 98 |
| E4-NEWS frozen cost basis | n not given in VERDICTS | PF 0.898 | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 86 |
| Silver transfer (E2) | n not given in VERDICTS | PF 0.450 | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 84 |

The recorded-clock rerun regenerated the stored flip events exactly: 1385 old-era and 1262 new-era events, all keys matching ([fable_recorded.json](../../../audit/phaseC/fable_recorded.json) `ev`). Deflated Sharpe: primary 0.0, secondary 0.12 at family N 41 ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 116). Verdict: original FAILED; audit VERIFIED-WITH-CORRECTIONS (line 23).

## Code and how to rerun
- Code: [h1_2026_test.py](../../../originals/gann_bot_500/fable-backtesting/h1_2026_test.py) (the original V4 loop), [bimodal_v4.py](../../../originals/gann_bot_500/fable-backtesting/bimodal_v4.py) (geometry choice), [innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py) (SimX), [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) (zone builder), [levels.py](../../../originals/gann_bot_500/levels.py). Audit rebuild: [audit/phaseC/fable_both.py](../../../audit/phaseC/fable_both.py), trades in [fable_v4_true.csv](../../../audit/phaseC/fable_v4_true.csv) and [fable_v4_recorded.csv](../../../audit/phaseC/fable_v4_recorded.csv). Logs: [fable_true.log](../../../audit/phaseC/logs_L1/fable_true.log), [fable_recorded.log](../../../audit/phaseC/logs_L1/fable_recorded.log).
- Audit rerun stage: `sb_fable`, then `fable_true` (public) and `fable_recorded` (broker list); `gate` for the matrix-cost row ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh) lines 18, 35, 75).
- Public data enough? Yes for the true-UTC column, with the `histdata_xau` group. No for the recorded-clock column. `fable_recorded` reads the unpublished `flip_events` group ([data/manifest.csv](../../../data/manifest.csv) lines 431-432; [audit/tools/outputs_broker.txt](../../../audit/tools/outputs_broker.txt)).

## Corrections from the release review
- The headline "2025 n=51 86.3% WR PF 2.90" does not survive the clock fix. On true UTC, 2025 is n=52, 76.9%, PF 1.13 ([fable_true.json](../../../audit/phaseC/fable_true.json)). Both are INSUFFICIENT SAMPLE.
- "Data: HistData M1 XAUUSD 2010-2026" is wrong for these results. The trades run 2015-06-19 to 2026-06-19 ([fable_both.py](../../../audit/phaseC/fable_both.py) line 20).
- "17 optimisation rounds ... Variants counted in the ledger: 37" is misleading. FINAL_v4 is round 7 ([bimodal_v4.py](../../../originals/gann_bot_500/fable-backtesting/bimodal_v4.py) line 2; MASTER_SUMMARY "Seven optimization rounds"). The 37 ledger rows include later work and leave inner variants uncounted. Read it as "at least 37" ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 48).
- The page's [spec.md](../../../experiments/pivot-breakout/XAU-FINAL-V4/spec.md) is not the FINAL_v4 spec. It describes the later v5.1 conviction dual-arm system (bail exits, ADX/news sizing). The FINAL_v4 definition is [MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md) lines 7-17.
- "Killed at decision-grade costs by H1 and TA-LAB round 11" is wrong on both counts. H1 tests the conviction dual-arm system, not FINAL_v4. TA-LAB round 11 uses the classic floor R3 (`ph + 2*(p - pl)`), not FINAL_v4's PP + (H − L) level ([round11.py](../../../originals/gann_bot_500/research/ta_lab/round11.py) line 29). The direct evidence for FINAL_v4 at realistic cost is PF 0.899 on n=577 at approximate matrix cost ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 98) and PF 0.898 in E4-NEWS (line 86).
- "Splits: train/test/virgin 2015-21" overstates the split. For V4 the geometry was tuned on 2021-26, with 2015-21 as validation, and both eras were "consulted repeatedly" (MASTER_SUMMARY methodology).
- "Rerun, recorded clock: n=565 PF 1.331" cannot be regenerated publicly. It reads unpublished flip-event files ([audit/tools/outputs_broker.txt](../../../audit/tools/outputs_broker.txt)). The true-UTC row can be regenerated.
- The page does not link the code: [h1_2026_test.py](../../../originals/gann_bot_500/fable-backtesting/h1_2026_test.py), [bimodal_v4.py](../../../originals/gann_bot_500/fable-backtesting/bimodal_v4.py) and [fable_both.py](../../../audit/phaseC/fable_both.py).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 2025 n=51 86.3% WR PF 2.90; 2021-26 PF 1.40; 2015-21 PF 1.21 at 20 pts |
| Rerun, recorded clock | n=565 PF 1.331; 2025 n=51 86.3%, PF 2.90 |
| Rerun, true UTC | n=577 PF 1.145; 2025 n=52 76.9%, PF 1.13 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Second engine within 1.4%. The 86% year does not survive. Both 2025 slices are INSUFFICIENT SAMPLE.

## Audit caveats
Headline PF 2.90 is n=51 at a flat 20-pt cost and eras consulted repeatedly. TP 0.8 / SL 2.4 needs 75% wins to break even. Killed at decision-grade costs by H1 and TA-LAB round 11.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md)
- [originals/gann_bot_500/fable-backtesting/STRATEGY_SPECIFICATION.md](../../../originals/gann_bot_500/fable-backtesting/STRATEGY_SPECIFICATION.md)
