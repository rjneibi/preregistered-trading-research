# CHANNEL-C

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-22. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Three public signal channels pass the gates.

Family: public channels. Market: not named. Timeframe: M1. Idea source: public channel.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The calls of three public signal channels were scored on M1 price data against a set of pass/fail gates. All three failed. The stored result also notes that two of the channels appear to be run by one operator, and that one shows signs of deleted posts ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 81; [registry/experiments.csv](../../../registry/experiments.csv) line 88). The channels are not named. Their posts, scoring code and logs are not published ([DECISIONS.md](../../../DECISIONS.md) items 6 and 7).

## Instruments and data
- Instruments: gold, per [registry/experiments.csv](../../../registry/experiments.csv) line 88. The README says "not named".
- Timeframe(s): M1 ([registry/experiments.csv](../../../registry/experiments.csv) line 88).
- Data source and file(s): the channels' posts. Not published.
- Period: Not recorded in the published files.
- In-sample / out-of-sample: "halves" ([registry/experiments.yaml](../../../registry/experiments.yaml), CHANNEL-C entry). The dates are not recorded in the published files.

## Rules
- Entry: the channels' own calls. The scoring rules are not recorded in the published files.
- Exit (stop, target, time): Not recorded in the published files.
- Filters: Not recorded in the published files.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Gates | Not recorded in the published files. | - |

## Costs
Not recorded in the published files. The README says "see log". [DECISIONS.md](../../../DECISIONS.md) item 7 says the public-channel rerun logs were removed.

## Tuning and selection
- Search: Not recorded in the published files.
- Configurations run (counted from the code/results): cannot be counted, because no code or results are published. Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 139, n_variants): 6, count basis "minimum, see entry". What the 6 variants are is not recorded.
- How the reported variant was chosen: none was chosen. All failed.
- Preregistered: not published.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All three channels | Not recorded in the published files | All FAIL | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 81 |

Verdict: original FAILED; audit VERIFIED ("Output identical"). The rerun log was removed, so a reader cannot check this.

## Code and how to rerun
- Code: not published.
- Audit rerun stage: none.
- Public data enough? No. No manifest group covers the channel posts.

## Corrections from the release review
- "Market: not named" is inconsistent with the registry, which records gold ([registry/experiments.csv](../../../registry/experiments.csv) line 88).
- The Hypothesis covers three channels, but the Caveat says "The channel is not named", in the singular. Three channels were scored.
- "scored against the rules in the audit notes", "Costs: see log" and "Gates: see log" lead nowhere. These items are withheld, and the log was removed ([DECISIONS.md](../../../DECISIONS.md) items 6 and 7).
- "All FAIL" gives no n and no gate figures. Neither is recorded in the published files.
- "VERIFIED" rests on an unpublished rerun. The page should say that a reader cannot check it.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All FAIL; two channels are one operator; one has deleted-post signs |
| Rerun, recorded clock | All FAIL |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Output identical.

## Audit caveats
The channel is not named in this repository.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

The registry lists no source files for this entry.
