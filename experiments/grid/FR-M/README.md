# FR-M

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** The Micro grid profile is viable.

Family: grid. Market: XAUUSD. Timeframe: M1. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Whether the author's "Micro" pyramiding grid bot works at its designed size. The bot adds tranches of trades in the entry direction, each taking a small profit, and closes everything after 10 minutes. The entries are a pinned stream of 1,353 replayed D-gate entries. Five variants were pinned before any run: the as-designed baseline and four filters or exits ([spec.md](../../../experiments/grid/FR-M/spec.md) lines 15-44; copy of [FR_PREREGISTRATION.md](../../../originals/gann_bot_500/research/fleet_review/FR_PREREGISTRATION.md), frozen 2026-07-06).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 bars; ATR from H1 at entry.
- Data source and file(s): entries [research/dr_backtest/trades_D.jsonl](../../../originals/gann_bot_500/research/dr_backtest/trades_D.jsonl) (fields entry_ts, direction, zone_source, atr). Prices `research/data/xauusd_m1_histdata.csv`, HistData M1 bid ([micro_grid_backtest.py](../../../originals/gann_bot_500/research/fleet_review/micro_grid_backtest.py) lines 26-28). Costs from [cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json).
- Period: entries 2021-06 to 2026-06 (spec.md line 20). M1 loaded from 2021-06-01 (micro_grid_backtest.py line 117).
- In-sample / out-of-sample: OOS = the last 30% of entry events by time (spec.md line 48; micro_grid_backtest.py line 152). M0 OOS has 406 zones.

## Rules
From [spec.md](../../../experiments/grid/FR-M/spec.md) lines 23-44:
- Entry: tranche 1 fills at the open of the first M1 bar at or after entry_ts. All trades in a tranche share that bar's open. When a tranche takes profit, the next tranche fills at the next bar's open. Tranche sizes 5, 10, 20, 30, 35 trades x 0.10 lot, at full spec (no margin caps).
- Exit (stop, target, time): each trade takes profit when favourable excursion from its entry reaches TP. Timer: at entry_ts + 600 s all open tranches close at that bar's close. If a bar could hit both TP and an adverse exit, the adverse exit wins.
- Variants: M0 as designed (TP $1.00, 600 s timer, no stop). M1 = M0 firing only on R3/S3 zones. M2 = M0 plus a grid stop: close all when adverse excursion from tranche-1 entry reaches 1.0 x ATR(H1), at the level (gap-through at bar open). M3 = M0 with TP = max(0.30 x ATR, $0.40) per tranche. M4 = M1 + M2 + M3.
- Position sizing: 0.10 lot per trade, fixed. Results in USD per backtest config, not an account.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Tranche sizes | 5, 10, 20, 30, 35 trades x 0.10 lot | [spec.md](../../../experiments/grid/FR-M/spec.md) line 24 |
| Fixed TP | $1.00 | spec.md line 38 |
| ATR TP | max(0.30 x ATR, $0.40) | spec.md line 43; [micro_grid_backtest.py](../../../originals/gann_bot_500/research/fleet_review/micro_grid_backtest.py) line 139 |
| Timer | 600 s | spec.md line 30; micro_grid_backtest.py line 34 |
| Grid stop | 1.0 x ATR(H1 at entry) | spec.md lines 40-42 |
| Zone filter | zone_source R3 or S3 | spec.md line 39 |
| OOS cut | last 30% of events | spec.md line 48 |

## Costs
Per trade round trip = 2 x matrix median spread (entry hour, per year) x 10 oz + $0.70 commission (0.1 lot at $7/lot) ([spec.md](../../../experiments/grid/FR-M/spec.md) lines 33-35; micro_grid_backtest.py lines 68, 96). The stored run used the partial matrix of its date (2026-07-06, commit 977fff5, shipped as [cost_matrix_977fff5.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix_977fff5.json)); the full-tick matrix came a day later ([audit/phaseC/frm_partial.py](../../../audit/phaseC/frm_partial.py) line 1). The prereg itself notes the 2019-2025 gap biases costs low (spec.md lines 86-88).

## Tuning and selection
- Search: the 5 pinned variants, "the ENTIRE search space" (spec.md line 37).
- Configurations run (counted from the code/results): 5. Ledger count (registry/trial_ledger.csv n_variants): 5. They match.
- How the reported variant was chosen: no selection. PASS needs, for one variant: full PF >= 1.20 at matrix costs; OOS PF >= 1.00; worst single zone >= -$5,000; at least 300 zones (spec.md lines 46-50).
- Preregistered: yes, [FR_PREREGISTRATION.md](../../../originals/gann_bot_500/research/fleet_review/FR_PREREGISTRATION.md) (commit a87b81e per the registry). Blind predictions: the assistant ALL FAIL; the author SOME VARIANT PASSES (spec.md lines 9-11).

## Results
"n" is zones (entry events). Each zone holds many trades (M0 average 24.1). From [FR_M_results.json](../../../originals/gann_bot_500/research/fleet_review/FR_M_results.json) (stored, partial matrix) and the full-matrix rerun log [recorded.micro_grid_backtest.log](../../../audit/phaseC/logs_L1/recorded.micro_grid_backtest.log).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| M0, stored (partial matrix) | 1,353 zones | PF 0.102, OOS PF 0.090 (406 zones), net -$293,888, worst zone -$18,843 | FR_M_results.json |
| M1, stored | 223 zones | PF 0.139, OOS 0.113 (67 zones) | same |
| M2, stored | 1,353 zones | PF 0.099 | same |
| M3, stored | 1,353 zones | PF 0.312, OOS 0.370 | same |
| M4, stored | 223 zones | PF 0.372, OOS 0.459 (67 zones), worst zone -$1,383 | same |
| M0, full matrix, recorded clock | 1,353 zones | PF 0.019 | recorded.micro_grid_backtest.log |
| M4, full matrix, recorded clock | 223 zones | PF 0.173 | same |
| M0 / M4, full matrix, true UTC | 1,308 / 208 zones | PF 0.018 / 0.165 | [true.micro_grid_backtest.log](../../../audit/phaseC/logs_L1/true.micro_grid_backtest.log) |
| M0 / M4, partial matrix, true UTC | 1,308 / 208 zones | PF 0.086 / 0.350 | [frm_partial_true.json](../../../audit/phaseC/frm_partial_true.json) |
| Audit | | VERIFIED-WITH-CORRECTIONS | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 30 |

All variants fail every PF gate on every cost basis.

## Code and how to rerun
- Code: [micro_grid_backtest.py](../../../originals/gann_bot_500/research/fleet_review/micro_grid_backtest.py); partial-matrix rerun [audit/phaseC/frm_partial.py](../../../audit/phaseC/frm_partial.py).
- Audit rerun stage: `dr_flip` (full matrix, both clocks; [audit/phaseC/run_dr_flip.sh](../../../audit/phaseC/run_dr_flip.sh)) and `c_frm_recorded` / `c_frm_true` (partial matrix).
- Public data enough? yes. `histdata_xau` (public) for M1; trades_D.jsonl and both cost matrices are in the repo.

## Corrections from the release review
- README Data: "HistData M1 XAUUSD 2010-2026 (bid)". Wrong. Entries cover 2021-06 to 2026-06 and the M1 is loaded from 2021-06-01 ([spec.md](../../../experiments/grid/FR-M/spec.md) line 20; [micro_grid_backtest.py](../../../originals/gann_bot_500/research/fleet_review/micro_grid_backtest.py) line 117; [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 139).
- README Costs and Gates: "see prereg". The cost formula (2 x median spread x 10 oz + $0.70) and four gates should be stated.
- README Results give "n" without saying it counts zones, not trades.
- README Provenance does not link the runner [micro_grid_backtest.py](../../../originals/gann_bot_500/research/fleet_review/micro_grid_backtest.py) or the entry stream.
- Headline PFs (0.102, 0.372) are on the partial cost matrix. On the full matrix they are 0.019 and 0.173 (n=1,353 and 223 zones).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All FAIL; M0 n=1353 PF=0.102; best M4 n=223 PF=0.372 |
| Rerun, recorded clock | M0 0.102, M4 0.372 exact |
| Rerun, true UTC | M0 0.086, M4 0.350 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Stored run used the partial matrix. Full matrix: M0 0.019, M4 0.173 recorded; 0.018, 0.165 true.

## Audit caveats
Dollars here are per backtest config, not an account.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
