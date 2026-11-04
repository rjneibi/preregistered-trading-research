# XAU-R3S3-FADE

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-02. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Fading R3/S3 has positive expectancy.

Family: pivot/mean-reversion. Market: XAUUSD. Timeframe: H1. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The claim is that fading gold's R3/S3 pivot extensions (selling at R3, buying at S3) has positive expectancy. The original fade tests left no code or numbers. The only record is the ledger line "breakout accepted, fade rejected" ([PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md), Trials Ledger row 10) and a docstring in an unimplemented placeholder. The audit therefore rebuilt the fade: it took the FINAL_v3 breakout entries, reversed their direction, and applied the FINAL_v3 and FINAL_v4 exit geometries ([audit/phaseC/fade_both.py](../../../audit/phaseC/fade_both.py) line 1).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): the entries are FINAL_v3's H4 closes at 12, 16 and 20 UTC ([audit/phaseC/fable_both.py](../../../audit/phaseC/fable_both.py) line 50). Exits are simulated on M1. H1 is used only for ATR.
- Data source and file(s): HistData M1 XAUUSD, `gann_bot_500/research/data/xauusd_m1_histdata.csv` ([data/manifest.csv](../../../data/manifest.csv) line 428, group `histdata_xau`), plus a clock-corrected copy for true UTC ([audit/phaseC/sandbox_fable.py](../../../audit/phaseC/sandbox_fable.py) line 9). Entry lists: [fable_v3_true.csv](../../../audit/phaseC/fable_v3_true.csv) and [fable_v3_recorded.csv](../../../audit/phaseC/fable_v3_recorded.csv).
- Period: 2015-06-19 to 2026-06-19 ([fable_both.py](../../../audit/phaseC/fable_both.py) line 20). M1 is loaded from 5 days before the first entry to 5 days after the last, per era ([fade_both.py](../../../audit/phaseC/fade_both.py) lines 33-35).
- In-sample / out-of-sample: two eras, reported separately. Old = 2015-06-19 to 2021-06-18. New = 2021-06-19 to 2026-06-19. Nothing was tuned in the rebuild.

## Rules
- Entry (audit rebuild): take each FINAL_v3 event and reverse it. FINAL_v3 events are H4 closes beyond an unflipped R3 or S3, from the stored flip-event scan, filtered to R3/S3 sources and no Mondays ([regime_switch.py](../../../originals/gann_bot_500/fable-backtesting/regime_switch.py) lines 95-99). Only closes at 12, 16 or 20 UTC are kept, first per day ([fable_both.py](../../../audit/phaseC/fable_both.py) lines 50-56). A close above R3 becomes SELL. A close below S3 becomes BUY ([fade_both.py](../../../audit/phaseC/fade_both.py) lines 26, 37). The fill is at the open of the first M1 bar at or after the H4 close (`SimX.run` in [innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py)).
- Exit (stop, target, time): "V3 geometry": TP 1.4 × ATR, SL 2.1 × ATR. "V4 geometry": TP 0.8 × ATR, SL 2.4 × ATR. Both use a 24 h time stop, and the stop wins when stop and target fall in the same M1 bar ([fade_both.py](../../../audit/phaseC/fade_both.py) line 27; innovate_r3s3.py `_leg`). ATR is recovered as the stored V3 TP divided by 1.4 (fade_both.py line 31).
- Filters: no Mondays; 12/16/20 UTC H4 closes; 1 per day; dead-level check over the last 10 H4 closes ([run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) line 152).
- Position sizing: fixed 1.00 lot. P&L = price move × 100 minus cost (innovate_r3s3.py `_leg`).
- Original attempts: the rules, number and results of the author's original fade tests are not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| R3 / S3 | PP ± 1.000 × (H − L), prior UTC day | [levels.py](../../../originals/gann_bot_500/levels.py) lines 65-91 |
| ATR | Wilder ATR(14) on H1, at day build | [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) lines 134-138, 328 |
| Dead-level check | 10 H4 closes before the day | run_flip_scalp.py line 152 |
| Session | H4 closes at 12, 16, 20 UTC | fable_both.py line 50 |
| V3 geometry | TP 1.4 / SL 2.1 × ATR | fade_both.py line 27 |
| V4 geometry | TP 0.8 / SL 2.4 × ATR | fade_both.py line 27 |
| Time stop | 24 h | innovate_r3s3.py `ts_h=24` |

## Costs
A flat 20 points ($0.20) per round trip at 1 lot ([innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py) line 36). No slippage.

## Tuning and selection
- Search: none in the rebuild. Two geometries were run, each taken unchanged from the breakout rules.
- Configurations run (counted from the code/results): 2 (V3 and V4 geometry) × 2 eras ([fade_true.json](../../../audit/phaseC/fade_true.json)). Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 63, n_variants): 1. They differ because the ledger counts the original idea, while the audit rebuild ran 2 geometries. The original attempt count is UNVERIFIED (README caveat).
- How the reported variant was chosen: no variant was chosen. The README headline uses the V3 geometry.
- Preregistered: no. The [spec.md](../../../experiments/pivot-mean-reversion/XAU-R3S3-FADE/spec.md) on the page is the H1/H2 goldbot preregistration. It is not a fade spec. The fade appears there only as ledger row 10.

## Results
All rows: audit rebuild, 1 lot, 20-point cost.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored | none recorded | "breakout accepted, fade rejected" | [PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md) ledger row 10 |
| Recorded clock, V3 geometry, pooled | 432 | PF 0.651, win 50.7%, net -$65,984 | [audit/phaseC/fade_recorded.json](../../../audit/phaseC/fade_recorded.json) |
| Recorded clock, V4 geometry, pooled | 432 | PF 0.556, win 66.0%, net -$71,023 | same |
| True UTC, V3 geometry, pooled | 436 | PF 0.736, win 53.0%, net -$47,526 | [audit/phaseC/fade_true.json](../../../audit/phaseC/fade_true.json) |
| True UTC, V3 geometry, old / new | 240 / 196 | PF 0.800 / 0.704 | same |
| True UTC, V4 geometry, pooled | 436 | PF 0.594, win 66.3%, net -$63,187 | same |
| True UTC, V4 geometry, old / new | 240 / 196 | PF 0.762 / 0.523 | same |

Every slice loses on both clocks. Verdict: original FAILED; audit VERIFIED-WITH-CORRECTIONS ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 22).

## Code and how to rerun
- Code: [audit/phaseC/fade_both.py](../../../audit/phaseC/fade_both.py). It reads the V3 entries written by [audit/phaseC/fable_both.py](../../../audit/phaseC/fable_both.py) and uses [innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py), [regime_switch.py](../../../originals/gann_bot_500/fable-backtesting/regime_switch.py) and [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py). The placeholder [pivots.py](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py) (lines 62-75) raises NotImplementedError.
- Audit rerun stage: `sb_fable`, `fable_true` then `fade_true` (public); `fable_recorded` then `fade_recorded` (broker list) ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh) lines 18, 35).
- Public data enough? Yes for true UTC, with the `histdata_xau` group. No for the recorded clock, because `fable_recorded` reads the unpublished `flip_events` group ([data/manifest.csv](../../../data/manifest.csv) lines 431-432).

## Corrections from the release review
- "Rules: Fade at R3/S3, as shipped in the pivots.py placeholder" is wrong. The placeholder implements nothing and raises NotImplementedError ([pivots.py](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py) lines 62-75). The figures come from the audit rebuild in [fade_both.py](../../../audit/phaseC/fade_both.py): FINAL_v3 entries with their direction reversed.
- "Timeframe: H1" is wrong. The rebuilt entries are H4 closes at 12/16/20 UTC. The "V4 geometry" rows reuse those H4 entries with V4's exits, not V4's H1 entries.
- "Data: HistData M1 XAUUSD 2010-2026" is wrong. The trades run 2015-06-19 to 2026-06-19 ([fable_both.py](../../../audit/phaseC/fable_both.py) line 20).
- The results give PFs with no n. The recorded clock has n=432 and true UTC has n=436. The README also leaves out the V4-geometry rows (0.556 and 0.594).
- The page's spec.md is the H1/H2 goldbot preregistration, not a fade specification.
- "Splits: 11 years" is a docstring phrase. The rebuild reports two eras, 2015-21 and 2021-26.
- The page does not link the rebuild code ([fade_both.py](../../../audit/phaseC/fade_both.py)) or its outputs.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Rejected; ledger row 10 reads 'breakout accepted, fade rejected' |
| Rerun, recorded clock | V3 geometry PF 0.651 |
| Rerun, true UTC | PF 0.736 |

## Verdict
VERIFIED-WITH-CORRECTIONS. No harness survives. L2 rebuild on V3 entries confirms the rejection.

## Audit caveats
The digest says fades failed OOS gates twice in flip_bot.py. Disk shows the rejection but no per-attempt numbers, and flip_bot is the breakout bot. Attempt count UNVERIFIED.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md)
- [originals/gann_bot_500/research/goldbot/README.md](../../../originals/gann_bot_500/research/goldbot/README.md)
