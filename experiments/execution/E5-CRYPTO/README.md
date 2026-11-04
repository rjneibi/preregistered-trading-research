# E5-CRYPTO

**Audit verdict: VERIFIED.** Original verdict: CORRECTION. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Real fees, funding and delisted coins change the results.

Family: execution. Market: crypto. Timeframe: D1. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
An audit-phase cost correction, run 2026-10-31. It reran the CR-1 rules (BTC, ETH) and the EDGE-1-F6 crypto trend rule as stored, on three real Binance fee tiers, with slippage and perpetual funding. It also added eight collapsed or delisted coins to F6's universe to test survivorship ([audit/prereg/E5-CRYPTO.md](../../../audit/prereg/E5-CRYPTO.md)). The slices were already opened, so results are cost corrections; the prereg says verdicts cannot improve.

## Instruments and data
- Instruments: CR-1: BTCUSDT, ETHUSDT. F6: BTC, ETH, BNB, XRP, ADA, SOL, DOGE, LTC, LINK, DOT, AVAX, TRX ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) line 201). Survivorship add-ons: LUNA (old chain), FTT, UST, SRM, WAVES, MITH, BTS, ANC, picked before data was read (prereg).
- Timeframe(s): D1.
- Data source and file(s): CR-1 Binance daily klines `cross_market/data/*USDT_1d.npz` / `_D1.npz` (group `binance`). F6 `cross_market/data_edge/C_<coin>_D1.npz` (fetched from Binance by [fetch_crypto2.py](../../../originals/gann_bot_500/research/cross_market/fetch_crypto2.py)). Funding history `audit/public/funding_<coin>.json` and dead-coin klines `audit/public/kl_<coin>.json`, fetched by [audit/phaseE/fetch_public.py](../../../audit/phaseE/fetch_public.py) (group `public_api`) ([e5_crypto.py](../../../audit/phaseE/e5_crypto.py) lines 17, 27-34, 200-206).
- Period: as the originals; CR-1 2017-08 to 2026-10. Dead coins join on their first kline and leave at their last ([e5_result.json](../../../audit/phaseE/e5_result.json) survivorship_notes).
- In-sample / out-of-sample: none. Same halves as the originals: CR-1 split at 2022-01-01; F6 split at 2022-07-01 (e5_crypto.py line 194).

## Rules
- Entry and exit: unchanged from CR-1 (see that page) and from EDGE-1-F6. The code imports the sandboxed crypto_lab, swing_lab and edge_lab unchanged ([e5_crypto.py](../../../audit/phaseE/e5_crypto.py) line 1).
- F6 as rerun: long a coin when close > SMA50; weight = 0.02 / 60-day return volatility, capped at 1, divided by the number of coins with a signal value; positions taken next day (e5_crypto.py lines 169-186).
- Dead coins: klines cut at the first gap over 3 days; if the last kline is more than 7 days before the panel end, a final day at 50% of the last close is added as the exit haircut (e5_crypto.py lines 200-220).
- Filters: none added.
- Position sizing: CR-1 100% notional long/flat; swing per-trade returns; F6 volatility-scaled equal risk.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Fee tiers (per side) | spot VIP0 0.10%; spot with BNB 0.075%; USD-M perp 0.05% | [e5_crypto.py](../../../audit/phaseE/e5_crypto.py) line 20; prereg |
| Slippage (per side) | 2 bp BTC and ETH; 10 bp other coins | e5_crypto.py lines 23-24 |
| Funding | Binance USD-M funding, daily sums, perp tier only; spot fee before a coin's perp listing | e5_crypto.py lines 27-34, 105-107, 182-186 |
| F6 trend and sizing | SMA50; 60-day vol; target 0.02 | e5_crypto.py lines 169-176 |
| Dead-coin haircut | 50% of last close | e5_crypto.py line 216 |
| CR-1b twin | run-shuffle, 1,000 draws, seed 3, gate p < 0.0125 | e5_crypto.py lines 61-89 |
| Swing gate | PF >= 1.15 both halves, n >= 30 per half, twin p < 0.005, ETH PF > 1 | e5_crypto.py line 163 |

## Costs
- Trend rules: each position change pays fee + slippage (per side); perp tier also pays funding while long ([e5_crypto.py](../../../audit/phaseE/e5_crypto.py) lines 108-112). CR-1 had charged 0.10% round trip (0.05% per side) plus 15%/yr financing, so E5 doubles the spot fee and replaces the flat financing with actual funding or none.
- Swing rules: round-trip cost = 2 x (fee + slippage) x median close, in price units; financing 0 (lines 138-148). Note from the code: the swing twin (`swing_lab.twin_p`) still charges its random trades 5%/yr financing ([swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) line 117) while the rule pays none here. This tilts the twin test slightly toward the rule.
- No depth-based slippage: historic order books are not available ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 53).

## Tuning and selection
- Search: 3 cost tiers x 2 experiments, plus 1 survivorship run. Also one reproduction of F6 at its original cost.
- Configurations run (counted from the code/results): 7. Ledger count (registry/trial_ledger.csv n_variants): 7 (row AUD-E5). They match. Two earlier runs were superseded: the first lacked the twin gate and had a weak ETH test (AUD-E5-FIX, [e5_result_first_run.json](../../../audit/phaseE/e5_result_first_run.json)); the second charged the perp fee before a coin's perp listing (AUD-E5-FIX2, [e5_result_second_run.json](../../../audit/phaseE/e5_result_second_run.json)).
- How the reported variant was chosen: no selection. All tiers are reported.
- Preregistered: yes, [audit/prereg/E5-CRYPTO.md](../../../audit/prereg/E5-CRYPTO.md). Stated deviation: no depth-based slippage.

## Results
From [audit/phaseE/e5_result.json](../../../audit/phaseE/e5_result.json). Trend Sharpe values are annualised from daily returns; no trade counts are stored for the trend rules.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| CR-1 trend, all tiers | not recorded (position series) | SMA50, SMA100, TSMOM30 beat buy-and-hold in both halves; none passes the CR-1b twin gate. SMA20 no longer beats buy-and-hold | e5_result.json CR1_trend |
| CR-1 SMA50 twin p, spot VIP0 | not recorded | BTC 0.004 / 0.083, ETH 0.073 / 0.031; fail | same |
| CR-1 swing MR3, spot VIP0 | BTC 82 (33 + 49) | PF 3.47 / 1.90, twin p 0.003, ETH PF 1.86: clears the original gate. INSUFFICIENT SAMPLE | e5_result.json CR1_swing |
| CR-1 swing MR3, spot BNB | BTC 82 | twin p 0.007; fail. INSUFFICIENT SAMPLE | same |
| CR-1 swing MR3, perp | BTC 82 | twin p 0.008; fail. INSUFFICIENT SAMPLE | same |
| CR-1 swing, other 8 rules, all tiers | BTC 24-269 | all fail | same |
| F6 at original cost (reproduction) | not recorded | Sharpe 1.522 vs buy-and-hold 0.959; max DD -26.6% vs -48.3% | e5_result.json F6_check_original_cost |
| F6 spot VIP0 / spot BNB / perp | not recorded | Sharpe 1.472 / 1.487 / 1.358 | e5_result.json F6 |
| F6 spot VIP0 with 8 dead coins | 7,742 coin-days added | Sharpe 1.508 vs buy-and-hold 0.882 | e5_result.json F6_survivorship_spot_vip0 |
| Audit | | VERIFIED. "No verdict moves" | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 87 |

The audit keeps MR3 failed: the slice was already opened, and p 0.003 against 0.007 and 0.008 on the other tiers is read as noise ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 43). The blind prediction (F6 Sharpe falls from survivorship) was wrong: F6 rose with the dead coins.

## Code and how to rerun
- Code: [audit/phaseE/e5_crypto.py](../../../audit/phaseE/e5_crypto.py), [audit/phaseE/fetch_public.py](../../../audit/phaseE/fetch_public.py); rule code [crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py), [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py), [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py).
- Audit rerun stage: `e5` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)). It is listed in [audit/tools/stages_broker.txt](../../../audit/tools/stages_broker.txt), so in the public tier it is expected to fail.
- Public data enough? partly. `binance` and `public_api` groups are public. The F6 coin files `data_edge/C_*_D1.npz` are classed `broker_mt5` in [data/manifest.csv](../../../data/manifest.csv) rows 338-349, although fetch_crypto2.py downloads them from Binance's public API. [audit/tools/outputs_broker.txt](../../../audit/tools/outputs_broker.txt) line 13 says e5_result.json "Reads MetaTrader 5 demo exports". The published files do not explain which MT5 input E5 needs.

## Corrections from the release review
- README Provenance: "`audit/phaseE` (not published)". Wrong. [e5_crypto.py](../../../audit/phaseE/e5_crypto.py) and [e5_result.json](../../../audit/phaseE/e5_result.json) are in the repo.
- README Data: "Binance" only. The public tier marks this stage as needing broker data, and the F6 coin files are classed broker in the manifest. The README should say the public rerun is expected to fail.
- README Results: "Cost correction, no verdict moves." Incomplete. MR3 clears CR-1's original swing gate at spot VIP0 (n=82, twin p 0.003, INSUFFICIENT SAMPLE) and is kept failed by an audit judgment ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 43). The README and the CR-1 summaries do not say this (review T7).
- README Rules, Costs, Splits all say "see prereg"; no n is given next to any figure.
- Not disclosed: in this rerun the swing twin is charged 5%/yr financing while the rule is charged none ([swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) line 117; [e5_crypto.py](../../../audit/phaseE/e5_crypto.py) line 148). This favours the rule in the twin test, which matters for the MR3 p-value.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Cost correction, no verdict moves. See audit/phaseE/e5_result.json. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. Cost correction of opened slices. No verdict moves. No trend rule passes. MR3 clears CR-1's gate at spot VIP0 at n=82, INSUFFICIENT SAMPLE, and stays failed: these slices were already opened, so a verdict cannot improve, and p 0.003 against 0.007 and 0.008 on the other tiers is noise. F6 Sharpe 1.36 to 1.49. Coin history stays incomplete: only 8 dead coins added.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
