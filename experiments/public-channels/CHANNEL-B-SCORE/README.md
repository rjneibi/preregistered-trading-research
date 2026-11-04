# CHANNEL-B-SCORE

**Audit verdict: UNVERIFIED.** Original verdict: UNVERIFIED. Dated 2026-10-18. A verdict grades the stored claim, not the strategy.

**Hypothesis:** A public crypto channel's calls beat random.

Family: public channels. Market: not named. Timeframe: M1. Idea source: public channel.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The calls of one public channel were to be scored on M1 data against random entries. The scored output file is missing, so no result could be checked. The entry stays UNVERIFIED, and its figures stay out of every summary ([DECISIONS.md](../../../DECISIONS.md) item 6; [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 82).

## Instruments and data
- Instruments: inconsistent. [registry/experiments.csv](../../../registry/experiments.csv) line 89 says gold. The README hypothesis calls it a crypto channel.
- Timeframe(s): M1 ([registry/experiments.csv](../../../registry/experiments.csv) line 89).
- Data source and file(s): the channel's posts. Not published. The scored file (scored_calls.json) was not found ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 82).
- Period: Not recorded in the published files.
- In-sample / out-of-sample: "halves" ([registry/experiments.yaml](../../../registry/experiments.yaml)). The dates are not recorded in the published files.

## Rules
- Entry: the channel's own calls. The scoring rules are not recorded in the published files.
- Exit (stop, target, time): Not recorded in the published files.
- Filters: Not recorded in the published files.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Benchmark | random entries | README hypothesis |
| Other parameters | Not recorded in the published files. | - |

## Costs
Not recorded in the published files.

## Tuning and selection
- Search: none recorded.
- Configurations run (counted from the code/results): cannot be counted, because no code or results are published. Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 140, n_variants): 1.
- How the reported variant was chosen: not applicable.
- Preregistered: not published.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All calls | The registry gives a call count that comes from memory, not a file. It is UNVERIFIED and is not repeated here. | UNVERIFIED. No figures are given, because the scored file was not found. | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 82 |

## Code and how to rerun
- Code: not published.
- Audit rerun stage: none.
- Public data enough? No.

## Corrections from the release review
- "figures in memory, source file to confirm" is internal to-do text. The final wording should be: the scored output is not in the snapshot, so the entry is UNVERIFIED.
- "Status of the number: found" is wrong. No file holds the number ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 82: scored_calls.json not found).
- The market is inconsistent. The README says "Market: not named" and calls it a crypto channel, while [registry/experiments.csv](../../../registry/experiments.csv) line 89 says gold.
- "scored against the rules in the audit notes", "Costs: see log" and "Gates: see log" lead nowhere. No such notes or log are published ([DECISIONS.md](../../../DECISIONS.md) items 6 and 7).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 641 calls; figures in memory, source file to confirm |
| Rerun, recorded clock | scored file missing |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. scored_calls.json not found. Its figures stay out of every summary.

## Audit caveats
The channel is not named in this repository.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

The registry lists no source files for this entry.
