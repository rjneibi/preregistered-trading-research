# H3-SILVER

**Audit verdict: VERIFIED.** Original verdict: NOT RUN. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** XAU/XAG spread diagnostic.

Family: transfer test. Market: XAUUSD/XAGUSD. Timeframe: see prereg. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author froze a preregistration on 2026-07-06, before any silver data was on disk. It asked whether the gold/silver log spread behaves as a mean-reverting (OU) process with a tradeable half-life, and whether a ±2 sigma reversion trade clears two-leg costs out of sample. The author never ran it. The audit ran it as frozen in Phase D on 2026-10-31. It failed the first gate, OU validity: the half-life is far longer than the 240-hour limit. By the decision tree, no trading numbers were computed. Sources: [H3_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/H3_PREREGISTRATION.md); [spec.md](../../../experiments/transfer-test/H3-SILVER/spec.md); [h3_result.json](../../../audit/phaseD/h3_result.json).

## Instruments and data
- Instruments: XAUUSD (1 lot = 100 oz gold leg) and XAGUSD (hedge leg) ([H3_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/H3_PREREGISTRATION.md) "Pinned protocol").
- Timeframe(s): H1 bars resampled from M1 ([spec.md](../../../experiments/transfer-test/H3-SILVER/spec.md) line 14; [h3_run.py](../../../audit/phaseD/h3_run.py) lines 53-58, 124).
- Data source and file(s): silver from Dukascopy ticks `fable-backtesting/download/xagusd-bi5-*.csv`, made into M1 bid bars (h3_run.py lines 22, 30-40; manifest group `dukascopy_ticks`, public, 93 files). Gold from HistData M1 `research/data/xauusd_m1_histdata.csv` (h3_run.py line 23; group `histdata_xau`, public), shifted to true UTC for the deciding run (lines 46-50) ([data/manifest.csv](../../../data/manifest.csv)).
- Period: common coverage 2015-03-01 23:00 to 2022-09-27 02:00 UTC; 44,144 H1 bars on true UTC, 43,076 on the recorded clock ([h3_result.json](../../../audit/phaseD/h3_result.json)). Silver ticks end 2022-09.
- In-sample / out-of-sample: IS = first 70% of bars, OOS = last 30% (prereg; h3_run.py lines 133-134). IS ends 2020-06-25 02:00 (true UTC) or 2020-06-23 00:00 (recorded).

## Rules
- Entry: z = (spread - mu) / (sigma / sqrt(2 theta)) from an OU fit on the trailing 90 days of the spread under the current month's beta. Enter when |z| >= 2.0, trading toward the mean. Signal on the bar close, fill at the next open (h3_run.py lines 75-97; prereg). No entry in a month whose trailing fit is invalid (spec judgment call 4).
- Exit (stop, target, time): exit when z crosses 0, hard stop at |z| >= 4, time stop 10 days (240 h) (h3_run.py lines 26, 99-103). Fills at the next open.
- Filters: one position at a time. Gate 1 must pass before any trading is computed (prereg "Gates"; h3_run.py lines 138-150).
- Position sizing: 1 lot gold (100 oz). Silver notional = beta x gold notional, volume treated as continuous (spec judgment call 1; h3_run.py lines 105-109).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Hedge ratio beta | OLS of log XAU on log XAG, trailing 90 days, re-estimated at each month start, needs >= 500 bars | h3_run.py lines 61-72 |
| OU validity (gate 1) | fit valid (0 < phi1 < 1, sigma recovery, stationarity t >= 3) and half-life in [4 h, 240 h] on IS | prereg; h3_run.py lines 135-139; [ou_estimator.py](../../../originals/gann_bot_500/research/goldbot/goldbot/ou_estimator.py) |
| OU min observations | 500 (gate 1 and trading fit) | config.yaml line 91; h3_run.py line 91 |
| Entry / exit / stop z | 2.0 / 0 / 4.0 | h3_run.py line 26 |
| Time stop | 240 h | h3_run.py line 26 |
| IS share | 0.70 | h3_run.py line 133 |

## Costs
Only defined; never applied, because gate 1 failed.
- Gold leg: goldbot per-year x hour cost matrix, median, k_slip 0.5, $7 per lot round trip (h3_run.py lines 172-173).
- Silver leg: matrix built from the silver ticks with the same builder, k_slip 0.5, $7 per 5,000-oz lot round trip ([xag_cost_matrix.json](../../../audit/phaseD/xag_cost_matrix.json); h3_run.py lines 41-42, 151).
- Admin fee: $5 per lot per night crossing 22:00 UTC on each leg, an ESTIMATE (spec judgment call 2; h3_run.py lines 27, 110-111).
- Carry gate 4: expected reversion capture must be at least 2x the all-in round-trip cost (prereg; h3_run.py lines 155-160).

## Tuning and selection
- Search: none. "Single pinned config, no grid" (prereg).
- Configurations run (counted from the code/results): 1 configuration, evaluated on two clocks. The true-UTC run decides; the recorded-clock run is reported beside it (spec line 13). Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row H3-SILVER, n_variants): 1. Row AUD-D-H3 counts the audit run as 0 new variants. They agree.
- How the reported variant was chosen: not applicable.
- Preregistered: yes, [H3_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/H3_PREREGISTRATION.md), frozen 2026-07-06, with the audit's completion notes in [audit/prereg/H3-SILVER.md](../../../audit/prereg/H3-SILVER.md). Deviation: the gold M1 is the clock-corrected true-UTC series, not the "existing XAUUSD M1". This is logged as a bug fix (spec line 13). The spec left six points open, and the audit fixed them in writing before the run (spec lines 17-23).

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Gate 1, true UTC (deciding) | no trades; 30,900 IS bars in the fit | fit valid, phi1 0.99863, half-life 504.0 h, limit 4-240 h: FAIL | [h3_result.json](../../../audit/phaseD/h3_result.json) |
| Gate 1, recorded clock | no trades; 30,153 IS bars | half-life 488.4 h: FAIL | h3_result.json |
| Monthly fits valid, true UTC / recorded (diagnostic, decides nothing) | - | 4.4% / 30% of months; median valid half-life 15.5 h / 9.9 h | h3_result.json |
| Gates 2-4 (OOS PF >= 1.20, OOS n >= 30, carry) | not computed | not reached, by the decision tree | prereg; h3_run.py lines 149-150 |

Verdict: FAILED at validity gate 1. No trading conclusion. The audit review adds that 57% of the movement in the stitched IS spread comes from 63 month-end beta jumps. With one beta, phi is at or above 1.0, so the spread does not mean-revert at all ([REVIEW_F.md](../../../audit/REVIEW_F.md) M7). That figure comes from the script [review_f/h3.py](../../../audit/review_f/h3.py). No output file for it is stored.

## Code and how to rerun
- Code: [h3_run.py](../../../audit/phaseD/h3_run.py) (`build`, then `run`); OU fit in [ou_estimator.py](../../../originals/gann_bot_500/research/goldbot/goldbot/ou_estimator.py); cost builder [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py).
- Audit rerun stage: `h3_build`, `h3_run` ([run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. It needs `dukascopy_ticks` (silver) and `histdata_xau` (gold) ([data/manifest.csv](../../../data/manifest.csv)). Neither stage is in [stages_broker.txt](../../../audit/tools/stages_broker.txt).

## Corrections from the release review
- Status. "NOT RUN" and "failed" are both used, and each is right for a different stage. The author froze H3 and never ran it: "Original verdict: NOT RUN" on the page and the ledger outcome "NOT RUN" for row H3-SILVER are correct for the original work. The audit then ran it as frozen and it FAILED at validity gate 1 ([h3_result.json](../../../audit/phaseD/h3_result.json); ledger row AUD-D-H3). The experiment's result is therefore FAILED. The index row "VERIFIED | NOT RUN" ([experiments/README.md](../../../experiments/README.md) line 79) is misleading. It should read "NOT RUN before the audit; FAILED validity gate 1 in the audit". "VERIFIED" grades no stored number, because none existed.
- H3-SILVER is missing from [NEGATIVE_RESULTS.md](../../../NEGATIVE_RESULTS.md), although it failed.
- README "Timeframe: see prereg". The timeframe is H1 (spec line 14).
- README "Data: XAGUSD ticks 2015-01 to 2022-09". Incomplete. The gold leg is HistData M1, shifted to true UTC. The analysed common window is 2015-03-01 to 2022-09-27 (h3_result.json).
- README "Rules / Costs / Splits / Gates: see prereg". The values are short enough to state: z entry 2, exit 0, stop 4, 10-day time stop, monthly 90-day beta, 70/30 split, gate half-life 4-240 h.
- README verdict "57% of the joined spread's movement comes from month-end beta jumps" had no saved output when the review began. [h3.py](../../../audit/review_f/h3.py) was rerun unchanged and its output saved as [review_f/out/h3.out](../../../audit/review_f/out/h3.out): a share of 0.568 over 63 month boundaries (audit DECISIONS 63).
- README "Provenance" does not link h3_run.py or h3_result.json, though both are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Frozen with zero silver bars on disk; no verdict logged |
| Rerun, recorded clock | half-life 488h, gate needs 4h to 240h |
| Rerun, true UTC | half-life 504h, gate needs 4h to 240h |

## Verdict
VERIFIED. Completed in Phase D as frozen. Result: FAILED at validity gate 1, so no trading conclusion. The 504h is an artefact: 57% of the joined spread's movement comes from month-end beta jumps, and with one beta there is no mean reversion. The 4.4% valid share is mostly test power. Both blind predictions were FAIL.

## Audit caveats
Cycle 4 recorded that silver ticks end 2022-09, before the window of interest.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/prereg/H3_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/H3_PREREGISTRATION.md)
