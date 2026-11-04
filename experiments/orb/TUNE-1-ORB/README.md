# TUNE-1-ORB

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-26. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Tuning improves ORB.

Family: ORB. Market: USTEC. Timeframe: M1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
TUNE-1 part 2 tried to tune the author's live USTEC 30-minute opening-range breakout (ORB-30) to a higher profit factor. An 800-cell grid was scored on USTEC M1 from 2022-07 to 2025-10-12 (DEV). Three finalists and the live ORB-30 were then read once on sealed data: USTEC from 2025-10-13 (HOLD-T), and US500 and US30 (HOLD-M). All three finalists failed.

## Instruments and data
- Instruments: USTEC (DEV, HOLD-T); US500 and US30 (HOLD-M) ([PREREG.md](../../../originals/gann_bot_500/research/tune1/PREREG.md), Part 2; [tune_orb.py:129-130](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).
- Timeframe(s): M1, converted from the broker server clock (Europe/Athens) to New York time; session 09:30-16:00 NY ([scalp_lab.py:35-46](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py); [tune_orb.py:26-38](../../../originals/gann_bot_500/research/tune1/tune_orb.py)). A day needs at least 300 bars, a bar at 09:30 or 09:31, and a bar at or after 15:31.
- Data source and file(s): MetaTrader 5 demo exports `cross_market/data/USTEC_M1.npz`, `US500_M1.npz`, `US30_M1.npz` (group `broker_mt5`, access `broker`, [data/manifest.csv](../../../data/manifest.csv) lines 315, 319, 325).
- Period: DEV = USTEC 2022-07-06 to 2025-10-12; HOLD-T = USTEC 2025-10-13 to 2026-10-13; HOLD-M = US500 and US30, 2012-08 to 2026-10 (PREREG.md). In code DEV is "all USTEC up to 2025-10-12" and HOLD-M is the full US500/US30 files, with no date limit ([tune_orb.py:16,92,130](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).
- In-sample / out-of-sample: DEV for all tuning; HOLD-T and HOLD-M read once for finalists and the live baseline. The prereg notes that SC-1 had already seen ORB-30 on US500/US30 (PREREG.md, Part 2 heading).

## Rules
- Entry: the opening range is the high and low of the first N minutes from 09:30 NY. Skip the day if (high - low)/high is below the minimum range. From 09:30 + N until the last-entry minute, the first M1 bar whose high is above the range high (buy) or whose low is below the range low (sell) triggers. If one bar breaks both sides, the day is skipped. Long-only configs skip the day on a downside break. Entry price = max(range high, bar open) for buys, min(range low, bar open) for sells ([tune_orb.py:41-58](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).
- Exit (stop, target, time): stop at the other side of the range or at the range midpoint. Target at 1R, 2R or 3R, or none (hold to the last bar of the session). Stop and target are checked from the bar after entry; if both are touched, the earlier bar wins and a tie goes to the stop ([tune_orb.py:59-73](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).
- Filters: minimum range 0.15% or 0.30% of price; side both or long only.
- Position sizing: none; each trade is a net return as a fraction of entry price ([tune_orb.py:74-75](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Range length N | 5, 15, 30, 45, 60 min | tune_orb.py:17 |
| Last entry (NY) | 11:00, 12:00, 13:30, 15:30, 16:00 (= until the close) | tune_orb.py:18 |
| Stop | other side of range, range mid | tune_orb.py:19 |
| Target | none (to 16:00), 1R, 2R, 3R | tune_orb.py:20 |
| Side | both, long only | tune_orb.py:21 |
| Minimum range | 0.15%, 0.30% of price | tune_orb.py:22 |
| Live baseline | N=30, until close, other side, no target, both, 0.15% | tune_orb.py:23 |
| Twin (HOLD-T) | same entries, random direction, 2,000 draws, seed 9 | tune_orb.py:128,136 |

## Costs
Cost per trade, in price units = 1.5 x the median in-session spread of that symbol's file (bars with spread > 0), charged once per trade; stop exits pay another 0.5 x that cost ([scalp_lab.py:43-45](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py); [tune_orb.py:69-75](../../../originals/gann_bot_500/research/tune1/tune_orb.py)). No commission or financing.

## Tuning and selection
- Search: the full product of the six lists above, 5 x 5 x 2 x 4 x 2 x 2 = 800 ([tune_orb.py:87-88](../../../originals/gann_bot_500/research/tune1/tune_orb.py)). DEV objective: robust PF = min PF of the first and second half of the config's trades (split by trade count, not by date), with n >= 100 in each half; plateau = median robust PF of the one-step neighbours in each dimension ([tune_orb.py:91-114](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).
- Configurations run (counted from the code/results): 800 ([orb_dev.csv](../../../originals/gann_bot_500/research/tune1/results/orb_dev.csv), 800 rows). Ledger count (registry/trial_ledger.csv n_variants): 800, basis "exact". They agree with the code. They do not agree with the prereg: PREREG.md lists 4 last-entry values (11:00, 12:00, 13:30, 15:30), which gives 640. The code adds 16:00 (960, "any time until the close"), the live baseline's value.
- How the reported variant was chosen: 138 configs had plateau >= 1.2 (orb_dev.csv). The three finalists in [orb_finalists.json](../../../originals/gann_bot_500/research/tune1/results/orb_finalists.json) are 30-min long to 13:30 (rank 1 by robust PF), 60-min long to 13:30 (rank 5) and 15-min long to 15:30 (rank 6). Ranks 2-4 are other 30-min long cells. No code writes orb_finalists.json, and no published file states the pick rule. The pick looks like one cell per range length, but that is not recorded. It was a choice by hand on DEV data.
- Preregistered: yes, [PREREG.md](../../../originals/gann_bot_500/research/tune1/PREREG.md) (dated 2026-10-26; the README cites tune_orb.py hash 94b34cd62eac. The published file's SHA-256 begins d552196a8250 (it holds path tokens), and what 94b34cd62eac refers to is not recorded in the published files). Deviation: the code grid has 5 last-entry values, the prereg 4. PASS = HOLD-T PF >= 1.2 and above the live ORB HOLD-T PF with n >= 100; HOLD-M pooled PF >= 1.1 and above live; twin p < 0.05 on HOLD-T ([tune_orb.py:145](../../../originals/gann_bot_500/research/tune1/tune_orb.py)).

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Live ORB-30, DEV | 719 | robust PF 1.23, PF 1.32, rank 118 of 800 | [recorded.tune1.tune_orb_py_dev.log](../../../audit/phaseC/logs_L1/recorded.tune1.tune_orb_py_dev.log) |
| O1 30m long, DEV | 375 | robust PF 1.429, PF 1.434, plateau 1.349 | orb_dev.csv |
| Live ORB-30, HOLD-T | 245 | PF 0.87, -3.57 bp/trade, twin p 0.761 | [orb_final.txt](../../../originals/gann_bot_500/research/tune1/results/orb_final.txt) |
| Live ORB-30, HOLD-M | 2,108 + 2,162 | US500 PF 1.08, US30 PF 1.08, pooled 1.08 | same |
| O1 30m long, HOLD-T / HOLD-M | 126 / 1,109 + 1,095 | PF 1.01, twin p 0.420 / pooled 1.10; FAIL | same |
| O2 60m long, HOLD-T / HOLD-M | 125 / 1,135 + 1,073 | PF 0.91, twin p 0.613 / pooled 1.10; FAIL | same |
| O3 15m long, HOLD-T / HOLD-M | 135 / 945 + 1,035 | PF 0.92, twin p 0.641 / pooled 1.21; FAIL | same |

The audit rerun is byte-identical ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 75; [recorded.tune1.tune_orb_py_final.log](../../../audit/phaseC/logs_L1/recorded.tune1.tune_orb_py_final.log)).

## Code and how to rerun
- Code: [tune_orb.py](../../../originals/gann_bot_500/research/tune1/tune_orb.py), [scalp_lab.py](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py) (`load_index`), [PREREG.md](../../../originals/gann_bot_500/research/tune1/PREREG.md), results in [tune1/results](../../../originals/gann_bot_500/research/tune1/results).
- Audit rerun stage: `l1_queue` (lines "recorded tune1 tune_orb.py dev" and "... final" in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)).
- Public data enough? No. It needs group `broker_mt5` (USTEC, US500, US30 M1), which is not published or fetchable ([data/MANIFEST.md](../../../data/MANIFEST.md)).

## Corrections from the release review
- "Rules: 800 grid" and "Parameters and tuning: 800" do not say the prereg froze a different grid. PREREG.md lists 4 last-entry values (640 cells); tune_orb.py:18 has 5 (800 cells). The extra value, 16:00, is the live baseline's. The page should say which grid was registered.
- "Market: USTEC" is incomplete. HOLD-M uses US500 and US30 (tune_orb.py:130).
- "Data: 2022-07 to 2026-10" gives no source. It is broker MT5 M1, not publicly available. HOLD-M runs over the full US500/US30 files, 2012-08 on (PREREG.md).
- "Costs: see code" and "Gates: see prereg" hide the facts: 1.5 x median in-session spread per trade, +0.5 x on stop exits; gates as above.
- How the 3 finalists were picked from 138 plateau configs is not recorded anywhere. The pick was made by hand on DEV.
- The README links only DECISIONS.log (not published). tune_orb.py, PREREG.md and the results are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0/3 PASS; live ORB-30 n245 PF 0.87 |
| Rerun, recorded clock | Live ORB-30 n=245 PF 0.87 |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Holdout CONTAMINATED. Byte-identical.

## Audit caveats
Sealed data now spent.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
