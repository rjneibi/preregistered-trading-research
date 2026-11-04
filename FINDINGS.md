# Findings

- **No strategy has a verified edge after audit.** Four numbers reproduce exactly but are fragile, and they rest on three distinct rules.
- **A clock bug changed the gold results, and most look worse on true UTC.** The HistData file runs an hour ahead of UTC on 62.1% of bars. On true UTC, H1 falls from PF 1.130 to 1.009.
- **The search was far larger than any one report suggests.** The ledger holds 179,000 variants, so a deflated Sharpe of 0.95 needs a t-statistic near 6.2.
- **Measured costs matter more than the rule.** FINAL_v3 reads PF 1.254 at a flat assumed cost and 1.040 at the measured cost matrix.
- **Every new experiment failed or lacked sample.** That covers pairs, silver transfer, news-window execution and two indicator rules.

A verdict grades the stored claim, so VERIFIED on a failed strategy means the failure holds. Nothing here is a statement about future returns.

## What held up

No rule passed everything. These are the closest, and each has a stated weakness.

| Result | Stored | DSR, full ledger | DSR, own programme | DSR at dated N | Other weakness |
|---|---|---:|---:|---:|---|
| XM-1-A1 | PF 2.37, n=124 | 0.29 | 0.93 | 0.71 | In market 11% of days, with a similar Sharpe to buy-and-hold. PF 1.80 with a one-bar delay |
| SW-1 | PF 1.74, n=397 | 0.21 | 0.87 | 0.66 | PF 1.29 with a one-bar delay. PF 1.54 without 2020 |
| EDGE-1-F6 | Sharpe 1.52 | 0.52 | 0.99 | 0.93 | Sharpe 1.36 on perpetuals with funding. Sharpe 0.33 since 2025. Coins picked in hindsight |
| TUNE-1-DIP | PF 3.05, n=122 | 0.49 | 0.70 | 0.54 | 0 of 3 finalists passed. Same rule as XM-1-A1. Holdout contaminated |

XM-1-A1 and SW-1 rest on broker bars that cannot be redistributed, so an outside reader cannot regenerate them here.

## What failed

| Area | Result |
|---|---|
| Gold rules | All failed. H-B, the rule behind FINAL_v3 at measured costs, falls from PF 1.376 to 1.040 on true UTC |
| FINAL_v3 | PF 1.254 at flat cost. At matrix cost 1.040, short of the 1.35 gate by 0.310 |
| FINAL_v4 | PF 1.145 at flat cost. About 0.90 at matrix cost |
| H3-SILVER | Failed its validity gate. Half-life 504h against a limit of 240h, mostly from month-end beta jumps |
| E1 pairs | 7 cells INSUFFICIENT SAMPLE, 2 FAIL at development. Cointegration passes both tests in 3.6%, 4.7% and 3.1% of months, about the false-positive rate of a 5% test |
| E2 silver transfer | H1 PF 0.487, FINAL_v3 0.683, FINAL_v4 0.450 |
| E4 news windows | H1 PF 1.008, FINAL_v3 1.056, FINAL_v4 0.898. Spreads rose about 1.5x, against a blind prediction of 3x to 6x, so that prediction was wrong |
| E7 indicators | FX PF 0.87 and 0.80 at development. Gold n=26, INSUFFICIENT SAMPLE |
| TVS-1 | 0 of 20. Its stored search cannot be replayed because of a salted seed, but the 1,020 sampled configs re-evaluate exactly and a fresh draw also gives 0 of 20 |

[NEGATIVE_RESULTS.md](NEGATIVE_RESULTS.md) lists every failed hypothesis.

## Corrections that changed numbers

| Bug | Effect |
|---|---|
| Gold stamps read as UTC | Most headline PFs fall and some rise. No verdict flips to a pass |
| Look-ahead in the sweep build | TA-LAB round 4 figures are INVALID |
| Flat assumed cost | FINAL_v3 and FINAL_v4 overstated against measured spreads |
| Partial cost matrix | Stored numbers depend on the date of the matrix |
| Unadjusted splits | One EWJ trade booked +295%. HOLD-M falls from PF 1.59 to 1.36. No verdict moves |
| Salted seed | TVS-1 search not replayable. The conclusion stands |

The audit made its own mistakes too. They are logged in [audit/REVIEW_F.md](audit/REVIEW_F.md), and no fix moved a verdict toward a pass.

## What is unknown

- **The 2010-2012 clock.** Those years are labelled ASSUMED-CLOCK. No pass or fail moves without them.
- **Whether the fragile rules hold forward.** They are frozen and tracked in [audit/FORWARD_TEST.md](audit/FORWARD_TEST.md). For the US500 rules, 100 trades take about 3.5 years for SW-1, at about 2.4 trades a month, and about 11 years for XM-1-A1, at about 9 trades a year.
- **iFVG.** Not specified and not tested. No spec is published in this release, see [FUTURE_WORK.md](FUTURE_WORK.md).
- **Excluded work.** 18 entries are counted in the ledger but not published or tested.

## Limits of the reading

- DSR is an order of magnitude. It uses the null trial variance and counts near-duplicate variants as independent, and those errors pull opposite ways.
- Index and ETF bars came from a broker demo feed, which can differ from other feeds.
- The crypto coin list was chosen in hindsight. Adding 8 collapsed coins gives Sharpe 1.51, so survivorship is only partly tested.
- E6 has 19 trades and the backtester has no trailing stop.
- The random-twin gate gives each twin trade a random side, so a long-only rule can beat it on market drift alone. That makes the gate easier to pass, so it cannot have caused a failure, but a pass on it says less for long-only rules. See [RESEARCH_AGENDA.md](RESEARCH_AGENDA.md), item 1.
