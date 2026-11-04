# DOOR-3

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: INCONCLUSIVE. Dated 2026-08-24. A verdict grades the stored claim, not the strategy.

**Hypothesis:** A $20 stop forced by a $2,000 account costs winners.

Family: risk geometry. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A $2,000 account at a broker with a 0.01-lot minimum can risk 1% only with a $20/oz stop. DOOR-3 replaced the goldbot "final" stop of 2.4 x ATR with a fixed $20/oz stop and changed nothing else. Both arms ran on the same 472 events. The author registered four predictions that the change would break the strategy. This is an engineering feasibility test, not an edge search ([spec.md](../../../experiments/risk-geometry/DOOR-3/spec.md) lines 7-35).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 resampled to H1, H4 and UTC D1 ([run_door3.py](../../../originals/gann_bot_500/research/goldbot/run_door3.py) lines 117-120).
- Data source and file(s): HistData XAUUSD M1 ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7); p90 spreads from [results/cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json) (run_door3.py line 42); swap points measured on a broker demo feed on 2026-08-24 (run_door3.py lines 39-40).
- Period: old era 2015-06-19 to 2021-06-18, new era from 2021-06-19 to data end (run_door3.py lines 31-33). Stored trades run from 2015-07-02 to 2026-06-10 ([door3_baseline_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/door3_baseline_trades.csv)).
- In-sample / out-of-sample: none. Summary windows by exit time: FULL, MODERN from 2021-06-19, RECENT from 2023-01-01 (run_door3.py lines 44-46).

## Rules
- Entry: the goldbot "final" events, unchanged (`generate_events_final`: R3/S3 = PP +/- (H - L) of the prior day; H1 close beyond a live level with H1 and H4 arms agreeing; 12-20 UTC; skip Monday; 10-H4-close dead-level check; 24 h block) (run_door3.py line 121; [events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py)).
- Exit (stop, target, time): both arms TP 0.8 x ATR, 24 h time stop, bail overlay (half at -1.2 ATR in high vol; all at -1.0 ATR after 8 h in low vol), fill mode `gap_open`. Baseline stop 2.4 x ATR; door-3 stop $20.00/oz (run_door3.py lines 123-130).
- Filters: none added.
- Position sizing: P&L per 1.0 lot. The $20 stop is derived: 1% x $2,000 / (0.01 lot x $100) (run_door3.py lines 36-37).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Account equity / risk / min lot | $2,000 / 1% / 0.01 | run_door3.py line 36 |
| Door-3 stop | $20.00/oz (derived) | run_door3.py line 37 |
| Baseline stop | 2.4 x ATR | config.yaml line 24 |
| TP | 0.8 x ATR | config.yaml line 23 |
| ATR | Wilder 14 on H1 | config.yaml lines 31-33 |
| Time stop | 24 h | config.yaml line 25 |
| Swap (per lot per night) | long -12.6 pts, short -4.6 pts; Wednesday x3; rollover 21:00 UTC | run_door3.py lines 40, 70-78 |
| Prediction window | RECENT: exit on or after 2023-01-01 | spec.md line 55 |

## Costs
Per trade per lot: p90 spread of the entry year x hour x 100 x 2 + $7 commission, plus measured swap (run_door3.py lines 59-80). This is not the median-matrix basis used by the other goldbot tests: it uses the p90 spread, the entry hour only, and adds swap. The audit recompute instead used the p90 matrix through `trade_cost_usd` with no swap ([l2_recompute.py](../../../audit/phaseC/l2_recompute.py) lines 76-91).

## Tuning and selection
- Search: none. One derived value ($20) against the baseline (spec.md lines 31-35).
- Configurations run (counted from the code/results): 2 arms (run_door3.py lines 128-130). Ledger count (registry/trial_ledger.csv n_variants): 2. They agree.
- How the reported variant was chosen: not chosen; the $20 stop is set by the account size.
- Preregistered: yes. [spec.md](../../../experiments/risk-geometry/DOOR-3/spec.md), copied from [door3_fixed_dollar_stop.md](../../../originals/gann_bot_500/research/goldbot/prereg/door3_fixed_dollar_stop.md), registered 2026-08-24, SHA prefix 77A50FB4. Predictions: P1 win rate falls >= 15 points; P2 RECENT mean net per trade negative; P3 >= 60% of trades have entry ATR > $20; P4 full-sample gross per trade lower (spec.md lines 54-59). The prereg's premise that ATR is about 22 (spec.md line 43) does not match the data: the median entry ATR in the stored trades is $3.51 (computed from door3_baseline_trades.csv, column `atr`). So the $20 stop is wider, not tighter, than 2.4 x ATR for most trades.

## Results
Figures marked "computed" were computed for this page from the stored trade CSVs (read only).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored baseline 2.4 x ATR, full | 472 | win rate 72.9%; gross $105.90, net $7.42 per trade; PF 1.037 (computed) | [door3_baseline_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/door3_baseline_trades.csv) |
| Stored door-3 $20, full | 472 | win rate 73.7%; gross $116.29, net $17.58 per trade; PF 1.093 | [door3_fixed20_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/door3_fixed20_trades.csv); [l2_recompute.json](../../../audit/phaseC/l2_recompute.json) `door3 stored` |
| RECENT (exit >= 2023-01-01), baseline / door-3 | 143 / 143 | net per trade $64.65 / $114.61 (computed) | the two CSVs |
| Predictions P1-P4 | 472 | all four refuted: win rate rose 0.8 points; RECENT net positive; 2.1% of trades have ATR > $20; gross higher (computed) | the two CSVs; README states "0 of 4" |
| Baseline TP winners whose MAE reached $20, recorded clock | 360 winners | 0 reach $20; max MAE $17.60/oz | [l2_recompute.json](../../../audit/phaseC/l2_recompute.json) `door3 recorded` |
| Same, true UTC clock | 353 winners (of 481 trades) | 4 reach $20; max MAE $37.86/oz | l2_recompute.json `door3 true_utc` |
| Audit recompute, p90 matrix cost, no swap, recorded clock | 472 | door-3 PF 1.103 vs baseline 1.045 | l2_recompute.json |
| Audit recompute, true UTC | 481 | door-3 PF 0.924 vs baseline 0.933 | l2_recompute.json |

## Code and how to rerun
- Code: [run_door3.py](../../../originals/gann_bot_500/research/goldbot/run_door3.py) (`python run_door3.py`, docstring line 11); [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py); audit recompute [l2_recompute.py](../../../audit/phaseC/l2_recompute.py) lines 73-98.
- Audit rerun stage: `c_l2_recompute` (a recompute in the audit's own script; run_door3.py itself is not run by any stage) ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. Manifest group `histdata_xau`; the cost matrix and swap values are in the repo.

## Corrections from the release review
- README "Costs: per-year x UTC-hour Dukascopy spread matrix, k_slip 0.5 x spread per side" is wrong for this test. run_door3.py charges the p90 entry-hour spread x 2 plus $7 plus measured swap (run_door3.py lines 59-80).
- README "Splits: n/a" omits that prediction P2 is judged on a RECENT window, exit on or after 2023-01-01 (spec.md line 55; run_door3.py line 46).
- README stored claim "zero of 360 winners reach $20 (max MAE $17.60)" is about the 360 take-profit trades of the baseline arm on the recorded clock. On true UTC it is 4 of 353, max $37.86 (l2_recompute.json). CHANGES.md line 21 retires the claim.
- README does not say why all predictions failed. The prereg assumed ATR near 22; the stored median entry ATR is $3.51, so the $20 stop is far wider than 2.4 x ATR for almost all trades (2.1% have ATR > $20) (computed from the stored CSVs).
- README "Rerun, recorded clock" row is not a rerun of run_door3.py. It is the audit's own recompute in l2_recompute.py, with a different cost basis (no swap).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0 of 4 predictions confirmed; zero of 360 winners reach $20 (max MAE $17.60) |
| Rerun, recorded clock | 0 of 360 reach $20, max $17.60 |
| Rerun, true UTC | 4 of 353, max $37.86 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Zero-of-360 claim fails on true UTC.

## Audit caveats
Engineering result about expressibility, not edge. Headroom 1.14x and eroding as ATR rises.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
