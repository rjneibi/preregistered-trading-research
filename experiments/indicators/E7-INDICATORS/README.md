# E7-INDICATORS

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** 200-day filter and Bollinger RSI pay after costs.

Family: indicators. Market: XAUUSD, EURUSD, GBPUSD. Timeframe: D1, H1. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Two textbook indicator rules, run by the audit under its common gates. Part A: hold gold long while the daily close is above its 200-day simple moving average. Part B: on EURUSD and GBPUSD H1, fade a close outside the 20-period Bollinger Bands when RSI(14) confirms, exit at the middle band. Both FX pairs failed on the development slice; gold had too few trades to judge and was marked contaminated in advance.

## Instruments and data
- Instruments: XAUUSD; EURUSD; GBPUSD.
- Timeframe(s): gold D1; FX H1 resampled from M1 ([spec.md](../../../experiments/indicators/E7-INDICATORS/spec.md)).
- Data source and file(s):
  - Gold: HistData M1 `research/data/xauusd_m1_histdata.csv` (manifest group `histdata_xau`, public), shifted to true UTC with [clockfix.py](../../../audit/phaseC/clockfix.py) `shifted`, then resampled to UTC D1, weekdays only ([e7_indicators.py](../../../audit/phaseE/e7_indicators.py) `gold_d1`).
  - FX: Dukascopy M1 `london-breakout/data/m1/EURUSD.npz`, `GBPUSD.npz` (manifest group `dukascopy_m1`, public), resampled to H1 with the median bar spread (e7_indicators.py `fx_h1`). The npz files hold mid prices plus spread (originals/gann_bot_500/research/crt_fvg/config.yaml comment on the same files); the spec says "H1 bid", and audit/DECISIONS.md item 53 records the departure "FX cost charged on mid with a measured spread".
- Period: gold 2010-2026, with 2010-2012 ASSUMED-CLOCK; slices start 2013-01-01 (e7_indicators.py `part_a`). FX 2013-01-01 to 2026-10-29 (e7_result.json `first`, `last`).
- In-sample / out-of-sample: dev first 50%, validation next 20%, holdout last 30% by calendar span ([COMMON.md](../../../audit/prereg/COMMON.md); [lib.py](../../../audit/phaseE/lib.py) `cuts`). Gold dev ends 2019-09-25, validation 2022-06-04. FX dev ends 2019-12-01, validation 2022-09-06 ([e7_result.json](../../../audit/phaseE/e7_result.json)). Validation and holdout open only if the previous slice passes.

## Rules
- Entry:
  - A (gold): at the D1 close, if close > SMA(200), hold long for the next day; fill at the next open. Each continuous long spell is one trade (e7_indicators.py `spells`).
  - B (FX): long when close < SMA20 - 2 x SD20 and RSI(14) < 30; short when close > SMA20 + 2 x SD20 and RSI(14) > 70; fill at the next open (e7_indicators.py `bb_trades`).
- Exit (stop, target, time):
  - A: flat at the next open after the close falls to or below SMA(200).
  - B: first close beyond the middle band (exit at the next open); stop 2 x ATR(14) from entry (a bar that opens through the stop fills at the open); time stop 48 H1 bars.
- Filters: none beyond the rules. B takes one trade at a time.
- Position sizing: not stated in the spec. The code measures per-unit returns: gold as a fraction of the entry price, FX in price units and in R (risk = 2 x ATR) (e7_indicators.py).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Gold trend filter | SMA(200) of D1 closes | spec.md A; e7_indicators.py `spells` |
| Bollinger Bands | 20-period SMA, 2 x population SD (`ddof=0`) | spec.md B; `bb_trades` |
| RSI | 14, Wilder (EWM alpha 1/14); thresholds 30 / 70 | same |
| ATR | 14, Wilder (EWM alpha 1/14); stop 2 x ATR | same |
| Time stop | 48 H1 bars | same |
| Warm-up | first 40 H1 bars skipped; first 200 D1 bars | same |
| Twin | 2,000 draws, seed 7, random sign, resampled holding times | lib.py `twin_p`; COMMON.md gate 4 |

## Costs
- Gold (A): per-switch spread from the per-year x UTC-hour matrix `research/goldbot/results/cost_matrix.json`, median, plus slippage 0.5 x spread per side, plus $7/lot round trip (`CostMatrix.load(..., stat="median", k_slip=0.5, commission_per_lot_rt=7.0)`, e7_indicators.py `part_a`). Night fee $0.05/oz per night held ($5/lot, marked ESTIMATE in the spec). Buy-and-hold pays the same fee at 1.4 nights per trading day (e7_indicators.py `bh`).
- FX (B): bar spread at entry and at exit, plus 0.5 x that sum as slippage, plus 0.00007 per unit ($7 per 100k lot round trip). No financing (e7_indicators.py `bb_trades`; spec.md B).
- Reported at 1x, 1.5x (FX) and 2x.

## Tuning and selection
- Search: none. Three fixed variants: gold A, EURUSD B, GBPUSD B.
- Configurations run (counted from the code/results): 3. Ledger count (registry/trial_ledger.csv, AUD-E7): 3. They match. (The page's ID E7-INDICATORS maps to ledger row AUD-E7.)
- How the reported variant was chosen: not applicable; all three reported.
- Preregistered: yes ([E7-INDICATORS.md](../../../audit/prereg/E7-INDICATORS.md), frozen with the other E specs on 2026-10-31 before data was read, audit/DECISIONS.md item 37). Recorded departures: FX cost charged on mid (DECISIONS.md item 53); the trade-count gate cannot be met by a slow spell rule (DECISIONS.md item 45).

## Results
Gates per slice (COMMON.md): PF >= 1.20; PF at 2x costs >= 1.00; n >= 100; random-entry twin one-sided p < 0.05. Gold also needs Sharpe >= buy-and-hold Sharpe.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| A gold, dev 2013-01-01 to 2019-09-25 | 26 spells | PF 0.964, PF 2x 0.92, twin p 0.566. INSUFFICIENT SAMPLE | [e7_result.json](../../../audit/phaseE/e7_result.json) |
| A gold, full 2013-2026 (reads sealed slices; not a headline) | 57 spells | PF 3.152; Sharpe 0.438 vs B&H 0.417; max DD -30.9% vs -40.3%. INSUFFICIENT SAMPLE, CONTAMINATED | e7_result.json `without_2010_2012`; DECISIONS.md item 45 |
| A gold, validation / holdout | | not evaluated (sealed) | e7_result.json |
| B EURUSD, dev 2013-01 to 2019-12 | 984 | PF 0.866 (gross 0.973), PF 2x 0.771, twin p 0.96, avg -0.079R. FAIL | e7_result.json |
| B GBPUSD, dev 2013-01 to 2019-12 | 1,053 | PF 0.802 (gross 0.975), PF 2x 0.658, twin p 0.997, avg -0.099R. FAIL | e7_result.json |
| B validation / holdout | | not evaluated (sealed) | e7_result.json |

## Code and how to rerun
- Code: [e7_indicators.py](../../../audit/phaseE/e7_indicators.py), [lib.py](../../../audit/phaseE/lib.py), [clockfix.py](../../../audit/phaseC/clockfix.py), cost class [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py).
- Audit rerun stage: `e7` (audit/tools/run_all.sh, run from `audit/phaseE`).
- Public data enough? Yes. Needs manifest groups `histdata_xau` and `dukascopy_m1`. `e7` is not in audit/tools/stages_broker.txt.

## Corrections from the release review
- README provenance "`audit/phaseE` (not published)" is wrong. audit/phaseE/e7_indicators.py and e7_result.json are in the repository.
- README "Rules: See prereg", "Costs: see prereg", "Splits: see prereg", "Gates: see prereg" give nothing on the page. The rules, the 50/20/30 split, the costs and the four gates are listed above (spec.md; COMMON.md; e7_indicators.py).
- README results give no n. Gold dev is 26 spells; EURUSD dev 984 trades; GBPUSD dev 1,053 (e7_result.json).
- README "Rerun, recorded clock: new" and "Rerun, true UTC: new" are not results. This experiment was first run by the audit, on true-UTC gold data and UTC Dukascopy FX data.
- README "Source: audit brief" does not say the spec states the earlier research report was not on disk, so textbook forms were used (spec.md).
- Not disclosed on the page: the random-entry twin draws cost-free log returns with a random sign, while the real side is net of costs (lib.py `twin_p`; e7_indicators.py). This biases the twin test toward FAIL for FX, and for a long-only gold rule the random sign removes the drift from the null.
- README caveat "See audit/DECISIONS.md" names no item. The relevant ones are items 37, 45 and 53.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | FX FAIL at dev. Gold INSUFFICIENT SAMPLE at dev. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. FX FAILED at dev. Gold INSUFFICIENT SAMPLE at dev and CONTAMINATED in advance. FX costs are charged on mid prices with a measured spread, which suits a rule this size.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
