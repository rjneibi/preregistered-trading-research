# H-N

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** 1.5x sizing on news days is cost-validated.

Family: news sizing. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
H-N checks whether the H1 conviction trades that fall on news days (FOMC, NFP, CPI) keep a strong edge after measured costs. The live bot sized those days at 1.5x, and a FAIL was pre-committed to remove that multiplier. The test does not simulate any 1.5x sizing. It splits the existing H1 trade list into news-day and other trades, and computes the profit factor of the news-day subset ([hn_runner.py:3](../../../originals/gann_bot_500/research/goldbot/prereg/hn_runner.py), "Pure subset analysis ... no simulation").

## Instruments and data
- Instruments: XAUUSD, 1 lot per trade (inherited from H1).
- Timeframe(s): as H1: H1/H4 signals, M1 exits.
- Data source and file(s): the H1 trade list [results/verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv) and the calendar [fable-backtesting/calendar/news_days.json](../../../originals/gann_bot_500/fable-backtesting/calendar/news_days.json) ([hn_runner.py:18,28-30](../../../originals/gann_bot_500/research/goldbot/prereg/hn_runner.py)). The calendar holds 260 days, 2015-01-02 to 2026-07-03: 94 FOMC, 139 NFP, 29 CPI (news_days.json fields).
- Period: the H1 trade period, 2015-07-02 to 2026-06-10 on the recorded clock (verdict_trades.csv).
- In-sample / out-of-sample: none. Eras old (2015-06-19 to 2021-06-18) and new (2021-06-19 on) from the H1 trade list.

## Rules
- Entry: none of its own. A trade is a "news" trade when the UTC date of its signal time is in news_days.json ([hn_runner.py:29-31](../../../originals/gann_bot_500/research/goldbot/prereg/hn_runner.py)). The entry rules are those of [H1](../../../experiments/pivot-breakout/H1/README.md).
- Exit (stop, target, time): as H1 (TP 0.8 x ATR, SL 2.4 x ATR, 24h, hivol/lovol bail; [config.yaml:20-35](../../../originals/gann_bot_500/research/goldbot/config.yaml)).
- Filters: the news-day calendar. FOMC dates are exact 2015-2026; NFP uses a first-Friday rule; CPI is exact only for 2015 and 2025-26, and "2016-2024 CPI missing" (news_days.json `note`).
- Position sizing: 1 lot on every trade. No 1.5x multiplier is applied anywhere in the code ([hn_runner.py:27-42](../../../originals/gann_bot_500/research/goldbot/prereg/hn_runner.py)).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| News-day set | 260 UTC dates: FOMC 94, NFP 139, CPI 29 | news_days.json |
| Day match | UTC date of `event_ts` | hn_runner.py:30 |
| Base strategy parameters | as H1 | config.yaml:9-35 |

## Costs
The H1 cost columns, unchanged: matrix median (`net_med`) and p90 (`net_p90`), each 100 oz x [mean of entry and exit bucket spread + 0.5 x (entry + exit spread)] + $7 per lot ([cost_matrix.py:124-128](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py)). The prereg notes that the matrix has no news-window cells; p90 is the stand-in for news spreads ([spec.md](../../../experiments/news-sizing/H-N/spec.md), "Pinned inputs").

## Tuning and selection
- Search: none ("zero degrees of freedom", spec.md).
- Configurations run (counted from the code/results): 1. Ledger count (registry/trial_ledger.csv n_variants): 1, basis "minimum, see entry"; GB-45 maps to it. They agree.
- How the reported variant was chosen: not applicable.
- Preregistered: yes, [spec.md](../../../experiments/news-sizing/H-N/spec.md) (copy of `HN_PREREGISTRATION.md`, commit 56d89dd in private history, not verifiable here). Gates, all required: news PF >= 1.50 at median costs; news PF >= 1.20 at p90; each era news PF >= 1.10; n >= 60 ([hn_runner.py:43-49](../../../originals/gann_bot_500/research/goldbot/prereg/hn_runner.py)).

## Results
Dollar figures per 1 lot. All news-subset slices are under 100 trades: INSUFFICIENT SAMPLE.
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Recorded clock, news days, median costs | 66 | PF 1.443, win 80.3%, net $4,877; FAIL gate 1. INSUFFICIENT SAMPLE | [HN_run.json](../../../originals/gann_bot_500/research/goldbot/results/HN_run.json), [logs_recorded/hn_runner.log](../../../audit/phaseC/logs_recorded/hn_runner.log) |
| Recorded, news days, p90 / flat 20 pt | 66 | PF 1.342 / 1.857. INSUFFICIENT SAMPLE | same |
| Recorded, news days, old / new era | not recorded per era | PF 1.130 / 1.656 | same |
| Recorded, non-news days, median | 406 | PF 1.087 (descriptive) | same |
| True UTC, news days, median | 65 | PF 0.914, win 73.8%, net -$1,345; FAIL gates 1-3. INSUFFICIENT SAMPLE | [logs_true/hn_runner.log](../../../audit/phaseC/logs_true/hn_runner.log) |
| True UTC, news days, p90 / old / new | 65 | PF 0.85 / 0.72 / 1.03. INSUFFICIENT SAMPLE | same |
| True UTC, non-news days, median | not printed | PF 1.03 | same |
| "Partial PASS PF 1.53" (README) | not recorded | Not recorded in the published files | none |

## Code and how to rerun
- Code: [hn_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hn_runner.py); calendar builders [build_calendar.py](../../../originals/gann_bot_500/fable-backtesting/build_calendar.py), [news_calendar.py](../../../originals/gann_bot_500/fable-backtesting/news_calendar.py); base trades from [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py).
- Audit rerun stage: `goldbot_both` ([run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh), after `run_verdict`).
- Public data enough? Yes: group `histdata_xau` (to rebuild the H1 trades); the calendar is committed.

## Corrections from the release review
- "Hypothesis: 1.5x sizing on news days is cost-validated" and "Rules: FOMC/NFP/CPI days 1.5x" are wrong about what ran. No 1.5x sizing is simulated. The test is the PF of H1 trades on news UTC days versus the rest (hn_runner.py:3,27-42). The 1.5x multiplier is only what a FAIL was committed to remove.
- "News days" are not FOMC/NFP/CPI in full. CPI dates for 2016-2024 are missing; only 29 CPI days are in the set (news_days.json `note`, `cpi_n`). NFP is a first-Friday rule, not the exact release dates.
- "Stored: Partial PASS PF 1.53" has no source in the published files. No published log or JSON holds 1.53 for H-N, and the audit did not rerun H-N on the partial matrix ([run_goldbot_partial.sh](../../../audit/phaseC/run_goldbot_partial.sh) does not list hn_runner). The stored HN_run.json is the full-coverage FAIL, PF 1.443.
- "Gates: median PF>=1.50, p90, eras" is incomplete. The gates are p90 PF >= 1.20, each era >= 1.10, and n >= 60 (hn_runner.py:43-49).
- The file [calendar/cpi.csv](../../../originals/gann_bot_500/fable-backtesting/calendar/cpi.csv) is a zip (Office spreadsheet) container, not a CSV: its first bytes are `PK` and `[Content_Types]`. hn_runner.py does not read it; it reads news_days.json.
- The README links only DECISIONS.log (not published) and HN_run.json; the runner and calendar are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Partial PASS PF 1.53; full-coverage confirmation 1.44, FAIL |
| Rerun, recorded clock | n=66 PF 1.443, old 1.13 |
| Rerun, true UTC | n=65 PF 0.914, old 0.724 |

## Verdict
VERIFIED-WITH-CORRECTIONS. News-day narrative retired. Both slices are INSUFFICIENT SAMPLE.

## Audit caveats
Second case of a pass killed by the confirmation rerun. Killed the multiplier, not news-day trading.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HN_run.json](../../../originals/gann_bot_500/research/goldbot/results/HN_run.json)
