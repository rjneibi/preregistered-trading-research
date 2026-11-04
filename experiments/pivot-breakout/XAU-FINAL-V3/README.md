# XAU-FINAL-V3

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-02. A verdict grades the stored claim, not the strategy.

**Hypothesis:** H4 flips with 1% risk and DD governor have edge.

Family: pivot/breakout. Market: XAUUSD. Timeframe: H4. Idea source: own + Fable optimisation.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
FINAL_v3 is the "conservative arm" of the author's gold pivot-breakout work from 2026-07-02. It enters at market when an H4 candle closes beyond the prior UTC day's R3 or S3, at the 12:00, 16:00 or 20:00 UTC closes only. It skips Mondays and takes at most one trade a day. It exits at TP 1.4 x ATR, SL 2.1 x ATR or after 24 hours. The audit regenerated the trades on the recorded HistData clock and on true UTC.

## Instruments and data
- Instruments: XAUUSD, 1 lot = 100 oz ([fable-backtesting/analysis_scripts/final_v3.py:47](../../../originals/gann_bot_500/fable-backtesting/analysis_scripts/final_v3.py), "pts at 1 lot -> $ = pts").
- Timeframe(s): M1 bars resampled to H1, H4 and UTC D1 ([audit/phaseC/fable_both.py:36-38](../../../audit/phaseC/fable_both.py)).
- Data source and file(s): HistData.com XAUUSD M1 bid, `research/data/xauusd_m1_histdata.csv` (`load_m1`, [run_flip_scalp.py:21-22,69-72](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py); [data/manifest.csv](../../../data/manifest.csv) line 428, group `histdata_xau`).
- Period: trades 2015-06-19 to 2026-06-19 17:57 UTC, in two eras: old 2015-06-19 to 2021-06-18, new 2021-06-19 to 2026-06-19 ([fable_both.py:20](../../../audit/phaseC/fable_both.py); [final_v3.py:18-26](../../../originals/gann_bot_500/fable-backtesting/analysis_scripts/final_v3.py)). M1 is loaded from 60 days before each era start.
- In-sample / out-of-sample: the exit geometry was first tuned on TRAIN = first 70% of 2021-26 trades (n=173) and checked on TEST = last 30% (n=74). 2015-21 was called the "virgin holdout" ([optimization_report.md:5-12](../../../originals/gann_bot_500/fable-backtesting/optimization_report.md)). Later rounds, including the ATR exits and the session filter that define FINAL_v3, were judged on both eras, so 2015-21 was used for selection ([optimization_report.md:93-100,130-138](../../../originals/gann_bot_500/fable-backtesting/optimization_report.md)).

## Rules
- Entry: daily zones are built at UTC 00:00 from the live bot's level code. R3 = PP + 1.000 x (H - L) and S3 = PP - 1.000 x (H - L) of the prior UTC day ([levels.py:65-88](../../../originals/gann_bot_500/levels.py); [run_flip_scalp.py:138-139](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py)). A level is "dead" for the day if any of the last 10 completed H4 closes before 00:00 was already beyond it ([run_flip_scalp.py:151-166](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py)). An H4 close above a live resistance gives BUY; below a live support gives SELL. Entry is at the open of the first M1 bar at the H4 close time ([run_flip_scalp.py:199-224](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py); [innovate_r3s3.py:92-100](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py)).
- Exit (stop, target, time): TP = fill + 1.4 x ATR, SL = fill - 2.1 x ATR (mirrored for sells), close at the M1 close 24 hours after fill ([fable_both.py:57](../../../audit/phaseC/fable_both.py); [innovate_r3s3.py:53-89](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py)). If stop and target are both touched in one M1 bar, the stop is taken (line 83).
- Filters: events must involve R3 or S3 and not fall on Monday ([regime_switch.py:95-99](../../../originals/gann_bot_500/fable-backtesting/regime_switch.py)). Only H4 closes at 12:00, 16:00, 20:00 UTC. First event per UTC day only ([fable_both.py:50-56](../../../audit/phaseC/fable_both.py)).
- Position sizing: all reported figures are fixed 1 lot. The spec's "1% equity risk, halved while equity is under 95% of peak" sizing is applied only in a separate equity curve in [final_v3.py:54-65](../../../originals/gann_bot_500/fable-backtesting/analysis_scripts/final_v3.py) ($30k start). The audit did not rerun that curve.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Pivot R3/S3 | PP ± 1.000 x prior-day range, rounded to 2 dp | levels.py:77-87 |
| ATR | Wilder ATR(14) on H1, value of the last H1 bar closed before 00:00 UTC | run_flip_scalp.py:133-138; fable_both.py:38 |
| Dead-level check | last 10 completed H4 closes before the day | run_flip_scalp.py:151-166 |
| TP / SL | 1.4 x ATR / 2.1 x ATR | fable_both.py:57 |
| Time stop | 24 h | innovate_r3s3.py:92 (`ts_h=24`) |
| Session | H4 closes at 12, 16, 20 UTC | fable_both.py:50 |
| Other zone inputs (built but filtered out) | Gann degrees 45-360, fib 0.382-0.786, ATR zone width 0.3, swing lookback 50 H4 | run_flip_scalp.py:84-89 |

## Costs
20 points ($0.20 per oz, $20 per lot) per round trip, flat: "13 pts observed live spread + 7 pts commission" ([run_flip_scalp.py:40-41](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py); `COST = 20.0` in [innovate_r3s3.py:36,84-89](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py)). Fills are at the bid M1 open, with no separate spread. No swap.

## Tuning and selection
- Search: in `tune_r3s3.py` the author tried about 22 exit variants on TRAIN (TP10/SL10, TP8/SL12, ATR-scaled, time stops, breakeven at +$5). TP $8 / SL $12 / 24h was kept ([optimization_report.md:12-38,57](../../../originals/gann_bot_500/fable-backtesting/optimization_report.md)). Later rounds added: the session filter at 12/16/20 UTC (round 3c), then one trade a day, ATR exits 1.4/2.1 "same 1:1.5 geometry", equity sizing and a loss-streak throttle (round 4, `adaptive_v3.py`) ([optimization_report.md:100-138](../../../originals/gann_bot_500/fable-backtesting/optimization_report.md)).
- Configurations run (counted from the code/results): 1 for this entry (fable_both.py runs one rule). Ledger count (registry/trial_ledger.csv n_variants): 1, basis "minimum, see entry". The search behind it is in other ledger rows: GB-22 (about 22 train variants, n_variants recorded as 1), GB-16, GB-25, GB-32. The true count is larger than 1, and these rows do not give it.
- How the reported variant was chosen: by hand, from the results of each round. The 1.4/2.1 ATR exit is the ATR form of the train-chosen TP8/SL12. It and the session filter were accepted after looking at both eras, including 2015-21, so the "virgin" era was used for selection.
- Preregistered: no.

## Results
All figures 1 lot, 20-pt cost.
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Recorded clock, old 2015-06..2021-06 | 243 | PF 1.244, net $11,466, win 65% | [fable_recorded.json](../../../audit/phaseC/fable_recorded.json) |
| Recorded clock, new 2021-06..2026-06 | 189 | PF 2.005, net $59,130, win 71.4% | same |
| Recorded clock, pooled | 432 | PF 1.667, net $70,596, maxDD $6,935 | same |
| Recorded clock, 2025 | 33 | PF 1.859, net $13,260. INSUFFICIENT SAMPLE | same |
| True UTC, old | 240 | PF 1.066, net $3,329, win 61.7% | [fable_true.json](../../../audit/phaseC/fable_true.json) |
| True UTC, new | 196 | PF 1.371, net $30,191, win 66.3% | same |
| True UTC, pooled (headline) | 436 | PF 1.254, net $33,520, maxDD $14,959 | same |
| True UTC, 2025 | 32 | PF 1.207, net $4,170. INSUFFICIENT SAMPLE | same |
| Second engine (nbe), recorded / true | 432 / 436 | 428 / 427 trades within 50c; PF 1.754 / 1.329; net differs by 13.9% / 30.1% (gap policy) | [spot_checks.json](../../../audit/trade_checks/spot_checks.json) |

The regenerated recorded-clock events match the stored signal lists exactly: 1,385 of 1,385 (old) and 1,262 of 1,262 (new) keys (fable_recorded.json, `ev`). Trade-level spot check: [FINAL-v3-true-utc.csv](../../../audit/trade_checks/FINAL-v3-true-utc.csv), [png](../../../audit/trade_checks/FINAL-v3-true-utc.png).

## Code and how to rerun
- Code: original [final_v3.py](../../../originals/gann_bot_500/fable-backtesting/analysis_scripts/final_v3.py), [adaptive_v3.py](../../../originals/gann_bot_500/fable-backtesting/adaptive_v3.py), [innovate_r3s3.py](../../../originals/gann_bot_500/fable-backtesting/innovate_r3s3.py), [run_flip_scalp.py](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py), [levels.py](../../../originals/gann_bot_500/levels.py). Audit rebuild: [fable_both.py](../../../audit/phaseC/fable_both.py). Write-ups: [optimization_report.md](../../../originals/gann_bot_500/fable-backtesting/optimization_report.md), [MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md).
- Audit rerun stage: `fable_recorded` and `fable_true` ([run_all.sh:35](../../../audit/tools/run_all.sh)); trade outputs `fable_v3_recorded.csv`, `fable_v3_true.csv`. Engine cross-check: `cross_engines`, `spot`.
- Public data enough? Partly. `fable_true` needs only group `histdata_xau`. `fable_recorded` is a broker-tier stage ([stages_broker.txt](../../../audit/tools/stages_broker.txt)) because it also opens the unpublished `flip_events` lists for the key comparison ([outputs_broker.txt](../../../audit/tools/outputs_broker.txt) lines 7-9).

## Corrections from the release review
- "Data: HistData M1 XAUUSD 2010-2026" is misleading. The FINAL_v3 trades cover 2015-06-19 to 2026-06-19 (fable_both.py:20). 2010-15 was a separate probe (ledger GB-35).
- "Rules: TP 1.4xATR, SL 2.1xATR, 24h stop" leaves out the entry. The entry is an H4 close beyond an un-breached prior-UTC-day R3/S3 (PP ± range), at 12/16/20 UTC only, no Mondays, one a day (MASTER_SUMMARY.md:19-22; fable_both.py:50-57).
- "Variants counted in the ledger: 1" hides the search. The geometry is the ATR form of TP8/SL12, chosen from about 22 train variants (optimization_report.md:57; ledger GB-22). The session filter and ATR exits were accepted after looking at 2015-21. Selection used the era later called out of sample.
- "1% risk and DD governor" in the hypothesis: every stored and rerun result is fixed 1 lot. The sizing appears only in an unaudited curve in final_v3.py:54-65.
- "Splits: train/test/virgin" without dates. TRAIN/TEST are 70/30 of 2021-26 trades; "virgin" is 2015-06-19 to 2021-06-18 (optimization_report.md:7-12).
- "Source: own + Fable optimisation" is never explained on the page. The only matching published name is the original research folder, `originals/gann_bot_500/fable-backtesting`; what "Fable" refers to is not recorded in the published files.
- The recorded-clock column cannot be regenerated from public data; the true-UTC column can (outputs_broker.txt:7-9).
- The README links no code. The scripts above are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 2021-26 PF 2.00; 2015-21 PF 1.24; pooled PF 1.67 |
| Rerun, recorded clock | n=432 PF 1.667, net $70,596, DD $6,935 |
| Rerun, true UTC | n=436 PF 1.254, net $33,520, DD $14,959 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Second engine 428/432 and 427/436 trades within 50c; net differs by gap policy. Spot checks 20/20. Headline is the true-UTC column.

## Audit caveats
Same issues as V4. H-B arm B binding FAIL.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md)
