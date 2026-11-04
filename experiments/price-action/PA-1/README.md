# PA-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** 6 patterns have edge.

Family: price action. Market: XAUUSD. Timeframe: H1/H4/D1. Idea source: classic patterns. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Six textbook price-action patterns were tested on gold on H1, H4 and D1 bars, 18 tests in all. Definitions were fixed before the run, with no tuning. Each pattern is compared with "twins": the same trades with a random direction ([PREREG.md](../../../originals/gann_bot_500/research/price_action/PREREG.md); [pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py) line 1). All 18 failed.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): H1, H4 and D1 bars built in UTC from M1. Trades are walked on M1 ([pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py) lines 38-49, 162). A bar needs at least 50% of its minutes on H1 and H4, and at least 600 minutes on D1 (line 42).
- Data source and file(s): `d_revival/m1.npz`, loaded by [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py). It joins HistData M1 (2010-01 to 2026-06-19) with MetaTrader 5 broker M1 from `ta_lab/data/XAU_M1.npy` for later months, stored in broker time (data.py lines 1-2, 14-26). pa1.py converts it to UTC with a fixed US-DST offset rule (lines 16-29). Manifest: `m1.npz` and `XAU_M1.npy` are group `broker_mt5`; the HistData CSV is `histdata_xau` ([data/manifest.csv](../../../data/manifest.csv) lines 427, 428, 511).
- Period: 2010-01 to 2026-10 (data.py line 1).
- In-sample / out-of-sample: no fitting. Three gate windows: A = 2010-2017, B = 2018-2026, C = 2023 onward. C overlaps B ([pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py) line 153).

## Rules
- Entry (pattern on completed bar i; [PREREG.md](../../../originals/gann_bot_500/research/price_action/PREREG.md); pa1.py lines 55-140):
  - PIN: lower wick ≥ 2/3 of range and body in the top third, so long (mirror short). Range ≥ 0.5 × ATR.
  - PINX: a PIN whose wick makes a new 20-bar low (long) or high (short).
  - ENG: prior bar of the opposite colour, body of i covers body of i-1, after a 3-bar move against (c[i-1] < c[i-4] for long).
  - IB: inside bar; OCO stop entries at the mother-bar high/low for the next 3 bars.
  - NR7: narrowest range of 7; OCO stop entries at bar i's high/low for the next 3 bars.
  - SFP: high above the prior 20-bar high with the close back below it, so short (mirror long).
  - PIN, PINX, ENG and SFP enter at the next bar open. IB and NR7 fill at the level, or at the M1 open if price gapped through. If both OCO sides fill on one M1 bar, the trade is skipped.
- Exit (stop, target, time):
  - Stop: the bar extreme (PIN, PINX, SFP), the lowest low of bars i-1 and i (ENG), or the other side of the range (IB, NR7). Floored at 0.25 × ATR (pa1.py lines 123, 137).
  - Target: 2R (line 95).
  - Time: close after 10 bars of the timeframe (line 115).
  - If one M1 bar holds both stop and target, the stop is taken.
- Filters: one position at a time per pattern × timeframe.
- Position sizing: results in R (P&L ÷ stop distance), per trade (pa1.py lines 156-157).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | Wilder 14 per timeframe, seeded by the 14-bar mean | [pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py) lines 47-49 |
| PIN wick / body | wick ≥ 2/3 range; body in outer third; range ≥ 0.5 ATR | pa1.py lines 62-68 |
| PINX / SFP lookback | 20 bars | pa1.py lines 66-68, 83 |
| ENG prior move | 3 bars | [PREREG.md](../../../originals/gann_bot_500/research/price_action/PREREG.md) |
| IB / NR7 entry window | 3 bars; NR7 = narrowest of 7 | PREREG.md |
| Stop floor | 0.25 × ATR | pa1.py lines 123, 137 |
| Target / time stop | 2R / 10 bars | pa1.py lines 95, 115 |
| Twins | 20 seeds, random direction, rng seed 11 | pa1.py lines 165-166 |

## Costs
$0.40/oz round trip, subtracted before dividing by risk. Stress cost $0.80/oz. A $0.22 "IC" column is shown for information ([pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py) lines 12, 156-157). No financing.

## Tuning and selection
- Search: none. 6 patterns × 3 timeframes, all with fixed definitions.
- Configurations run (counted from the code/results): 18 ([recorded log](../../../audit/phaseC/logs_L1/recorded.price_action.pa1_py.log), 18 lines). Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 109, n_variants): 18. They agree.
- How the reported variant was chosen: no variant was chosen. D1 IB is quoted because it came closest.
- Preregistered: yes ([PREREG.md](../../../originals/gann_bot_500/research/price_action/PREREG.md), sha 2a0618d57046 per README). The PASS rule per test requires: net avg R > 0 in each of A, B and C; real − twin ≥ 0.05R in each; stress-cost avg R > 0 in B; and overall t (real vs twin) ≥ 2.8 (pa1.py lines 168-177). One small deviation: the prereg says a bar needs ≥ 50% of its minutes, but D1 bars need only 600 of 1,440 (pa1.py line 42).

## Results
All figures at $0.40 cost, in R.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All 18 tests | 70 to 9,404 per test | 18/18 FAIL; no test has t ≥ 2.8 | [recorded.price_action.pa1_py.log](../../../audit/phaseC/logs_L1/recorded.price_action.pa1_py.log) |
| D1 IB (closest) | 387 (A 185 / B 202 / C 83) | net +0.134R, win 47%, t +2.15, so FAIL on t. Window C n=83 is INSUFFICIENT SAMPLE | same |
| D1 NR7 | 471 | net +0.101R, t +1.21, FAIL | same |
| D1 PINX | 70 | net +0.115R, t +0.83, FAIL. INSUFFICIENT SAMPLE | same |
| H1 patterns | 1,678 to 9,404 | net -0.108R to -0.207R, all FAIL | same |
| Audit, true UTC, D1 IB | 387 | net +0.137R, t +2.24, FAIL | [true.price_action.pa1_py.log](../../../audit/phaseC/logs_L1/true.price_action.pa1_py.log) |
| Audit, true UTC, all | 18 tests | 18/18 FAIL | same |

Verdict: original FAILED; audit VERIFIED, reruns exact ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 68).

## Code and how to rerun
- Code: [pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py), [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py), prereg [PREREG.md](../../../originals/gann_bot_500/research/price_action/PREREG.md). Logs: [recorded](../../../audit/phaseC/logs_L1/recorded.price_action.pa1_py.log), [true UTC](../../../audit/phaseC/logs_L1/true.price_action.pa1_py.log), [without 2010-2012](../../../audit/phaseC/logs_L1/no1012.price_action.pa1.py.log).
- Audit rerun stage: `l1_queue` (`recorded price_action pa1.py`, `true price_action pa1.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); `no1012_run` for the 2010-2012 sensitivity.
- Public data enough? Partly. HistData (`histdata_xau`) covers 2010-01 to 2026-06-19. The months after that come from broker M1 (`broker_mt5`, `ta_lab/data/XAU_M1.npy`), and the cached `d_revival/m1.npz` is itself listed as `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv) lines 427, 511).

## Corrections from the release review
- "Data: 2010-26" leaves out that the series is HistData joined with broker MT5 M1 after 2026-06-19, and that the cached file is a broker-group file ([d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2, 14-26).
- "Costs: see prereg" should state the costs: $0.40/oz round trip, $0.80 stress, $0.22 shown ([pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py) line 12).
- The results give only the best cell. The other D1 cells and all H1/H4 cells are in the log, and all are negative or below the t gate.
- "D1 IB n387 +0.134R" hides that window C has n=83 (INSUFFICIENT SAMPLE). D1 PINX (n=70) is also under 100.
- The provenance cites only `DECISIONS.log (not published)`. The code and prereg are published: [pa1.py](../../../originals/gann_bot_500/research/price_action/pa1.py), [PREREG.md](../../../originals/gann_bot_500/research/price_action/PREREG.md).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 18/18 FAIL; D1 IB n387 +0.134R t=+2.15 |
| Rerun, recorded clock | 18/18 FAIL; D1 IB +0.134R |
| Rerun, true UTC | +0.137R |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
