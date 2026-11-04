# TVS-1

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-10-23. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Video rule works, and a search finds OOS survivors.

Family: indicator search. Market: XAUUSD, SPY, QQQ. Timeframe: 1m-1D. Idea source: video VWAP + 9 EMA, TradingView built-ins.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Phase 1 replicated a social-media video rule: go long when EMA(9) crosses above a session VWAP, short on the cross down, with a $5 target, on many timeframes and three exit variants. Phase 2 searched TradingView built-in indicators, strategy templates, filters and exits across 9 asset-timeframe cells, ranked the results on out-of-sample Sharpe, and tested the top 20 against eight pass conditions. 0 of 20 passed. The audit's new draw of the search also gave 0 of 20.

## Instruments and data
- Instruments: XAUUSD, SPY, QQQ ([common.py](../../../originals/gann_bot_500/research/tvsearch/src/common.py) `ASSETS`).
- Timeframe(s): Phase 1: 1, 2, 3, 5, 10, 15, 30, 45, 60, 120, 240 minutes and D (common.py `TFS`). Phase 2: 5, 15, 60 minutes (phase2.py `CELLS`). All timeframes are resampled from one base series per asset ([tvsearch/README.md](../../../originals/gann_bot_500/research/tvsearch/README.md)).
- Data source and file(s):
  - XAU: broker MT5 demo export `tvsearch/data/xau_tv.npz`, M1 and M5 bid with spread and tick volume, last 99,999 bars each (tvsearch/README.md "Data"). data/manifest.csv group `broker_mt5`.
  - SPY, QQQ: Yahoo chart endpoint bars, regular hours, `tvsearch/data/{SPY,QQQ}_{1m,5m,1h,1d}.csv` ([fetch_yf.py](../../../originals/gann_bot_500/research/tvsearch/src/fetch_yf.py)). Manifest group `yahoo_intraday`, access "dated": Yahoo no longer serves those dates (REPRODUCE.md section 3).
- Period (from the data lines in the result logs):
  - XAU M1 2026-07-15 to 2026-10-23; XAU M5 2025-05-29 to 2026-10-23 ([phase1_log.txt](../../../originals/gann_bot_500/research/tvsearch/results/phase1_log.txt); [phase2_log.txt](../../../originals/gann_bot_500/research/tvsearch/results/phase2_log.txt)).
  - SPY/QQQ 1m 2026-09-24 to 2026-10-23; 5m 2026-08-27 to 2026-10-23; 1h 2024-10-24 to 2026-10-23; 1d 10 years (logs; README "Data").
- In-sample / out-of-sample:
  - Phase 1 "primary" horizon = the last 30 days; "long" = all available history (common.py `window`, `source_for`).
  - Phase 2: first 70% of bars IS, last 30% OOS, per cell (phase2.py `IS_FRAC`). Split dates: SPY/QQQ 5m and 15m 2026-10-07; SPY/QQQ 60m 2026-03-23; XAU all cells 2026-05-25 (phase2_log.txt). Walk-forward: 6 equal blocks, train on 2, test on the next, 4 folds (phase2.py docstring).

## Rules
- Entry:
  - Phase 1: EMA(9, close) crossing VWAP(OHLC4, session anchor; weekly anchor on D bars). Long on cross up, short on cross down. Signal on bar close, fill at the next bar's open ([phase1.py](../../../originals/gann_bot_500/research/tvsearch/src/phase1.py) docstring, `signals`).
  - Phase 2: a config = one template (`xover`, `trend`, `breakout`, `meanrev`, `pullback`) with its indicator choices, up to two filters, a side (both/long/short) and an exit ([strategies.py](../../../originals/gann_bot_500/research/tvsearch/src/strategies.py) `make_config`).
- Exit (stop, target, time):
  - Phase 1 variants: (a) TP, else the opposite cross (stop and reverse); (b) TP, else flat at end of session; (c) TP, else opposite cross or end of session. TP sweep $0.25, 0.5, 1, 2, 3, 5; the video's $5 is the headline (phase1.py).
  - Phase 2 exits: fixed $ TP/SL, ATR TP/SL, R-multiple, ATR trailing stop, opposite signal with ATR stop, or time stop with ATR stop; optional end-of-session flat (strategies.py `exit_spec`).
  - Same bar touches stop and target: stop assumed. A bar opening past a level fills at the open ([engine.py](../../../originals/gann_bot_500/research/tvsearch/src/engine.py) docstring).
- Filters (Phase 2): none, time of day (skip 0/15/30/60 min after open or before close), day of week, ADX minimum, MA side, higher timeframe, ATR percentile band, relative volume (strategies.py).
- Position sizing: 1 share or 1 ounce per trade; results in $ per share/oz (tvsearch/README.md "Rules baked in").

## Indicators and parameters
Phase 2 value sets (strategies.py `make_config`; `FIXED`):

| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Video rule (Phase 1) | EMA 9 on close; VWAP on OHLC4, session (D: weekly) anchor | phase1.py |
| MA kinds (xover) | sma, ema, wma, hma, vwma, dema, tema, alma, kama; fast 5/9/13/21; slow MA 34/50/100/200, or VWAP (session/week/month anchor; source c/hl2/hlc3/ohlc4), or price | strategies.py |
| Trend systems | Supertrend len 7/10/14 x mult 2/3/4; PSAR start 0.01/0.02, max 0.1/0.2; Ichimoku TK and cloud; DMI len 14/21, ADX 0/20/25; Aroon 14/25; MACD 12/26/9, 8/21/5, 5/35/5 (signal or zero line); TSI; AO; ROC and momentum 9/14/21 | strategies.py |
| Breakouts | Donchian 10/20/55; ORB 5/15/30 min; previous-day high/low; Bollinger len 20/50, k 1.5/2/2.5; Keltner len 20/50, k 1/1.5/2 | strategies.py |
| Mean reversion | RSI len 2/7/14, level 10/20/30; Stoch, StochRSI, MFI level 10/20/30; CCI 100/150/200; Williams %R 10/20; BB touch; VWAP band k 1/2; KC touch | strategies.py |
| Pullback | state: EMA side or slope 50/100/200, Supertrend dir, DMI dir, HTF, VWAP side, cloud; trigger: RSI pullback (len 2/7/14, level 20/30/40), Stoch, MA touch, VWAP touch, MACD cross | strategies.py |
| Exits | fixed TP/SL XAU $2/3/5/8/12, SPY/QQQ $0.25/0.5/1/2/3; ATR TP 1/1.5/2/3, SL 0.5/1/1.5/2; R target 1/1.5/2/3; trail 1/2/3 ATR, SL 1/2; opposite with SL 2/3 ATR; time 5/10/20 bars, SL 1/2 ATR; end-of-session on/off | strategies.py |
| ATR | ATR(14), SMA-seeded as TradingView | common.py; tvsearch/README.md "Indicator fidelity" |
| Search budget | 6,000 random + 1,500 Optuna TPE (seed 7) per cell, 9 cells | phase2.py `N_RANDOM, N_OPTUNA` |
| Minimum OOS trades to rank | 30 | phase2.py `MIN_N` |

## Costs
From engine.py and data.py:
- XAU: bars are bid; a long buys at ask (open + spread) and exits on bid; a short's stop, target and exit are watched on ask. Spread = recorded bar spread, floor $0.22 ([data.py](../../../originals/gann_bot_500/research/tvsearch/src/data.py) `SPREAD_FLOOR`). No slippage or commission (engine.py `COST`).
- SPY, QQQ: $0.01 per share per side, no commission (engine.py `COST`).

## Tuning and selection
- Search: Phase 1 = 3 assets x 12 timeframes x 2 horizons x 3 exit variants x 6 targets. Phase 2 = per cell, 6,000 configs drawn at random from the value sets above, then 1,500 Optuna TPE trials maximising in-sample daily Sharpe (phase2.py docstring and `run_cell`).
- Configurations run (counted from the code/results): Phase 1 1,296 rows (phase1_log.txt). Phase 2 64,521 configs, of which 21,119 had at least 30 OOS trades (phase2_log.txt). Ledger count (registry/trial_ledger.csv): TVS-1 64,521; the audit's redraw AUD-D-TVS adds 64,431. Phase 1's 1,296 rows are not in the ledger.
- How the reported variant was chosen: the top 20 were ranked by OUT-OF-SAMPLE daily Sharpe among configs with at least 30 OOS trades (phase2.py `analyse`, `ok.sort_values("oos_sharpe")`). So the out-of-sample slice was used for selection and is not a clean test. The walk-forward check picks the best train-Sharpe config blind per fold.
- Preregistered: no separate preregistration document. The pass rule is written in the phase2.py docstring; the registry cites a source hash (`research/tvsearch src sha ec9256604311`, registry/experiments.csv). Whether that code was fixed before any result was seen: Not recorded in the published files.

## Results
PASS (phase2.py docstring and `analyse`) needs all of: OOS n >= 30; OOS net > 0 and PF >= 1.2; IS net > 0; OOS net beats buy-and-hold; beats >= 95% of 200 random-entry draws; DSR >= 0.95 counting all trials; at least 50% of one-step parameter neighbours profitable OOS.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Phase 1 video rule, TP $5, last 30 days, best rows (XAU 10m b / 60m a) | 58 / 58 | net +$123.1 / +$110.6 per oz, PF 1.87 / 1.77; beats 86% / 81% of random draws. INSUFFICIENT SAMPLE | phase1_log.txt |
| Phase 1 video rule, SPY/QQQ, last 30 days | 21 to 23 per row | INSUFFICIENT SAMPLE | phase1_log.txt |
| Phase 1, long history, best XAU row (120m b, TP $5) | 588 | net +$225.7 per oz vs buy-and-hold +$733.7 | phase1_log.txt |
| Phase 2 search, all cells | 64,521 configs | 21,119 with OOS n >= 30 | phase2_log.txt |
| Phase 2 top 20 by OOS Sharpe (all SPY/QQQ 5m) | OOS n 30 to 80 each; 12 OOS sessions | 0 of 20 pass; best DSR 0.957 (rank 2, OOS n=34). INSUFFICIENT SAMPLE | [phase2_top20.csv](../../../originals/gann_bot_500/research/tvsearch/results/phase2_top20.csv) |
| Walk-forward net, 4 folds per cell | trade n not recorded | 4 of 9 cells negative (QQQ 5m, QQQ 15m, SPY 5m, XAU 60m -$382.3); best XAU 5m +$389.6 | phase2_log.txt |
| Audit: stored configs re-evaluated | 1,020 configs | 1,020 of 1,020 exact, including the top 20 | [tvs_recheck.json](../../../audit/phaseC/tvs_recheck.json) |
| Audit: new Phase 2 draw | 64,431 configs | 0 of 20 pass; best DSR 0.969 | audit/phaseC/logs_D/tvs_phase2.log; tvs_recheck.json |
| "DSR hurdle Sharpe 11.3" (registry) | | Not found in any published result file; the report it may come from, reports/report.html, is not in the repository | registry/experiments.csv |

## Code and how to rerun
- Code: [run_all.py](../../../originals/gann_bot_500/research/tvsearch/src/run_all.py), [phase1.py](../../../originals/gann_bot_500/research/tvsearch/src/phase1.py), [phase2.py](../../../originals/gann_bot_500/research/tvsearch/src/phase2.py), [strategies.py](../../../originals/gann_bot_500/research/tvsearch/src/strategies.py), [ind.py](../../../originals/gann_bot_500/research/tvsearch/src/ind.py), [engine.py](../../../originals/gann_bot_500/research/tvsearch/src/engine.py), [data.py](../../../originals/gann_bot_500/research/tvsearch/src/data.py), tests [test_indicators.py](../../../originals/gann_bot_500/research/tvsearch/tests/test_indicators.py), notes [README.md](../../../originals/gann_bot_500/research/tvsearch/README.md). Audit check [tvs_recheck.py](../../../audit/phaseC/tvs_recheck.py).
- Audit rerun stage: `tvs_p2` (new Phase 2 draw) and `tvs_recheck` (audit/tools/run_all.sh). The Phase 1 rerun is not a named stage in run_all.sh.
- Public data enough? No. Needs `broker_mt5` (`xau_tv.npz`) and the dated `yahoo_intraday` copies. Both `tvs_p2` and `tvs_recheck` are listed in audit/tools/stages_broker.txt.

## Corrections from the release review
- README "Splits: IS 70 / OOS 30" hides that the top 20 were ranked on OOS Sharpe (phase2.py `analyse`). The OOS slice was used to select and so is not an independent test.
- README does not state the search method: per cell, 6,000 random configs plus 1,500 Optuna TPE trials maximising IS Sharpe, over 9 cells (phase2.py line 32).
- README "Data: broker M1/M5; Yahoo SPY/QQQ" gives no dates. Phase 2's SPY/QQQ 5m and 15m cells cover 2026-08-27 to 2026-10-23 only (57 days), and the top 20 had 12 OOS sessions (phase2_log.txt; phase2_top20.csv `oos_days`).
- README results give no n. Every top-20 config has 30 to 80 OOS trades, under 100 (phase2_top20.csv).
- README stored result "DSR hurdle Sharpe 11.3" has no source in the published files (registry/experiments.csv only).
- README "Preregistration: research/tvsearch src sha ec9256604311" is a code hash, not a preregistration. There is no prereg document.
- README "Rerun, true UTC: same" has no meaning here: the clock issue concerns the HistData gold file, which this study does not use.
- Provenance lists `DECISIONS.log` and `reports/report.html`, neither in the repository, and does not link the published tvsearch README or src/.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0/20 PASS; DSR hurdle Sharpe 11.3 |
| Rerun, recorded clock | Phase 1: 1,296 rows, trade metrics 100%; Phase 2 stored 0/20 on 64,521 configs |
| Rerun, true UTC | same |

## Verdict
VERIFIED-WITH-CORRECTIONS. The stored search cannot be replayed: its grid seed uses Python's salted hash, a defect. All 1,020 stored configs checked re-evaluate exactly, including the top 20. A new draw of 64,431 configs also gives 0/20. Random-baseline columns are unseeded and differ. TVS-1's own DSR counts its own configs, not the ledger, and its best config reads 0.957 stored and 0.969 rerun. A pass needed eight conditions at once, and no config met them all.

## Audit caveats
Top cells had only 12 OOS sessions.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- `originals/gann_bot_500/research/tvsearch/reports/report.html` (not published)
