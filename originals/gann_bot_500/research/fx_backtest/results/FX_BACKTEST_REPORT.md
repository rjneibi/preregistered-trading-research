# FX Transfer Test — Profiles D, R, S on EURUSD / GBPUSD / AUDUSD

Backtest-only study. No live trading, Telegram, or config.py change was made. The live Profiles D/R/S and the running fleet are untouched.

## Methodology

- **Data**: broker demo feed, verified bare symbol names `EURUSD`/`GBPUSD`/`AUDUSD` (no broker suffix). 7-year window 2019-06 → 2026-06, fetched via `copy_rates_range`. All three share identical contract specs: digits 5, point 1e-5, tick_value $1.0, tick_size 1e-5, contract 100 000 → point value **$1 / point / lot**.
- **Walk-forward**: 70/30 chronological in-sample/out-of-sample split (same methodology as the gold D/R validation). Locked, already-validated parameters — **no per-pair re-optimisation** of any gate. All ATR-relative params (SL/TP/BE/trail/confluence/ADX/swing) identical across pairs.
- **D/R engine**: reuses the live six-gate logic in `research/backtest.py` **unchanged**. FX OHLC scaled ×10 000 so FX's 1e-5 point maps onto the engine's gold-calibrated 0.01 (2-decimal) tick granularity — otherwise the live `levels.py` rounding collapses every FX level and forces ATR to 0. All performance metrics (R, win%, PF, expectancy, MaxDD) are scale-invariant.
- **S engine**: reuses `backtest_s.py` **unchanged** (raw-float math, no 2dp rounding) — runs natively at 1e-5. Adds a currency-aware news blackout on top of the engine's weekend-gap control.
- **Costs (realistic, after-cost expectancy)**: per-symbol spread + $7/lot round-trip commission, charged once per trade. S additionally charges nightly swap (dynamic, from `symbol_info`).

### Step 2 — symbol-aware sizing & spread (per-symbol config)

`risk.calculate_lot_size()` was audited: it already reads `trade_tick_value`, `trade_tick_size`, `point`, and `volume_min/max/step` from `symbol_info()` per symbol — fully symbol-agnostic, **no gold hardcoding, no change needed**. The only instrument-specific knob in scope is the spread filter. `MAX_SPREAD_POINTS=40` is gold-tuned (~10× a typical FX spread → effectively disabled on FX), so per-symbol values are derived from 7y of recorded bar spreads:

| Symbol | 7y H1 spread (median / mean / p90, pts) | Backtest spread cost (pts) | Proposed live `MAX_SPREAD_POINTS` |
|---|---|---|---|
| EURUSD | 2 / 3.4 / 8 | 8 (+7 commission) | 15 |
| GBPUSD | 3 / 5.9 / 18 | 12 (+7 commission) | 30 |
| AUDUSD | 4 / 5.5 / 16 | 11 (+7 commission) | 25 |

Backtest spread cost ≈ 2× the recorded mean (a conservative retail markup over this tight demo feed); proposed live threshold ≈ p90 + buffer so it blocks only genuine news-spike spreads. These are **proposals documented here only** — no live config.py change was applied (task guardrail).

## Master comparison table (9 runs + gold baseline)

Metrics are **FULL period** unless the column says OOS. PF and expectancy are in R, net of spread + commission. MaxDD% is on a 1%-fixed-fractional equity curve (same basis for all profiles). ‘Pol-flip win%’ = win rate of trades where the polarity gate flipped vs didn’t (D); for S the polarity/break-retest gate is mandatory so it equals the overall win rate.

| Profile | Pair | Trades (full / OOS) | Win% (full / OOS) | PF (full / OOS) | MaxDD% (full / OOS) | Exp R (full / OOS) | Pol-flip win% (flip / no-flip) | Long/Short | Meets gold PF≥1.20? |
|---|---|---|---|---|---|---|---|---|---|---|
| D | EURUSD | 710 / 203 | 22% / 20% | 0.72 / 0.63 | 85% / 52% | -0.243 / -0.331 | 129/578=22% / 26/132=20% | 394/316 | ❌ |
| D | GBPUSD | 673 / 195 | 23% / 24% | 0.80 / 0.81 | 72% / 32% | -0.171 / -0.160 | 129/550=23% / 29/123=24% | 416/257 | ❌ |
| D | AUDUSD | 765 / 233 | 23% / 22% | 0.73 / 0.68 | 87% / 57% | -0.239 / -0.291 | 141/617=23% / 33/148=22% | 446/319 | ❌ |
| R | EURUSD | 1140 / 372 | 38% / 41% | 0.90 / 1.03 | 69% / 21% | -0.065 / +0.019 | — / 434/1139=38% | 467/673 | ❌ |
| R | GBPUSD | 1220 / 386 | 37% / 37% | 0.88 / 0.84 | 69% / 50% | -0.078 / -0.110 | — / 456/1220=37% | 520/700 | ❌ |
| R | AUDUSD | 1150 / 327 | 37% / 35% | 0.84 / 0.76 | 75% / 50% | -0.109 / -0.169 | — / 429/1150=37% | 477/673 | ❌ |
| S | EURUSD | 24 / 5 | 29% / 0% | 0.41 / 0.00 | 5% / 2% | -0.358 / -1.071 | 29% (all 24) / — | 17/7 | ❌ |
| S | GBPUSD | 41 / 16 | 27% / 31% | 0.54 / 0.15 | 7% / 4% | -0.206 / -0.480 | 27% (all 41) / — | 30/11 | ❌ |
| S | AUDUSD | 31 / 12 | 42% / 42% | 0.40 / 0.53 | 3% / 2% | -0.255 / -0.184 | 42% (all 31) / — | 17/14 | ❌ |
| **D (gold ref)** | **XAUUSD** | — / 162 | — | **1.20** (OOS) | ≤25% | **+0.146** | n/a | — | baseline (walk-forward validated) |

## Directional / USD-correlation bias

EUR, GBP and AUD all trade **against USD**, so a directional tilt that is *consistent across pairs within a profile* is concentrated USD exposure, not diversification — even when each pair's PF looks independent.

| Profile | EURUSD L/S | GBPUSD L/S | AUDUSD L/S | Cross-pair tilt |
|---|---|---|---|---|
| D | 394/316 (55% L) | 416/257 (62% L) | 446/319 (58% L) | **long-biased (~59% L) — correlated USD-short** |
| R | 467/673 (41% L) | 520/700 (43% L) | 477/673 (41% L) | **short-biased (~42% L) — correlated USD-long** |
| S | 17/7 (71% L) | 30/11 (73% L) | 17/14 (55% L) | **long-biased (~66% L) — correlated USD-short** |

## Step 5 — Profile S go/no-go benchmarks on FX

Gold benchmarks: PF ≥ 1.20, **≥100 OOS trades**, MaxDD ≤ 25%, polarity-gate win rate > 56%.

**Observed S trade counts over 7y (full / OOS):** EURUSD 24/5, GBPUSD 41/16, AUDUSD 31/12.

**Proposal.** The ≥100-OOS-trade bar cannot transfer: Profile S is a low-frequency Daily/H4 swing system, and across a *full 7-year* FX window each pair produced only ~24–41 trades total and **5–16 OOS** — versus gold's recent high-volatility regime that generated 100+ OOS trades in ~1.5y. I therefore propose, applied consistently to all three pairs:

1. **Minimum sample for any verdict: ≥30 OOS trades.** Below this, PF/win-rate are statistically meaningless and the verdict is **INCONCLUSIVE (NO-GO by insufficient data)** regardless of the point estimate. *(All three FX pairs fail this floor — 5/16/12 OOS.)*
2. PF ≥ 1.20, MaxDD ≤ 25%, polarity-gate win > 56% **retained unchanged** — they are scale-free quality bars — but only *evaluated* once the sample floor is met.

Under this rule every FX pair is **NO-GO for Profile S on data-sufficiency grounds alone**; the sub-1.0 full-period PFs (0.41 / 0.54 / 0.40) reinforce it. The news blackout (NFP + RBA windows) blocked 0 entries — with only ~30 setups in 7y, the chance of one landing in a monthly 3-hour window is negligible; ECB/BoE/FOMC decision days are not fixed-date and are not reproducible without a historical calendar feed (unavailable via the MT5 Python API).

## Verdict vs the gold PF 1.20 baseline

- **Profile D**: fails on every FX pair — full-period PF 0.72 / 0.80 / 0.73, negative expectancy (−0.24 / −0.17 / −0.24 R), OOS PF 0.63 / 0.81 / 0.68. Does **not** transfer.
- **Profile R**: best of the three but still sub-baseline — full PF 0.90 / 0.88 / 0.84. Only **EURUSD OOS** crosses break-even (PF 1.03, +0.019 R over 372 trades), and only marginally; well under PF 1.20. Does **not** meet the gold bar.
- **Profile S**: insufficient OOS sample on every pair (NO-GO by data floor) and sub-1.0 full-period PF.

**No pair/logic combination meets or exceeds the gold PF 1.20 benchmark.** The gold-validated edge is volatility-regime-specific and does not transfer to EUR/GBP/AUD on the existing, un-retuned logic. A notable structural reason: FX's ATR-to-price ratio (~0.1%) is far below gold's (~0.7%), so the Gann Square-of-9 confluence levels (spaced ~1–2% of price) fall outside the 10×ATR zone-relevance window and contribute essentially nothing — FX zone construction rests on Fib pivots + retracements alone.

## Artifacts

Per-run trade logs (daily_log format + full per-trade reasoning) and JSON summaries are in `research/fx_backtest/results/`: `trades_{D,R,S}_{EURUSD,GBPUSD,AUDUSD}.csv`, `summary_*.json`.

