# VS-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Vol-targeting or fear gauges improve the dip bot.

Family: volatility. Market: US500/US30/USTEC. Timeframe: D1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
VS-1 asked whether the index dip bot improves if position size depends on volatility or on fear gauges. The bot's two rules (MR1 RSI2 and MR2 IBS from SW-1) were run as a daily mark-to-market portfolio on three index CFDs. Five sizing schemes were compared with fixed sizing, and each had to beat it on Sharpe and on MAR in both halves. All five failed. A per-trade check also asked whether trades taken in high fear do better than those in low fear. Source: [vs_lab.py](../../../originals/gann_bot_500/research/cross_market/vs_lab.py) lines 1-21.

## Instruments and data
- Instruments: US500, US30, USTEC in the portfolio (vs_lab.py line 29); IWM and EWA added for the per-trade check (line 140). VIXY and VIXM are used for the fear measures (line 40).
- Timeframe(s): D1.
- Data source and file(s): broker MT5 demo exports `research/cross_market/data/<SYM>_D1.npz` (manifest group `broker_mt5`, not published; [data/manifest.csv](../../../data/manifest.csv)), loaded by [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) lines 36-41.
- Period: portfolio trades from 2013-01-01 (vs_lab.py line 88). The docstring gives US500 and US30 "2013+" and USTEC "2023+" (line 3). The per-trade check uses 2011-01-01 to 2019-12-31 and 2020 on (line 145). End dates: Not recorded in the published files (the D1 files run to 2026-10-13 for US500; [data_profile.json](../../../audit/infrastructure/data_profile.json)).
- In-sample / out-of-sample: no fit. Halves 2013-2019 and 2020-2026 (vs_lab.py lines 19, 129).

## Rules
- Entry: MR1, RSI(2) < 10 with close > SMA200; MR2, IBS < 0.2. Signal at the close, fill at the next open ([swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 62-65, 89-106; vs_lab.py lines 47-50).
- Exit (stop, target, time): MR1 exits when close > SMA5; MR2 exits when IBS > 0.8 or close > the previous high. Both exit at the next open, with a 15-day maximum hold (swing_lab.py lines 29, 63-65).
- Filters: S3 skips trades in the bottom fear tercile by VIXY/VIXM (vs_lab.py line 84). There is no other filter.
- Position sizing: each position is 1/3 of equity notional times the scheme multiplier. Total open notional is capped at 150%; a trade that would breach the cap is skipped (vs_lab.py lines 4, 30, 95-101). Multipliers (lines 13-18, 74-85):
  - S0: 1.0 (the live bot).
  - S1: median(vol20 over 252 days) / vol20, clipped to 0.33-2.
  - S2: by the F2 tercile, 1.5 top, 1.0 middle, 0.5 bottom.
  - S3: 0 in the bottom F2 tercile, else 1.
  - S4: as S2 but on F1.
  - S5: as S2 but on F3.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| F1 realised vol | 20-day std of daily returns, percentile rank in trailing 252 days | vs_lab.py lines 8, 53-54 |
| F2 VIX term structure | VIXY / VIXM, rank in trailing 252 days | lines 9-10, 41-42 |
| F3 VIX spike | VIXY / SMA20(VIXY), ranked over 252 days for terciles | lines 11, 43-44 |
| Terciles | below 1/3, 1/3-2/3, above 2/3 | line 85 |
| S1 clip | 0.33 to 2.0 | line 55 |
| Base notional / cap | 1/3 / 150% | line 30 |
| Dip rule parameters | as SW-1 (RSI2, IBS 0.2/0.8, SMA5/200, 15-day max) | swing_lab.py |
| Per-trade min cell | 15 trades | vs_lab.py line 147 |

## Costs
- Spread: 1.5 x the symbol's median recorded spread, charged on the entry day as spread / entry open (vs_lab.py lines 5, 63; xm_lab.py line 41). If a file has no positive spread, 2 bp of the median close is used instead (swing_lab.py lines 35-36).
- Financing: 5%/yr on longs per calendar day held (vs_lab.py lines 30, 64-65).
- No commission or slippage.

## Tuning and selection
- Search: the five schemes S1-S5 against S0, and three fear measures in the per-trade check (vs_lab.py lines 126, 141). No parameter grid.
- Configurations run (counted from the code/results): 5 schemes plus the S0 baseline in the portfolio test, and 3 fear measures x 5 markets in the per-trade check. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row VS-1, n_variants): 5. That matches the schemes. The per-trade checks are not counted.
- How the reported variant was chosen: not applicable; all schemes are reported. The pass rule is fixed: Sharpe and MAR above S0 in both halves (line 19). A fear effect counts only if high fear beats low fear in both halves on at least 4 of 5 markets (lines 20-21).
- Preregistered: partly. The rules are "pre-declared, written before any result" in the code docstring (vs_lab.py line 1). There is no separate prereg file. The original dated record, `DECISIONS.log`, is not in the repo.

## Results
Portfolio of US500 + US30 + USTEC, MR1 + MR2: 1,153 trades (US500 519, US30 503, USTEC 131) ([recorded.cross_market.vs_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.vs_lab_py.log) line 3). The log does not print the trade count per half.

| Slice | Trades (n) | Result 2013-2019 / 2020-2026 | Source file |
|---|---|---|---|
| S0 fixed | 1,153 total | Sharpe 0.23 / 1.01; MAR 0.11 / 1.04; CAGR +1.6% / +12.4% | vs_lab log |
| S1 vol target | n not printed | Sharpe 0.18 / 1.06; MAR 0.09 / 1.16; fail | vs_lab log |
| S2 F2 boost | n not printed | Sharpe 0.19 / 0.82; MAR 0.07 / 0.59; fail | vs_lab log |
| S3 F2 filter | n not printed | Sharpe -0.01 / 0.72; MAR -0.02 / 0.55; fail | vs_lab log |
| S4 F1 boost | n not printed | Sharpe 0.17 / 0.82; MAR 0.06 / 0.61; fail | vs_lab log |
| S5 F3 boost | n not printed | Sharpe 0.25 / 0.94; MAR 0.11 / 1.03; fail | vs_lab log |
| Per-trade fear effect F1 / F2 / F3 | 128 to 345 per cell (USTEC first half under 15: "few") | high beats low in both halves on 3/5, 0/5, 2/5 markets; no effect | vs_lab log |

S1 beat S0 in 2020-2026 but not in 2013-2019, so it failed the both-halves rule. A split-adjusted rerun is in [adj.cross_market.vs_lab.py.log](../../../audit/phaseC/logs_L1/adj.cross_market.vs_lab.py.log).

## Code and how to rerun
- Code: [vs_lab.py](../../../originals/gann_bot_500/research/cross_market/vs_lab.py), with [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) and [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py). Run `python vs_lab.py`.
- Audit rerun stage: `l1_queue` (job `recorded cross_market vs_lab.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); `adj_run` ([run_adj.sh](../../../audit/phaseC/run_adj.sh)).
- Public data enough? No. It needs `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv)).

## Corrections from the release review
- README "Rules: S1-S5." Not usable as written. The schemes, fear measures, 1/3-notional base and 150% cap are defined only in vs_lab.py lines 1-21, 74-106.
- README "Costs: as live". Not a cost statement. The code charges 1.5x median spread once per trade and 5%/yr financing on longs, with no commission (vs_lab.py lines 5, 63-65).
- README "Market: US500/US30/USTEC". Incomplete. IWM and EWA are also run, in the per-trade fear check (vs_lab.py line 140). USTEC starts only in 2023, per the docstring (line 3).
- README "Results: All FAIL" gives no figures and no n. The log gives 1,153 trades and Sharpe/MAR for each scheme and half.
- README "Provenance" lists only `DECISIONS.log (not published)`. vs_lab.py and its rerun log are published and should be linked.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All FAIL |
| Rerun, recorded clock | All FAIL |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
Dip portfolio Sharpe 0.23 in 2013-19 vs 1.01 in 2020-26.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
