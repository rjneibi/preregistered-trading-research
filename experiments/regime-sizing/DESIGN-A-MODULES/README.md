# DESIGN-A-MODULES

**Audit verdict: VERIFIED.** Original verdict: UNVERIFIED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Regime gate and ATR sizing modules behave as specified.

Family: regime/sizing. Market: XAUUSD. Timeframe: n/a. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
This entry is not a backtest. It checks that two code modules behave as written: a regime gate based on the Kaufman efficiency ratio with hysteresis ([modules/regime.py](../../../originals/gann_bot_500/research/goldbot/modules/regime.py)) and an ATR-based position sizer ([modules/sizing.py](../../../originals/gann_bot_500/research/goldbot/modules/sizing.py)). The check is a suite of 18 unit tests. The modules were later used in HR and SZ.

## Instruments and data
- Instruments: XAUUSD contract spec only (tick size 0.01, tick value 1.0, lot step 0.01) (sizing.py line 74).
- Timeframe(s): n/a.
- Data source and file(s): synthetic data generated inside the tests (seeded RNG 7, [test_modules.py](../../../originals/gann_bot_500/research/goldbot/modules/test_modules.py) line 23). No market data.
- Period: n/a.
- In-sample / out-of-sample: n/a.

## Rules
- Entry: n/a.
- Exit (stop, target, time): n/a.
- Filters: the regime gate. ER = |close_t - close_{t-window}| / sum of absolute 1-bar changes (regime.py lines 2-5, 32). Three states (MOMENTUM, NEUTRAL, MEAN_REVERSION) with separate enter and exit thresholds, ordered enter_mr < exit_mr <= exit_mom < enter_mom, and an N-bar confirmation (regime.py lines 46-57, 92-140). Default thresholds are placeholders to be replaced by IS calibration (regime.py lines 12-17, 64). ER is the only indicator in the module.
- Position sizing: lots = floor((equity x risk fraction) / (stop distance x value per unit per lot), lot step); 0 if below the minimum lot; capped at the maximum (sizing.py lines 105-129). ATR is Wilder with alpha 1/n, NaN for the first n bars (sizing.py lines 93-102).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ER window (default) | 14 | regime.py line 32 |
| Placeholder thresholds | enter_mr 0.25, exit_mr 0.35, exit_mom 0.45, enter_mom 0.60 | regime.py line 64 |
| Confirmation bars | >= 1 (1 = immediate switch) | regime.py lines 92-98 |
| ATR | Wilder, n = 14 default | sizing.py line 93 |
| XAUUSD spec | tick 0.01, tick value 1.0, lot step 0.01 | sizing.py lines 74-77 |

## Costs
None. Unit tests only.

## Tuning and selection
- Search: none.
- Configurations run (counted from the code/results): 0 strategy configurations; 18 test functions (test_modules.py lines 27-171). Ledger count (registry/trial_ledger.csv n_variants): 0. They agree.
- How the reported variant was chosen: n/a.
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| goldbot modules test suite | n/a (18 tests) | 18 passed | [existing_suites.log](../../../audit/infrastructure/existing_suites.log) lines 20-22; [PHASE_B_REPORT.md](../../../audit/infrastructure/PHASE_B_REPORT.md) line 19 |

## Code and how to rerun
- Code: [modules/regime.py](../../../originals/gann_bot_500/research/goldbot/modules/regime.py), [modules/sizing.py](../../../originals/gann_bot_500/research/goldbot/modules/sizing.py), [modules/test_modules.py](../../../originals/gann_bot_500/research/goldbot/modules/test_modules.py). Run from the modules folder: `pytest test_modules.py -v` (test_modules.py line 2).
- Audit rerun stage: none in [audit/tools/run_all.sh](../../../audit/tools/run_all.sh). The pass was recorded in the audit's Phase B infrastructure check ([existing_suites.log](../../../audit/infrastructure/existing_suites.log)).
- Public data enough? Yes; no data needed.

## Corrections from the release review
- README "Rules: regime.py ER/ADX/Hurst with hysteresis" is wrong. The module implements only the Kaufman efficiency ratio with hysteresis; there is no ADX or Hurst code in modules/regime.py (regime.py lines 1-17, 32).
- README stored result "pass state to confirm in Phase 3" is internal to-do text. The suite passes: 18 passed (existing_suites.log line 22).
- README links the test file but gives no run command. The command is `pytest test_modules.py -v` in the modules folder (test_modules.py line 2).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 18 test functions on disk; pass state to confirm in Phase 3 |
| Rerun, recorded clock | 18 tests pass |
| Rerun, true UTC | n/a |

## Verdict
VERIFIED. Design B has no artifact.

## Audit caveats
Design A as a strategy never ran as one experiment; the sizing question was answered by SZ and HR. Design B has no artifact found.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/research/goldbot/modules/test_modules.py](../../../originals/gann_bot_500/research/goldbot/modules/test_modules.py)
