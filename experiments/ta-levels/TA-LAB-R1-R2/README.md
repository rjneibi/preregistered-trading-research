# TA-LAB-R1-R2

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-12. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Pivots, fib and Asia breakouts have edge.

Family: TA levels. Market: XAUUSD. Timeframe: M15. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Round 1 asked whether any classic chart method makes money on its own on gold M5 over about 17 months. Each method got the same two exits and was judged on a train period (before 2026-02-01) and a test period (after). Round 2 took eight of the round-1 methods to about four years of M15 bars, with one exit, and reported each calendar year. Random entries were the baseline in both rounds. Source: [round1.py](../../../originals/gann_bot_500/research/ta_lab/round1.py) lines 1-3; [round2.py](../../../originals/gann_bot_500/research/ta_lab/round2.py) line 1.

## Instruments and data
- Instruments: XAUUSD ([lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) lines 3, 29).
- Timeframe(s): round 1 M5 (round1.py line 12); round 2 M15 (round2.py line 3). The round-2 log header prints "M5" because the label is hard-coded in round1.py line 23. The data loaded is M15.
- Data source and file(s): broker MT5 demo export, `research/ta_lab/data/XAU_M5.npy` and `XAU_M15.npy` (manifest group `broker_mt5`, access `broker`, not published; [data/manifest.csv](../../../data/manifest.csv) lines 512-513). Timestamps are shifted to UTC by the loader: winter bars get +1 h (lab.py lines 3-5, 29-38).
- Period: round 1, 2025-05-05 to 2026-10-12. Round 2, 2022-07-11 to 2026-10-12 ([recorded.ta_lab.round1_py_M5.log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round1_py_M5.log) line 1; [recorded.ta_lab.round2_py.log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round2_py.log) line 1). Each file holds 99,999 bars ([data_profile.json](../../../audit/infrastructure/data_profile.json) keys `talab_xau_m5`, `talab_xau_m15`).
- In-sample / out-of-sample: round 1, TRAIN before 2026-02-01 and TEST after (round1.py line 18). Round 2, no split; results by calendar year (round2.py lines 15-18).

## Rules
- Entry (round1.py lines 32-164):
  - Random: one order per UTC day at a random bar between 07:00 and 17:00 UTC, market at that bar's open; direction random, or the sign of the H1 trend slope in the "with trend" variant. Stop 1 ATR.
  - Fib 38.2 / 50 / 61.8: on each confirmed zigzag leg (reversal of 2.5 ATR) at least 5 ATR long, a limit order at the retracement level, waiting up to 24 h. Stop at the 78.6% level (38.2 and 50) or 88.6% (61.8).
  - Asia sweep fade: Asia range is 00:00-06:00 UTC (at least 2.5 h of bars). From 06:00 to 16:00, a bar that wicks beyond the range and closes back inside triggers a fade at the next open. Stop $0.30 beyond the wick. At most one per side per day.
  - Asia breakout: the first bar from 06:00 to 16:00 that closes beyond the Asia range triggers a trade with it at the next open. Stop at the range midpoint. One per day.
  - Pivot S1/R1: classic floor pivots from the previous UTC day. Buy limit at S1, sell limit at R1, valid to day end. Stop halfway from S1 to S2 (R1 to R2). "With trend" takes only the side of the H1 slope.
  - Round $25 with trend: at the first bar after 06:00, a limit at the next $25 level below (buy) or above (sell), with the trend only. Stop 1 ATR. Waits 10 h.
- Exit (stop, target, time) ([lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) lines 75-133):
  - Ladder 0.6R: each time the best price reaches +k x 0.6R, the stop moves to +k x 0.6R.
  - TP2R+BE (round 1 only): take profit at 2R, stop to breakeven at +1R.
  - Time cap: 288 bars in round 1 (24 h at M5, lab.py line 76 default); 96 bars in round 2 (24 h at M15, round2.py line 13).
  - Intrabar order is pessimistic: the stop is checked before any favourable move. On a limit fill bar the favourable extreme is ignored (lab.py lines 9-10, 108-112).
- Filters: trades with initial risk of $0.05 or less are skipped (lab.py line 101). One trade at a time (lab.py line 86).
- Position sizing: none. Every result is in R, the trade's own initial risk (lab.py lines 8-9, 130).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | 14-bar Wilder-style, scaled by sqrt(bars per hour) to approximate H1 ATR | lab.py lines 44-53; round1.py line 17 |
| Trend | EMA of 50 H1-equivalent bars; slope = sign vs 4 h earlier | round1.py lines 28-29 |
| Zigzag reversal / minimum leg | 2.5 ATR / 5 ATR | round1.py lines 45, 69 |
| Fib entry / stop | 38.2 / 78.6; 50 / 78.6; 61.8 / 88.6 | round1.py lines 170-172 |
| Asia window / trade window | 00:00-06:00 / 06:00-16:00 UTC | round1.py lines 86-97 |
| Pivot | P=(H+L+C)/3, R1=2P-L, S1=2P-H, R2=P+(H-L), S2=P-(H-L) | round1.py lines 142-144 |
| Round number step | $25 | round1.py line 153 |
| Ladder step | 0.6R | round1.py line 183; round2.py line 13 |
| TP / BE | 2R / at +1R | round1.py line 184; lab.py lines 115-120 |
| Random seed | 7 | round1.py line 21 |

## Costs
Per-bar recorded spread, floored at $0.20 ([lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) lines 5-6, 39). A buy fills at open + spread; a sell exits at price + spread (lab.py lines 91, 106-107, 129). No commission or slippage is added in rounds 1 and 2.

## Tuning and selection
- Search: no parameter search. Round 1 ran 10 fixed methods x 2 exits (round1.py lines 167-187). Round 2 ran 8 of those methods with the ladder exit only (round2.py lines 11-13). How the 8 were picked for round 2: Not recorded in the published files (the round-2 docstring calls them "the round-1 candidates").
- Configurations run (counted from the code/results): 28 (20 in round 1, 8 in round 2), of which 4 are random baselines. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row TA-LAB-R1-R2, n_variants): 5, marked "minimum". The code ran more than the ledger counts.
- How the reported variant was chosen: no variant was chosen. The study rejected the methods by comparing them with the random baselines. The figures on the README are round-2 "ALL" rows.
- Preregistered: no.

## Results
Round 2 (M15, 2022-07-11 to 2026-10-12, ladder 0.6R), stored rerun [recorded.ta_lab.round2_py.log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round2_py.log):

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Random, any direction | 1,261 | +0.072R/trade, PF 1.18 | round2 log |
| Random, with H1 trend | 1,250 | +0.098R, PF 1.26 | round2 log |
| Asia breakout | 782 | -0.190R, PF 0.62 | round2 log |
| Pivot S1/R1 | 847 | +0.043R, PF 1.10 | round2 log |
| Pivot S1/R1 with trend | 486 | +0.161R, PF 1.45 | round2 log |
| Fib 61.8% | 439 | +0.062R, PF 1.16 | round2 log |
| Fib 50% | 524 | +0.048R, PF 1.13 | round2 log |
| Asia sweep fade | 1,123 | +0.185R, PF 1.44 | round2 log |
| Pivot S1/R1, pessimistic same-bar rule A | 853 | -0.008R, PF 0.98 | [pessA.round2_py.log](../../../audit/phaseC/logs_talab/pessA.round2_py.log) |
| Pivot with trend, pessimistic rule A | 488 | +0.104R, PF 1.29 (random with trend: n=1,261, +0.043R) | pessA.round2_py.log |

Round 1 (M5, ladder 0.6R, TRAIN / TEST), [recorded.ta_lab.round1_py_M5.log](../../../audit/phaseC/logs_L1/recorded.ta_lab.round1_py_M5.log). Every slice below has fewer than 300 trades and most have fewer than 150; all slices under 100 are INSUFFICIENT SAMPLE.

| Slice | Trades (n) TRAIN / TEST | Result TRAIN / TEST | Source file |
|---|---|---|---|
| Random, any direction | 223 / 204 | +0.028R PF 1.07 / +0.135R PF 1.38 | round1 log |
| Asia breakout | 129 / 109 | -0.228R PF 0.57 / -0.276R PF 0.49 | round1 log |
| Pivot S1/R1 | 151 / 134 | -0.003R PF 0.99 / +0.073R PF 1.20 | round1 log |
| Fib 61.8% | 95 / 91 | -0.059R PF 0.86 / +0.268R PF 2.06 (INSUFFICIENT SAMPLE) | round1 log |

The full round-1 table (both exits, all 10 methods) is in the round-1 log. The audit's gap rerun (stops fill at the open on a real gap) moves the round-2 rows by under 0.5R in total net: e.g. pivot S1/R1 net +36.8R to +36.0R ([gap2.round2_py.log](../../../audit/phaseC/logs_talab/gap2.round2_py.log)). Summary of the pessimistic reruns: [talab_pess.json](../../../audit/phaseC/talab_pess.json).

## Code and how to rerun
- Code: [lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py), [round1.py](../../../originals/gann_bot_500/research/ta_lab/round1.py), [round2.py](../../../originals/gann_bot_500/research/ta_lab/round2.py). Audit variants: [talab_gap.py](../../../audit/phaseC/talab_gap.py), [talab_pess.py](../../../audit/phaseC/talab_pess.py).
- Audit rerun stage: `l1_queue` (jobs `recorded ta_lab round1.py M5` and `recorded ta_lab round2.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); `talab_gap_make`/`talab_gap_run`; `talab_pess_make`/`talab_pess_run`/`talab_pess_rep` ([run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? No. It needs `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv)).

## Corrections from the release review
- README "Timeframe: M15" and "Data: M15 2022-07 to 2026-10". Incomplete. Round 1 ran on M5, 2025-05-05 to 2026-10-12, with a train/test cut at 2026-02-01 (round1.py lines 12, 18; round-1 log line 1).
- README "Rules: Lock ladder 0.6R." Incomplete. Round 1 also ran a second exit, TP 2R with breakeven at 1R (round1.py lines 183-184). The entry rules for the ten methods are not on the page (round1.py lines 32-164).
- README "Parameters and tuning: several. Variants counted in the ledger: 5." The code ran 28 method-exit cells (20 + 8).
- README "Costs: see lab.py". The cost is the per-bar spread floored at $0.20, with no commission (lab.py lines 5-6, 39).
- README results give mean R with no trade counts. The counts are n=782 (Asia breakout), 847 (pivots), 439 (fib 61.8) and 1,261 (random) (round-2 log).
- README results leave out two round-2 rows that beat their random baseline in the stored log: pivot S1/R1 with trend (n=486, +0.161R vs random with trend +0.098R) and the Asia sweep fade (n=1,123, +0.185R). The page should show them and state why the study still counts as FAILED. That reason is Not recorded in the published files.
- README caveat "Limit fill-bar bug had inflated pivots from +0.34R to +0.04R". The +0.34R figure is in no published file. The published lab.py already contains the fix (lines 111-112).
- README "`originals/gann_bot_500/research/ta_lab` (not published)". Wrong. The folder is published: lab.py and round1-12.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Asia breakout -0.19R; pivots +0.04R; fib 61.8 +0.06R vs random +0.07R |
| Rerun, recorded clock | -0.19R; +0.04R; +0.06R vs random +0.07R |
| Rerun, true UTC | same, clean clock |

## Verdict
VERIFIED. Real-gap fills change these by under 0.5R.

## Audit caveats
Limit fill-bar bug had inflated pivots from +0.34R to +0.04R.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/ta_lab](../../../originals/gann_bot_500/research/ta_lab)
