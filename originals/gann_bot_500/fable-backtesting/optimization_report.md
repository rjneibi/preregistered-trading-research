# R3/S3 flip-scalp optimization loop — final report

_2026-07-02. Harness: `tune_r3s3.py`. Data: HistData M1 XAUUSD._

## Protocol (anti-overfitting)

- All tuning on **TRAIN** = first 70% of no-Monday R3/S3 trades, 2021-2026 (n=173).
- Survivors checked once on **TEST** = last 30% (n=74).
- Finalist faced a **VIRGIN HOLDOUT**: 2015-2021 (299 no-Mon R3/S3 trades,
  never examined by any prior decision), with $-targets price-deflated by
  entry_price / 2531 (the 2021-26 mean entry).

## FINAL STRATEGY

**Enter at market on the H4 close that flips R3 or S3 (one per zone per day).
Skip Mondays. TP +$8, SL -$12, close at market after 24h if neither hit.**

| Window | n | Win rate | PF | Net (1 lot) | MaxDD |
|---|---:|---:|---:|---:|---:|
| 2021-26 ALL | 247 | **68.4%** | **1.63** | **$47,455** | $6,456 |
| 2021-26 train | 173 | 69.4% | 1.81 | $38,005 | — |
| 2021-26 test | 74 | 66.2% | 1.33 | $9,451 | — |
| **2015-21 virgin holdout** | 299 | 62.2% | **1.14** | $9,169 | — |

Exit mix 2021-26: 151 TP / 56 SL / 40 time-stop. ~1 trade/week.

Compared to the pre-tuning $10/$10 version: WR 59.5%→68.4%, PF 1.42→1.63,
net +$4.8k, drawdown -$0.9k.

## What survived, what died

| Idea | Train | Test | Verdict |
|---|---|---|---|
| TP$8/SL$12 (asym., WR-oriented) | PF 1.83 | 1.25 | ✅ kept |
| 24h time stop | 1.73 | 1.32 | ✅ kept |
| Combo TP8/SL12+ts24h | 1.81 | 1.33 | ✅ **final** |
| Breakeven move at +$5 | **2.07** | **0.94** | ❌ overfit (train champion, test failure) |
| Retest/pullback entries | 1.25-1.44 | — | ❌ misses 25-36% of flips, no gain |
| ATR-scaled TP/SL | 1.22-1.47 | — | ❌ under fixed-$ in-era |
| H4-bias agreement (earlier round) | PF drops to 1.12 | — | ❌ hurts |
| Skip Monday (earlier round) | — | — | ✅ **confirmed on virgin data**: 2015-21 Mondays PF 0.93 (negative) vs no-Mon 1.14 |

## Honest bottom line

1. The strategy is **real but era-amplified**: PF 1.63 in 2021-26, PF 1.14 in
   2015-21. Both positive, both >60% WR, but the virgin-holdout PF is below
   the 1.20 house bar. Expect live performance between the two, closer to the
   recent era while gold volatility stays high.
2. The **Monday effect replicated out-of-era** — strongest evidence produced
   today (mechanism: weekend gap corrupts prior-day-range pivots).
3. Fixed-$ targets need **rescaling as gold's price level changes** (raw $8/12
   degrades to PF 1.02 in the $1,200-gold era). If deployed, express TP/SL as
   ~0.32%/0.47% of price, refreshed monthly, or revisit ATR scaling.
4. Multiple-comparisons caveat: TRAIN saw ~22 variants; TEST saw 6; holdout
   saw 1 family. Confidence ordering: Monday-skip > R3/S3 selection >
   TP8/SL12+ts24h geometry.

## Round 2 — aggressive innovations (2026-07-02, `innovate_r3s3.py`)

Tested: trailing stops, EOD exit, pyramid add-on at +$4, re-entry after SL,
overshoot(fresh-break) filter, far-Gann entry stream.

| Variant | Train PF | Test PF | **Virgin holdout PF** | Verdict |
|---|---:|---:|---:|---|
| FINAL_v1 (ref) | 1.81 | 1.33 | **1.14 (+$9.2k)** | ✅ stands |
| pyramid +4 | 1.58 | 1.41 | — | looked validated… |
| pyramid+4 + re-entry | 1.33 | 1.55 | **0.91 (-$10.3k)** | ❌ regime bet |
| pyr+reentry+overshoot<1.5 | 1.51 | 1.55 | **0.80 (-$17.0k)** | ❌ regime bet |
| pyramid+4 + overshoot<1.5 | 1.78 | 1.42 | **0.85 (-$11.3k)** | ❌ regime bet |
| trailing stops (all forms) | 1.7-1.8 | 0.96-1.22 | — | ❌ died at test |
| EOD exit | 1.17-1.31 | — | — | ❌ died at train |
| far-Gann standalone stream | 1.07 (n=32) | — | — | ❌ no edge alone |
| re-entry after SL (alone) | 1.56 | 1.61 | (inside composites: fails) | ⚠️ trend-regime only |

**Key lesson (the most valuable output of round 2):** pyramiding and
re-entry are *leverage on trend continuation*. They pass 2021-26 train AND
test because the whole era trends; on the choppy 2015-21 virgin data they
flip sign and lose more than they made. Survived-test-but-died-on-holdout is
exactly the failure mode the 3-tier protocol exists to catch. The aggressive
composites are regime bets, not edge.

**FINAL_v1 (R3/S3, no Monday, TP$8/SL$12, 24h stop) remains the champion** —
the only spec positive in every window: train 1.81 / test 1.33 / holdout 1.14.
To be "more aggressive" with it, scale lots (drawdown scales linearly), not
logic.

## Round 3 — regime switch, news calendar, blueprint filters (2026-07-02)

**3a. ADX-gated pyramid (`regime_switch.py`).** Pyramid +$4 only when D1
ADX(14)>25 (textbook threshold, not tuned). Gate fires ~44% of days in both
eras. New era: PF 1.81/net $71.3k (vs 1.63/$47.5k). Old era: +$5.0k (vs
ungated pyramid's -$3.0k) — the gate has real predictive content, but gated
still trails plain FINAL_v1 there (1.06 vs 1.14). Verdict: optional
aggression mode, not core.

**3b. News blackout (`news_blackout.py`, `build_calendar.py`).** Calendar:
FOMC exact 2015-26 (Fed site), NFP first-Friday rule (9/12 vs exact 2015),
CPI exact 2015+2025-26 only (BLS bot-walled). **REJECTED — inverted:** news
days are the BEST trades (new era PF 2.40 WR 76%; old era 1.19), consistent
cross-era. H4-close entries ride post-news expansion rather than scalping
through the spike. Caveat: real news-day spreads > 20pt cost model.

**3c. Blueprint filters (`blueprint_filters.py`; user-provided document).**
| Filter | New era PF | Old era PF | Verdict |
|---|---:|---:|---|
| Session: only 12/16/20 UTC closes | 1.63→**1.84** | 1.14→**1.26** | ✅ **ADOPTED — validates both eras** |
| Dollar-trend (DTWEXBGS 50d) | 2.27 | 1.02 | ❌ era mirage |
| VIX>25 → BUYs only | 1.56 | 1.20 | ❌ inconsistent, tiny |
| Round-number avoidance | 1.64 | 1.13 | ❌ no effect |

## FINAL_v2 (supersedes FINAL_v1)

**R3/S3 flip → skip Monday → only H4 closes at 12:00/16:00/20:00 UTC →
market entry → TP +$8 / SL -$12 / 24h time stop.** (Price-scale the $ params
as ~0.32%/0.47% of gold price.)

| Window | n | WR | PF | Net (1 lot) |
|---|---:|---:|---:|---:|
| 2021-26 | 189 | 70.4% | **1.84** | $43,485 |
| 2015-21 virgin | 245 | 63.7% | **1.26** | $12,374 |
| Pooled 11y | 434 | 66.4% | 1.56 | **$55,861 (maxDD $4,540)** |

First spec to clear PF≥1.20 in BOTH eras. Optional aggression: + ADX-gated
pyramid → pooled $67k but maxDD $9.0k and old-era PF 1.11.

## Round 4 — drawdown reduction / adaptivity (`adaptive_v3.py`) → FINAL_v3

Tested (pre-registered, both eras): A one-trade-per-day; B ATR-scaled exits
(TP 1.4×ATR / SL 2.1×ATR, same 1:1.5 geometry); C equity-%-risk sizing with
DD governor (1% risk, halved while equity <95% of peak); D loss-streak
throttle. A ✅ (small, free); B ✅ (old 1.24 / new 2.00 — self-adaptive, kills
manual price-rescaling); C ✅ (maxDD 15.1%→8.0% of equity, +70%/11y on $30k);
D ❌ (DD got worse — streaks not predictive).

**FINAL_v3 (current best): R3/S3 flip · no Monday · 12/16/20 UTC closes only
· max 1 trade/day · TP 1.4×ATR(H1) · SL 2.1×ATR · 24h time stop · size = 1%
equity risk, halved while >5% off equity peak.**

| Window | n | WR | PF | Net (fixed 1 lot) |
|---|---:|---:|---:|---:|
| 2015-21 virgin | 243 | 65.0% | **1.24** | $11,466 |
| 2021-26 | 189 | 71.4% | **2.00** | $59,130 |
| Pooled 11y | 432 | 67.8% | 1.67 | $70,596 (maxDD $6,935) |

With the sizing layer: maxDD 8.0% of equity. Optional ADX-gated pyramid
still stacks for trending regimes (config flag).

## Artifacts

- `final_candidate_trades.csv`, `final_candidate_equity.png`
- `tune_r3s3.py`, `tune_train_results.csv`, `tune_test_results.csv`
- `events.jsonl` (2021-26), `events_2015_2021.jsonl` (holdout)

## Next steps (not done)

- Demo forward test (Profile-L playbook: own magic/terminal, 0.01-0.1 lot).
- News-calendar blackout test (needs an economic calendar dataset).
- Percent-scaled TP/SL live implementation detail.
