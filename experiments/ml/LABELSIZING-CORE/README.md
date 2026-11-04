# LABELSIZING-CORE

**Audit verdict: VERIFIED.** Original verdict: NOT RUN. Dated 2026-06-29. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Validation harness for triple-barrier labels, CPCV, Venn-Abers and CVaR sizing.

Family: ML. Market: synthetic. Timeframe: H1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
LABELSIZING-CORE is a test harness, not a market test. It checks that a labeling and sizing pipeline works correctly on synthetic H1 bars made inside the process. The pipeline covers triple-barrier labels, purged combinatorial cross-validation, a calibrated XGBoost classifier, a tail-loss stop model and a CVaR-limited sizing program. A set of asserts gates correctness. There is no market result by design ([README.md](../../../originals/gann_bot_500/research/labelsizing_core/README.md), opening lines).

## Instruments and data
- Instruments: none. Synthetic "gold-like" price path ([synth_data.py:3-5,44-45](../../../originals/gann_bot_500/research/labelsizing_core/synth_data.py)).
- Timeframe(s): H1 ([config.py:18](../../../originals/gann_bot_500/research/labelsizing_core/config.py)).
- Data source and file(s): generated in process: a geometric random walk with a two-state Markov volatility regime (about 0.3% calm, 0.9% turbulent per hour) and GARCH(1,1)-style innovations, seed 42 ([synth_data.py:1-50](../../../originals/gann_bot_500/research/labelsizing_core/synth_data.py); config.py:54).
- Period: 20,000 synthetic bars, stamped 2018-01-01 to 2020-04-13 ([logs_D/labelsizing_validation.log](../../../audit/phaseC/logs_D/labelsizing_validation.log); config.py:37).
- In-sample / out-of-sample: CPCV with 6 groups and 2 test groups (15 splits, 5 paths), embargo 24 bars, purge using the 24-bar label horizon and the 1,512-bar feature lookback ([config.py:19-30](../../../originals/gann_bot_500/research/labelsizing_core/config.py)).

## Rules
- Entry: test signals every 3rd bar after warm-up, side = sign of the 12-bar momentum; entry at the close of bar t + 2 (N_CONFIRM) ([run_validation.py:41-54](../../../originals/gann_bot_500/research/labelsizing_core/run_validation.py); config.py:20). These are harness signals, not a strategy.
- Exit (stop, target, time): TP 2.0 x ATR, SL 1.0 x ATR at entry, timeout after 24 bars; a bar touching both resolves as SL (config.py:19,33-34; README "What it validates").
- Filters: none.
- Position sizing: CVaR-constrained linear program giving a weight vector of length 5 ("M=5" in the log; what the 5 entries stand for is not described in the log), CVaR alpha 0.95, limit 3%, max gross exposure 1.0, max turnover 0.5, 2,000 scenarios; De-Risk-to-Cash fallback when infeasible (config.py:45-51; log step 7-8).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Label horizon / confirm bars | 24 / 2 | config.py:19-20 |
| TP / SL | 2.0 / 1.0 x ATR | config.py:33-34 |
| HMM regime feature | on; rolling window 63 x 24 = 1,512 bars | config.py:23-25 |
| CPCV | N=6, k=2, embargo 24 | config.py:28-30 |
| XGBoost | multi:softprob, 3 classes, 200 trees, depth 4, learning rate 0.05, subsample 0.8 (further params in file) | [calibration.py:116-122](../../../originals/gann_bot_500/research/labelsizing_core/calibration.py) |
| Calibration | one-vs-rest inductive Venn-Abers | README; calibration.py |
| GPD tail | xi clamp 0.49, min 30 exceedances, fallback x1.5 | config.py:40-42 |
| CVaR LP | alpha 0.95, limit 0.03, exposure 1.0, turnover 0.5, 2,000 scenarios | config.py:45-51 |

## Costs
Inside the sizing LP only: spread 0.0001 and commission 0.00005 (fractions of notional) ([config.py:49-50](../../../originals/gann_bot_500/research/labelsizing_core/config.py)). No trading costs elsewhere, as there is no market test.

## Tuning and selection
- Search: none.
- Configurations run (counted from the code/results): 1 harness run. Ledger count (registry/trial_ledger.csv n_variants): 0 (and AUD-D-LS, 0). They agree; this is not a trial.
- How the reported variant was chosen: not applicable.
- Preregistered: no. The gating asserts are fixed in the README: OHLC coherence; entry = signal + N_CONFIRM; non-empty train and test in all 15 splits; zero leakage violations plus a feature-causality probe; CVaR exception rate <= (1 - alpha) + tolerance.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Synthetic labels | 6,152 signals | TP 2,016 (32.8%), SL 3,981 (64.7%), timeout 155 (2.5%) | [labelsizing_validation.log](../../../audit/phaseC/logs_D/labelsizing_validation.log) |
| CPCV | 15 splits | all non-empty; test about 2,050 each | same |
| Pooled OOS calibration | 30,760 predictions | macro ECE 0.0321, Brier 0.1603 | same |
| CVaR check | 2,000 scenarios | CVaR 0.00548 vs limit 0.03; exception rate 0.0000; PASS | same |
| Fallback | forced infeasible case | De-Risk-to-Cash engaged; PASS | same |
| Overall | n/a | "all gating asserts passed". No market result | same |

## Code and how to rerun
- Code: [run_validation.py](../../../originals/gann_bot_500/research/labelsizing_core/run_validation.py), [config.py](../../../originals/gann_bot_500/research/labelsizing_core/config.py), [synth_data.py](../../../originals/gann_bot_500/research/labelsizing_core/synth_data.py), [labeler.py](../../../originals/gann_bot_500/research/labelsizing_core/labeler.py), [cpcv.py](../../../originals/gann_bot_500/research/labelsizing_core/cpcv.py), [calibration.py](../../../originals/gann_bot_500/research/labelsizing_core/calibration.py), [tail_loss.py](../../../originals/gann_bot_500/research/labelsizing_core/tail_loss.py), [optimizer.py](../../../originals/gann_bot_500/research/labelsizing_core/optimizer.py), [hmm_regime.py](../../../originals/gann_bot_500/research/labelsizing_core/hmm_regime.py), [requirements.txt](../../../originals/gann_bot_500/research/labelsizing_core/requirements.txt). A real-data runner also exists: [run_real.py](../../../originals/gann_bot_500/research/labelsizing_core/run_real.py), [REAL_DATA_NOTES.md](../../../originals/gann_bot_500/research/labelsizing_core/REAL_DATA_NOTES.md). It needs a signal CSV exported with MT5. No published log shows it was ever run.
- Audit rerun stage: `labelsizing` ([run_all.sh:59](../../../audit/tools/run_all.sh)), in its own pinned environment ([requirements_labelsizing_env.txt](../../../audit/infrastructure/requirements_labelsizing_env.txt)). The L1 queue copy failed for lack of xgboost in that environment ([recorded.labelsizing.log](../../../audit/phaseC/logs_L1/recorded.labelsizing.log)); the dedicated stage is the valid run.
- Public data enough? Yes. No market data is needed.

## Corrections from the release review
- "Costs: n/a" is not exact. The sizing LP charges spread 0.0001 and commission 0.00005 (config.py:49-50).
- The README does not mention run_real.py or REAL_DATA_NOTES.md, a real-data path that needs an MT5-exported signal file. Not recorded in the published files whether it was ever run; the audit did not run it.
- "Original verdict: NOT RUN" is confusing beside a run log that passes. NOT RUN means no market test was made.
- The audit's L1-queue log for this harness is a failed import (recorded.labelsizing.log). The README should point to logs_D/labelsizing_validation.log.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No market result by design |
| Rerun, recorded clock | all gating asserts pass, synthetic data |
| Rerun, true UTC | n/a |

## Verdict
VERIFIED. Rerun in its own pinned environment. No market result.

## Audit caveats
Method validation on synthetic data, not a market test.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/research/labelsizing_core/README.md](../../../originals/gann_bot_500/research/labelsizing_core/README.md)
