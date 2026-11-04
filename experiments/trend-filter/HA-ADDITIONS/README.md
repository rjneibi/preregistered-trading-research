# HA-ADDITIONS

**Audit verdict: UNVERIFIED.** Original verdict: INCONCLUSIVE. Dated 2026-06-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Heikin-Ashi trail, session filter and H4 HA colour streak improve D/R/S.

Family: trend filter. Market: XAUUSD. Timeframe: H1/H4. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The registry says three additions were tested on the live gold profiles D, R and S, each alone and combined. A1 is a Heikin-Ashi trailing stop. A2 blocks entries outside 06:00-17:00 UTC. A3 requires two H4 Heikin-Ashi candles whose colour matches the EMA50 bias ([registry/experiments.yaml](../../../registry/experiments.yaml) lines 64-84). The original verdict was INCONCLUSIVE. The report, the code and the bars are not in the repo, so nothing can be checked beyond those lines.

## Instruments and data
- Instruments: XAUUSD (registry).
- Timeframe(s): H1/H4 (registry).
- Data source and file(s): MT5 history (registry). [FUTURE_WORK.md](../../../FUTURE_WORK.md) line 23 says the bars came only from MT5 and were never cached. No file is in [data/manifest.csv](../../../data/manifest.csv).
- Period: Not recorded in the published files.
- In-sample / out-of-sample: "see report" (registry). The report is not published. Not recorded in the published files.

## Rules
- Entry: the live profile D, R or S entry logic. The live parameters are in [config.py](../../../originals/gann_bot_500/config.py), but the engine used for this study is not published. Additions per the registry: A2, no new entries outside 06:00-17:00 UTC; A3, enter only if the last two H4 Heikin-Ashi candles match the EMA50 bias.
- Exit (stop, target, time): profile exits, plus A1, a Heikin-Ashi trailing stop. How the trail is defined: Not recorded in the published files.
- Filters: A2 and A3 as above.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Session window (A2) | 06:00-17:00 UTC | registry/experiments.yaml line 72 |
| HA streak (A3) | 2 H4 candles | same |
| Bias EMA (A3) | EMA50 (timeframe not stated) | same |
| HA trail (A1) | Not recorded in the published files | - |

## Costs
Not recorded in the published files. The registry says "see report", and the report is not published.

## Tuning and selection
- Search: 3 additions plus a combined version, on 3 profiles (registry line 73).
- Configurations run (counted from the code/results): cannot be counted; no code or results are published. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row HA-ADDITIONS, n_variants): 12, marked "minimum". 4 x 3 = 12, so the ledger matches the registry description.
- How the reported variant was chosen: Not recorded in the published files.
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Any | not recorded | Original verdict INCONCLUSIVE; no figures published | [VERDICTS.md](../../../audit/VERDICTS.md) line 15 |

Audit verdict: UNVERIFIED, at level L5, because no trade list exists ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 4).

## Code and how to rerun
- Code: none published. The ledger source, `originals/gann_bot_500/backtest_results/HA_ADDITIONS_REPORT.md`, is not in the repo. Neither is the D/R/S backtest engine.
- Audit rerun stage: none.
- Public data enough? No. There is no code or report, and the MT5 bars were never cached.

## Corrections from the release review
- README "Status of the number: found". Wrong. No number is in any published file. The page's only result is "See HA_ADDITIONS_REPORT.md tables", and that report is not published.
- README caveat "Not transcribed yet; verify in Phase 3." This is an internal to-do note. It should read "report not published; UNVERIFIED".
- README "Costs / Splits / Gates: see report". The report is not published, so these are unknown and should say so.
- README "Rules: A1 HA trail". The trail is not defined in any published file.
- README does not say the study cannot be rerun: the engine and report are not published, and the bars were never cached (FUTURE_WORK.md line 23).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | See HA_ADDITIONS_REPORT.md tables |
| Rerun, recorded clock | MT5 bars not cached |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. Reported tables only.

## Audit caveats
Not transcribed yet; verify in Phase 3.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/backtest_results/HA_ADDITIONS_REPORT.md` (not published)
