# TAEVAL-1

**Audit verdict: UNVERIFIED.** Original verdict: INCOMPLETE. Dated 2026-10-25. A verdict grades the stored claim, not the strategy.

**Hypothesis:** TradingAgents has an edge after costs.

Family: LLM agent. Market: 27 US symbols. Timeframe: weekly. Idea source: TauricResearch TradingAgents v0.7.0.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
An evaluation of the open-source multi-agent LLM trading framework TradingAgents (version 0.7.0), asking whether its weekly decisions earn an edge after costs. The study ran in a separate private repository. It broke on 2026-10-30 and was stopped before it finished, so there is no result. Only the registry entry is published.

## Instruments and data
- Instruments: "27 US symbols" (registry/experiments.yaml, TAEVAL-1). The symbols are Not recorded in the published files.
- Timeframe(s): weekly (registry/experiments.yaml).
- Data source and file(s): Not recorded in the published files.
- Period: "2023; 2024-08 to 2026-10" (registry/experiments.yaml `data`).
- In-sample / out-of-sample: "pre/post model cutoff" (registry/experiments.yaml `splits`), meaning periods before and after the language model's training cutoff. Exact dates and the model used: Not recorded in the published files.

## Rules
- Entry: decisions come from the TradingAgents framework (registry/experiments.yaml `idea_source`). Prompts, models and settings: Not recorded in the published files.
- Exit (stop, target, time): Not recorded in the published files.
- Filters: Not recorded in the published files.
- Position sizing: Not recorded in the published files.
- The registry lists "E1-E9, 17 variants" without defining them (registry/experiments.yaml `rules`).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Framework | TauricResearch TradingAgents v0.7.0 | registry/experiments.yaml |
| Variants | 17 (E1-E9), not defined | registry/experiments.yaml |
| Model, prompts, agent settings | Not recorded in the published files | |

## Costs
10 bps per side (registry/experiments.yaml `costs`). How it was applied in code: Not recorded in the published files.

## Tuning and selection
- Search: "E1-E9, 17 variants" (registry). What varies: Not recorded in the published files.
- Configurations run (counted from the code/results): cannot be counted; no code or results are published. Ledger count (registry/trial_ledger.csv, TAEVAL-1): 17, marked "minimum, see entry".
- How the reported variant was chosen: not applicable; no result.
- Preregistered: yes, in a private repository (`PREREGISTRATION.md`, commit dd3a9ce, per registry/experiments.yaml). The document is not published, so its content cannot be checked here. Gates per the registry: "H1-H5 with DSR, SPA, Holm".

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Whole study | not recorded | No result. Broken since 2026-10-30 06:19 with 4,947 ERROR rows; stopped by the author | registry/experiments.yaml `results`; audit/VERDICTS.md:78 |

Known issue (registry/experiments.yaml `known_issues`): the local model server binary was not found; ERROR rows sit in the decisions database, and the preregistration maps ERROR to "keep", so analysing the database as it stands would give wrong numbers. Whether a resume skips ERROR rows was not checked. The audit ran no GPU jobs for it (audit/DECISIONS.md item 9).

## Code and how to rerun
- Code: not published (private repository).
- Audit rerun stage: none.
- Public data enough? No. Code, prereg and data are not in the repository; no manifest group covers it.

## Corrections from the release review
- README "Market: 27 US symbols" does not name the symbols, and no published file does.
- README "Rules: E1-E9, 17 variants" defines nothing. The variants, models, prompts and settings are not in any published file.
- README "Preregistration: `<private>`/... commit dd3a9ce" and the provenance items point to a private repository. The page should say plainly that the prereg cannot be read by the public.
- README "Rerun, recorded clock: no result" implies a rerun was attempted. The audit did not rerun it (audit/DECISIONS.md item 9: "no GPU runs").
- README "Gates: H1-H5 with DSR, SPA, Holm" cannot be checked; the gate definitions are not published.
- The ledger's 17 is a minimum (registry/trial_ledger.csv); the README does not say so.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No result. Study broken since 2026-10-30 06:19: 4,947 ERROR rows |
| Rerun, recorded clock | no result |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. INCOMPLETE. Stopped by the author before it finished.

## Audit caveats
llama-server binary not found. ERROR rows sit in decisions.db and the prereg maps ERROR to 'keep', so analysing the DB as it stands would produce wrong numbers. Whether resume skips ERROR rows is not yet checked.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `<private>/tradingagents-eval\PREREGISTRATION.md` (not published)
- `<private>/tradingagents-eval\PROGRESS.md` (not published)
