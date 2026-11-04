# E2-SILVER-TRANSFER

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Gold rules transfer unchanged.

Family: transfer test. Market: XAGUSD. Timeframe: M1. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The audit took the three headline gold rules and ran them on silver with no parameter changes. Silver was never used to design them, so the whole span is one test with no development slice. The question was whether the rules transfer unchanged. All three failed. Source: [spec.md](../../../experiments/transfer-test/E2-SILVER-TRANSFER/spec.md) lines 5-15.

## Instruments and data
- Instruments: XAGUSD.
- Timeframe(s): M1 bars; H1, H4 and UTC D1 bars are resampled from them for signals ([e2_silver.py](../../../audit/phaseE/e2_silver.py) line 73; [fable_xag.py](../../../audit/phaseE/fable_xag.py) line 37).
- Data source and file(s): Dukascopy XAGUSD M1 bid and ask by year, `audit/dk_xag/xagusd-{bid,ask}-<year>.csv` (manifest group `dukascopy_xag`, public, 26 files; [data/manifest.csv](../../../data/manifest.csv)). Flat zero-volume padding bars are dropped (e2_silver.py lines 33-35).
- Period: 2015-06-19 to 2026-10-29 (spec line 10; fable_xag.py line 20).
- In-sample / out-of-sample: none; the whole span is a single test (spec line 13). Two eras for the era gate: old 2015-06-19 to 2021-06-18, new 2021-06-19 on (fable_xag.py line 20; [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) line 41).

## Rules
- Entry:
  - H1: goldbot `final` variant, R3/S3 pivot breakout on H1 closes 12-20 UTC, Monday skipped, dead-level check on the last 10 H4 closes, 24 h re-entry block (e2_silver.py lines 57-75; [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 9-15).
  - FINAL_v3: regenerated flip events with entry hour 12, 16 or 20 UTC, first event per day, at the R3/S3 level (fable_xag.py lines 39, 50-59).
  - FINAL_v4: each non-Monday day, live R3/S3 zones that have not flipped; first H1 close from 12 to 20 UTC beyond a level (below support = sell, above resistance = buy); one trade per day (fable_xag.py lines 62-91).
- Exit (stop, target, time):
  - H1: TP 0.8 x ATR, SL 2.4 x ATR, 24 h time stop, bail on (half out at -1.2 ATR in high vol; all out at -1.0 ATR after 8 h in low vol); stops fill at the gap open (e2_silver.py line 75; config.yaml lines 21-29).
  - FINAL_v3: TP 1.4 x ATR, SL 2.1 x ATR (fable_xag.py line 57).
  - FINAL_v4: TP 0.8 x ATR, SL 2.4 x ATR (fable_xag.py line 88).
  - Time stop for v3/v4 is inside the original simulator `SimX` (fable_xag.py line 18). Its value is not stated in the audit files.
- Filters: as in the entry rules. No silver-specific filter.
- Position sizing: the rules' 100-oz unit, 1 lot (e2_silver.py lines 21-22). Dollar results per 100 oz.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | H1, 14, Wilder | e2_silver.py line 74; fable_xag.py line 38 |
| H1 TP / SL / time stop | 0.8 / 2.4 ATR / 24 h | config.yaml lines 22-24 |
| H1 bail | half at -1.2 ATR (high vol), all at -1.0 ATR after 8 h (low vol) | config.yaml lines 25-29 |
| FINAL_v3 TP / SL | 1.4 / 2.1 ATR | fable_xag.py line 57 |
| FINAL_v4 TP / SL | 0.8 / 2.4 ATR | fable_xag.py line 88 |
| Entry hours | v3: 12, 16, 20; v4 and H1: 12-20 UTC | fable_xag.py lines 50, 75; config.yaml line 11 |
| Gold-dollar constants | none reached; zone, TP and SL are ATR multiples | [e2_result.json](../../../audit/phaseE/e2_result.json) `constants` |

## Costs
- Spread: per-year x UTC-hour matrix built from silver M1 bar-close spreads (ask close - bid close, kept if between 0 and $1), median and p90 per bucket ([e2_silver.py](../../../audit/phaseE/e2_silver.py) lines 40-48; stored as [e2_xag_m1_matrix.json](../../../audit/phaseE/e2_xag_m1_matrix.json)). The spec notes M1 spreads understate peak spread inside a minute (spec line 11).
- Slippage: k_slip 0.5 x bucket spread per side (e2_silver.py lines 83-84).
- Commission: $7 per 5,000-oz lot, i.e. $0.14 per 100-oz unit (line 21).
- Night fee: $5 per 5,000-oz lot per night, i.e. $0.10 per unit, for trades crossing 22:00 UTC. Charged on H1 only (lines 22, 87, 90, 107).
- FINAL_v3 and v4: their pnl gets $20 added back before costs, so the silver costs replace a flat $20 (line 110). No exit time is saved, so the entry-hour spread is used on both sides and the night fee is left out ([e2_result.json](../../../audit/phaseE/e2_result.json) `note`).
- Stress columns: 1.5x and 2x median cost, and the p90 matrix (e2_silver.py lines 95-98).

## Tuning and selection
- Search: none. "No parameter changes" (spec line 8).
- Configurations run (counted from the code/results): 3 rules. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row AUD-E2, n_variants): 3, "exact". They agree. The ledger files E2 under the audit ID AUD-E2, not under E2-SILVER-TRANSFER.
- How the reported variant was chosen: not applicable; all three are reported.
- Preregistered: yes, [audit/prereg/E2-SILVER-TRANSFER.md](../../../audit/prereg/E2-SILVER-TRANSFER.md), under the shared rules frozen 2026-10-31 ([COMMON.md](../../../audit/prereg/COMMON.md)). One deviation is stated in the spec: the tick feed failed, so the cost matrix uses M1 spreads (spec line 11). A second is in the result file: v3/v4 twins reuse H1 holding times ([e2_result.json](../../../audit/phaseE/e2_result.json) `twin_note`).

## Results
All from [e2_result.json](../../../audit/phaseE/e2_result.json). Gates: PF >= 1.20, 2x-cost PF >= 1.00, each era PF >= 1.00, n >= 100, twin p < 0.05, p90 PF >= 1.00 (spec line 14).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| H1, net at median cost | 468 | PF 0.487 (gross 1.116, 2x 0.22, p90 0.372); twin p 0.225 | e2_result.json |
| H1, old / new era | 227 / 241 | PF 0.202 / 0.587 | e2_result.json |
| FINAL_v3, net | 410 | PF 0.683 (gross 1.157, 2x 0.388, p90 0.594); twin p 0.096 | e2_result.json |
| FINAL_v3, old / new era | 205 / 205 | PF 0.488 / 0.748 | e2_result.json |
| FINAL_v4, net | 576 | PF 0.450 (gross 0.969, 2x 0.211, p90 0.367); twin p 0.348 | e2_result.json |
| FINAL_v4, old / new era | 282 / 294 | PF 0.191 / 0.534 | e2_result.json |

Verdict: FAILED for all three. H1 trade list: [e2_h1_silver_trades.csv](../../../audit/phaseE/e2_h1_silver_trades.csv). v3/v4 trade lists: [fable_v3_xag.csv](../../../audit/phaseC/fable_v3_xag.csv), [fable_v4_xag.csv](../../../audit/phaseC/fable_v4_xag.csv).

## Code and how to rerun
- Code: [e2_silver.py](../../../audit/phaseE/e2_silver.py) (`prep`, then `score`), [fable_xag.py](../../../audit/phaseE/fable_xag.py), [lib.py](../../../audit/phaseE/lib.py) (twin test, PF), goldbot package [goldbot/](../../../originals/gann_bot_500/research/goldbot/goldbot/).
- Audit rerun stage: `e2_prep`, `e2_fable`, `e2_score` ([run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. It needs `dukascopy_xag` ([data/manifest.csv](../../../data/manifest.csv)). None of the E2 stages is in [stages_broker.txt](../../../audit/tools/stages_broker.txt).

## Corrections from the release review
- README "Night fees were not added". Wrong for H1. H1 is charged a $0.10 per-unit night fee for nights crossing 22:00 UTC (e2_silver.py lines 87, 90, 107). Only FINAL_v3 and v4 leave it out.
- README "`audit/phaseE` (not published)". Wrong. The folder is published: e2_silver.py, fable_xag.py, e2_result.json and the trade files.
- README verdict quotes PF without n. The counts are H1 n=468, FINAL_v3 n=410, FINAL_v4 n=576 (e2_result.json).
- README leaves out the cost approximation for v3/v4: the entry-hour spread is used on both sides (e2_result.json `note`).
- README "Rules / Costs / Splits / Gates: see prereg". The prereg states the gates and data but not the rule parameters. Those are in config.yaml lines 9-29 and fable_xag.py lines 50-91, as set out above.
- In e2_result.json the twin gate is stored as the string "False", not a boolean. It does not change the verdict.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All three FAIL. See audit/phaseE/e2_result.json. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. FAILED. H1 PF 0.487, FINAL_v3 0.683, FINAL_v4 0.450 at silver costs. Twins for FINAL rules reuse H1 holding times. Night fees were not added; all three fail before them.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
