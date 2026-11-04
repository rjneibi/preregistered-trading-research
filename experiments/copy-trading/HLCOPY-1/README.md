# HLCOPY-1

**Audit verdict: UNVERIFIED.** Original verdict: INCOMPLETE. Dated 2026-10-18. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Copying steady wallets beats a twin and BTC.

Family: copy trading. Market: Hyperliquid wallets. Timeframe: live. Idea source: the author.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A forward shadow test, started 2026-10-18, meant to check whether copying "steady" Hyperliquid wallets beats a matched twin and BTC. It was to run to 2026-12-13 against 5 gates. No journal survives: the bot task was removed in the 2026-10-20 VM rebuild, leaving at most about one day of data ([registry/experiments.yaml](../../../registry/experiments.yaml) lines 1408-1428). Nothing was measured that can be checked.

## Instruments and data
- Instruments: "Hyperliquid wallets" ([registry/experiments.yaml](../../../registry/experiments.yaml) line 1411). Which wallets, and how they were picked: Not recorded in the published files. No wallet address is published ([scans/README.md](../../../scans/README.md) line 31).
- Timeframe(s): live.
- Data source and file(s): forward data from the live venue. No journal or data file is published.
- Period: from 2026-10-18; planned end 2026-12-13 (same file, lines 1409, 1420). Data actually recorded: about one day at most (line 1426).
- In-sample / out-of-sample: forward only.

## Rules
- Entry: "smart vs twin vs BTC" (line 1416). The copy rules are in a prereg that is not published.
- Exit (stop, target, time): Not recorded in the published files.
- Filters: Not recorded in the published files.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Wallet selection rule ("steady") | Not recorded in the published files | prereg not published |
| Comparators | a twin, and BTC | [registry/experiments.yaml](../../../registry/experiments.yaml) line 1416 |
| Gates | "5 gates"; their content is not recorded in the published files | same file, line 1422 |

## Costs
"see prereg" (line 1421). The prereg is not published, so the costs are Not recorded in the published files.

## Tuning and selection
- Search: none recorded. Single config.
- Configurations run (counted from the code/results): no code or results published. Ledger count (registry/trial_ledger.csv n_variants): 1.
- How the reported variant was chosen: not applicable.
- Preregistered: yes, per the registry: `originals/gann_bot_500/research/hl_copy/PREREG.md` sha e194ce11b258 (line 1419). That file is not in the repo, so the prereg cannot be read or checked.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Forward | not recorded | No journal on disk. INCOMPLETE | [registry/experiments.yaml](../../../registry/experiments.yaml) line 1423 |
| Audit | not recorded | UNVERIFIED | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 79 |

## Code and how to rerun
- Code: not published. The `hl_copy` folder is not in [originals/gann_bot_500/research](../../../originals/gann_bot_500/research).
- Audit rerun stage: none.
- Public data enough? no. No data was kept and no manifest group in [data/manifest.csv](../../../data/manifest.csv) covers it.

## Corrections from the release review
- README Provenance: "Status of the number: found". Misleading. No number exists; there is no journal.
- README Costs: "see prereg", and Preregistration gives a path. That prereg is not published, so a reader cannot see the costs, rules or the 5 gates. The README should say the prereg is withheld.
- README Source: "user". Chat wording; it should read "the author" (review O-13).
- README Data: "forward". It should say no data was retained (about one day at most, then lost in the 2026-10-20 rebuild).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No journal on disk; bot task removed in the 2026-10-20 VM rebuild |
| Rerun, recorded clock | no journal |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. INCOMPLETE.

## Audit caveats
About one day of data at most, on a machine that was later shut down.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- `originals/gann_bot_500/research/hl_copy/PREREG.md` (not published)
