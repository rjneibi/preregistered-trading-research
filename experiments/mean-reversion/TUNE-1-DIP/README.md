# TUNE-1-DIP

**Audit verdict: REPRODUCES-BUT-FRAGILE.** Original verdict: PASSED. Dated 2026-10-26. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Tuning beats the live dip rules.

Family: mean-reversion. Market: US500/US30/US2000; 18 unseen. Timeframe: D1. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Whether tuning the index "buy the dip" rules beats the two live rules. A 3,960-config grid of entry, trend filter, exit and maximum hold was searched on index CFD data up to 2023-10-12. Three finalists and the two live baselines were then run once on sealed data: the same indices after the cut (HOLD-T) and 18 markets never used by any dip study (HOLD-M). All 3 finalists failed. The "PASSED" in the registry refers to the live RSI2 baseline, which had no gate and is the same rule as XM-1-A1.

## Instruments and data
- Instruments: DEV US500, US30, US2000. HOLD-T US500, US30, US2000, USTEC. HOLD-M DE40, FRA40, ESP35, AUS200, HK50 (CFDs), EWG, EWJ, EWU, EFA, EEM, FXI, INDA, SMH, XLK, XLV, XLP, XLE, VNQ (ETFs) ([tune_dip.py](../../../originals/gann_bot_500/research/tune1/tune_dip.py) lines 15-19).
- Timeframe(s): D1.
- Data source and file(s): `research/cross_market/data/*_D1.npz` and `cross_market/data_edge/*_D1.npz` (tune_dip.py `DIRS`), all MT5 demo exports, manifest group `broker_mt5` (not public), including the ETF files (e.g. `data_edge/EWJ_D1.npz`).
- Period: DEV 2012-08 to 2023-10-12; HOLD-T 2023-10-13 to 2026-10-14; HOLD-M full history per market ([spec.md](../../../experiments/mean-reversion/TUNE-1-DIP/spec.md); tune_dip.py `DEV_END`).
- In-sample / out-of-sample: DEV (tuning) split into halves 2012-17 and 2018 to 2023-10 (`HALF`); HOLD-T and HOLD-M sealed, opened once. Spec caveat: the live baselines were chosen after seeing US500/US30 to 2026-10, so HOLD-T is not unseen for them.

## Rules
From spec.md "Part 1" and tune_dip.py `run`.
- Entry: signal at day i close, enter at the next open. Long only. One position per config per market.
- Exit (stop, target, time): exit at the open after the exit condition is met, or after the maximum hold. No stop.
- Filters: trend filter from the grid.
- Position sizing: per-trade net returns (fully invested per trade); PF = sum of wins / sum of losses.
- Live baselines: `live_rsi2` = RSI2 < 10, close > SMA200, exit close > SMA5, max 10 days; `live_ibs` = IBS < 0.2, no filter, exit IBS > 0.8 or close > previous high, max 15 days (tune_dip.py `LIVE`).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| RSI(2) | `ewm(alpha=0.5)` of up/down moves; thresholds 5, 10, 15, 20, 25, 30 | tune_dip.py `prep`, `ENTRIES` |
| IBS = (close-low)/(high-low) | < 0.1, 0.15, 0.2, 0.25, 0.3 | same |
| RSI2 and IBS combos | RSI2 {10,20,30} x IBS {0.2,0.3,0.5} | same |
| N down closes | 2, 3, 4 | same |
| k-day low | 3, 5, 7, 10 | same |
| Cumulative 2-day RSI2 | < 20, 35, 50 | same |
| Stretch below SMA5 in ATR(10) | 0.5, 1.0, 1.5 | same |
| Trend filter | none, > SMA200, > SMA100, > SMA50, SMA50 > SMA200 | `FILTERS` |
| Exit | close > SMA5, SMA3, SMA10, previous high, IBS > 0.8 or previous high, RSI2 > 50, RSI2 > 70, first up close | `EXITS` |
| Max hold | 5, 10, 15 days | `HOLDS` |
| Min trades per DEV cell | 20 | `MIN_CELL` |
| Twin | 1,000 draws, seed 3, same filter pool and hold lengths | `twin_pooled` |

## Costs
From tune_dip.py `load` and `run`: spread = max(1.5 x median recorded spread, 2 bp of the median price), charged once per trade; financing 5%/yr long per calendar night (`FIN_L = 0.05/365`). No commission.

## Tuning and selection
- Search: 33 entries x 5 filters x 8 exits x 3 holds (tune_dip.py lines 21-27).
- Configurations run (counted from the code/results): 3,960 ([dip_dev.csv](../../../originals/gann_bot_500/research/tune1/results/dip_dev.csv) rows; dev log "3960 configs, 3480 with n>=20 in all 6 cells"). Ledger count (registry/trial_ledger.csv, TUNE-1-DIP): 3,960. They match.
- How the reported variant was chosen: DEV objective = robust PF, the minimum PF over 6 cells (3 markets x 2 halves), n >= 20 per cell (spec.md). The prereg also required a finalist to sit on a plateau, with median robust PF of its grid neighbours >= 1.2. The code computes `plateau` but applies no threshold. The finalists are hand-written in [dip_finalists.json](../../../originals/gann_bot_500/research/tune1/results/dip_finalists.json). In dip_dev.csv their DEV ranks are 2 (F1, plateau 1.02), 6 (F2, plateau 1.06) and 28 (F3, plateau 1.01), so none meets the frozen 1.2 plateau rule. No published file records the rule actually used. Selection used DEV data only.
- Preregistered: partly. [PREREG.md](../../../originals/gann_bot_500/research/tune1/PREREG.md) (copied as spec.md) was written 2026-10-26; deviation: the plateau rule was not applied as frozen (above). The published copy was edited to remove names, so it no longer matches its registry hash `b63b3eac` (root DECISIONS.md item 20, line 26).

## Results
Finalist PASS (spec.md): G1 HOLD-T pooled PF >= 1.30, n >= 30, and > the better baseline's HOLD-T PF; G2 HOLD-M pooled PF >= 1.15, PF > 1 in >= 2/3 of markets, and > the better baseline's HOLD-M PF; G3 twin p < 0.05 on both.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| F1 stretch 1.0, >SMA200, exit prev high, 15d: HOLD-T / HOLD-M | 87 / 2,124 | PF 2.36 / 1.20; G1 n, G2 n, G3 Y; FAIL. HOLD-T INSUFFICIENT SAMPLE | [dip_final.txt](../../../originals/gann_bot_500/research/tune1/results/dip_final.txt) |
| F2 RSI2<20 & IBS<0.2, >SMA50, exit RSI2>70, 15d | 84 / 1,690 | PF 2.44 / 1.64; G1 n, G2 Y, G3 Y; FAIL. HOLD-T INSUFFICIENT SAMPLE | dip_final.txt |
| F3 3 down closes, >SMA50, exit >SMA10, 5d | 79 / 1,742 | PF 1.80 / 1.63; G1 n, G2 Y, G3 n; FAIL. HOLD-T INSUFFICIENT SAMPLE | dip_final.txt |
| live_rsi2 baseline (no gate) | 122 / 2,158 | PF 3.05 / 1.59; twin p 0.000; PF > 1 in 83% of HOLD-M | dip_final.txt |
| live_ibs baseline (no gate) | 356 / 10,311 | PF 2.10 / 1.23 | dip_final.txt |
| live_rsi2, split-adjusted ETF prices (audit) | 122 / 2,195 | PF 3.05 / 1.36; the raw 1.59 rests partly on a reverse split (one EWJ trade +295%) | audit/phaseC/logs_L1/adj.tune1.tune_dip.py.log; audit/VERDICTS.md:74 |
| live_rsi2 HOLD-T, DSR at ledger N | 122 | 0.489; trades cluster in 60 weeks, week-averaged DSR 0.142 | audit/VERDICTS.md:104, 119, 122 |
| DEV, live baselines | 262 / 950 | robust PF 0.89 / 1.12 (ranks 1,129 and 177 of 3,960) | audit/phaseC/logs_L1/recorded.tune1.tune_dip_py_dev.log |

## Code and how to rerun
- Code: [tune_dip.py](../../../originals/gann_bot_500/research/tune1/tune_dip.py) (`python tune_dip.py dev`, then `python tune_dip.py final`). Audit: [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) (jobs `tune1 tune_dip.py dev` and `final`), split-adjusted rerun via [split_fix.py](../../../audit/phaseC/split_fix.py) and [run_adj.sh](../../../audit/phaseC/run_adj.sh).
- Audit rerun stage: `l1_queue`; sensitivity `adj_make` / `adj_run` (audit/tools/run_all.sh).
- Public data enough? No. All inputs are manifest group `broker_mt5`.

## Corrections from the release review
- README "Rules: 3960 grid, sealed holdouts" gives no rules. The grid values, exit timing and baselines are listed above (tune_dip.py lines 21-28).
- README "Data: 2012-2026" hides that all CFD and ETF files are MT5 demo exports, not public (data/manifest.csv).
- README "Costs: spread + financing" gives no figures: max(1.5 x median spread, 2 bp) per trade and 5%/yr per night (tune_dip.py).
- README caveat "Plateau gate was weakened before the sealed look, disclosed" is not supported by any published file. The frozen rule (neighbour median robust PF >= 1.2) is not applied in code, the finalists' plateau values are 1.01 to 1.06, and the finalists come from a hand-written JSON (dip_dev.csv; dip_finalists.json).
- README results give finalist n and PF nowhere. All three finalists have HOLD-T n under 100 (79 to 87) (dip_final.txt).
- README "Preregistration ... sha b63b3eacd499" no longer matches the published copy, which was edited (root DECISIONS.md line 26).
- README "Rerun, true UTC: same" has no meaning here; the study uses broker D1 index data, not the HistData gold file.
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link tune_dip.py or the results folder.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0/3 PASS; live rsi2 HOLD-T n122 PF 3.05, HOLD-M n2158 PF 1.59 |
| Rerun, recorded clock | HOLD-T n=122 PF 3.05; HOLD-M n=2,158 PF 1.59 raw, n=2,195 PF 1.36 split-adjusted |
| Rerun, true UTC | same |

## Verdict
REPRODUCES-BUT-FRAGILE. The registered test failed: 0 of 3 finalists passed. PASSED in the registry attaches to the live baseline, which had no gate, and which is the same rule as XM-1-A1, so this is not a fourth independent result. HOLD-M 1.59 came from a reverse split in raw ETF prices, one EWJ trade booking +295%. Adjusted HOLD-M PF is 1.36 with 83% of markets above 1. Holdout CONTAMINATED. Spot checks 20/20 did not reach HOLD-M.

## Audit caveats
PASSED refers to the live RSI2 rule confirmed on 18 unseen markets; the tuning itself failed. Plateau gate was weakened before the sealed look, disclosed.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/tune1/PREREG.md](../../../originals/gann_bot_500/research/tune1/PREREG.md)
