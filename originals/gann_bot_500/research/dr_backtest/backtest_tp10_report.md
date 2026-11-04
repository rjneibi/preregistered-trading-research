# D/R backtest — TP override to $10 (1000 pts) for BOTH profiles

_Generated 2026-07-01T10:57:54Z._
_Window: 2021-06-19 -> 2026-06-19 (5y, same as prior)._

## Mandatory caveats — read first

1. **Unthrottled != live P&L.** Every H1 close where all six gates pass is a distinct entry — no `_fired_zones` (1/zone/day for D, 2/zone/day for R), no `MAX_OPEN_TRADES`, no zone-reentry gates, no trade cooldown, no 3% daily-loss cap. Aggregate PF / expectancy / MDD read as entry-signal quality, not the equity curves D or R accounts would produce.
2. **5-year window is regime-specific.** 2021-06 → 2026-06 covers gold ~$1700→$4500. Not the full 16-year HistData history — pre-2021 gold ($1100-1700) makes a $10 TP a 2-3× more meaningful move, which would inflate WR. Do not read this as a full-history edge measurement.
3. **HistData is a broker-fill proxy.** Reconstructed exits approximate the live broker but are not identical to the tick the bot saw.
4. **Positively-correlated clustered entries → effective sample < raw n.** Unthrottled entries cluster tightly around a single H4 setup (bias + zone + confirmation persist across multiple H1 closes), so many of these 1000-plus 'independent' trades are actually the same underlying decision fired again and again. Treat PF confidence intervals as WIDER than a n>1000 IID sample would suggest. This is a first-order screen.
5. **Only TP is overridden.** D SL stays 1.0×ATR, R SL stays 1.5×ATR. Polarity flip stays ON for D / OFF for R. Partial-close @ 1.0×ATR stays ON for both. ADX=0, RSI off, spread gate skipped — exactly as in the prior report.

## R sanity gate (must-pass)

R's live config already uses TP_FIXED_POINTS=1000, so this run MUST reproduce the prior R backtest trade-for-trade. Result: **PASS** — identical trade-for-trade across n=1013.

## D @ 900 pts (prior) vs D @ 1000 pts (this run) — outcome counts

| Outcome | D@900 | D@1000 | Δ |
|---|---:|---:|---:|
| TP | 292 | 257 | -35 |
| SL | 514 | 520 | +6 |
| PARTIAL_THEN_TP | 299 | 291 | -8 |
| PARTIAL_THEN_BE | 246 | 283 | +37 |
| AMBIGUOUS_SAME_BAR | 1 | 1 | +0 |
| OPEN_AT_HORIZON | 1 | 1 | +0 |
| OUT_OF_HISTDATA | 0 | 0 | +0 |
| **Total** | **1353** | **1353** | +0 |

## D @ 900 vs D @ 1000 — aggregate stats

| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **ALL: D@900** | 1351 | 0.620 | 1.326 | 97.1 | 637.3 | -782.5 | 18030.3 |
| **ALL: D@1000** | 1351 | 0.615 | 1.312 | 96.9 | 662.6 | -807.1 | 18217.6 |
| **ALL: Δ** | +0 | -0.005 | -0.014 | -0.2 | +25.3 | -24.6 | +187.3 |
| **IS 70%: D@900** | 946 | 0.589 | 1.409 | 88.4 | 517.2 | -525.6 | 8446.7 |
| **IS 70%: D@1000** | 946 | 0.589 | 1.406 | 87.8 | 516.2 | -525.6 | 8431.5 |
| **IS 70%: Δ** | +0 | +0.000 | -0.003 | -0.6 | -1.0 | +0.0 | -15.2 |
| **OOS 30%: D@900** | 405 | 0.691 | 1.241 | 117.5 | 876.2 | -1582.0 | 18030.3 |
| **OOS 30%: D@1000** | 405 | 0.677 | 1.222 | 118.2 | 960.2 | -1643.0 | 18217.6 |
| **OOS 30%: Δ** | +0 | -0.014 | -0.019 | +0.7 | +84.0 | -61.0 | +187.3 |

### D validation flags

- **D@900:** (no flags)
- **D@1000:** (no flags)

## R @ 1000 pts (unchanged from live config; must match prior)

| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **R@1000: ALL** | 1012 | 0.640 | 1.060 | 24.8 | 682.2 | -1145.5 | 24266.4 |
| **R@1000: IS 70%** | 708 | 0.607 | 1.078 | 23.6 | 539.6 | -774.6 | 15842.6 |
| **R@1000: OOS 30%** | 304 | 0.717 | 1.042 | 27.6 | 963.4 | -2344.5 | 24266.4 |

Validation flags: IS: PF 1.078 < 1.20 — no edge threshold; OOS: PF 1.042 < 1.20 — no edge threshold

## Profits & losses overview

Point-P&L across all eligible trades in each bucket. Positive = winner.

| Bucket | n | Total pts | Sum wins | Sum losses | Best trade | Worst trade | Median | Std |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D@900 | 1351 | +131194.5 | +533389.9 | -402195.4 | +900.0 | -7145.1 | +235.9 | 842.7 |
| D@1000 | 1351 | +130934.5 | +550601.0 | -419666.5 | +1000.0 | -10220.7 | +223.0 | 911.9 |
| R@1000 | 1012 | +25084.4 | +442058.1 | -416973.7 | +1000.0 | -6065.9 | +260.5 | 1053.1 |

### Outcome mix (share of eligible trades)

| Bucket | TP full | SL full | Partial→TP | Partial→BE | Winners share |
|---|---:|---:|---:|---:|---:|
| D@900 | 292 (22%) | 514 (38%) | 299 (22%) | 246 (18%) | 62.0% |
| D@1000 | 257 (19%) | 520 (38%) | 291 (22%) | 283 (21%) | 61.5% |
| R@1000 | 207 (20%) | 364 (36%) | 241 (24%) | 200 (20%) | 64.0% |

## How to read this

- The TP change moves the take-profit further from entry (900 → 1000 pts = 10% wider TP). Expected qualitative effects on D: (a) some full-TP hits convert to PARTIAL_THEN_BE (the leg doesn't reach further TP after partial); (b) some full-TP hits become full SL (the extra distance gives more time to reverse); (c) trades that DO hit the wider TP capture 100 pts more per full-lot TP hit, +50 pts per partial→TP. Net direction depends on which channel dominates.
- **Δ PF and Δ expectancy** in the D table above are the only stats to trust here — win% shifts driven by TP-hit reclassification are structural, not edge.
- **R must show zero deltas vs the prior run.** If it does, the harness is consistent; if not, that's a bug and the whole comparison is suspect.

## Artifacts

- `trades_D_tp10.jsonl` / `trades_R_tp10.jsonl` — per-trade records at TP=1000.
- `trades_D.jsonl` / `trades_R.jsonl` — prior-run (D@900) for the D comparison.
- Harness unchanged: `backtest.py`, `data_prep.py`, `exit_sim.py`, `metrics.py`, `polarity_pure.py`.
