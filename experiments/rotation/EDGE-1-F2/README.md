# EDGE-1-F2

**Audit verdict: UNVERIFIED.** Original verdict: NOT RUN. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Sector rotation.

Family: rotation. Market: XL* ETFs. Timeframe: D1. Idea source: published.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
EDGE-1-F2 was a pre-declared test of cross-sectional momentum in US sector ETFs: each month hold the 3 of 9 sector ETFs with the best 12-1 month return, against an equal-weight basket of the same sectors. It never ran. The code requires at least 6 of the 9 ETFs, and the data folder held daily bars for only 4.

## Instruments and data
- Instruments: intended XLE, XLF, XLK, XLU, XLV, XLP, XLI, XLB, XLY ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) line 152). Found: XLE, XLK, XLV, XLP ([logs_L1/recorded.cross_market.edge_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.edge_lab_py.log) line 10).
- Timeframe(s): D1.
- Data source and file(s): `research/cross_market/data_edge/<symbol>_D1.npz` (edge_lab.py lines 33, 152). In [data/manifest.csv](../../../data/manifest.csv) these are group `broker_mt5` (MetaTrader 5 terminal exports, not published). The folder also has XLC, which is not in the list of 9.
- Period: not recorded in the published files for these ETFs. The pass rule splits at 2016-01-01 (edge_lab.py line 169).
- In-sample / out-of-sample: none; two halves, before and from 2016-01-01 (edge_lab.py lines 63-65, 169).

## Rules
- Entry: at each month's last trading day, rank sectors by close 21 days ago / close 252 days ago - 1 (the 12-1 month return); hold the top 3 at 1/3 weight each until the next month end; positions take effect the next day (edge_lab.py lines 157-165).
- Exit (stop, target, time): no stops; monthly rebalance only.
- Filters: no position while any sector's momentum is undefined (edge_lab.py line 164). The test is skipped if fewer than 6 sector files exist (lines 153-155).
- Position sizing: equal weight, 1/3 per held ETF, fully invested (edge_lab.py line 162).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Momentum | close(t-21) / close(t-252) - 1 | edge_lab.py line 158 |
| Holdings | top 3 of available sectors | edge_lab.py lines 160-162 |
| Rebalance | last trading day of each month | edge_lab.py line 159 |
| Benchmark | equal-weight mean of sector returns | edge_lab.py line 167 |
| Minimum sectors to run | 6 | edge_lab.py line 153 |
| Half split | 2016-01-01 | edge_lab.py line 169 |
| Pass rule | excess Sharpe vs equal weight >= 0.3 in both halves | edge_lab.py lines 8-9, 170 |

## Costs
0.05% of turnover per rebalance (`pos.diff().abs().sum() * 0.0005`, edge_lab.py line 166). Never applied, because the test did not run.

## Tuning and selection
- Search: none.
- Configurations run (counted from the code/results): 0. Ledger count (registry/trial_ledger.csv n_variants): 0. They agree.
- How the reported variant was chosen: n/a.
- Preregistered: partly. The rule and the pass gate were declared in the docstring before any run, dated 2026-10-13 (edge_lab.py lines 1-9). There is no separate frozen prereg file.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Recorded-clock audit rerun | 0 | not run: "not enough sector ETFs", 4 found | [logs_L1/recorded.cross_market.edge_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.edge_lab_py.log) line 10 |

## Code and how to rerun
- Code: [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) function `f2` (lines 151-173).
- Audit rerun stage: `l1_queue` (job `recorded cross_market edge_lab.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)).
- Public data enough? No. The ETF files are in manifest group `broker_mt5`, and even those cover only 4 of the 9 sectors.

## Corrections from the release review
- README "Rules: n/a" is wrong. The rule was declared: top 3 of 9 XL* sector ETFs by 12-1 month return, rebalanced monthly, against equal weight (edge_lab.py lines 8-9, 151-166).
- README "Splits: n/a" and "Gates: n/a" are wrong. The halves split at 2016-01-01 and the pass rule is excess Sharpe >= 0.3 in both halves (edge_lab.py lines 169-170).
- README "Costs: n/a" is wrong. The code charges 0.05% of turnover (edge_lab.py line 166).
- README "Market: XL* ETFs" should name them: XLE, XLF, XLK, XLU, XLV, XLP, XLI, XLB, XLY; only XLE, XLK, XLV and XLP had data (edge_lab.py line 152; rerun log line 10).
- README provenance lists only the unpublished DECISIONS.log. The code ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py)) and the rerun log are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Untestable: 4 of 9 ETFs have history |
| Rerun, recorded clock | not run |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. 4 of 9 ETFs have history.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
