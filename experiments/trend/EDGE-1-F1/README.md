# EDGE-1-F1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Multi-asset TSMOM works on CFDs.

Family: trend. Market: 59 markets. Timeframe: D1. Idea source: Moskowitz et al.; Hurst et al..

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
F1 is one of seven pre-declared portfolio tests in EDGE-1 (F1-F7). It ran diversified time-series momentum (the Moskowitz/Ooi/Pedersen 2012 design) on every non-crypto market in the author's daily data set. Each market was sized to equal risk and rebalanced every 21 days. It passed only if the net Sharpe was at least 0.4 in both halves and beat a random-sign control. It failed: the net Sharpe was negative. Source: [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 1-7, 108-147.

## Instruments and data
- Instruments: 59 markets: EURUSD, EWA, IWM, TLT, US30, US500, USTEC, XAGUSD, XAUUSD, AUDJPY, AUDUSD, AUS200, DBC, DE40, EEM, EFA, ESP35, EURCHF, EURGBP, EURJPY, EWC, EWG, EWJ, EWU, FRA40, FXA, FXE, FXI, FXY, GBPJPY, GBPUSD, GDX, HK50, IEF, INDA, LQD, NZDUSD, SHY, SMH, TIP, US2000, USDCAD, USDCHF, USDJPY, USDMXN, USDNOK, USDSEK, USDTRY, USDZAR, USO, VNQ, WTI, XLC, XLE, XLK, XLP, XLV, XPDUSD, XPTUSD ([recorded.cross_market.edge_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.edge_lab_py.log) line 2). The universe is every `*_D1.npz` file with more than 750 rows, minus crypto, VIX products, thin factor ETFs and duplicates of the CFD indices (edge_lab.py lines 69-84).
- Timeframe(s): D1, weekdays only (edge_lab.py line 114).
- Data source and file(s): broker MT5 demo exports in `research/cross_market/data/` and `data_edge/` (manifest group `broker_mt5`, not published; [data/manifest.csv](../../../data/manifest.csv)).
- Period: closes from 2004-01-01, returns counted from 2005-01-01 (edge_lab.py lines 111, 118). End date: Not recorded in the published files (the data files run to 2026-10).
- In-sample / out-of-sample: no fit, so no IS/OOS. The gate uses halves split at 2016-01-01: 2005-15 and 2016-26 (lines 7, 121).

## Rules
- Entry: signal = average of sign(close / close 21 days ago - 1), sign(... 63 days ago ...) and sign(... 252 days ago ...), so it takes values -1, -1/3, +1/3 or +1. Weight = signal x 0.10 / annualised 60-day vol (vol floored at 3%), clipped to ±2. Weights are then scaled by sqrt(n)/n across active markets, which gives about 10% book vol if the markets were uncorrelated (edge_lab.py lines 87-93).
- Exit (stop, target, time): no stops. Weights are reset every 21 trading days and held in between (lines 94-95). Positions take effect with a 1-day lag (line 101).
- Filters: daily moves over 40% are masked as bad prints or rolls, and gaps are forward-filled for up to 5 days (lines 111-113).
- Position sizing: equal-risk weights as above. The return is the portfolio's daily net return.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Lookbacks | 21, 63, 252 days | edge_lab.py line 87 |
| Rebalance | every 21 days | line 87 |
| Vol estimate | 60-day std of daily returns, annualised by sqrt(252), floor 3% | line 89 |
| Vol target per market | 10% | line 91 |
| Weight clip | ±2 | line 91 |
| Execution lag | 1 day (stress: 2 days) | lines 99, 123 |
| Bad-print mask | abs daily move > 40% | line 112 |
| Random-sign control | 200 draws, seed 7 | lines 34, 130 |

## Costs
- Spread: turnover x (1.5 x the market's median spread/close + 0.0002) ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 104, 115).
- Financing: 3%/yr on gross exposure, charged daily (lines 6, 99, 104).
- No commission or slippage beyond that.

## Tuning and selection
- Search: none. One pre-declared rule (edge_lab.py lines 1-7). The only extra run is a 2-day-lag stress (line 123).
- Configurations run (counted from the code/results): 1 (plus the lag stress). Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row EDGE-1-F1, n_variants): 1. They agree.
- How the reported variant was chosen: not applicable.
- Preregistered: partly. The rule and gate are "PRE-DECLARED before any run" in the code docstring (edge_lab.py lines 1-7). There is no separate prereg file. The original dated record, `DECISIONS.log`, is not in the repo.

## Results
| Slice | Days | Result | Source file |
|---|---|---|---|
| All, 2005-2026, net | not printed | Sharpe -0.27, CAGR -10.0%, vol 26.1%, maxDD 92.4% | [edge_lab log](../../../audit/phaseC/logs_L1/recorded.cross_market.edge_lab_py.log) |
| 2005-15 | not printed | Sharpe -0.29 | edge_lab log |
| 2016-26 | not printed | Sharpe -0.26 | edge_lab log |
| 2-day lag | not printed | Sharpe -0.28 | edge_lab log |
| Random-sign control | 200 draws | p = 0.005 | edge_lab log |
| Gate | - | FAIL (Sharpe below 0.4 in both halves) | edge_lab log |

This is a portfolio return series, not a trade list, so the 100-trade rule does not apply. The series has about 21 years of daily returns. The README's "Gross Sharpe ~0.27" appears in no published output. The script prints net figures only.

## Code and how to rerun
- Code: [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py), function `f1` (lines 68-147). Run `python edge_lab.py f1`, or with no argument for all of F1-F7 (lines 318-325).
- Audit rerun stage: `l1_queue` (job `recorded cross_market edge_lab.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); `adj_run` for split-adjusted ETF prices ([adj.cross_market.edge_lab.py.log](../../../audit/phaseC/logs_L1/adj.cross_market.edge_lab.py.log)).
- Public data enough? No. It needs `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv)).

## Corrections from the release review
- README "Rules: 12m TSMOM." Wrong. The signal is the mean sign of the 1-, 3- and 12-month returns (21/63/252 days), rebalanced every 21 days, with 60-day-vol equal-risk sizing at 10% per market (edge_lab.py lines 4-6, 87-96).
- README "Costs: CFD financing". Incomplete. Costs are turnover x (1.5x median spread + 2 bp), plus 3%/yr financing on gross exposure (edge_lab.py lines 6, 104, 115).
- README "Gates: see code". The gate is net Sharpe >= 0.4 in both halves (2005-15, 2016-26) and random-sign control p < 0.05 (edge_lab.py line 7).
- README "Market: 59 markets" names none. The list is in the rerun log, line 2.
- README "Stored: Gross Sharpe ~0.27". No published file holds a gross Sharpe. Only the net Sharpe, -0.27, is in the log.
- README "Provenance" links edge_lab.py but not the rerun log.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Gross Sharpe ~0.27, net -0.27 |
| Rerun, recorded clock | Net Sharpe -0.27 |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/cross_market/edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py)
