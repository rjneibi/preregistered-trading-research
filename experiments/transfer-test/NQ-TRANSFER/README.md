# NQ-TRANSFER

**Audit verdict: UNVERIFIED.** Original verdict: UNVERIFIED. Dated 2026-06-30. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Six-gate strategy transfers from gold to NASDAQ.

Family: transfer test. Market: USTEC. Timeframe: H1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The registry says the live gold six-gate strategy was run on the NASDAQ CFD (USTEC), using the live `evaluate_signal` with an ATR take-profit and a widened session ([registry/experiments.yaml](../../../registry/experiments.yaml) lines 127-146). The script, its output and the report it cites are not in the repo. The audit located no result. Nothing beyond the one-line description can be checked.

## Instruments and data
- Instruments: USTEC (registry).
- Timeframe(s): H1 (registry).
- Data source and file(s): MT5 USTEC bars (registry). [FUTURE_WORK.md](../../../FUTURE_WORK.md) line 23 says the bars came only from MT5 and were never cached. No file is in [data/manifest.csv](../../../data/manifest.csv).
- Period: Not recorded in the published files.
- In-sample / out-of-sample: the registry says "walk-forward". Split dates and method: Not recorded in the published files.

## Rules
- Entry: "Live evaluate_signal" (registry). That function's gate logic as used here: Not recorded in the published files.
- Exit (stop, target, time): "ATR TP" (registry). Multiples, stop and time exit: Not recorded in the published files.
- Filters: "widened session" (registry). Hours: Not recorded in the published files.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| All parameters | Not recorded in the published files | registry points to `originals/gann_bot_500/backtest_nq.py`, which is not in the repo |

## Costs
Not recorded in the published files. The registry says "see code", and the code is not published.

## Tuning and selection
- Search: Not recorded in the published files.
- Configurations run (counted from the code/results): unknown; no code or results are published. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row NQ-TRANSFER, n_variants): blank. The trial counter reads the blank as 0 ([trial_count.py](../../../audit/stats/trial_count.py) line 11; [TRIAL_COUNT.md](../../../audit/stats/TRIAL_COUNT.md) line 12). The programme total therefore counts this study as zero variants.
- How the reported variant was chosen: Not recorded in the published files.
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Any | not recorded | no result located | [VERDICTS.md](../../../audit/VERDICTS.md) line 18 |

Verdict: UNVERIFIED. The audit put this entry at level L5 because no trade list exists ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 4).

## Code and how to rerun
- Code: none published. The ledger source `originals/gann_bot_500/backtest_nq.py:7` and the cited `originals/gann_bot_500/AUDIT_REPORT.md` are not in the repo.
- Audit rerun stage: none.
- Public data enough? No. There is no code, and the MT5 bars were never cached.

## Corrections from the release review
- README "Status of the number: found". Wrong. No number exists in any published file. VERDICTS.md line 18 says "no output located".
- README "Variants counted in the ledger: None". Misleading. The ledger cell is blank and the trial count reads it as 0 (trial_count.py line 11). It should read "unknown, counted as 0 in the ledger total".
- README "Stored: Not transcribed yet" and caveat "Locate result output in Phase 3". These are internal to-do notes. The final wording should be "no output in the published files; UNVERIFIED".
- README "Gates: see AUDIT_REPORT" points to `originals/gann_bot_500/AUDIT_REPORT.md`, which is not published. The root [audit/AUDIT_REPORT.md](../../../audit/AUDIT_REPORT.md) does not define gates for this study.
- README does not say the study cannot be rerun: the code is not published and the bars were never cached (FUTURE_WORK.md line 23).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Not transcribed yet |
| Rerun, recorded clock | no output located |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED.

## Audit caveats
Locate result output in Phase 3.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/backtest_nq.py` (not published)
- `originals/gann_bot_500/AUDIT_REPORT.md` (not published)
