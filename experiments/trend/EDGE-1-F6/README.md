# EDGE-1-F6

**Audit verdict: REPRODUCES-BUT-FRAGILE.** Original verdict: PASSED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Crypto trend portfolio beats buy and hold.

Family: trend. Market: 12 crypto coins. Timeframe: D1. Idea source: published.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
F6 is the crypto trend portfolio among the seven pre-declared EDGE-1 tests. Each of 12 coins is held long while its close is above its 50-day average, and flat otherwise. Positions are sized to equal risk. The test asked whether this beats an equal-weight buy-and-hold of the same coins in both halves, with a smaller drawdown. It passed its gate. The audit graded it REPRODUCES-BUT-FRAGILE: the coin list is a hindsight pick, and the variants are close neighbours. Sources: [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 1-2, 17-19, 256-286; [VERDICTS.md](../../../audit/VERDICTS.md) line 64.

## Instruments and data
- Instruments: BTC, ETH, BNB, XRP, ADA, SOL, DOGE, LTC, LINK, DOT, AVAX, TRX against USDT ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) line 201). These are today's large coins, chosen in 2026 (caveat on the README; [E5-CRYPTO.md](../../../audit/prereg/E5-CRYPTO.md)).
- Timeframe(s): D1, 365 days a year (Sharpe annualised by sqrt(365); edge_lab.py lines 281-285).
- Data source and file(s): Binance public spot klines, fetched by [fetch_crypto2.py](../../../originals/gann_bot_500/research/cross_market/fetch_crypto2.py) lines 8-18 into `data_edge/C_<coin>_D1.npz`. The manifest files these under group `broker_mt5`, access `broker` ([data/manifest.csv](../../../data/manifest.csv) lines 338-349), although the fetch script reads Binance's public API.
- Period: klines requested from 2017-08-17 (start time 1502928000000 ms, fetch_crypto2.py line 11). The scored series has 3,284 days ([pass_audit.json](../../../audit/stats/pass_audit.json) `EDGE-1-F6`). Yearly results run from 2017 to 2026 ([recorded.cross_market.f6_stress_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.f6_stress_py.log)). Each coin enters when its own history starts.
- In-sample / out-of-sample: no fit. Halves split at 2022-07-01 (edge_lab.py line 271).

## Rules
- Entry: per coin, signal = 1 when close > SMA50, else 0 (undefined until the SMA exists) (edge_lab.py line 260).
- Exit (stop, target, time): flat when close <= SMA50. No stop or target. Daily rebalance with a 1-day lag (lines 263-267).
- Filters: none.
- Position sizing: weight = signal x 0.02 / 60-day std of daily returns, capped at 1.0, then divided by the number of coins with data that day (lines 259, 263-265). Buy-and-hold benchmark: the same sizing with the signal always 1 (line 270).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Trend filter | SMA 50 of close | edge_lab.py line 260 |
| Vol estimate | 60-day std of daily returns | line 259 |
| Daily vol target per coin | 0.02 | line 263 |
| Weight cap | 1.0 | line 263 |
| Lag | 1 day | line 266 |
| Half split | 2022-07-01 | line 271 |
| Run-shuffle control | 200 draws, seed 7: each coin's on/off runs reshuffled, same time in market | lines 34, 274-282 |
| Stress set | SMA 20/30/50/100/200; 2-day lag; 3x cost; BTC+ETH only; 10 alts only; drop best coin (BNB); since 2021-01 | [f6_stress.py](../../../originals/gann_bot_500/research/cross_market/f6_stress.py) lines 14-20 |

## Costs
- 0.1% of turnover per side: `pos.diff().abs().sum() x 0.001` (edge_lab.py line 267). No spread, financing or slippage in the original.
- Audit E5 reran F6 on three fee tiers: Binance spot VIP0 0.10%/side, spot with BNB discount 0.075%, USD-M perpetual 0.05% plus funding. It added slippage of 2 bp (BTC, ETH) or 10 bp (others) per side, an ESTIMATE ([E5-CRYPTO.md](../../../audit/prereg/E5-CRYPTO.md) lines 7-10).

## Tuning and selection
- Search: SMA50 was pre-declared (edge_lab.py line 17). After the pass, f6_stress.py ran 11 lines: five SMA lengths, a 2-day lag, 3x cost, two coin subsets, dropping the best coin, and a 2021+ start (f6_stress.py lines 14-20). The audit added lags 2 and 3 ([VERDICTS.md](../../../audit/VERDICTS.md) line 64) and the E5 cost and survivorship runs.
- Configurations run (counted from the code/results): 11 distinct configurations in the original (the SMA50 line in f6_stress.py repeats edge_lab's base). Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row EDGE-1-F6, n_variants): 8. The two differ, and the ledger count is lower. The audit's PBO uses 5 variants (the SMA lengths) ([pass_audit.json](../../../audit/stats/pass_audit.json) `cscv`). The family N for DSR is 34 ([VERDICTS.md](../../../audit/VERDICTS.md) line 120).
- How the reported variant was chosen: SMA50 was declared before the run, and it is the variant reported. The stress runs came after it and did not replace it. SMA20 has the same Sharpe of 1.52 (f6_stress log).
- Preregistered: partly. The rule and gate are "PRE-DECLARED before any run" in the edge_lab.py docstring (lines 1-2, 17-19). There is no separate prereg file. The coin list was picked with hindsight. The original dated record, `DECISIONS.log`, is not in the repo.

## Results
Gate: Sharpe >= buy-and-hold in both halves, maxDD <= 0.6 x buy-and-hold's, run-shuffle p < 0.05 (edge_lab.py lines 18-19, 283). This is a daily portfolio return series, not a trade list. The 100-trade rule does not apply as such. The series has 3,284 days.

| Slice | Days | Result | Source file |
|---|---|---|---|
| Trend, all | 3,284 | Sharpe 1.52, CAGR +34.9%, vol 21.2%, maxDD 26.6% | [edge_lab log](../../../audit/phaseC/logs_L1/recorded.cross_market.edge_lab_py.log); pass_audit.json |
| Buy-and-hold, all | 3,284 | Sharpe 0.96, CAGR +30.7%, maxDD 48.3% | edge_lab log |
| Half 1 / half 2, trend vs buy-and-hold | split 2022-07-01 | 1.98 vs 1.06 / 1.00 vs 0.85 | edge_lab log |
| Run-shuffle control | 200 draws | p = 0.005; gate PASS | edge_lab log |
| SMA 20 / 30 / 100 / 200 | - | Sharpe 1.52 / 1.47 / 1.26 / 1.03 | [f6_stress log](../../../audit/phaseC/logs_L1/recorded.cross_market.f6_stress_py.log) |
| 3x cost; BTC+ETH only; 10 alts; drop BNB; since 2021 | - | Sharpe 1.40; 1.44; 1.28; 1.45; 1.28 | f6_stress log |
| By year | - | 2017 +47%, 2018 -10%, 2019 +40%, 2020 +99%, 2021 +102%, 2022 -20%, 2023 +52%, 2024 +52%, 2025 +1%, 2026 +7% | f6_stress log |
| Lag 1 / 2 / 3 | - | Sharpe 1.52 / 1.50 / 1.43 | VERDICTS.md line 64 |
| E5 cost tiers: VIP0 / BNB / perp | - | Sharpe 1.472 / 1.487 / 1.358 | [e5_result.json](../../../audit/phaseE/e5_result.json) |
| E5 with 8 collapsed coins added (VIP0) | +7,742 coin-days | Sharpe 1.508 vs buy-and-hold 0.882 | e5_result.json |
| DSR at ledger N 179,000 / family N 34 | 3,284 | 0.52 / 0.993 | VERDICTS.md line 120 |
| PBO (5 SMA variants) | - | 0.742 | pass_audit.json |
| Since 2025 | - | Sharpe 0.33 | [review_f/out/f6.out](../../../audit/review_f/out/f6.out) (saved 2026-11-03, audit DECISIONS 63) |

## Code and how to rerun
- Code: [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) function `f6` (lines 256-286), run with `python edge_lab.py f6`; [f6_stress.py](../../../originals/gann_bot_500/research/cross_market/f6_stress.py); data fetch [fetch_crypto2.py](../../../originals/gann_bot_500/research/cross_market/fetch_crypto2.py). Audit: [pass_audit.py](../../../audit/stats/pass_audit.py), [e5_crypto.py](../../../audit/phaseE/e5_crypto.py), spot rows [EDGE-1-F6.csv](../../../audit/trade_checks/EDGE-1-F6.csv).
- Audit rerun stage: `l1_queue` (jobs `recorded cross_market edge_lab.py` and `recorded cross_market f6_stress.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); `pass_audit`; `spot`; `e5` ([run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? No, as the manifest stands. The coin files are in group `broker_mt5`, and `pass_audit`, `spot` and `e5` are in [stages_broker.txt](../../../audit/tools/stages_broker.txt). The same klines can be fetched from Binance's public API with fetch_crypto2.py, but a fresh fetch is not checked against the stored hashes.

## Corrections from the release review
- README "Market: 12 crypto coins" does not name them. They are BTC, ETH, BNB, XRP, ADA, SOL, DOGE, LTC, LINK, DOT, AVAX, TRX (edge_lab.py line 201).
- README "Rules: Close>SMA50, equal risk." Incomplete. Sizing is 0.02 / 60-day vol, capped at 1, split equally across live coins, with a 1-day lag (edge_lab.py lines 259-267).
- README "Splits: halves" gives no date. The split is 2022-07-01 (edge_lab.py line 271).
- README "Gates: see code". The gate is Sharpe >= buy-and-hold in both halves, maxDD <= 0.6 x buy-and-hold's, and run-shuffle p < 0.05 (edge_lab.py lines 18-19).
- README "Parameters and tuning: stress set. Variants counted in the ledger: 8." The stress set has 11 lines (f6_stress.py lines 14-20), more than the ledger's 8. The page should list them.
- README "Data: Binance" gives no range. The range is 2017-08-17 on, 3,284 scored days. The manifest labels these files `broker_mt5`, which contradicts "Binance". One of the two is wrong, and the manifest should be fixed or explained.
- README "Sharpe 0.33 since 2025" had no saved output when the review began; only [f6.py](../../../audit/review_f/f6.py) line 22 computed it. The script was rerun unchanged and its output saved as [review_f/out/f6.out](../../../audit/review_f/out/f6.out): Sharpe 0.33 for 2025 onward, and 1.522, 1.501 and 1.432 at lags 1, 2 and 3 (audit DECISIONS 63).
- README "Provenance" lists only `DECISIONS.log (not published)`. edge_lab.py, f6_stress.py, the rerun logs, pass_audit.json and e5_result.json are all published and should be linked.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Sharpe 1.52 vs 0.96, maxDD 27% vs 48%, run-shuffle p=0.005 |
| Rerun, recorded clock | Sharpe 1.52 vs 0.96, DD 26.6/48.3 |
| Rerun, true UTC | no HistData dependence |

## Verdict
REPRODUCES-BUT-FRAGILE. Rewrite exact. PBO 0.742 on 5 variants, all with Sharpe 1.03 to 1.52, so it shows which neighbour won and not whether trend works. Delay barely matters: 1.52, 1.50, 1.43 at lags 1, 2, 3. Sharpe 0.33 since 2025. The twelve coins stay hindsight picks, so survivorship is not cleared. E5: Sharpe 1.36 to 1.49 on real cost tiers, 1.51 with eight collapsed coins added. Spot checks 20/20.

## Audit caveats
SURVIVORSHIP: today's top-12 coins. 2025 +1%, 2026 +7%. Needs spot venue. Not deflated by programme trial count.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
