# GANN-PROFILE-D-BASE

**Audit verdict: UNVERIFIED.** Original verdict: FAILED. Dated 2026-06-11. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Six-gate zone logic with polarity has positive expectancy.

Family: support/resistance. Market: XAUUSD. Timeframe: H1 / M1. Idea source: own (Gann and fib levels).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
An early backtest (dated 2026-06-11) of the author's live support/resistance Profile D: zone entries from Gann and Fibonacci levels with the polarity flip, stop 1 x ATR, target 3 x ATR and a 50% partial at 1 x ATR. It compared the immediate entry with the "Option C" M1 pullback entry. It ran on the author's live-bot backtester, which imports live trading modules and is not published. Only the reported summary figures survive in the registry.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): H1 / M1 (registry).
- Data source and file(s): broker demo-feed bars from a MetaTrader 5 terminal (README; [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 14 "MT5 bars not cached"). No bar file for this test is in the repo.
- Period: 2020-10 to 2026-06 (README). Not recorded in any other published file.
- In-sample / out-of-sample: 70/30 chronological (README). Boundary date not recorded in the published files.

## Rules
- Entry: Profile D zone logic of the live bot: price inside a confluence zone, side re-evaluated by polarity, H4 bias agreement, H1 close confirmation ([signals.py](../../../originals/gann_bot_500/signals.py) `evaluate_signal`). Zone = level +/- 0.3 x ATR(H1); H4 swing lookback 50 bars ([config.py](../../../originals/gann_bot_500/config.py) lines 125-126). Option C arm: wait up to 15 M1 bars for a pullback, abandon on a runaway move (config.py lines 178-181). Which version of these files the 2026-06-11 test used is not recorded.
- Exit (stop, target, time): SL 1.0 x ATR, TP 3.0 x ATR, 50% partial at 1.0 x ATR (README; config.py lines 67-71 and 168-172). The live config later replaced the 3 x ATR target with a fixed 900 points ($9) (config.py lines 66-70); D-REVIVAL uses that later $9 target.
- Filters: Not recorded in the published files beyond the above.
- Position sizing: results in R and a percentage drawdown (registry); the sizing rule is not recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| SL | 1.0 x ATR | README; config.py line 71 |
| TP | 3.0 x ATR (at the time of this test) | README; config.py lines 66-70 |
| Partial close | 50% at 1.0 x ATR | config.py lines 168-172 |
| Zone width | 0.3 x ATR(H1) | config.py line 126 |
| H4 swing lookback | 50 | config.py line 125 |
| Option C pullback | 15 M1 bars | config.py lines 180-181 |
| Gann degrees, Fibonacci levels used in the test | Not recorded in the published files | - |

## Costs
4.0 points round trip ($0.04/oz) per the README. The code that applied it is not published.

## Tuning and selection
- Search: baseline entry vs Option C M1 pullback (README).
- Configurations run (counted from the code/results): Not recorded in the published files (code and output not published). Ledger count (registry/trial_ledger.csv n_variants): 2.
- How the reported variant was chosen: Not recorded in the published files. The reported row is labelled "Full".
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Full sample, as reported | 685 | PF 1.11; +0.060R per trade; max DD 11.9%; UNVERIFIED | [registry/experiments.csv](../../../registry/experiments.csv) line 4 (cites `research/backtest_results/comparison_summary_20260611.txt`, not published) |
| IS / OOS slices, Option C arm | Not recorded in the published files | - | - |
| Audit rerun | - | not possible: MT5 bars not cached | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 14 |

## Code and how to rerun
- Code: not published. The engine (`research/backtest.py`) imports live trading modules and broker settings and is not in the repo. The live gate modules it calls are published: [signals.py](../../../originals/gann_bot_500/signals.py), [levels.py](../../../originals/gann_bot_500/levels.py), [structure.py](../../../originals/gann_bot_500/structure.py), [config.py](../../../originals/gann_bot_500/config.py). The closest published rerunnable engine for the same profile is [research/dr_backtest](../../../originals/gann_bot_500/research/dr_backtest) (see DR-EDGE-SCREEN).
- Audit rerun stage: none.
- Public data enough? No. The bars came from a broker MT5 terminal (manifest group `broker_mt5` type data, not cached for this test), and the code is not published.

## Corrections from the release review
- README provenance cites only `comparison_summary_20260611.txt` "(not published)" and does not say the engine is also missing. The backtester is not in the repo, so the figure cannot be checked or rerun (VERDICTS.md line 14).
- README "Rules: Six gates" does not define the gates. No published file lists them; the published gate code is signals.py `evaluate_signal`.
- README does not say that this "Profile D" (TP 3 x ATR) differs from the Profile D replayed in D-REVIVAL (TP fixed $9). The live config changed the target after this test (config.py lines 66-70).
- README result "Full n=685, PF 1.11" omits the IS/OOS split figures its own gate ("OOS PF>=1.2 and expectancy>0") needs; they are not recorded in the published files.
- README "Costs: 4.0 pts round-trip" should say this is $0.04/oz, far below the $0.35 used in D-REVIVAL (sim.py `--spread`).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Full n=685, PF 1.11, +0.060R, maxDD 11.9% |
| Rerun, recorded clock | MT5 bars not cached |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. Reported figure only.

## Audit caveats
Superseded: faithful M1 replay D-REVIVAL gave PF 0.87. Backtest cost of 4 pts is far below realistic spread.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/backtest_results/comparison_summary_20260611.txt` (not published)
