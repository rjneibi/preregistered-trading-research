# Phase B: infrastructure report

**Corrections from Phase C, 2026-10-31. The original text stands below.**

- B1: the rule "NY local + 5h" holds only through 2018. From 2019 the shift follows EU dates. The H1 true-UTC column below came from the
  first fix and is replaced by n=481, PF 1.009, old 0.831, new 1.114, p90 0.933, hour 20 at p90 n=102, PF 1.081, +$1,948. The share of bars shifted is 62.1%. See `../findings/CLOCK_BUG.md`.
- B2: real effect is tiny once only true gaps count. TA-LAB M5 goes from +38.7R to +38.6R. No verdict moves. Severity low.
- B3: closed. LBO's frozen config has no target exits, and CRT changes on 17 of 1,076 target exits, at most 0.005R per cell. No verdict moves.
- B4: **withdrawn.** `ta_lab` EU dates are correct. Its bars match Dukascopy on all 1,098 days.
- Lookahead: this harness stopped one row short, so a one-bar peek could pass. Rerun with the window closed, all rows stay clean (`lookahead_margin0.json`). The control now includes a one-bar peek (`../phaseC/lookahead2.py`).

Inputs were read only. Tests ran on copies in `audit/_copy` (not committed; rebuilt from the originals).
All runs use the goldbot venv listed in `requirements_goldbot_venv.txt`.

## Results

| Check | Result | Evidence |
|---|---|---|
| Existing test suites | All pass: goldbot 13, modules 18, flip_bot 15, crt_fvg 15, tvsearch 10, lbo 28 (2 skipped) | `existing_suites.log`; the flip_bot rerun with its helper modules printed 15/15 to the console only |
| Audit engine known-answer tests | 19 of 19 pass | `../engine/test_kat.py` |
| Cross-engine, 625 synthetic trades | goldbot and tvsearch match the audit engine exactly; 3 engines differ, see B2 and B3 | `cross_engines.json` |
| Truncation lookahead | Control flagged in 14 of 40 cuts. Seven other functions clean across about 248,000 signal comparisons | `lookahead.json` |
| Resampling vs native bars | 99.9% or better on each field | `resample_and_defects.json` |
| Data defects | No backward stamps in gold data, no non-positive prices, no bad OHLC. 3 and 13 backward stamps in US500 and USTEC M1 | `resample_and_defects.json` |
| Clock | One defect, B1 | `data_profile.json`, `clock_cross.json` |

## Defects

**B1. HistData is not UTC. Severity high.**
Stamps are NY local + 5h, which is UTC+1 during US daylight time (65.3% of bars).
Evidence: NFP spike at 13:30 in both seasons, true 12:30 in summer; 60-minute lag against Dukascopy in
every July sample and 0 in every January sample. The July docs, `goldbot/data.py` and `dr_backtest` treat it as UTC.
Live `flip_bot` uses true UTC, so these backtests did not test the rule as the bot trades it.

Measured on H1, rules unchanged. The recorded run reproduces exactly (472 trades, net $11,811.50, same gross on every trade).

| Metric, net at matrix costs | Recorded clock | True UTC |
|---|---|---|
| Trades | 472 | 478 |
| Full PF | 1.130 | 1.012 |
| Old era PF | 0.897 | 0.893 |
| New era PF | 1.276 | 1.077 |
| Full PF at p90 cost | 1.045 | 0.935 |
| Positive splits of 15 | 11 | 8 |
| Max drawdown | $7,108 | $11,291 |
| Hour 20 at p90 cost | n=110, PF 1.793, +$11,700 | n=98, PF 1.067, +$1,561 |

The H1 verdict (FAILED) stands and gets worse. Both runs are on 1.00 lot, and n=478 is one sample, so the gap also
shows how fragile the result is to a one-hour shift. The recorded run is a valid NY-anchored rule, mislabelled as UTC.
The hour-20 finding behind cycles 2 to 6 and H-20 was measured on stamps that are 19:00 UTC in summer. The rationale
written for it, the 20:00 UTC cash close, does not fit those trades.

**B2. `ta_lab/lab.py` never fills a stop at the gap price. Severity medium, optimistic.**
Gapped synthetic series: sum +9.00 vs +2.41 in the audit engine. Real effect to be measured in Phase C.

**B3. `lbo` and `crt_fvg` fill stops at the gap but targets at the target. Severity low, pessimistic.**
Gapped synthetic series: -52.55 vs +2.41, with an artificially high 1% gap rate. Both studies failed their gates.
The real size must still be measured, because a harsh engine weakens a FAILED verdict.

**B4. `ta_lab` DST uses EU dates for a US-linked broker clock.** About 3 weeks a year sit one hour off.

**B5. Bid-only bars miss short-side stops.** Already disclosed in H-20. Confirmed in `run_exits`.

**B6. Bid vs mid.** HistData sits $0.14 to $0.38 below Dukascopy mid, which fits bid. Costs are charged on top.

## Results now marked SUSPECT until rerun

- B1, HistData read as UTC: XAU-FLIP-RAW, XAU-R3S3-FADE, XAU-FINAL-V3, XAU-FINAL-V4, H1, H2, H-S, H-M, FR-M, FR-L, H-N, H-P, H-B,
  HR, SZ, HV, HCRT, HSW, CYCLES-1-10, DOOR-3, DR-EDGE-SCREEN, FORWARD-FLIP-DEMO spec figures. Each must confirm which loader it used.
- B2 and B4: all TA-LAB rounds.
- B3: LBO-1, CRT-FVG-1.

Not affected by B1 from the code read so far: D-REVIVAL, EXIT-2-FLIP, SWEEP-MTF-1, PA family and TA-LAB, which convert clocks explicitly.

## Not done in Phase B, carried into Phase C

Shift test; truncation for `cross_market`, `tvsearch`, `edge_lab` and `lbo` signals; sizing test on the live code path;
spread widening around rollover and news; triple-swap handling; Binance cross-source check;
coverage of the HistData gaps. No check in this report covers the PASS strategies yet.
