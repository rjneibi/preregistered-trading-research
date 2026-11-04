# CHANNEL-A

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-21. A verdict grades the stored claim, not the strategy.

**Hypothesis:** A public signal channel's calls score above chance.

Family: public channels. Market: not named. Timeframe: M1. Idea source: public channel.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The calls of one public signal channel were scored on M1 price data to see whether they beat chance. The scored result was compared with random "coin-flip twin" trades. The channel is not named. Its posts, scoring code and logs are not published ([DECISIONS.md](../../../DECISIONS.md) items 6 and 7).

## Instruments and data
- Instruments: gold, per [registry/experiments.csv](../../../registry/experiments.csv) line 87. The README says "not named".
- Timeframe(s): M1 ([registry/experiments.csv](../../../registry/experiments.csv) line 87).
- Data source and file(s): the channel's posts. Not published.
- Period: Not recorded in the published files.
- In-sample / out-of-sample: "halves" ([registry/experiments.yaml](../../../registry/experiments.yaml), CHANNEL-A entry). The dates in each half are not recorded in the published files.

## Rules
- Entry: the channel's own calls. The scoring rules are not recorded in the published files.
- Exit (stop, target, time): Not recorded in the published files.
- Filters: Not recorded in the published files.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Benchmark | coin-flip twin trades | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 80; [registry/experiments.csv](../../../registry/experiments.csv) line 87 |
| Other parameters | Not recorded in the published files. | - |

## Costs
Not recorded in the published files. The README says "see log". [DECISIONS.md](../../../DECISIONS.md) item 7 says the public-channel rerun logs were removed because they name channels.

## Tuning and selection
- Search: Not recorded in the published files.
- Configurations run (counted from the code/results): cannot be counted, because no code or results are published. Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 138, n_variants): 2, count basis "minimum, see entry". What the 2 variants are is not recorded.
- How the reported variant was chosen: Not recorded in the published files.
- Preregistered: not published.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| "P1" (label not defined in the published files) | Not recorded in the published files | PF 0.58. With n unknown, sample size cannot be judged. | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 80 |
| Real calls vs coin-flip twins | Not recorded in the published files | The real result beats 1.4% of twins | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 80 |

Verdict: original FAILED; audit VERIFIED. The rerun log behind VERIFIED was removed ([DECISIONS.md](../../../DECISIONS.md) item 7), so a reader cannot check it from this repository.

## Code and how to rerun
- Code: not published.
- Audit rerun stage: none.
- Public data enough? No. The channel posts are not published, and no manifest group covers them.

## Corrections from the release review
- "Market: not named" is inconsistent with the registry, which records gold ([registry/experiments.csv](../../../registry/experiments.csv) line 87).
- "scored against the rules in the audit notes" is misleading. No such notes are in the repository. The rules, scoring code, costs and gates are withheld with the posts ([DECISIONS.md](../../../DECISIONS.md) items 6 and 7).
- "Costs: see log" and "Gates: see log" lead nowhere. The log was removed ([DECISIONS.md](../../../DECISIONS.md) item 7).
- "P1 PF 0.58" gives a PF with no n. The number of calls is not recorded in the published files. "P1" is not defined.
- "VERIFIED" rests on an unpublished rerun. The page should say plainly that a reader cannot check it.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | P1 PF 0.58, worse than coin-flip twin |
| Rerun, recorded clock | P1 PF 0.58 |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Real beats 1.4% of twins.

## Audit caveats
The channel is not named in this repository.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

The registry lists no source files for this entry.
