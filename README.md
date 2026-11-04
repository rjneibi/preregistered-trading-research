# Preregistered trading research

A public record of about a year of trading research on gold, FX, index CFDs, ETFs and crypto, followed by an independent-style audit of every result. Negative results are reported as findings. Nothing here is financial advice, see [DISCLAIMER.md](DISCLAIMER.md).

## Headline findings

**After audit, no strategy has a verified edge.** That is the main result of this repository.

- **A clock bug changed the gold results.** The HistData gold file runs one hour ahead of UTC on 62.1% of bars. Results that looked close to passing were partly a clock effect. See [the finding](audit/findings/CLOCK_BUG.md).
- **The trial count is 179,000 variants, a floor.** A count from the published code finds at least 190,234, see [audit/stats/TRIAL_COUNT.md](audit/stats/TRIAL_COUNT.md). Of these, 64,431 are the audit's own new draw of the TVS-1 grid (audit DECISIONS 46), and one study, REEL-1, is not in the ledger. Selecting from that many tries means a deflated Sharpe ratio of 0.95 needs a t-statistic near 6.2. Almost nothing can clear that, so failing it alone says little. It does mean no headline number here can be taken at face value. See [how the count is built](audit/stats/TRIAL_COUNT.md).
- **Four numbers reproduce exactly but are fragile.** They rest on three distinct rules, and they are the only rules being tracked forward:

| Result | Stored | DSR, full ledger (N=179,000) | DSR, own programme | Main weakness |
|---|---|---:|---:|---|
| XM-1-A1 | PF 2.37, n=124 | 0.29 | 0.93 | PF 1.80 with a one-bar delay. 4 of 14 years lose |
| SW-1 | PF 1.74, n=397 | 0.21 | 0.87 | PF 1.29 with a one-bar delay |
| EDGE-1-F6 | Sharpe 1.52 | 0.52 | 0.99 | Sharpe 1.36 on perpetuals with funding. Coins picked in hindsight |
| TUNE-1-DIP | PF 3.05, n=122 | 0.49 | 0.70 | 0 of 3 finalists passed its registered test. Same rule as XM-1-A1. Holdout contaminated |

The gate is DSR >= 0.95 at the full ledger count. The programme count is a secondary column and decides nothing.

## Verdicts

Of 96 registry entries, 78 were audited and 18 are excluded and appear only as ledger counts.

| Verdict | Entries | Meaning |
|---|---:|---|
| VERIFIED | 38 | The stored claim holds on rerun |
| VERIFIED-WITH-CORRECTIONS | 24 | The claim holds after a stated correction, shown beside the original |
| REPRODUCES-BUT-FRAGILE | 4 | Numbers are exact but fail the ledger-count DSR or a robustness check |
| UNVERIFIED | 11 | No file or no run backs the number |
| INVALID | 1 | The original figures come from a look-ahead leak |

**A verdict grades the stored claim, not the strategy.** Most VERIFIED entries are confirmed failures: the failure reproduces. VERIFIED never means profitable.

Every entry is in [audit/VERDICTS.md](audit/VERDICTS.md), including the gates each result above PF 1.1 misses and by how much.

## Where to go

| To read | Open |
|---|---|
| The honest summary | [FINDINGS.md](FINDINGS.md) |
| The full audit | [audit/AUDIT_REPORT.md](audit/AUDIT_REPORT.md) |
| Every failed hypothesis and why | [NEGATIVE_RESULTS.md](NEGATIVE_RESULTS.md) |
| How tests were run | [METHODOLOGY.md](METHODOLOGY.md) |
| Terms in plain language | [GLOSSARY.md](GLOSSARY.md) |
| Every strategy, with instruments, timeframe, indicators, search size and verdict | [experiments/README.md](experiments/README.md) |
| One experiment in full: rules, parameters, tuning, results, code | `experiments/<family>/<ID>/README.md` |
| Every trial counted | [registry/trial_ledger.csv](registry/trial_ledger.csv) |
| Original beside corrected numbers | [audit/CHANGES.md](audit/CHANGES.md) |
| Judgment calls | [DECISIONS.md](DECISIONS.md) and [audit/DECISIONS.md](audit/DECISIONS.md) |
| The live paper test | [audit/FORWARD_TEST.md](audit/FORWARD_TEST.md) |
| Literature, with evidence grades | [LITERATURE.md](LITERATURE.md) |
| External material reviewed | [evaluations/](evaluations/) |
| What was never tested | [FUTURE_WORK.md](FUTURE_WORK.md) |
| Where to go next, with files to start from | [RESEARCH_AGENDA.md](RESEARCH_AGENDA.md) |
| How to contribute or add a test | [CONTRIBUTING.md](CONTRIBUTING.md) and [ADD_AN_EXPERIMENT.md](ADD_AN_EXPERIMENT.md) |

## Reproducing

[REPRODUCE.md](REPRODUCE.md) has exact steps. There are three levels:

| Level | Needs | Proves |
|---|---|---|
| `verify` | Python only, under a minute | Stored outputs match their hashes, every number in the main reports appears in an evidence file, tests pass |
| `public` | Public downloads, about 22 GB, and about 90 minutes | Stages that rest on public data rerun and match |
| `full` | Public downloads and broker exports, about 1 hour 40 minutes | Every stage |

Broker MT5 exports cannot be downloaded or redistributed, so an outside reader cannot run the `full` level as published. The index and ETF results, including XM-1-A1 and SW-1, rest on those exports. For them a reader can check the code and the stored outputs, but cannot regenerate them from this repository alone. [REPRODUCE.md](REPRODUCE.md) lists exactly which stages this affects.

## Forward test

The surviving rules are frozen and tracked on public data, paper only. Status: **RUNNING since the freeze on 2026-10-31, no forward trades scored yet, no edge claimed.** The first monthly update is due on 2026-12-01. Results are appended monthly by a public scheduled job, whatever they show. See [audit/FORWARD_TEST.md](audit/FORWARD_TEST.md).

## Author and licence

Rashed Al Jneibi. Code is under the [MIT licence](LICENSE). Writing and figures are under [CC BY 4.0](LICENSE-docs). Market data is not included, see [data/MANIFEST.md](data/MANIFEST.md). To cite this work, see [CITATION.cff](CITATION.cff).

Much of the code and the audit were produced with Claude Code, under the rules in [audit/DECISIONS.md](audit/DECISIONS.md). The audit's own mistakes are logged in [audit/REVIEW_F.md](audit/REVIEW_F.md) and [audit/CHANGES.md](audit/CHANGES.md).
