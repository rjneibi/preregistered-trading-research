# CR-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Index swing rules and long/flat trend work on crypto.

Family: crypto. Market: BTC/ETH. Timeframe: D1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Whether daily long/flat trend rules and the swing rules from the author's index study (SW-1) work on Bitcoin and Ether. Block A compared six trend rules with buy-and-hold. Block B ran nine long-only swing rules against a random-entry twin. Block C reported mean return by weekday only. A follow-up (CR-1b) asked whether the trend rules that beat buy-and-hold show real timing, using run-shuffled twins ([crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py) lines 1-15; [crypto_twin.py](../../../originals/gann_bot_500/research/cross_market/crypto_twin.py) lines 1-3).

## Instruments and data
- Instruments: BTCUSDT (discovery) and ETHUSDT (confirmation) ([crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py) lines 1, 6).
- Timeframe(s): daily bars, UTC days. Decisions at the daily close, trades at the next open.
- Data source and file(s): Binance public klines, fetched by [fetch_binance.py](../../../originals/gann_bot_500/research/cross_market/fetch_binance.py) into `cross_market/data/BTCUSDT_1d.npz`, `ETHUSDT_1d.npz` (trend block) and `*_D1.npz` (swing block; same hashes as the 1d files) ([data/manifest.csv](../../../data/manifest.csv) rows 283-296, group `binance`).
- Period: 2017-08 to 2026-10 (crypto_lab.py line 1).
- In-sample / out-of-sample: no IS/OOS. Two halves, 2017-08-01 to 2021-12-31 and 2022-01-01 onward, each must pass (crypto_lab.py lines 6, 22).

## Rules
- Entry, Block A (trend, long or flat; position decided at close t, held open t+1 to open t+2): A1 close > SMA(N), N = 20, 50, 100, 200; A2 close above close 30 days earlier (TSMOM30); A3 Donchian, enter on close above the prior 20-day high, exit on close below the prior 10-day low (crypto_lab.py lines 9-11, 54-62).
- Entry, Block B (swing, long only; signal at close, enter next open), from [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 9-21 and 58-87: MR1 RSI2 < 10 above SMA200; MR2 IBS < 0.2; MR3 three down closes above SMA200; MR4 close below lower Bollinger(20,2) above SMA200; MR5 close at the 7-day low above SMA200; TR1 close above the 55-day high; TR2 SMA50 > SMA200 and close back above EMA20 after at least 3 closes below; TR3 close at the 252-day high; TR4 NR7 day then close above its high. MR6 (short) was skipped for crypto (crypto_lab.py line 92).
- Exit (stop, target, time): Block A, on the rule turning off. Block B: MR1 close > SMA5; MR2 IBS > 0.8 or close > previous high; MR3 first up close; MR4 close > SMA20; MR5 close at the 7-day high; TR1 close < 20-day low; TR2 close < SMA50 or close > entry close + 2 ATR; TR3 close < SMA50; TR4 after 5 days. Max hold 15 days. Exit fills at the open after the exit condition. No stops (swing_lab.py lines 3-4, 28, 89-106).
- Filters: the SMA200 conditions above; the first 252 bars are warm-up (swing_lab.py line 93).
- Position sizing: 100% notional, long or flat; returns are per-unit percentages.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| SMA trend lengths | 20, 50, 100, 200 | [crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py) line 53 |
| Time-series momentum | 30 days | crypto_lab.py line 54 |
| Donchian | entry 20-day high, exit 10-day low | crypto_lab.py line 55 |
| Swing SMAs, EMA | SMA 5, 20, 50, 200; EMA 20 | [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 38-39 |
| RSI2, IBS, Bollinger | RSI2 < 10; IBS < 0.2 / > 0.8; BB(20,2) | swing_lab.py lines 10-13 |
| Breakouts | 55/20-day; 252-day high; 7-day low/high; NR7 | swing_lab.py lines 14-21 |
| TR2 target | 2 x ATR | swing_lab.py line 78 |
| Max hold (swing) | 15 days | swing_lab.py line 28 |
| Swing twin draws | 2,000 random-entry sets, same hold lengths | swing_lab.py lines 109-129 |
| CR-1b twin draws | 1,000 run-shuffles per half, seed 3 | [crypto_twin.py](../../../originals/gann_bot_500/research/cross_market/crypto_twin.py) lines 2, 5 |

## Costs
- CFD world (the gate): 0.10% round trip, charged as half per position change, plus 15%/yr financing on longs per night ([crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py) lines 3-5, 19, 38-44). Spot world (reported only): 0.10% round trip, no financing.
- Swing block: the spread is 0.10% of the median close, in price units, and financing 15%/yr (crypto_lab.py lines 85-87, 95).
- Note from the code: the swing twin (`swing_lab.twin_p`) charges its random trades 5%/yr financing, not 15% ([swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) line 117). This makes the twin cheaper than the rule, so it tilts the test toward fail.

## Tuning and selection
- Search: a fixed battery, no parameter tuning. Block A 6 rules; Block B 9 rules; CR-1b re-tests the 4 rules that passed Block A.
- Configurations run (counted from the code/results): 15 distinct rules (19 rule tests with CR-1b), each on BTC and ETH and under two cost worlds. Ledger count (registry/trial_ledger.csv n_variants): 20. The code count is 15 (or 19); the ledger figure of 20 is not explained in the published files.
- How the reported variant was chosen: no selection. All rules are reported. Pass rules: Block A, Sharpe and MAR above buy-and-hold in both halves, on BTC and ETH, under CFD costs. Block B, PF at least 1.15 in both halves, at least 30 trades per half, twin p < 0.005, ETH PF > 1 (crypto_lab.py lines 9-14). CR-1b, run-shuffle twin p < 0.0125 (0.05 / 4) in both halves on BTC and ETH (crypto_twin.py lines 2-3).
- Preregistered: partly. The code docstrings say "pre-declared" (crypto_lab.py line 1). No separate prereg file or hash is published. CR-1b was added after Block A results were seen.

## Results
Recorded rerun, from [audit/phaseC/logs_L1/recorded.cross_market.crypto_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.crypto_lab_py.log) and [recorded.cross_market.crypto_twin_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.crypto_twin_py.log).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| A: SMA20, SMA50, SMA100, TSMOM30 vs buy-and-hold | not counted (position series) | PASS on Sharpe and MAR, both halves, BTC and ETH | crypto_lab log |
| A: SMA200, Donchian20/10 | not counted | fail | crypto_lab log |
| A example: BTC SMA50, CFD | not counted | Sharpe 1.55 / 0.56 by half vs buy-and-hold 0.90 / 0.19 | crypto_lab log |
| CR-1b SMA50 run-shuffle p | not counted | BTC 0.005 / 0.097, ETH 0.092 / 0.036; fail | crypto_twin log |
| CR-1b SMA20, SMA100, TSMOM30 | not counted | all fail p < 0.0125 | crypto_twin log |
| B: MR1 | BTC 69 (ETH 64) | PF 1.16 / 2.28, twin p 0.233; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: MR2 | BTC 269 (ETH 287) | PF 1.18 / 0.90, twin p 0.669; fail | crypto_lab log |
| B: MR3 | BTC 82 (ETH 67) | PF 4.17 / 1.90, twin p 0.010; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: MR4 | BTC 24 (ETH 23) | PF 0.33 / 5.21; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: MR5 | BTC 82 (ETH 84) | PF 0.91 / 1.73; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: TR1 | BTC 50 (ETH 44) | PF 1.56 / 1.81, twin p 0.290; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: TR2 | BTC 58 (ETH 50) | PF 2.92 / 0.88; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: TR3 | BTC 34 (ETH 22) | PF 3.05 / 1.52; fail. INSUFFICIENT SAMPLE | crypto_lab log |
| B: TR4 | BTC 137 (ETH 127) | PF 1.29 / 0.74; fail | crypto_lab log |
| Audit | | VERIFIED, reruns exact | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 60 |

The PF pairs are first half / second half for BTC; n is the BTC total over both halves. Later, E5 repriced these rules on real cost tiers; MR3 then cleared the original gate at one tier (n=82, INSUFFICIENT SAMPLE), see [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 87 and the E5-CRYPTO page.

## Code and how to rerun
- Code: [crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py), [crypto_twin.py](../../../originals/gann_bot_500/research/cross_market/crypto_twin.py), [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py), [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) (loader), [fetch_binance.py](../../../originals/gann_bot_500/research/cross_market/fetch_binance.py) (data).
- Audit rerun stage: `l1_queue` ([audit/phaseC/run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) lines 56-57; [audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? yes. Manifest group `binance` (public). The scripts use a path token that is filled by `audit/tools/render_paths.py`.

## Corrections from the release review
- README Preregistration: "pre-declared twin p<0.0125". Wrong as a description of CR-1. There were two blocks with different gates: trend PASS = Sharpe and MAR above buy-and-hold in both halves on BTC and ETH; swing PASS = PF >= 1.15, n >= 30 per half, twin p < 0.005, ETH PF > 1 ([crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py) lines 9-14). The p < 0.0125 gate belongs to the later CR-1b run-shuffle test ([crypto_twin.py](../../../originals/gann_bot_500/research/cross_market/crypto_twin.py) lines 2-3), which the README does not link.
- README Results: "All FAIL the twin gate". Incomplete. Four trend rules passed the buy-and-hold gate and then failed the CR-1b twin. All nine swing rules failed their own gate.
- README Rules: "MR1-5, TR1-4, SMA, TSMOM30". Omits the A3 Donchian 20/10 rule and the discovery-BTC / confirmation-ETH design.
- README Results give no trade counts. Seven of nine swing rules have fewer than 100 BTC trades: INSUFFICIENT SAMPLE.
- Ledger count 20 does not match the 15 rules (19 tests) in the code.
- The summaries do not mention that MR3 cleared the gate at one E5 cost tier (n=82, INSUFFICIENT SAMPLE) (review T7).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All FAIL the twin gate; SMA50 p .005/.097 and .092/.036 |
| Rerun, recorded clock | All FAIL twin gate |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
Probable timing edge, not proven; halves ~4y.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/cross_market/crypto_lab.py](../../../originals/gann_bot_500/research/cross_market/crypto_lab.py)
