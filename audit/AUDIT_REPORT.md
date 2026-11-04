# Audit report

Dated 2026-10-31. A verified result means the code does what its spec says on the stated data, with realistic costs and no lookahead, and that it reproduces. It says nothing about future returns.

## Executive summary

**No strategy in this programme has a verified edge.** Most results weakened under a correct clock and measured costs. Four numbers reproduce exactly but are fragile. One of them, TUNE-1-DIP, never passed its registered test and is the same rule as XM-1-A1, so there are three distinct rules. None clears the deflated Sharpe at the full trial count, though that gate needs a t-statistic near 6.2 and failing it alone says little.

**What was verified.** Of 96 registry entries, 78 were audited and 18 excluded as analyst-derived. 38 are VERIFIED, 24 VERIFIED-WITH-CORRECTIONS, 4 REPRODUCES-BUT-FRAGILE, 1 INVALID and 11 UNVERIFIED. A verdict grades the stored claim, so a VERIFIED failed strategy has a confirmed failure.

**What failed.**
- All gold rules. On true UTC, H1 falls from PF 1.130 to 1.009. H-B, the rule behind FINAL_v3 at measured costs, falls from 1.376 to 1.040.
- All new experiments: pairs, silver transfer, news-window execution and the two indicator rules. No pairs or FX cell got past its development slice, so validation and holdout were not evaluated for them.
- H3-SILVER, frozen in July and never run, failed its validity gate. The spread's half-life is 504 hours against a limit of 240, and most of that reading comes from month-end beta jumps.

**What changed most.**
- The gold file's timestamps run an hour ahead for 62.1% of bars. `findings/CLOCK_BUG.md` documents this on 3,474 days. Results that looked close to passing were partly a clock effect, and four narratives were retired.
- TVS-1's stored search cannot be replayed because its seed used a salted hash. Its 1,020 sampled configs re-evaluate exactly, and a fresh draw also gives 0 of 20.
- The trial count rose from 114,500 to 179,000.
- Daily ETF prices were not split-adjusted. TUNE-1-DIP HOLD-M falls from PF 1.59 to 1.36. Reruns on adjusted prices move no verdict.

**What is still unknown.**
- 2010-2012 clock, labelled ASSUMED-CLOCK. No pass or fail moves without those years.
- Whether the four fragile results hold forward. They are frozen in `FORWARD_TEST.md` and reported monthly whatever happens.
- iFVG was not tested during the audit, because its spec had not been received. It is listed in FUTURE_WORK.md. CHANNEL-B-SCORE stays UNVERIFIED because its scored file is missing.

## Infrastructure checks

Details are in `infrastructure/PHASE_B_REPORT.md`, with corrections at its top.

| Check | Result |
|---|---|
| Known-answer engine tests | 19 of 19 pass |
| Clock, all data files | One defect: HistData gold. All others clean |
| Lookahead truncation | Clean, after the harness was fixed |
| Delay test | PF falls about a quarter for A1 and SW-1 with a one-bar delay, which points to execution sensitivity, not a leak |
| Same-bar ordering, TA-LAB | Both orderings run. No row at or below zero turns positive. Rows above zero fall from 89 to 53 |
| Gap fills | Tiny effect, no verdict moves |
| Spreads around news | XAU first-minute median 1.49x NFP, 1.43x CPI and 1.51x FOMC against same-hour non-event days of the same year |
| Data holes | US500, US30, US2000 and USTEC have no bars from 2025-07-16 to 2025-09-09. DE40 has a 48-day hole. Indicators run across it by bar count |
| Clean rerun, `make audit` | All 70 stages pass from a fresh clone and fresh environments. On the audit's own run one output file, `phaseE/e4_spreads.json`, differed in formatting only, with every value equal. After its committed copy was replaced with the run's bytes, the comparison read 74 same, 0 different (DECISIONS 59). The release's own clean run is in REPRODUCE.md. `phaseC/deferred_checks.json` cannot be regenerated because its inputs were fetched once and not kept. `make` was not installed, so the target ran through `tools/make_audit.sh`. An outside reader needs the data first, see REPRODUCE.md |

## Verdicts

`VERDICTS.md` has every entry, the named gate failures for every PF above 1.1, DSR at both counts, and the ASSUMED-CLOCK table.

FINAL_v3 (PF 1.254) and FINAL_v4 (PF 1.145) need care. Both use a flat assumed cost. FINAL_v3 at measured costs is H-B, PF 1.040, which fails its gates, listed in the gate table of VERDICTS.md. FINAL_v4 at matrix cost reads PF 0.90. E4 confirms both at 1.056 and 0.898.

| Result | Stored | Primary DSR | Secondary DSR | DSR at dated N | Other weakness |
|---|---|---:|---:|---:|---|
| XM-1-A1 | PF 2.37, n=124 | 0.29 | 0.93 | 0.71 | In market 11% of days, with a similar Sharpe to buy-and-hold and a smaller drawdown; PF 1.80 with one-bar delay |
| SW-1 | PF 1.74, n=397 | 0.21 | 0.87 | 0.66 | PF 1.29 with one-bar delay; PF 1.54 without 2020 |
| EDGE-1-F6 | Sharpe 1.52, 3,284 days, 2017-2026 | 0.52 | 0.99 | 0.93 | Sharpe 1.36 on perpetuals with funding; Sharpe 0.33 since 2025; coins picked in hindsight |
| TUNE-1-DIP | PF 3.05, n=122 | 0.49 | 0.70 | 0.54 | 0 of 3 finalists passed; same rule as XM-1-A1; holdout CONTAMINATED; ledger DSR 0.14 averaged by week |

## Bugs and their effect

Every number that changed is in `CHANGES.md`, old beside new. Main items:

| Bug | Where | Effect |
|---|---|---|
| Gold stamps read as UTC | Goldbot, zone-flip, DR, FR families | Most headline PFs fall and some rise. No verdict flips to a pass |
| Look-ahead in sweep build | TA-LAB rounds 4, 8, 9 | Original figures INVALID |
| Salted seed | TVS-1 Phase 2 | Search not replayable, conclusion stands |
| Partial cost matrix | H-P, SZ, H-R, H-M, H-S, FR-M | Stored numbers depend on the date of the matrix |
| Flat assumed cost | FINAL_v3, FINAL_v4 | PF overstated against measured spreads |
| Unadjusted splits | Daily ETF files in cross-market and TUNE-1 | One EWJ trade booked +295%. HOLD-M PF 1.59 becomes 1.36. No verdict moves |

The audit made mistakes too, all logged: a first clock fix that was wrong, a rewritten file in an original folder (byte-identical, proven in DECISIONS 34), a weak lookahead harness, an overstated gap patch, and bugs in its own new experiment code. The fresh review caught several of those: E4 first used the wrong cost basis for FINAL rules, E1 dropped 35 of 139 months, a rule change in E1 was logged as a bug fix, and E1 and E7 counted trades past the slices they had not evaluated. `REVIEW_F.md` has every finding. All were fixed and logged.

## New experiments

Prereg commit 0fab84c, frozen before any experiment data was read.

| ID | Result | Reading |
|---|---|---|
| H3-SILVER | FAILED at validity gate | Half-life 504h is mostly beta jumps. Fits valid in 4.4% of months, which is mostly test power |
| E1 pairs | 7 cells INSUFFICIENT SAMPLE, 2 FAIL at dev | Cointegration passes both tests in 3.6%, 4.7% and 3.1% of months, about the false-positive rate of a 5% test |
| E2 silver | FAILED | H1 PF 0.487, FINAL_v3 0.683, FINAL_v4 0.450 |
| E3 portfolio | Descriptive only | Correlations near zero between trend and dip streams. Combined Sharpe 1.78 is hindsight-scaled and not a result |
| E4 news | FAILED | H1 PF 1.008, FINAL_v3 1.056, FINAL_v4 0.898. Few trades enter in a window, and spreads rose far less than the blind prediction of 3x to 6x |
| E5 crypto | Cost correction | F6 Sharpe 1.36 to 1.49. Adding 8 collapsed coins gives 1.51, so survivorship is only partly tested |
| E6 paper | INSUFFICIENT SAMPLE | 6 of 19 demo trades matched, median exit gap $11.66 |
| E7 indicators | FAILED or INSUFFICIENT SAMPLE | FX PF 0.87 and 0.80 at dev. Gold n=26 at dev |

E8, a Google Trends test, was skipped by decision because the data is not point-in-time. iFVG was blocked.

## Limitations

- DSR is an order of magnitude. It uses the null trial variance, because trial Sharpes are not all on disk, and it counts near-duplicate variants as independent. Those errors pull opposite ways.
- Split adjustment is detected from price jumps, so a few of the 27 events may be real moves or data-inception jumps. Reruns that say exact were exact on raw prices.
- The audit departed from its preregistrations in the ways listed in DECISIONS 53.
- E1 and E2 use M1 spreads for silver, which understates peak spread.
- E4 has CPI dates only for 2015 and 2025-26.
- E5 has no depth-based slippage, because no free historic order-book data exists.
- E6 has 19 trades, and the backtester has no trailing stop.
- Forward bars for index rules come from Dukascopy, not the original broker demo feed. Rule code matches the audited rewrites on the same bars.
- FR-L's small-sample figure and CHANNEL-B-SCORE stay out of every summary. Both are UNVERIFIED, and the FR-L figure is also INSUFFICIENT SAMPLE. FR-L's stored reference run is graded separately in `VERDICTS.md`.
