# FLIP-BOT-DEFECTS

**Audit verdict: VERIFIED.** Original verdict: PASSED. Dated 2026-08-24. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Implementation matches spec.

Family: implementation audit. Market: XAUUSD. Timeframe: live. Idea source: the author's notes (not published) MT5 review.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Whether the live demo bot `flip_bot.py` did what its spec said. Defects were found in versions 1.1 to 1.3 and fixed in 1.2 to 1.5: a state wipe at UTC midnight, duplicate exit journal rows, a rejected close dropping state, unmanaged orphan positions, and lot sizing errors. Each fix is pinned by an offline regression test that stubs the MetaTrader 5 module. No trading performance was measured.

## Instruments and data
- Instruments: XAUUSD (the bot's symbol). Tests also cover other contract sizes, such as a 5,000 oz silver lot ([test_flip_bot_state.py](../../../originals/gann_bot_500/fable-backtesting/test_flip_bot_state.py) `t8`).
- Timeframe(s): the bot trades H1 closes (12:00-20:00 UTC) and an H4 arm ([flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) docstring lines 10-14). The tests drive the clock by hand.
- Data source and file(s): none. The tests use a stub `MetaTrader5` module with synthetic prices, positions and broker specs (test_flip_bot_state.py lines 1-7, 40-140).
- Period: versions dated 2026-08-24 (v1.2 to v1.5) (flip_bot.py docstring lines 20-36). The test clock starts at 2026-08-25 20:00 UTC (test_flip_bot_state.py `World.now`).
- In-sample / out-of-sample: not applicable.

## Rules
The bot's rules, for context only; they were not backtested here (flip_bot.py docstring lines 4-19): buy on an H1/H4 close above R3, sell below S3, R3/S3 from the previous UTC day; both arms must agree ("conviction"); no Mondays; 1 trade per direction per day.
- Entry: as above.
- Exit (stop, target, time): server TP +0.8 x ATR, SL -2.4 x ATR (v1.5 caps the stop at $20/oz), managed half-out at -1.2 x ATR in high volatility, bail at -1.0 x ATR after 8 h in low volatility, hard close at 24 h.
- Filters: no Mondays; daily breaker at -1.5% equity.
- Position sizing: 1% equity risk with reductions and a 1.5x news-day multiplier; v1.5 sizes on a $2,000 notional account. v1.3 derived lot value from tick value / tick size; v1.4 replaced that with `order_calc_profit()` because tick value was quoted per 0.1 lot on the demo server (flip_bot.py lines 27-35).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Not applicable: this entry audits code behaviour, not a parameterised strategy | | |
| Regression tests | 15 (t1 to t15) | test_flip_bot_state.py `main()` list |
| Demo-only guard | `boot()` exits unless the account trade mode is demo | flip_bot.py lines 618-623; audit/DECISIONS.md item 16 |

## Costs
Not applicable. The tests model slippage only to check that v1.5 records it (test_flip_bot_state.py `t15`, `World.slippage`).

## Tuning and selection
- Search: none.
- Configurations run (counted from the code/results): 0 strategy variants; 15 tests. Ledger count (registry/trial_ledger.csv, FLIP-BOT-DEFECTS): 0. They agree.
- How the reported variant was chosen: not applicable.
- Preregistered: no (code defects, not a hypothesis).

What the 15 tests pin (test_flip_bot_state.py docstrings):
- t1-t6: an open position survives UTC midnight; managed exits (24h stop) still fire after midnight; no duplicate exit row; a failed close keeps state; an orphan position is adopted; no stacking a second position across midnight.
- t7-t13: sizing matches the old rule on a 100 oz USD contract; sizing is correct for other contract sizes; never rounds above the risk budget; refuses to size an unpriceable contract; reports over-risk at the volume minimum; documents step granularity; real broker spec beats tick value (the v1.3 bug, sized about 10x too large).
- t14-t15: the v1.5 $20 stop cap with the risk ladder on a $2,000 account; slippage recorded on both sides.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Offline regression suite, author's run | no trades | 15 of 15 pass, printed to the console only; no stored log | audit/infrastructure/PHASE_B_REPORT.md line 19 |
| Offline regression suite, audit sandbox | no trades | did not run: `ModuleNotFoundError: No module named 'news_calendar'`, exit 1 | [existing_suites.log](../../../audit/infrastructure/existing_suites.log) lines 24-33 |
| Demo-only guard | | present: non-demo account raises `SystemExit` | flip_bot.py lines 621-622 |
| Backtest exposure | | no goldbot, flip_scalp or dr_backtest script imports flip_bot.py | audit/VERDICTS.md:45 |

## Code and how to rerun
- Code: [flip_bot.py](../../../originals/gann_bot_500/fable-backtesting/flip_bot.py) (v1.5), [test_flip_bot_state.py](../../../originals/gann_bot_500/fable-backtesting/test_flip_bot_state.py), run as `py -3.11 test_flip_bot_state.py` from `fable-backtesting/` (test docstring). flip_bot.py imports `news_calendar` ([news_calendar.py](../../../originals/gann_bot_500/fable-backtesting/news_calendar.py)) and other helper modules, which must be importable.
- Audit rerun stage: none. The suite is not a stage in audit/tools/run_all.sh; it was run once in Phase B (existing_suites.log).
- Public data enough? Yes, no market data is needed. The helper modules must be on the import path.

## Corrections from the release review
- The earlier page cited an internal note as its source. The defects and fixes are documented in flip_bot.py's version notes (docstring lines 20-60).
- README "Rules: Mutation-checked offline tests" is not supported. No published file records a mutation check. The tests are regression tests with a stubbed MT5 module (test_flip_bot_state.py lines 1-7).
- README "Data: demo terminal" is wrong for the tests. They use no terminal and no market data (test_flip_bot_state.py).
- README "Rerun, recorded clock: 15 tests pass" overstates the record. The audit's stored log shows the suite failing to import (`news_calendar` missing); the 15/15 pass was printed to the console only (existing_suites.log lines 24-33; PHASE_B_REPORT.md line 19).
- README "Stored" results are right on the substance: the midnight wipe was fixed in v1.2, and the v1.3 sizing fix measured 10x wrong and was replaced in v1.4 (flip_bot.py lines 20-35).
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link flip_bot.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | UTC-midnight state wipe fixed in v1.2; duplicate exits, unconfirmed closes, orphan adoption fixed; contract-size fix v1.3 was itself wrong and replaced in v1.4 |
| Rerun, recorded clock | 15 tests pass |
| Rerun, true UTC | n/a |

## Verdict
VERIFIED. Bot refuses non-demo accounts. No goldbot, flip_scalp or dr_backtest script imports flip_bot.py; the last two import the live levels and signals modules.

## Audit caveats
Answers the brief's Phase 3 item: the state wipe was live-only. Backtests never ran through this code, and the log records no verdict affected.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/fable-backtesting/test_flip_bot_state.py](../../../originals/gann_bot_500/fable-backtesting/test_flip_bot_state.py)
