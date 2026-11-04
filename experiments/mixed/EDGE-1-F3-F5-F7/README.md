# EDGE-1-F3-F5-F7

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Turn of month, funding carry, cross-sectional momentum and gold/silver ratio pass.

Family: mixed. Market: US500, crypto, XAU/XAG. Timeframe: D1. Idea source: published.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
This entry groups four of the published edge families in the author's EDGE-1 study of 2026-10-13. The rules and pass bars were written into the script docstring before the run. F3: the turn-of-month effect on US500. F4: crypto funding carry (long spot, short perpetual). F5: crypto cross-sectional momentum. F7: gold/silver ratio mean reversion. All four failed. The page title names F3, F5 and F7, but F4 is also part of this entry.

## Instruments and data
- Instruments: F3 US500 CFD; F4 and F5 BTC, ETH, BNB, XRP, ADA, SOL, DOGE, LTC, LINK, DOT, AVAX, TRX; F7 XAUUSD and XAGUSD ([edge_lab.py:10-20,177-178,201,289-290](../../../originals/gann_bot_500/research/cross_market/edge_lab.py)).
- Timeframe(s): D1 (F3, F4, F7); daily closes resampled to weekly, Sunday (F5) (edge_lab.py:236-238).
- Data source and file(s): US500, XAUUSD, XAGUSD D1 from the MT5 demo terminal (`cross_market/data/*_D1.npz`). Crypto daily klines `data_edge/C_<coin>_D1.npz` and funding history `data_edge/F_<coin>.npz` from public Binance endpoints ([fetch_crypto2.py:1,12-27](../../../originals/gann_bot_500/research/cross_market/fetch_crypto2.py)). The manifest classes the crypto and funding files as `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv) lines 338-381).
- Period: full history of each file. Exact first and last dates are not printed in the log. F4 starts at 2019-12-01 (edge_lab.py:223).
- In-sample / out-of-sample: none fitted. Each family is judged in two halves, with different cut dates: F3 2019-01-01, F4 2023-01-01, F5 2022-07-01, F7 2016-01-01 (edge_lab.py:185-186,224,249,312).

## Rules
- Entry: F3 long US500 for the return of the last trading day of a month and the first 3 days of the next (lines 181-183). F4 per coin, hold the carry position when yesterday's 7-day mean funding is > 0 (line 218). F5 each week, hold the top 3 of 12 coins by 4-week return, equal weight; needs at least 6 coins with data (lines 238-245). F7 when the 60-day z of log(gold/silver) passes ±2, go the opposite way (long gold/short silver when z < -2), enter next day (lines 292-301).
- Exit (stop, target, time): F3 out of the market outside the window. F4 drop the position when the funding signal turns off. F5 weekly rebalance. F7 exit the day after z changes sign, or after 40 days (lines 300-306).
- Filters: none beyond the rules.
- Position sizing: F3 100% in the window. F4 equal weight across coins, return per spot notional. F5 1/3 per selected coin. F7 return on the log ratio, one trade at a time.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| F3 window | last 1 day + first 3 days of month | edge_lab.py:183 |
| F4 funding signal | 7-day trailing mean > 0, lagged 1 day | edge_lab.py:218 |
| F5 momentum | 4-week return, top 3 of 12, weekly | edge_lab.py:240-242 |
| F7 z-score | 60-day rolling mean and sd of log(gold/silver); entry abs(z) > 2; max 40 days | edge_lab.py:292-302 |

## Costs
- F3: 1.5 x median spread/price on each position change, plus 5% a year financing while long (edge_lab.py:192-196). The pass test itself is on raw daily returns.
- F4: 0.3% round trip per switch, charged half on each switch (edge_lab.py:220-221).
- F5: 0.1% per side on weight changes (edge_lab.py:245).
- F7: 1.5 x (gold + silver median spread/price) + 2 x 0.02%, plus 4% a year on holding days (edge_lab.py:294,304).

## Tuning and selection
- Search: none. One pre-declared rule per family (edge_lab.py:1-24, "PRE-DECLARED before any run").
- Configurations run (counted from the code/results): 4 (F3, F4, F5, F7). Ledger count (registry/trial_ledger.csv n_variants): 4. They agree.
- How the reported variant was chosen: not applicable.
- Preregistered: partly. Rules and pass bars are in the docstring, dated 2026-10-13. There is no separate prereg file. PASS bars: F3 in-window mean > out-of-window, t >= 2 overall and higher in both halves; F4 net yield > 5%/yr in both halves and worst month > -2%; F5 excess Sharpe >= 0.3 in both halves; F7 PF >= 1.2 in both halves with n >= 15 per half.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| F3 all | 680 in-window days | +4.5 bp/day vs +5.4 rest, t = -0.21; FAIL | [recorded.cross_market.edge_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.edge_lab_py.log) |
| F3 halves | 308 / 372 days | -0.9 vs +4.9 bp/day / +9.0 vs +5.9 bp/day | same |
| F3 window-only strategy | n/a | Sharpe 0.16, CAGR +0.8%, maxDD 18.3%, 19% in market | same |
| F4 all / 2019-22 / 2023-26 | daily series | yield +10.3% / +17.6% / +4.3% a year; worst month -0.48%; FAIL (second half under 5%) | same |
| F5 excess vs equal weight | weekly series | excess Sharpe all 0.11, H1 0.20, H2 -0.02; FAIL | same |
| F7 all | 76 | PF 0.76, mean -0.81% per trade; FAIL. INSUFFICIENT SAMPLE | same |
| F7 halves | 31 / 45 | PF 1.05 / 0.61. INSUFFICIENT SAMPLE | same |

## Code and how to rerun
- Code: [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) (functions `f3`, `f4`, `f5`, `f7`), data fetchers [fetch_crypto2.py](../../../originals/gann_bot_500/research/cross_market/fetch_crypto2.py) and [fetch3.py](../../../originals/gann_bot_500/research/cross_market/fetch3.py).
- Audit rerun stage: `l1_queue` ("recorded cross_market edge_lab.py" in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); a split-adjusted variant in `adj_run` ([adj.cross_market.edge_lab.py.log](../../../audit/phaseC/logs_L1/adj.cross_market.edge_lab.py.log)).
- Public data enough? No. F3 and F7 need group `broker_mt5` MT5 D1 files. F4 and F5 use Binance data that a public fetch could rebuild, but the manifest files them under `broker_mt5`, so the public tier does not supply them.

## Corrections from the release review
- The title says F3, F5 and F7, but the entry and its 4 ledger variants also cover F4 (funding carry). The README results quote F4's "+4.3%/yr" without naming it as a FAIL against a 5% bar.
- "Rules: F3, F4, F5, F7" and "Costs: see code" and "Gates: see code" give nothing. The rules, costs and gates are in edge_lab.py:1-24 and the functions above.
- "Splits: halves" hides that each family uses a different cut date (2019-01-01, 2023-01-01, 2022-07-01, 2016-01-01).
- F7 "PF 0.76" is given without n. It is n=76 (halves 31 and 45), INSUFFICIENT SAMPLE.
- "Data: MT5, Binance" is right, but the manifest labels the Binance crypto and funding files `broker_mt5` (manifest.csv lines 338-381), so they are not offered for public rerun.
- The caveat says "No cointegration test exists anywhere on disk". That is now out of date: the audit's [E1-PAIRS](../../../experiments/pairs/E1-PAIRS/README.md) runs Engle-Granger and Johansen tests ([e1_pairs.py](../../../audit/phaseE/e1_pairs.py)). F7 itself has no such test.
- The README links no code. edge_lab.py is published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All FAIL; F7 gold/silver ratio z>2 PF 0.76; F4 2023-26 +4.3%/yr |
| Rerun, recorded clock | All FAIL |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
F7 is a ratio z-score. No cointegration test exists anywhere on disk.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
