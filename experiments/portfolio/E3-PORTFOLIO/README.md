# E3-PORTFOLIO

**Audit verdict: VERIFIED.** Original verdict: DESCRIPTIVE. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Descriptive only.

Family: portfolio. Market: four fragile streams. Timeframe: D1. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
E3 is a descriptive check run by the audit. It takes the four results graded REPRODUCES-BUT-FRAGILE and puts them on one daily calendar. It then reports how correlated they are, how often their worst days and drawdowns overlap, and what an equal-risk mix looks like. By the author's instruction it selects nothing and cannot produce a PASS ([audit/prereg/E3-PORTFOLIO.md](../../../audit/prereg/E3-PORTFOLIO.md); [audit/DECISIONS.md](../../../audit/DECISIONS.md) item 32).

## Instruments and data
- Instruments, by stream:
  - XM-1-A1: US500.
  - SW-1: US500.
  - TUNE-1-DIP: 18 markets: DE40, FRA40, ESP35, AUS200, HK50, EWG, EWJ, EWU, EFA, EEM, FXI, INDA, SMH, XLK, XLV, XLP, XLE, VNQ ([tune_dip.py](../../../originals/gann_bot_500/research/tune1/tune_dip.py) lines 18-19).
  - EDGE-1-F6: 12 coins, BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) line 201).
- Timeframe(s): D1 bars. Each trade's return is booked on its exit date. Days with no exit count as 0 ([e3_portfolio.py](../../../audit/phaseE/e3_portfolio.py) lines 20-28, 44-45).
- Data source and file(s): MetaTrader 5 demo exports, `cross_market/data/*_D1.npz` and `data_edge/*_D1.npz` ([audit/stats/pass_audit.py](../../../audit/stats/pass_audit.py) lines 15-16, 22-34; [data/manifest.csv](../../../data/manifest.csv), group `broker_mt5`).
- Period: 2012-01-11 to 2026-10-13, 5,390 calendar days. The common window, with all four streams live, starts 2017-10-17 ([e3_result.json](../../../audit/phaseE/e3_result.json)).
- In-sample / out-of-sample: none. Descriptive only.

## Rules
- Entry (from [audit/stats/pass_audit.py](../../../audit/stats/pass_audit.py), the audit's rewrite that matched the originals trade by trade, per [audit/DECISIONS.md](../../../audit/DECISIONS.md) item 41):
  - XM-1-A1: long when RSI(2) < 10 and close > SMA200, at the next open (`a1`, lines 59-79).
  - SW-1: long when IBS < 0.2, after 252 bars, at the next open (`ibs_rule`, lines 82-100).
  - TUNE-1-DIP: the `a1` rule on each of the 18 markets (e3_portfolio.py lines 35-39).
  - EDGE-1-F6: each coin long when close > SMA50 ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 256-268).
- Exit (stop, target, time):
  - `a1`: close > SMA5, or 10 bars, exit at the next open.
  - `ibs_rule`: IBS > 0.8, or close > the prior high, or 15 bars.
  - F6: daily rebalancing by signal.
- Filters: none beyond the rules.
- Position sizing: each stream is a return series. TUNE-1-DIP gives each of its 18 markets weight 1/18 (e3_portfolio.py line 38). F6 sizes each coin at 2% / 60-day vol, capped at 1 (edge_lab.py line 263). The combination weights each stream by the inverse of its daily sd over the common window (e3_portfolio.py lines 69-71). The prereg calls this "information figure only".

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| RSI | period 2, recursion with alpha 0.5; entry < 10 | [pass_audit.py](../../../audit/stats/pass_audit.py) lines 44-56, 59 |
| Trend / exit MA (`a1`) | SMA200 / SMA5; max 10 bars | pass_audit.py line 59 |
| IBS | entry < 0.2; exit > 0.8 or close > prior high; max 15 bars | pass_audit.py lines 82-92 |
| Crypto trend | SMA50; 60-day vol; 2% vol target per coin | [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 258-263 |
| Worst-day set | each stream's worst 10% of losing days | [e3_portfolio.py](../../../audit/phaseE/e3_portfolio.py) line 60 |
| Deep drawdown | days at ≤ 50% of the stream's max DD; other stream counted if in DD > 2% | e3_portfolio.py lines 66-67 |
| Sharpe | daily mean / sd × √365 | e3_portfolio.py line 77 |

## Costs
- `a1` and `ibs_rule`: spread = 1.5 × median positive spread of the export, charged once per trade, plus financing of 5%/365 per night ([pass_audit.py](../../../audit/stats/pass_audit.py) lines 17, 32, 75, 96).
- TUNE-1-DIP markets: spread floored at 0.02% of median price ([e3_portfolio.py](../../../audit/phaseE/e3_portfolio.py) line 37).
- F6: 0.1% of turnover ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) line 267).
- The prereg itself states no costs.

## Tuning and selection
- Search: none.
- Configurations run (counted from the code/results): 1 descriptive run. Ledger count: 0 ([audit/prereg/E3-PORTFOLIO.md](../../../audit/prereg/E3-PORTFOLIO.md); README). They agree.
- How the reported variant was chosen: not applicable. The weights use the full common window, so the combination is hindsight-scaled ([e3_result.json](../../../audit/phaseE/e3_result.json) note).
- Preregistered: partly. [audit/prereg/E3-PORTFOLIO.md](../../../audit/prereg/E3-PORTFOLIO.md) says streams come from saved trades in `trade_checks/`. The code instead rebuilds them from the pass_audit.py rule code, because those files hold only 20 sampled trades ([e3_portfolio.py](../../../audit/phaseE/e3_portfolio.py) line 1; [audit/DECISIONS.md](../../../audit/DECISIONS.md) item 41).

## Results
No trade counts are written to [e3_result.json](../../../audit/phaseE/e3_result.json). The figures are daily-series statistics on the common window (2017-10-17 to 2026-10-13).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Daily correlation, common window | not recorded | XM-1-A1 vs TUNE-1-DIP 0.385; all other pairs -0.015 to 0.061 | [e3_result.json](../../../audit/phaseE/e3_result.json) |
| XM-1-A1 worst-decile days | not recorded | TUNE-1-DIP also down on 100% of them; SW-1 and EDGE-1-F6 on 0% | same |
| Each alone (Sharpe, max DD) | not recorded | XM-1-A1 0.74, -10.7%; SW-1 1.19, -14.6%; TUNE-1-DIP 0.51, -6.1%; EDGE-1-F6 1.52, -26.6% | same |
| Equal-risk weights | - | XM-1-A1 0.23, SW-1 0.106, TUNE-1-DIP 0.613, EDGE-1-F6 0.05 | same |
| Equal-risk combination | not recorded | Sharpe 1.78, max DD -7.1%, total +45.9% | same |

These Sharpe levels annualise by √365 on a calendar-day index. They are not comparable with the stored Sharpes of the source entries ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 41). Verdict: DESCRIPTIVE; audit VERIFIED ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 85).

## Code and how to rerun
- Code: [audit/phaseE/e3_portfolio.py](../../../audit/phaseE/e3_portfolio.py). It reuses [audit/stats/pass_audit.py](../../../audit/stats/pass_audit.py), [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) and [tune_dip.py](../../../originals/gann_bot_500/research/tune1/tune_dip.py). Output: [e3_result.json](../../../audit/phaseE/e3_result.json).
- Audit rerun stage: `e3` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh) line 66). It is listed as a broker stage in [audit/tools/stages_broker.txt](../../../audit/tools/stages_broker.txt).
- Public data enough? No. It needs the `broker_mt5` group ([audit/tools/outputs_broker.txt](../../../audit/tools/outputs_broker.txt): "phaseE/e3_result.json | Reads MetaTrader 5 demo exports").

## Corrections from the release review
- "Provenance: `audit/phaseE` (not published)" is wrong. [e3_portfolio.py](../../../audit/phaseE/e3_portfolio.py) and [e3_result.json](../../../audit/phaseE/e3_result.json) are in the repository.
- "Rules: See prereg", "Costs: see prereg" and "Splits/Gates: see prereg" lead to a prereg that states no rules, costs or gates. The stream rules are in [pass_audit.py](../../../audit/stats/pass_audit.py), and the costs are listed above.
- "Data: as sources" leaves out that every input is a broker MT5 export, so the public tier cannot regenerate the result.
- The page does not say that the inputs differ from the prereg. The prereg says saved trades; the code rebuilds streams from rule code ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 41).
- "Market: four fragile streams" overstates the independence. TUNE-1-DIP is the same rule as XM-1-A1 on other markets ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 74). On every one of XM-1-A1's worst-decile days, TUNE-1-DIP is also down ([e3_result.json](../../../audit/phaseE/e3_result.json)).
- The results table gives no figure. The correlation, overlap and combination figures above are in [e3_result.json](../../../audit/phaseE/e3_result.json).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Descriptive. No verdict can come from this entry. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. Descriptive only. It cannot produce a pass.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
