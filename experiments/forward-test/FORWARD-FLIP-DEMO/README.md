# FORWARD-FLIP-DEMO

**Audit verdict: UNVERIFIED.** Original verdict: INCOMPLETE. Dated 2026-08-25. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Winner MAE stays inside the $20 cap at N>=20-30.

Family: forward test. Market: XAUUSD. Timeframe: live. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A forward test on a broker demo account, started 2026-08-25. It ran the author's flip_bot v1.5 "forward-test build": the conviction R3/S3 breakout rule sized as a $2,000 notional account, with the stop capped at $20/oz. The aim was to check that winning trades' adverse excursion (MAE) stays inside the $20 cap once 20-30 trades exist, and to measure real slippage for the first time ([registry/experiments.yaml](../../../registry/experiments.yaml) lines 715-735; [flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) lines 36-57). The demo account was purged for inactivity by 2026-09-29, before the target n was reached. No closing report exists.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): live; signals on H1 closes 12:00-20:00 UTC, the 12/16/20 UTC closes also count as the H4 arm (flip_bot.py lines 10-13).
- Data source and file(s): live broker demo feed. The bot writes `flip_bot_journal.csv` with MAE, fill price, slippage and spread (flip_bot.py lines 91, 124-128). No journal for this test is published. A demo journal `research/trades.db` is classed `demo_journal`, broker access, unpublished ([data/manifest.csv](../../../data/manifest.csv) row 514); whether it holds this test's trades is Not recorded in the published files.
- Period: 2026-08-25 to the account purge, by 2026-09-29.
- In-sample / out-of-sample: forward only.

## Rules
From [flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) docstring, lines 1-57:
- Entry: R3/S3 from the previous UTC day's high, low, close. Buy when price closes above R3, sell below S3. Two arms: H1 closes 12:00-20:00 UTC, and the H4 arm at 12/16/20 UTC. Enter only when both arms fire the same direction that day. No Mondays. Max 1 trade per direction per day.
- Exit (stop, target, time): server TP +0.8 x ATR; stop = min(2.4 x ATR, cap), cap derived as 1% of notional equity at volume_min, about $20/oz (lines 355-365). Managed: high-volatility half-out at -1.2 x ATR; low-volatility bail at -1.0 x ATR after 8 hours; hard close at 24 hours.
- Filters: a daily breaker at -1.5% of equity.
- Position sizing: 1% of notional equity risk (0.5% while below 95% of peak); x0.5 if D1 ADX <= 22; x1.5 on news days; x0.5 in the low-volatility regime. Notional equity = 2,000 + (equity - start). Lots floored to the broker volume step; max 5 lots (lines 15-17, 37-42, 95-99).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Pivots | previous UTC day R3, S3 | [flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) lines 10-11 |
| Session hours | 12-20 UTC | flip_bot.py line 92 |
| TP / SL | +0.8 x ATR / min(2.4 x ATR, ~$20) | flip_bot.py lines 14, 102, 363-364 |
| Derisk / bail / time stop | -1.2 x ATR half-out (hivol); -1.0 x ATR after 8h (lovol); 24h | flip_bot.py lines 14-15 |
| Risk | 1% (0.5% below 95% of peak); ADX <= 22 x0.5; news x1.5; lovol x0.5; breaker -1.5% | flip_bot.py lines 15-17 |
| Notional equity | $2,000 | flip_bot.py line 99 |
| ATR warning | ATR >= 20 / 0.835 = about 23.95 (warn only) | flip_bot.py lines 103-105 |
| ATR and ADX periods | Not recorded in the lines read; see the code | flip_bot.py |

## Costs
"observed" ([registry/experiments.yaml](../../../registry/experiments.yaml) line 728). The bot journals intended price, fill price, slippage and spread at entry (flip_bot.py lines 50-55, 124-128). Only one slippage observation was recorded (same file, line 733). Its value is Not recorded in the published files.

## Tuning and selection
- Search: none. One frozen build (v1.5).
- Configurations run (counted from the code/results): 1. Ledger count (registry/trial_ledger.csv n_variants): 1. They match.
- How the reported variant was chosen: not applicable. The $20 cap is derived from the account size, not tuned (flip_bot.py lines 43-49).
- Preregistered: "cycle 10 pre-registered criteria" per the registry. The criteria text is not published (it sits in the unpublished DECISIONS.log).

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Forward demo | not recorded (below the 20-30 target) | No closing report; account purged by 2026-09-29. INCOMPLETE | [registry/experiments.yaml](../../../registry/experiments.yaml) line 730 |
| Observed slippage | 1 | value not recorded. INSUFFICIENT SAMPLE | same, line 733 |
| Audit | | UNVERIFIED | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 46 |

Related evidence: the $20 cap rests on a backtest worst winner MAE of $17.60 (flip_bot.py lines 56-57, 103-104). The audit's recompute of that backtest on the true UTC clock finds a worst winner MAE of $37.86/oz, with 4 of 353 winners reaching $20 ([audit/phaseC/l2_recompute.json](../../../audit/phaseC/l2_recompute.json), "door3 true_utc"; recorded clock: $17.60, 0 of 360).

## Code and how to rerun
- Code: [flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) (the docstring lists v1.5 changes), test [test_flip_bot_state.py](../../../originals/gann_bot_500/fable-backtesting/test_flip_bot_state.py) (offline, stubs MetaTrader5).
- Audit rerun stage: none.
- Public data enough? no. A forward test cannot be rerun; it needs a live MT5 terminal, and no journal is published.

## Corrections from the release review
- README Gates: "winner MAE <= 0.906xATR". No published file gives 0.906. The bot's own threshold is 0.835 x ATR ($17.60 / ATR 21.09) ([flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) lines 56-57, 103-105). Source the 0.906 figure or correct it.
- README Rules: "Frozen spec on $2,000 notional." It does not name or link the build. It is flip_bot.py v1.5, with the stop at min(2.4 x ATR, ~$20).
- README Provenance: "Status of the number: found". Misleading. No result number exists.
- README omits that the $20 cap's premise (worst winner MAE $17.60) fails on the true UTC clock: worst winner MAE $37.86, 4 winners at or beyond $20 ([l2_recompute.json](../../../audit/phaseC/l2_recompute.json)).
- README Costs: "observed". Only one slippage value was recorded and it is not published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No closing report found; demo account purged by 2026-09-29 |
| Rerun, recorded clock | no closing report |
| Rerun, true UTC | n/a |

## Verdict
UNVERIFIED. INCOMPLETE.

## Audit caveats
Account died from idle purge before n was reached. First observed slippage n=1 only.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
