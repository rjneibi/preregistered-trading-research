# ML-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** GBM on 27 price features predicts 1 ATR barrier.

Family: ML. Market: XAUUSD. Timeframe: H1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
ML-1 asks whether a machine-learning model can find an edge in gold's own price history. At every H1 open a gradient-boosted tree model predicts whether price moves +1 ATR before -1 ATR within 24 hours. It is trained walk-forward, one test year at a time from 2014 to 2026, and compared with the same model trained on shuffled labels. Trades are taken when the predicted probability passes a threshold.

## Instruments and data
- Instruments: XAUUSD ([ml_lab.py:1](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)).
- Timeframe(s): decisions at each H1 open; features from closed H1 bars and the previous broker D1 bar; labels on M1 ([ml_lab.py:3-4,35-96](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)).
- Data source and file(s): `d_revival/m1.npz`, a splice of HistData M1 bid (2010-01 to 2026-06-19) and the broker MT5 export `ta_lab/data/XAU_M1.npy` (from 2026-06-26), stored in broker time (UTC+2/+3) ([data.py:1-26](../../../originals/gann_bot_500/research/d_revival/data.py)). The manifest classes m1.npz as `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv) line 427).
- Period: data 2010-01 to 2026-10; test years 2014 to 2026; 98,996 decisions (log below).
- In-sample / out-of-sample: expanding walk-forward. For each test year, train on all earlier decisions whose label resolved before the first bar of the test year; never refit on test data ([ml_lab.py:126-134](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)). Results are reported for 2014-19 and 2020-26.

## Rules
- Entry: at the H1 open, long if p >= thr, short if p <= 1 - thr; one position at a time ([ml_lab.py:99-116](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)).
- Exit (stop, target, time): +1 ATR target and -1 ATR stop from the H1 open price, checked on M1; if both are touched in a bar, the stop is taken first; else close at the M1 close 24 hours later ([ml_lab.py:79-96](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)).
- Filters: the threshold only.
- Position sizing: none; results in R, where 1R = 1 ATR.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | EMA of true range, span 27 (about Wilder 14), on H1 | ml_lab.py:38-39 |
| Other series | ATR span 199; EMA 399 on H1 (about H4 EMA50); EMA 399 (about EMA200); RSI from EMA span 27 | ml_lab.py:40-45 |
| Features (27) | returns over 1, 2, 4, 8, 24, 72, 240 H1 bars in ATR; ATR/price; ATR/ATR100; bar range/ATR; position in 24 h and 120 h range; distance to prior-day H, L, C and to the nearest of 7 pivots (PP ± 0.382/0.618/1.0 range); distance to the two EMAs; EMA slope; RSI; body ratio; wicks; two sweep flags; UTC hour; weekday | ml_lab.py:64-74 |
| Model | numpy GBM: 200 iterations, learning rate 0.05, depth 3, 32 bins, min leaf 200, lambda 1.0 | ml_lab.py:132; [gbm.py:7](../../../originals/gann_bot_500/research/d_revival/gbm.py) |
| Thresholds | 0.52, 0.55, 0.58, 0.60 | ml_lab.py:141 |
| Control | same model, labels permuted (seed 0) | ml_lab.py:124,131 |

## Costs
Spread $0.35 per trade, charged in R as 0.35/ATR ([ml_lab.py:7-8,23,114](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)). No commission, slippage or swap.

## Tuning and selection
- Search: model settings fixed; 4 thresholds, each for the model and the shuffled control.
- Configurations run (counted from the code/results): 4 thresholds (8 rows with the control). Ledger count (registry/trial_ledger.csv n_variants): 4. They agree.
- How the reported variant was chosen: no selection; all thresholds are printed.
- Preregistered: partly. The pass rule is in the docstring, "fixed before the run": OOS AUC > 0.52; net PF >= 1.15 in 2014-19 and in 2020-26 with n >= 200 each; beating the shuffled model ([ml_lab.py:9-10](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)). There is no separate prereg file.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| OOS AUC 2014-2026, recorded clock | 98,996 decisions | model 0.519, shuffled 0.503; yearly 0.494-0.547 | [recorded.d_revival.ml_lab_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.ml_lab_py.log) |
| thr 0.52, 2014-19 / 2020-26 | 8,379 / 8,084 | PF 0.83 / 0.94 | same |
| thr 0.55 | 4,902 / 2,947 | PF 0.86 / 1.02 | same |
| thr 0.58 | 2,228 / 707 | PF 0.99 / 1.21 | same |
| thr 0.60 | 1,200 / 258 | PF 1.02 / 1.17 | same |
| Shuffled control, thr 0.58 | 242 / 19 | PF 0.69 / 1.52 (2020-26 INSUFFICIENT SAMPLE) | same |
| OOS AUC, "true" clock sandbox | 98,996 decisions | model 0.518, shuffled 0.503 | [true.d_revival.ml_lab_py.log](../../../audit/phaseC/logs_L1/true.d_revival.ml_lab_py.log) |
| "true" sandbox, thr 0.52 / 0.55 / 0.58 / 0.60 | 8,382+8,137 / 4,901+2,967 / 2,226+754 / 1,203+277 | PF 0.83/0.94, 0.86/0.97, 0.98/1.13, 1.01/1.12 | same |

No threshold passes: no cell has PF >= 1.15 in both periods, and the AUC is under 0.52. The audit notes that the "true" run of this file is a New York clock run ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 20).

## Code and how to rerun
- Code: [ml_lab.py](../../../originals/gann_bot_500/research/d_revival/ml_lab.py), [gbm.py](../../../originals/gann_bot_500/research/d_revival/gbm.py), [data.py](../../../originals/gann_bot_500/research/d_revival/data.py), [sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py). Audit sandbox: [sandbox_research.py](../../../audit/phaseC/sandbox_research.py).
- Audit rerun stage: `l1_queue` (lines "recorded d_revival ml_lab.py" and "true d_revival ml_lab.py" in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)).
- Public data enough? No. It needs `d_revival/m1.npz` or `ta_lab/data/XAU_M1.npy`, both group `broker_mt5`. The `sb_research` stage that builds the sandbox is a broker stage ([stages_broker.txt](../../../audit/tools/stages_broker.txt)).

## Corrections from the release review
- "Data: M1 2014-2026" is wrong. The file runs 2010-01 to 2026-10 and training starts in 2010; 2014-2026 are the test years. It is a splice of HistData (to 2026-06-19) and a broker MT5 export (from 2026-06-26), stored in broker time (data.py:1-26).
- "Costs: $0.35" does not say how it is charged: once per trade, in R as 0.35/ATR, with no commission.
- The README gives AUC only. Per-threshold n and PF are in the log above; the gate is PF >= 1.15 with n >= 200 in both periods, and AUC > 0.52.
- "Rerun, true UTC: lower thresholds in 2020-26, no skill" gives no number. The true-sandbox AUC is 0.518 (shuffled 0.503), and per-threshold results are above.
- The README links ml_lab.py but not gbm.py, data.py or sim.py, which it imports.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | OOS AUC 0.519 (shuffled 0.503) |
| Rerun, recorded clock | AUC 0.519, shuffled 0.503 |
| Rerun, true UTC | lower thresholds in 2020-26, no skill |

## Verdict
VERIFIED. Embargo is label resolved before the test year, which exceeds the label horizon.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/d_revival/ml_lab.py](../../../originals/gann_bot_500/research/d_revival/ml_lab.py)
