# Forward test

**Status: RUNNING. Monitored, no edge claimed.** Paper only. This reads public bars, places no orders and touches no broker account.

Nothing here predicts results. Each rule below is REPRODUCES-BUT-FRAGILE, and none has a verified edge.

## Freeze

| Field | Value |
|---|---|
| Freeze commit, private audit history | `ef9609220ed4fb5e12f1015a2c06741c475198d2` |
| SHA-256 of `forward/strategies.json`, LF line endings | `10bff07d109d08ed5f1a2290a530eda0ab1dc73af7c272c68358e0f62ccbdf75` |
| First public timestamp | Set when this repository goes public |
| Freeze time, UTC | 2026-10-31 15:29:00 |
| Rules, parameters, data source, cost model | `forward/strategies.json` |
| Update code | `forward/forward_update.py`, hash pinned in `strategies.json` |

The freeze commit is in the audit's private history, because this repository starts fresh. The public evidence is the content hash above, the code hashes inside `strategies.json`, and the public timestamp of this repository. The monthly job runs `forward/verify_freeze.py` first and fails on any mismatch. Only signals dated after the freeze day count.

## Frozen strategies

| ID | Source | Market | Bars | Cost |
|---|---|---|---|---|
| FW-XM-1-A1 | XM-1-A1 | US500 | Dukascopy daily | Spread 0.45 per round trip, 5% a year financing |
| FW-SW-1 | SW-1 MR2 | US500 | Dukascopy daily | Spread 0.45 per round trip, 5% a year financing |
| FW-TUNE-1-DIP | TUNE-1-DIP baseline | US500, US30, US2000, USTEC | Dukascopy daily | Spread 0.582, 5.222, 0.33 and 3.828 per round trip, 5% a year financing |
| FW-EDGE-1-F6 | EDGE-1-F6 | 12 coins | Binance daily | 0.1% of turnover |

## Which strategies share a rule

| Strategy | Rule | Relation |
|---|---|---|
| FW-XM-1-A1 | RSI(2) dip on US500 | Base case of the RSI(2) dip rule |
| FW-TUNE-1-DIP | RSI(2) dip on four indices | Same rule and parameters as FW-XM-1-A1. Its US500 leg repeats FW-XM-1-A1 at a different frozen spread |
| FW-SW-1 | IBS dip on US500 | A different signal and exit, in the same family: long US500 after a down move. 70.5% of A1's days in market are also SW-1 days, and 32.3% of A1 signals fall on the day of an SW-1 signal, on the audited bars (`forward/rule_overlap.json`) |
| FW-EDGE-1-F6 | Crypto trend basket | Unrelated to the other three |

So there are three distinct rules, not four, and two of those three are one correlated family. The log keeps every frozen row as written. `forward/FORWARD_SUMMARY.md` counts each rule on each market once: the US500 leg of FW-TUNE-1-DIP is logged but not counted again, per `forward/rule_groups.json`. Read the two US500 rules as related, not as two confirmations.

## Rules of the test

- A frozen strategy is never re-frozen or changed. Any change is a new strategy with its own freeze.
- Results are appended on the first UTC day of each month, first on 2026-12-01, whatever they show, by the public workflow `.github/workflows/forward.yml`. Each run keeps a log in `forward/runs/`. Only computed results are committed, never raw data.
- `forward/FORWARD_LOG.csv` is append-only. Rows are never rewritten.
- A strategy under 100 closed trades is labelled INSUFFICIENT SAMPLE. At one or two trades a month for the US500 rules, that takes years.

## Checks before the freeze

Run on the audited bars, the forward code matches the audited rewrites: A1 n=124 PF 2.372, IBS n=397 PF 1.741, and F6 daily returns at correlation 0.99999 from 2024. See `forward/parity.log`. A dry run on live public data with a temporary earlier freeze date worked end to end.

## Delayed entry

XM-1-A1 falls from PF 2.37 to 1.80 and SW-1 from 1.74 to 1.29 when entry and exit move one bar later, which is about a quarter of PF. Live or forward fills should be compared with the delayed figures as well as the headline ones.

## Limits

- Index bars come from Dukascopy, while the backtests used a broker demo feed. Dukascopy was chosen because the audit used it and it needs no login. The differences that matter:
  - Dukascopy daily bars close at its own day boundary, while the broker's follow its server clock, so a bar's open, high, low and close can differ.
  - Dukascopy's index price is its own CFD quote, not the exchange index and not the broker's quote.
  - The spread is a frozen constant, so a real fill could cost more or less.
  - Some signals will therefore differ from those a broker feed gives. The rule code itself was checked on the broker bars.
- Spreads are constants from each backtest, not measured forward.
- The coin list is the hindsight list from the original study.

## Results

No forward trades yet. Results start with the first monthly update, in `forward/FORWARD_SUMMARY.md`, which counts each rule on each market once.
