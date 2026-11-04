# ARB-BTC-PAPER

**Audit verdict: UNVERIFIED.** Original verdict: NOT RUN. Dated 2025-09-24. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Cross-venue BTCUSDT edges above 20 bps exist.

Family: arbitrage. Market: BTCUSDT. Timeframe: tick. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Nothing was measured. In September 2025 the author scaffolded a paper-only logger meant to record cross-venue BTCUSDT price gaps above a threshold. The log files it would have written are empty, so no result exists ([registry/experiments.yaml](../../../registry/experiments.yaml) lines 1-21; [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 12).

## Instruments and data
- Instruments: BTCUSDT ([registry/experiments.yaml](../../../registry/experiments.yaml) line 4).
- Timeframe(s): tick, live only (same file, lines 5-6).
- Data source and file(s): "exchange WebSocket feeds, live only" (same file, line 6). Which venues: Not recorded in the published files. No data file is published.
- Period: dated 2025-09-24 (same file, line 2). Running period: Not recorded in the published files.
- In-sample / out-of-sample: none (same file, line 13).

## Rules
- Entry: none. Paper logging only: "Log edges above alert_edge_bps; paper only" ([registry/experiments.yaml](../../../registry/experiments.yaml) line 9).
- Exit (stop, target, time): none.
- Filters: Not recorded in the published files.
- Position sizing: none (no trades).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| alert_edge_bps | 20 bps per the hypothesis text; the config file itself is not published | [registry/experiments.yaml](../../../registry/experiments.yaml) line 8; ledger source field in [registry/trial_ledger.csv](../../../registry/trial_ledger.csv) points to a private config.yaml line 2 |

## Costs
Not modelled ([registry/experiments.yaml](../../../registry/experiments.yaml) line 14).

## Tuning and selection
- Search: none. Single config.
- Configurations run (counted from the code/results): 0 run with output; code not published. Ledger count (registry/trial_ledger.csv n_variants): 1.
- How the reported variant was chosen: not applicable.
- Preregistered: no ([registry/experiments.yaml](../../../registry/experiments.yaml) line 12).

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored | 0 | No result. edges.log and ticks.log are empty | [registry/experiments.yaml](../../../registry/experiments.yaml) line 16 |
| Audit | 0 | UNVERIFIED, "Scaffold." | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 12 |

## Code and how to rerun
- Code: not published. The bot folder and its config are private.
- Audit rerun stage: none.
- Public data enough? no. No data was recorded, and no manifest group in [data/manifest.csv](../../../data/manifest.csv) covers it.

## Corrections from the release review
- README Provenance says "Status of the number: found". This is misleading. There is no number. The logs are empty and no result exists ([registry/experiments.yaml](../../../registry/experiments.yaml) line 16).
- README Rules give "alert_edge_bps" without a value. The only published value is the 20 bps in the hypothesis. The config that sets it is not published.
- README Data says "exchange WebSocket feeds". The venues are not named in any published file.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | edges.log and ticks.log are empty; no result exists |
| Rerun, recorded clock | no result exists |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. Scaffold.

## Audit caveats
Scaffold only, September 2025. Nothing was measured.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `<private>/arb_bot\config.yaml` (not published)
