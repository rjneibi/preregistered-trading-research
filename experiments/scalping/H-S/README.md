# H-S

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Bar-level scalps clear costs.

Family: scalping. Market: XAUUSD. Timeframe: M1. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
H-S asked whether any simple scalp on gold M1 bars beats measured costs. Two signals (a z-score fade and a 20-bar breakout burst) were crossed with three fixed-dollar TP/SL geometries and two session choices: 12 configs, the whole pre-registered space. Selection was done on training folds of 15 purged splits, then scored on the test folds and against a permutation baseline.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 ([hs_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hs_runner.py)).
- Data source and file(s): HistData XAUUSD M1 ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7). Costs from [results/cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json) (hs_runner.py line 41).
- Period: from 2015-06-19 (hs_runner.py line 42). The audit rerun loaded 3,848,235 M1 bars from 2015-06-18 to 2026-06-19 17:57 ([logs_recorded/hs_runner.log](../../../audit/phaseC/logs_recorded/hs_runner.log)).
- In-sample / out-of-sample: trade times are cut into 6 equal time groups; each of the 15 pairs of groups is a test fold; train excludes a purge of 24 h before and 40 h after each test span (hs_runner.py lines 280-298). Eras for gate 2: old before 2021-06-19, new after (line 43). The reported "OOS" set is the union of the winner's test folds.

## Rules
- Entry: signals on closed M1 bars, entry at the next bar's open ([spec.md](../../../experiments/scalping/H-S/spec.md) lines 31-33).
  - A, z-score fade: z of close against a rolling 60-bar mean and std; short when z > +2, long when z < -2 ([scalp_lab.py](../../../originals/gann_bot_500/research/goldbot/prereg/scalp_lab.py) line 17).
  - B, momentum burst: long when close > highest high of the prior 20 bars; short is the mirror (scalp_lab.py line 30).
  - Events closer than 5 bars to the previous kept event are dropped (scalp_lab.py lines 39-42).
- Exit (stop, target, time): fixed $/oz TP and SL from the entry price; exit at the open if a bar gaps through; if one bar touches both, it counts as a stop; time exit after 30 M1 bars (scalp_lab.py lines 56-77; hs_runner.py line 46). A vectorised copy of the engine is asserted equal to scalp_lab before use (hs_runner.py lines 7-11).
- Filters: session either all hours or M1 closes 12:00-20:00 UTC only (labelled `ldn_ny` in outputs) (spec.md line 36; hs_runner.py line 48).
- Position sizing: 1 lot (100 oz) per trade (hs_runner.py line 45).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| z-score lookback / threshold | 60 bars / 2.0 | scalp_lab.py line 17 |
| Momentum lookback | 20 bars | scalp_lab.py line 30 |
| Min gap between events | 5 bars | scalp_lab.py lines 17-18, 30 |
| TP / SL ($/oz) | (0.50, 0.50), (1.00, 1.00), (1.50, 0.75) | hs_runner.py line 47 |
| Sessions | all hours; 12-20 UTC | hs_runner.py line 48 |
| Horizon cap | 30 M1 bars | hs_runner.py line 46 |
| Permutation replicates | 200, seed 0 | hs_runner.py line 49 and permutation block |
| Purge / margin | 24 h / 40 h | hs_runner.py line 285 |

## Costs
Per oz: entry-hour spread x (1 + 2 x 0.5) from the per-year x UTC-hour median matrix; plus $7 per lot round trip (hs_runner.py lines 13-16, 44-45). Only the entry hour's spread is used for both sides. p90 spreads for the stress gate. Mean per-oz cost excluding commission: $0.520 in the stored run, $0.822 in the audit full-matrix rerun ([HS_run.json](../../../originals/gann_bot_500/research/goldbot/results/HS_run.json) `cost_levels_per_oz_excl_comm`; logs_recorded/hs_runner.log). The stored run used fallback spreads on about 1.12 million lookups (HS_run.json `fallback_hits`), and matches the audit rerun on the earlier partial matrix ([logs_partial/hs_runner.log](../../../audit/phaseC/logs_partial/hs_runner.log)).

## Tuning and selection
- Search: 2 signals x 3 geometries x 2 sessions (spec.md lines 29-38).
- Configurations run (counted from the code/results): 12 (HS_run.json `config_summary`). Ledger count (registry/trial_ledger.csv n_variants): 12. They agree.
- How the reported variant was chosen: in each of the 15 splits, the config with the highest training-fold PF is picked, but only among configs with at least 50 training trades (hs_runner.py line 302). The "winner" is the config picked in the most splits (hs_runner.py line 319). The n >= 50 floor and the most-picked rule are not in the prereg, which says only "config selection on the training folds" (spec.md lines 48-49). Here the same config, z-fade TP 1.50 / SL 0.75, 12-20 UTC, was picked in all 15 splits (HS_run.json `selections`).
- Preregistered: partly. [spec.md](../../../experiments/scalping/H-S/spec.md), copied from [HS_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/HS_PREREGISTRATION.md), commit 55539b9 per the registry. Gates: OOS PF >= 1.30; each era OOS PF >= 1.10; p90 OOS PF >= 1.10; OOS n >= 500; winner PF above the 95th percentile of best-of-12 PF over >= 200 time-randomised replicates (spec.md lines 47-59). Deviation: the selection floor and tie rule above were added in code.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored winner OOS (z-fade 1.50/0.75, 12-20 UTC) | 56,260 | PF 0.307; p90 PF 0.227 | [HS_run.json](../../../originals/gann_bot_500/research/goldbot/results/HS_run.json) `winner_oos` |
| Stored winner, old era / new era | 31,333 / 24,927 | PF 0.324 / 0.288 | HS_run.json |
| Stored permutation best-of-12 | 200 replicates | median 0.279, p95 0.282 | HS_run.json `permutation` |
| Stored gates | - | gates 1-3 FAIL; 4 and 5 pass: BAR-LEVEL FAIL | HS_run.json `gates` |
| Stored, other 11 configs, full period | 56,260 to 247,261 each | PF 0.001 to 0.279 | HS_run.json `config_summary` |
| Audit rerun, partial matrix | 56,260 | PF 0.307 (matches stored) | [logs_partial/hs_runner.log](../../../audit/phaseC/logs_partial/hs_runner.log) |
| Audit rerun, full matrix, recorded clock | 56,260 | PF 0.200; old 0.270, new 0.135; FAIL | [logs_recorded/hs_runner.log](../../../audit/phaseC/logs_recorded/hs_runner.log) |
| Audit rerun, full matrix, true UTC | 55,477 | PF 0.197; old 0.268 (n=30,860), new 0.134 (n=24,617); FAIL | [logs_true/hs_runner.log](../../../audit/phaseC/logs_true/hs_runner.log) |
| Break-even win rate, full matrix, all-in cost $0.892/oz | - | 139% / 94.6% / 73.0% for the three geometries | logs_recorded/hs_runner.log |

## Code and how to rerun
- Code: [hs_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hs_runner.py), [scalp_lab.py](../../../originals/gann_bot_500/research/goldbot/prereg/scalp_lab.py), [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py), exhibits [HS_exhibits.md](../../../originals/gann_bot_500/research/goldbot/results/HS_exhibits.md), tests [test_hs_pack.py](../../../originals/gann_bot_500/research/goldbot/prereg/test_hs_pack.py).
- Audit rerun stage: `goldbot_both` and `goldbot_partial` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. Manifest group `histdata_xau`; cost matrices are committed.

## Corrections from the release review
- README "Splits: OOS" does not describe the protocol. It is 15 purged combinatorial splits over 6 time groups; the winner is the config with best training PF among those with >= 50 training trades, taken most often across splits. The n >= 50 floor is not in the prereg (hs_runner.py lines 302, 319; spec.md lines 48-49).
- README "Winner OOS PF 0.307 n=56260" does not say that n=56,260 is every trade of that config. The winner was picked in all 15 splits, so the union of its test folds is the full sample (HS_run.json `selections`, `config_summary`).
- README "Costs: per-year x UTC-hour Dukascopy spread matrix" is misleading for the stored number. The stored PF 0.307 is on the earlier partial matrix (about 1.12 million fallback lookups); on the full matrix the PF is 0.200 (logs_recorded/hs_runner.log). The code also applies the entry-hour spread to both sides (hs_runner.py lines 13-16).
- README "Rules: 12 configs" omits all parameters. They are listed above (spec.md lines 31-38; scalp_lab.py lines 17-42).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Winner OOS PF 0.307 n=56260 |
| Rerun, recorded clock | Winner OOS PF 0.200, n=56,260 |
| Rerun, true UTC | PF 0.197, n=55,477 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Stored PF 0.307 reproduces on the partial matrix.

## Audit caveats
Frontier showed 60-109% required win rates at measured costs.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HS_run.json](../../../originals/gann_bot_500/research/goldbot/results/HS_run.json)
