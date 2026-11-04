# BINANCE-TESTNET-P1

**Audit verdict: UNVERIFIED.** Original verdict: NOT RUN. Dated 2026-05-26. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Plumbing test for a paper bot.

Family: trend/mean-reversion. Market: BTCUSDT. Timeframe: not determined. Idea source: own (crypto bot roadmap, May 2026).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Nothing was backtested or traded forward. The registry describes BINANCE-TESTNET-P1 as a plumbing test for a paper-trading bot on the Binance testnet, from the author's May 2026 crypto bot roadmap ([registry/experiments.yaml](../../../registry/experiments.yaml) line 22 onward). No result exists, and the bot's code and README are not in the repo. The audit graded it UNVERIFIED as infrastructure with no evidence value ([VERDICTS.md](../../../audit/VERDICTS.md) line 13).

## Instruments and data
- Instruments: BTCUSDT (registry).
- Timeframe(s): Not recorded in the published files (registry: "not determined").
- Data source and file(s): Binance testnet (registry). No file is in [data/manifest.csv](../../../data/manifest.csv).
- Period: Not recorded in the published files.
- In-sample / out-of-sample: none (registry).

## Rules
- Entry: the registry says "RSI + 50-MA", taken from the author's notes and not re-verified. Exact conditions: Not recorded in the published files.
- Exit (stop, target, time): Not recorded in the published files.
- Filters: Not recorded in the published files.
- Position sizing: Not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| RSI | period not recorded | registry (author's notes, unverified) |
| Moving average | 50 (type not recorded) | registry (author's notes, unverified) |

## Costs
None applied (registry: "none"). Nothing was run.

## Tuning and selection
- Search: none; single configuration (registry).
- Configurations run (counted from the code/results): 0; no code or result is published. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row BINANCE-TESTNET-P1, n_variants): 1, marked "minimum". The ledger counts one planned configuration that never produced a result.
- How the reported variant was chosen: not applicable.
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Any | 0 | No backtest or forward result exists | [VERDICTS.md](../../../audit/VERDICTS.md) line 13 |

## Code and how to rerun
- Code: none published. The ledger source is the author's private bot folder (not published).
- Audit rerun stage: none.
- Public data enough? Not applicable. There is nothing to rerun.

## Corrections from the release review
- README "Status of the number: found". Wrong. No number exists; the page itself says "No backtest or forward result on disk".
- The earlier page gave the rules only as "RSI + 50-MA" and cited a private README and an internal note. The rules beyond that are not recorded in the published files.
- README provenance `<private>/TradingBot-Binance\README.md` is a placeholder path with a Windows backslash, pointing to a file the reader cannot see. It should read "author's private folder (not published)". The same path is in [trial_ledger.csv](../../../registry/trial_ledger.csv) row 54.
- Ledger "n_variants 1" counts a configuration that was never run. It inflates the trial count by one. The amount is immaterial, but the page should say that nothing was run.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No backtest or forward result on disk |
| Rerun, recorded clock | no result exists |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. Infrastructure.

## Audit caveats
Infrastructure only. No evidence value.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `<private>/TradingBot-Binance\README.md` (not published)
