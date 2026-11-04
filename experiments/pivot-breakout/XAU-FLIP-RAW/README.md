# XAU-FLIP-RAW

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-02. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Entering on any zone flip has edge.

Family: pivot/breakout. Market: XAUUSD. Timeframe: H1/H4 flips. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author tested whether entering at once, in the direction of the break, whenever any of the live bot's daily zones "flips" has an edge on gold. A zone flips when an H4 candle closes beyond its level. The exits were a grid of fixed-dollar targets and stops, an exit on the next opposite flip, and a target with no stop. The script docstring credits the idea to "user" ([run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) lines 4-16).

## Instruments and data
- Instruments: XAUUSD ([run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) line 106).
- Timeframe(s): signals on H4 closes. ATR on H1, daily bars cut at UTC 00:00, exits simulated on M1 (lines 9, 325-328, 233-293).
- Data source and file(s): HistData M1 XAUUSD, loaded through `research.dr_backtest.data_prep.load_m1` (line 22, line 70; [data_prep.py](../../../originals/gann_bot_500/research/dr_backtest/data_prep.py)). File: `gann_bot_500/research/data/xauusd_m1_histdata.csv` ([data/manifest.csv](../../../data/manifest.csv) line 428, group `histdata_xau`). The audit's true-UTC rerun used a clock-corrected copy of the same file ([audit/phaseC/sandbox_fable.py](../../../audit/phaseC/sandbox_fable.py) line 9).
- Period: 2021-06-19 00:00 to 2026-06-19 17:57 UTC, with a 45-day load buffer before the start (lines 81-83). 1,551 trading days were scanned ([recorded log](../../../audit/phaseC/logs_L1/recorded.run_flip_scalp.log)).
- In-sample / out-of-sample: the trades are sorted by entry time. The first 70% are IS and the last 30% are OOS (`is_oos_split`, lines 299-302). This gives IS n=883 and OOS n=379 ([flip_scalp_report.md](../../../originals/gann_bot_500/fable-backtesting/flip_scalp_report.md)). The split is by trade count, not by a fixed date.

## Rules
- Entry: zones are built once a day at the UTC 00:00 D1 open from Gann levels, fib pivots, fib retracements and PP (lines 142-149). A zone is skipped for the day if any of the 10 H4 closes before the day already breached it (lines 151-167). When an H4 close is above an unflipped resistance, the trade is BUY. When it is below an unflipped support, the trade is SELL (lines 206-212). A zone flips at most once per day. There is at most one trade per (H4 close, direction) (lines 213-225). The fill is at the open of the first M1 bar at or after the H4 close (line 251).
- Exit (stop, target, time): fixed-dollar TP and SL from the grid. When TP and SL fall in the same M1 bar, the trade is scored as SL (lines 245-246, 271-275). Horizon 120 h, then mark-to-market (line 96). FLIPEXIT cells: TP only, exit at the next opposite-direction flip, no fixed stop (lines 358-366). NOSL cells: TP only, no stop, 720 h horizon (lines 369-376).
- Filters: none beyond the baseline dead-check. No cooldown, no cap on open trades, no daily loss cap ([flip_scalp_report.md](../../../originals/gann_bot_500/fable-backtesting/flip_scalp_report.md) caveat 1). Positions may overlap.
- Position sizing: none. P&L is in points per trade, with $1 = 100 points (line 92), which is 1.00 lot in the program's convention ([spec.md](../../../experiments/pivot-breakout/XAU-FINAL-V4/spec.md) header).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Gann degrees (from the daily open) | 45, 90, 135, 180, 225, 270, 315, 360 | [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) line 86; [levels.py](../../../originals/gann_bot_500/levels.py) lines 24-61 |
| Fibonacci pivots (prior UTC day H/L/C) | PP; R/S at PP ± 0.382, 0.618, 1.000 × range | [levels.py](../../../originals/gann_bot_500/levels.py) lines 65-91 |
| Fib retracement ratios (H4 swing) | 0.382, 0.500, 0.618, 0.786 | run_flip_scalp.py line 87 |
| H4 swing lookback | 50 bars (minimum closed H4 bars) | run_flip_scalp.py lines 89, 130 |
| Zone width | 0.3 × ATR | run_flip_scalp.py line 88 |
| ATR | Wilder ATR(14) on H1, last H1 bar closed before the day open | run_flip_scalp.py lines 134-138, 328 |
| Baseline dead-check | last 10 H4 closes before the day | run_flip_scalp.py line 152 |
| Zone side | by label prefix R/S; PP side set by the daily open | [signals.py](../../../originals/gann_bot_500/signals.py) lines 46-71; run_flip_scalp.py lines 157-160 |
| TP grid | 500, 1000, 1500 pts ($5, $10, $15) | run_flip_scalp.py line 93 |
| SL grid | 500, 1000, 1500 pts | run_flip_scalp.py line 94 |
| Horizon | 120 h (NOSL: 720 h) | run_flip_scalp.py lines 96, 375 |
| Headline cell | TP $10 / SL $10, fixed in code | run_flip_scalp.py line 97 |

## Costs
20 points ($0.20) per round trip, subtracted from every trade. This is 13 points of observed spread plus 7 points of commission ([run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) lines 40-41, 95, 290). No slippage is modelled beyond the fill at the next M1 open.

## Tuning and selection
- Search: TP {$5, $10, $15} × SL {$5, $10, $15} (9 cells), plus TP {$5, $10, $15} × flip-exit (3 cells), plus TP {$5, $10, $15} with no stop (3 cells) (lines 348-378).
- Configurations run (counted from the code/results): 15 cells, all on the same 1,262 events ([grid_summary.json](../../../originals/gann_bot_500/fable-backtesting/grid_summary.json) has 15 keys). Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 62, n_variants): 2. These differ: the ledger counts 2 ideas (enter on any flip; TP-only), not the 15 cells the code ran.
- How the reported variant was chosen: no variant was put forward as a strategy. The headline cell TP10/SL10 is fixed in code before the run (line 97). The audit quotes TP5/SL5 and TP5/SL15. [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 100 says TP5/SL15 was a "grid cell picked after the fact". Each cell is flagged against PF 1.20 and a 25% DD budget on IS and OOS ([flip_scalp_report.md](../../../originals/gann_bot_500/fable-backtesting/flip_scalp_report.md), "Validation flags").
- Preregistered: no. It appears afterwards as row 8 of the Trials Ledger in the goldbot preregistration, marked "rejected" ([PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md)).

## Results
All rows: 20-point cost, P&L in points.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored, headline TP10/SL10, ALL | 1262 | PF 1.05, win 52.2%, +24.4 pts/trade | [flip_scalp_report.md](../../../originals/gann_bot_500/fable-backtesting/flip_scalp_report.md) |
| Stored, TP10/SL10, IS / OOS | 883 / 379 | PF 1.055 / 1.04 | same |
| Stored, TP10, no stop, 720 h, ALL | 1262 | win 92.1%, PF 0.869, avg win 979 pts, avg loss -13,087 pts | same |
| Stored, best IS cell (TP5/FLIPEXIT, PF 1.137) | 883 | flagged: PF < 1.20, IS DD 41% > 25% | same |
| Stored, TP5/SL5 ALL | 1262 | PF 0.965 | same; [grid_summary.json](../../../originals/gann_bot_500/fable-backtesting/grid_summary.json) |
| Stored, TP5/SL15 ALL | 1262 | PF 1.057 | same |
| Audit rerun, recorded clock | 1262 | grid identical to stored | [recorded.run_flip_scalp.log](../../../audit/phaseC/logs_L1/recorded.run_flip_scalp.log); [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 21 |
| Audit rerun, true UTC, TP5/SL5 | 1255 | PF 1.024 | [true.run_flip_scalp.log](../../../audit/phaseC/logs_L1/true.run_flip_scalp.log) (n); [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 21 (PF) |
| Audit rerun, true UTC, TP5/SL15 | 1255 | PF 1.147, below the 1.20 gate | same; VERDICTS.md line 100 |

None of the 15 cells passes PF ≥ 1.20 on both IS and OOS. Verdict: original FAILED; audit VERIFIED-WITH-CORRECTIONS ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 21). The true-UTC report with all 15 cells is not in the repository. Only the two cells above are published.

## Code and how to rerun
- Code: [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) (identical copy in [research/flip_scalp/](../../../originals/gann_bot_500/research/flip_scalp/run_flip_scalp.py)). It imports [levels.py](../../../originals/gann_bot_500/levels.py), [signals.py](../../../originals/gann_bot_500/signals.py), [structure.py](../../../originals/gann_bot_500/structure.py), [config.py](../../../originals/gann_bot_500/config.py) and [research/dr_backtest](../../../originals/gann_bot_500/research/dr_backtest). The sandbox is built by [audit/phaseC/sandbox_fable.py](../../../audit/phaseC/sandbox_fable.py) (stage `sb_fable`).
- Audit rerun stage: none. The `sb_fable` stage builds the sandboxes, but no stage in [audit/tools/CLEAN_RUN_stages.txt](../../../audit/tools/CLEAN_RUN_stages.txt) or [audit/tools/run_all.sh](../../../audit/tools/run_all.sh) runs run_flip_scalp.py itself. The two logs record a one-off run ([_status.txt](../../../audit/phaseC/logs_L1/_status.txt) lines 71-72).
- Public data enough? Yes. It needs the `histdata_xau` group ([data/manifest.csv](../../../data/manifest.csv) line 428), plus the clock correction for the true-UTC column.

## Corrections from the release review
- "Timeframe: H1/H4 flips" is wrong. The flip rule uses H4 closes only ([run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py) lines 9-13, 199-212). H1 is used only for ATR.
- "Data: HistData M1 XAUUSD 2010-2026" is wrong. The test window is 2021-06-19 to 2026-06-19 (lines 81-82; [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 139).
- "Variants counted in the ledger: 2" understates the search. The code ran 15 cells on one event set ([grid_summary.json](../../../originals/gann_bot_500/fable-backtesting/grid_summary.json)).
- "Splits: train/test/virgin" is wrong for this script. It uses a 70/30 split by trade order inside 2021-26 (lines 299-302). There is no virgin era.
- "Rules: All zones, immediate entry; TP-only variant" leaves out the zone set (Gann 8 degrees, fib pivots, fib retracements, PP), the SL grid, the flip-exit cells and the 120 h horizon.
- "Gates: none" is incomplete. The script flags each cell against PF 1.20 and a 25% DD budget on IS and OOS ([flip_scalp_report.md](../../../originals/gann_bot_500/fable-backtesting/flip_scalp_report.md)).
- The result rows give PFs with no n. Stored and recorded-clock n = 1262. True-UTC n = 1255 ([true.run_flip_scalp.log](../../../audit/phaseC/logs_L1/true.run_flip_scalp.log)).
- The page does not link the script. It is published at [run_flip_scalp.py](../../../originals/gann_bot_500/fable-backtesting/run_flip_scalp.py).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | enter-on-any-flip PF~1.05; TP-only hit $10 92% yet lost (avg loss -$131 vs +$9.79) |
| Rerun, recorded clock | TP5/SL5 0.965, TP5/SL15 1.057 |
| Rerun, true UTC | TP5/SL5 1.024, TP5/SL15 1.147 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Grid byte-identical on the recorded clock. Still not a tradable result at 20-point cost and above.

## Audit caveats
Selection on repeatedly consulted eras.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md](../../../originals/gann_bot_500/fable-backtesting/MASTER_SUMMARY.md)
