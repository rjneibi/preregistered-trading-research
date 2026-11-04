# Methodology

This describes the rules used in the audit and the later research programmes. Earlier work was looser, and each experiment README states what applied to it.

## Preregistration

A rule, its parameters, splits, costs and gates are written down and frozen before the first run. After that, only bug fixes are allowed, each logged with before and after. A change to a rule is a new variant and goes in the ledger. Blind predictions were recorded where the protocol asked for them, and some were wrong. The E4 spread prediction is one.

The holdout is read once per hypothesis. A second read marks it `CONTAMINATED`.

Limit: this repository starts with a fresh git history, so preregistration dates for past work rest on the audit's private commit log and the file hashes listed in [audit/CHANGES.md](audit/CHANGES.md), not on public timestamps. Only material pushed here, such as the forward freeze content hash, carries a public timestamp.

## Splits

Audit experiments use time-ordered slices per instrument: development is the first 50%, validation the next 20%, and holdout the last 30%, by calendar span of the usable data. A slice is only reached if the one before passed. Slices not reached stay unevaluated. See [audit/prereg/COMMON.md](audit/prereg/COMMON.md).

## Gates

On each slice, net of costs:

| # | Gate |
|---:|---|
| 1 | PF >= 1.20 |
| 2 | PF at 2x costs >= 1.00 |
| 3 | n >= 100 |
| 4 | Random-entry twin: same count and holding time, 2,000 draws, one-sided p < 0.05 |
| 5 | On holdout only: deflated Sharpe >= 0.95 at the ledger trial count |

A slice with n below 100 is `INSUFFICIENT SAMPLE`. That stops progress but is not called a fail. A pass means a candidate for the forward test and nothing more.

## Costs

Costs come from measured spreads where possible. The gold cost matrix holds the spread by year and hour. Rules are read at 1x, 1.5x and 2x. A flat assumed cost overstated FINAL_v3 and FINAL_v4, which is why both are shown at each basis.

## Clock

HistData gold stamps run UTC+1 for part of each year. Through 2018 the shift follows US switch dates, and from 2019 EU dates. This was measured against Dukascopy on every trading day from 2013 to 2026. The years 2010 to 2012 have no Dukascopy overlap, so they are assumed to follow US dates and are labelled ASSUMED-CLOCK.

The correction is in [src/clock.py](src/clock.py) with tests in [tests/test_clock.py](tests/test_clock.py). Original stamps are kept beside the corrected results. See [audit/findings/CLOCK_BUG.md](audit/findings/CLOCK_BUG.md).

## Multiple testing

| Tool | Use |
|---|---|
| Trial ledger | One variant is one distinct rule, parameter set and market that produced a result, looked at or not. [How the count is built](audit/stats/TRIAL_COUNT.md) |
| Deflated Sharpe | Primary DSR at the full ledger count. Secondary DSR at the programme count, reported and not deciding. A third column uses N as dated when the result was made |
| PBO and CSCV | Probability of backtest overfitting across combinatorial splits |
| White's Reality Check, Hansen's SPA | Best-of-N selection against a benchmark |
| PSR, MinTRL | Probabilistic Sharpe and the sample length a Sharpe needs |
| Random twins | Same entry count and holding time at random times. Run-shuffle twins keep streak structure |

DSR here is an order of magnitude. Trial Sharpe variance uses the null value 1/T because not all trial Sharpes are on disk, which understates the hurdle. N counts near-duplicates as independent, which overstates it.

## Robustness checks

- Lookahead: truncate the data and confirm earlier signals do not change.
- Delay: move entry and exit one bar later.
- Same-bar ordering: rerun with the pessimistic stop-first rule.
- Known-answer tests: a second engine, gated on 19 known-answer tests.
- Spot checks: trades replayed by hand or by script against the bars.
- Walk-forward and purged cross-validation where the programme specified them.

## Audit verdicts

| Verdict | Meaning |
|---|---|
| VERIFIED | Trade count exact and P&L within 0.5% on rerun, or the stored output is identical |
| VERIFIED-WITH-CORRECTIONS | Holds after a stated correction |
| REPRODUCES-BUT-FRAGILE | Numbers exact, but fails the ledger-count DSR or a robustness check |
| NOT-REPRODUCIBLE | A rerun does not match within tolerance |
| INVALID | The result comes from a defect such as lookahead |
| UNVERIFIED | No file or no run backs the number |

## Determinism

Seeds are fixed, package versions are pinned, and `PYTHONHASHSEED=0` is set. Input files are hashed in [data/manifest.csv](data/manifest.csv), and output hashes are checked by `make audit`. See [REPRODUCE.md](REPRODUCE.md).
