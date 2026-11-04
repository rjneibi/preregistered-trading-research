# TA-LAB-R5-R9

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-10-12. A verdict grades the stored claim, not the strategy.

**Hypothesis:** London-range, previous-day, H4-filtered and silver sweep fades have edge.

Family: ICT/SMC. Market: XAUUSD/XAGUSD. Timeframe: M15/M5. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Four follow-up rounds of the TA lab's sweep-fade idea. Round 5 fades a New York-session sweep of the London range. Round 6 fades a sweep of the previous UTC day's high or low. Round 8 splits the round-4 Asia fade by an H4 trend filter. Round 9 runs the round-4 Asia fade on silver. Each is compared with random-entry twins. None showed an edge over its twin; rounds 8 and 9 reuse round 4's leaky range build, so their positive figures are invalid.

## Instruments and data
- Instruments: XAUUSD (rounds 5, 6, 8); XAGUSD (round 9).
- Timeframe(s): M15 for tuning and the main test; M5 as a check (each round's `__main__` loop over `("M15", 4), ("M5", 12)`).
- Data source and file(s): broker MT5 demo exports `research/ta_lab/data/XAU_M15.npy`, `XAU_M5.npy`, `XAG_M15.npy`, `XAG_M5.npy`, loaded and shifted to UTC by [lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) `load`. data/manifest.csv classes them `broker_mt5` (not public).
- Period: gold M15 2022-07 to 2026-10, M5 2025-05 to 2026-10 ([round4.py](../../../originals/gann_bot_500/research/ta_lab/round4.py) docstring). Silver M15 from 2024-01 (so "<2025" is 2024 only), M5 from 2025-11 ([round9.py](../../../originals/gann_bot_500/research/ta_lab/round9.py) docstring).
- In-sample / out-of-sample: before 2025-01-01 UTC vs 2025-01-01 onward ([round5.py](../../../originals/gann_bot_500/research/ta_lab/round5.py) `CUT`, `halves`). M5 has no pre-2025 data, so M5 rows are 2025+ only.

## Rules
Shared (round5.py `run`; lab.py `simulate`): market entry at the next bar's open after a bar that wicks past the level and closes back inside; stop = wick plus a buffer, widened to at least `min_stop_atr` x ATR; lock-ladder exit (stop moves to +k x step R at each +k x step R); time cap 24 hours of bars; 1 trade per day; one position at a time; stop checked before favourable moves inside a bar. Results in R.
- Round 5 (London range, NY fade): range = 06:00-12:00 UTC high/low (at least half the range hours present); signal window 13:30 to `win_end` UTC (round5.py `sweep_orders`).
- Round 6 (previous day): levels = previous UTC day's high/low; Mondays after the weekend gap skipped; signal window from the grid ([round6.py](../../../originals/gann_bot_500/research/ta_lab/round6.py) `pdh_orders`).
- Round 8 (H4 trend split): round-4 Asia fade with fixed settings (window 06-20, min stop 0.5 ATR, ladder 0.4R). Trend = sign(close - EMA of 50 x 4 x bars-per-hour closes, i.e. an H4 EMA50 on the bar series), using the bar before the signal. Variants: all, with trend, against trend ([round8.py](../../../originals/gann_bot_500/research/ta_lab/round8.py)).
- Round 9 (silver): round-4 Asia fade unchanged except silver-scaled stop buffer $0.005 (round9.py).
- Twin: for each real trade, a random bar in the same day's window, random direction, same stop distance in ATR terms (round5.py `twin`). Rounds 5, 6, 8 and 9 use one twin draw (default seed 11).
- Position sizing: R units.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | ATR(14), recursive alpha 1/14, scaled by sqrt(bars per hour) | lab.py `atr`; round5.py |
| R5 window end | grid 16, 18, 20; chosen 18 | round5.py; audit/phaseC/logs_L1/recorded.ta_lab.round5_py.log |
| R5 min stop | grid 0.3, 0.5, 0.8 ATR; chosen 0.5 | same |
| R5 ladder step | grid 0.4, 0.6, 1.0 R; chosen 0.4 | same |
| R6 window | grid (0,24), (6,20), (6,12) UTC; chosen (0,24) | round6.py; recorded.ta_lab.round6_py.log |
| R6 min stop / ladder | grids as R5; chosen 0.5 ATR / 0.4R | same |
| Stop buffer | $0.30 gold; $0.005 silver | round5.py `buf=0.3`; round9.py |
| R8 trend EMA | 50 x 4 x bph bars (H4 EMA50 equivalent) | round8.py |
| R8/R9 fixed spec | window 06-20, min stop 0.5 ATR, ladder 0.4R | round8.py, round9.py |

## Costs
- Gold: per-bar spread floored at $0.20 (lab.py `load`) plus $0.30 slippage per trade, in R (round5.py `SLIP`).
- Silver: spread floor $0.003, slippage $0.005 per trade, scaled to silver's price (round9.py docstring, `SLIP`).
- No commission or swap in the code.

## Tuning and selection
- Search: round 5 window end {16,18,20} x min stop {0.3,0.5,0.8} x ladder {0.4,0.6,1.0} = 27; round 6 window {(0,24),(6,20),(6,12)} x min stop x ladder = 27; round 8: 3 fixed variants; round 9: 1 fixed spec.
- Configurations run (counted from the code/results): 58. Ledger count (registry/trial_ledger.csv, TA-LAB-R5-R9): 4. They differ: the ledger counts one per round.
- How the reported variant was chosen: rounds 5 and 6 sort by pre-2025 M15 `net / (maxDD + 5)` and take the top config (round5.py and round6.py `res.sort`). Pre-2025 data only. Rounds 8 and 9 reuse round 4's chosen settings, which were picked on pre-2025 gold data.
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| R5 M15 <2025 | 414 | +0.094R avg, PF 1.27; twin (n=474) +0.078R | [round5 log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round5_py.log) |
| R5 M15 2025+ | 311 | +0.105R, PF 1.30; twin (n=359) +0.111R | same |
| R5 M5 2025+ | 275 | -0.020R, PF 0.94; twin (n=321) +0.071R | same |
| R6 M15 <2025 | 517 | +0.021R, PF 1.05; twin (n=515) -0.034R | [round6 log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round6_py.log) |
| R6 M15 2025+ | 362 | +0.052R, PF 1.14; twin (n=363) +0.109R | same |
| R6 M5 2025+ | 310 | +0.025R, PF 1.07; twin (n=311) +0.031R | same |
| R8 M15, all / with / against trend, <2025 | 624 / 235 / 390 | +0.048 / +0.038 / +0.051R. INVALID (leaky build) | [round8 log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round8_py.log) |
| R8 M15, all / with / against, 2025+ | 362 / 138 / 224 | +0.235 / +0.221 / +0.244R. INVALID | same |
| R8 M5 2025+, all / with / against | 296 / 107 / 189 | +0.131 / +0.033 / +0.186R. INVALID | same |
| R9 silver M15 2024 / 2025+ | 202 / 383 | +0.109R / +0.102R; twins +0.035 / +0.090R. INVALID (leaky build) | [round9 log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round9_py.log) |
| R9 silver M5 2025+ | 187 | +0.020R; twin +0.057R. INVALID | same |
| Audit same-bar worst ordering, sum of printed rows | R5 18 rows, R6 18, R8 9, R9 3 | sum net R falls from +553.9 to -284.9 (R5), +96.9 to -579.5 (R6), +306.6 to +134.9 (R8), +64.9 to +18.7 (R9); no row turns newly positive | [talab_pess.json](../../../audit/phaseC/talab_pess.json) `summary` |

No pass threshold against the twin is recorded in the code. The "no edge" reading rests on each round's real result not clearly exceeding its twin.

## Code and how to rerun
- Code: [round5.py](../../../originals/gann_bot_500/research/ta_lab/round5.py), [round6.py](../../../originals/gann_bot_500/research/ta_lab/round6.py), [round8.py](../../../originals/gann_bot_500/research/ta_lab/round8.py), [round9.py](../../../originals/gann_bot_500/research/ta_lab/round9.py), shared [lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) and [round4.py](../../../originals/gann_bot_500/research/ta_lab/round4.py) (build reused by rounds 8 and 9). Audit: [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh), [talab_pess.py](../../../audit/phaseC/talab_pess.py), [talab_gap.py](../../../audit/phaseC/talab_gap.py).
- Audit rerun stage: `l1_queue`; sensitivities `talab_gap_make`/`talab_gap_run`, `talab_pess_make`/`talab_pess_run`/`talab_pess_rep` (audit/tools/run_all.sh).
- Public data enough? No. Needs manifest group `broker_mt5` (`ta_lab/data/XAU_*.npy`, `XAG_*.npy`).

## Corrections from the release review
- README "Rules: Rounds 5,6,8,9" gives no rules. The level definitions, windows, stop and ladder rules are in round5/6/8/9.py (above).
- README "Data: as R4" points to a page that itself gives no source. The data are broker MT5 demo exports, not public; silver covers M15 from 2024-01 and M5 from 2025-11 only (round9.py docstring; data/manifest.csv).
- README "Costs: $0.30 slip" is wrong for silver ($0.005 slip, $0.003 spread floor) and omits gold's per-bar spread floor of $0.20 (round9.py; lab.py).
- README "4 rounds. Variants counted in the ledger: 4" understates the search. Rounds 5 and 6 each ran a 27-config grid; round 8 ran 3 variants; 58 configurations in all (round5.py, round6.py, round8.py).
- README results "All NO EDGE" give no n or figures. See the table above, n 107 to 624 per slice (round logs).
- README "Gates: random twin" states no threshold, and rounds 5, 6, 8 and 9 use a single twin draw (seed 11), not 20 (round5.py `twin`).
- Provenance lists only `DECISIONS.log`, which is not in the repository. No script is linked.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All NO EDGE |
| Rerun, recorded clock | All no edge |
| Rerun, true UTC | same, clean clock |

## Verdict
VERIFIED-WITH-CORRECTIONS. Rounds 8 and 9 reuse the leaky build, so their positive printed figures are invalid. The rejection stands.

## Audit caveats
Rounds 8 and 9 reused the leaky build; already rejected.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
