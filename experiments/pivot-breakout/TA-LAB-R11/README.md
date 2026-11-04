# TA-LAB-R11

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-12. A verdict grades the stored claim, not the strategy.

**Hypothesis:** FINAL_v4 holds in an independent lab.

Family: pivot/breakout. Market: XAUUSD. Timeframe: H1. Idea source: FINAL_v4 spec.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author re-ran a version of the FINAL_v4 gold breakout rule inside a separate research lab (the "TA lab"), with no tuning. It buys when a close is above the prior day's R3, and sells when a close is below S3. It runs on broker M15 bars, 2022-07 to 2026-10, and compares the result with a random-entry twin. As coded, the level it uses is not the R3/S3 that FINAL_v4 is defined on (see Corrections).

## Instruments and data
- Instruments: XAUUSD ([round11.py:15](../../../originals/gann_bot_500/research/ta_lab/round11.py), `load("M15")`, default symbol "XAU" in [lab.py:29](../../../originals/gann_bot_500/research/ta_lab/lab.py)).
- Timeframe(s): M15 bars. An "H1 close" is taken as the M15 bar that ends on the hour ([round11.py:33-34](../../../originals/gann_bot_500/research/ta_lab/round11.py)).
- Data source and file(s): MetaTrader 5 broker demo feed, `ta_lab/data/XAU_M15.npy` ([lab.py:3-6](../../../originals/gann_bot_500/research/ta_lab/lab.py); [data/manifest.csv](../../../data/manifest.csv) line 512, group `broker_mt5`, access `broker`). Times are shifted from broker time to UTC by the loader, with an EU daylight-saving rule ([lab.py:23-41](../../../originals/gann_bot_500/research/ta_lab/lab.py)).
- Period: 2022-07-11 to 2026-10-09, per the audit's clock check of this file ([audit/phaseC/talab_clock.json](../../../audit/phaseC/talab_clock.json), 1,098 days, 0 days off-clock).
- In-sample / out-of-sample: no tuning, so the docstring calls the whole record out of sample for this lab ([round11.py:3-4](../../../originals/gann_bot_500/research/ta_lab/round11.py)). Results are split at 2025-01-01 UTC: "<2025" and "2025+" (`halves`, `CUT` in [round5.py:15,75-76](../../../originals/gann_bot_500/research/ta_lab/round5.py)).

## Rules
- Entry: for each day, the pivot is built from the previous data day's high, low and close: `p = (H+L+C)/3`, `R3 = H + 2*(p - L)`, `S3 = L - 2*(H - p)` ([round11.py:27-29](../../../originals/gann_bot_500/research/ta_lab/round11.py)). On the M15 bars that close on the hour from 12:00 to 19:00 UTC (bars starting 11:45 to 18:45, `11.75 <= hour < 19.75`, line 33), the first close above R3 gives a buy and the first close below S3 gives a sell. Entry is at market at the next bar's open (lines 35-40; fill rule in [lab.py:89-90](../../../originals/gann_bot_500/research/ta_lab/lab.py)).
- Exit (stop, target, time): stop = next-bar open ∓ 2.4 x ATR. Target = 0.8/2.4 of the initial risk, i.e. about 0.8 x ATR ([round11.py:36,39,44](../../../originals/gann_bot_500/research/ta_lab/round11.py)). Time exit after 96 M15 bars (24 hours) at that bar's open ([round11.py:44](../../../originals/gann_bot_500/research/ta_lab/round11.py); [lab.py:129-131](../../../originals/gann_bot_500/research/ta_lab/lab.py)). Inside a bar the stop is checked before the target ([lab.py:9-10,107-112](../../../originals/gann_bot_500/research/ta_lab/lab.py)). The "tp" mode also moves the stop to breakeven at +1R ([lab.py:117-118](../../../originals/gann_bot_500/research/ta_lab/lab.py)); with a 0.33R target this never triggers.
- Filters: no Mondays; skip a day if the previous data day is more than 3 days earlier ([round11.py:24-26](../../../originals/gann_bot_500/research/ta_lab/round11.py)). At most one signal per day (the loop `break`s after the first, lines 37,40). One position at a time (`one_at_a_time=True`, [lab.py:76,86](../../../originals/gann_bot_500/research/ta_lab/lab.py)). There is no dead-level check (not in round11.py).
- Position sizing: none. Every trade is measured in R, its own initial risk ([lab.py:8-9](../../../originals/gann_bot_500/research/ta_lab/lab.py)).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Pivot formula | classic floor: R3 = H + 2(PP - L), S3 = L - 2(H - PP) | round11.py:28-29 |
| ATR | Wilder-style smoothing, alpha 1/14, on M15 true range, multiplied by 2 as an H1 proxy, value at the last bar of the prior day | round11.py:18,30; lab.py:44-53 |
| Stop | 2.4 x ATR from the next-bar open | round11.py:36,39 |
| Target | 0.8/2.4 R (0.333R) | round11.py:44 |
| Max hold | 96 M15 bars (24 h) | round11.py:31,44 |
| Signal window | closes 12:00-19:00 UTC | round11.py:33 |
| Twin | random bar 12:00-20:00 UTC on the same day, random side, same stop distance scaled by ATR, seed 11 | round5.py:51-65; round11.py:51 |
| Cut date | 2025-01-01 UTC | round5.py:15 |

## Costs
- Spread: per-bar broker spread (points x $0.01), floored at $0.20. Buys pay it at entry; sells pay it on their exit side ([lab.py:5-6,39,89-90,107-108,130](../../../originals/gann_bot_500/research/ta_lab/lab.py)).
- Slippage: $0.30 per trade, subtracted in R as `0.30 / risk` ([round11.py:46](../../../originals/gann_bot_500/research/ta_lab/round11.py)).
- No commission or swap in the code.

## Tuning and selection
- Search: none. Parameters are taken from the author's description of FINAL_v4 ([round11.py:1-4](../../../originals/gann_bot_500/research/ta_lab/round11.py)).
- Configurations run (counted from the code/results): 1, plus the random twin. Ledger count (registry/trial_ledger.csv n_variants): 1 (count basis "minimum, see entry"). They agree.
- How the reported variant was chosen: not chosen; single fixed rule.
- Preregistered: no. The docstring states the rule is fixed in advance, but there is no prereg file.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| <2025 (2022-07 to 2024-12) | 64 | net -4.9R, avg -0.077R, PF 0.73, win 72%, maxDD 7.8R; twin avg -0.070R. INSUFFICIENT SAMPLE | [recorded.ta_lab.round11_py.log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round11_py.log) |
| 2025+ (2025-01 to 2026-10) | 42 | net +1.4R, avg +0.032R, PF 1.15, win 79%, maxDD 4.0R; twin avg -0.235R. INSUFFICIENT SAMPLE | same |
| Real-gap stop fills (gap2) and both same-bar orderings (pessA, pessB) | 64 / 42 | identical to the stock run | [gap2.round11_py.log](../../../audit/phaseC/logs_talab/gap2.round11_py.log), [pessA](../../../audit/phaseC/logs_talab/pessA.round11_py.log), [pessB](../../../audit/phaseC/logs_talab/pessB.round11_py.log), [talab_pess.json](../../../audit/phaseC/talab_pess.json) |
| US-DST clock variant (gapus, dropped by the audit) | 64 / 44 | PF 0.79 / 1.22. INSUFFICIENT SAMPLE | [gapus.round11_py.log](../../../audit/phaseC/logs_talab/gapus.round11_py.log); dropped per [talab_gap.py:1-3](../../../audit/phaseC/talab_gap.py) |

## Code and how to rerun
- Code: [round11.py](../../../originals/gann_bot_500/research/ta_lab/round11.py), [lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py), [round5.py](../../../originals/gann_bot_500/research/ta_lab/round5.py) (twin and split). Audit variants: [talab_gap.py](../../../audit/phaseC/talab_gap.py), [talab_pess.py](../../../audit/phaseC/talab_pess.py).
- Audit rerun stage: `l1_queue` (line "recorded ta_lab round11.py" in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); variants in `talab_gap_run` and `talab_pess_run` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh) lines 38, 41-45).
- Public data enough? No. It needs group `broker_mt5` (`ta_lab/data/XAU_M15.npy`), which is not published or fetchable ([data/MANIFEST.md](../../../data/MANIFEST.md)). talab_pess.json and talab_clock.json are listed as not regenerable publicly ([outputs_broker.txt](../../../audit/tools/outputs_broker.txt) lines 3, 10).

## Corrections from the release review
- The README presents this as a check of FINAL_v4 ("FINAL_v4 holds in an independent lab"). That is wrong as coded. round11.py:29 uses the classic floor pivot, `R3 = H + 2*(PP - L)`, `S3 = L - 2*(H - PP)`. FINAL_v4 defines `R3 = PP + (H - L)`, `S3 = PP - (H - L)` ([XAU-FINAL-V4 spec.md:22-23](../../../experiments/pivot-breakout/XAU-FINAL-V4/spec.md)). The goldbot port says plainly that it is "NOT the classic floor-trader R3" ([pivots.py:11-12](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py)). The classic R3 sits further out than the FINAL_v4 R3 by (PP - L), and the classic S3 further below by (H - PP), so this run tests a different, wider level. It is not a test of FINAL_v4.
- Other differences from FINAL_v4: M15 bars, not H1; ATR is M15 ATR x 2, not Wilder ATR(14) on H1 (round11.py:18; V4 spec.md:32-33); no dead-level check (V4 spec.md:27-28); signal closes 12:00-19:00 UTC, not 12:00-20:00 (round11.py:33); no hivol/lovol bail stack (V4 spec.md:35-37).
- "Timeframe: H1" and "Data: H1" are wrong. The data is broker MT5 M15, 2022-07-11 to 2026-10-09 (round11.py:15; talab_clock.json), not publicly available.
- "Costs: see lab.py" is incomplete. Costs are the per-bar spread floored at $0.20 plus $0.30 per trade in R (lab.py:39; round11.py:46).
- The XAU-FINAL-V4 README:45 says FINAL_v4 was "Killed ... by H1 and TA-LAB round 11". The round-11 part does not hold, because round 11 tests a different level. Both round-11 slices are also INSUFFICIENT SAMPLE (n=64, n=42).
- Provenance cites only `DECISIONS.log (not published)`. The code and logs above are published and should be linked.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | <2025 n64 -0.077R PF0.73; 2025+ n42 +0.032R PF1.15 |
| Rerun, recorded clock | n=64 PF 0.73; n=42 PF 1.15 |
| Rerun, true UTC | same, clean clock |

## Verdict
VERIFIED. Both slices are INSUFFICIENT SAMPLE. Not a test of FINAL_v4: it uses the classic floor R3 and S3 on M15 bars, while FINAL_v4 uses R3 = PP + (H - L) on H1 (found by the second release review).

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
