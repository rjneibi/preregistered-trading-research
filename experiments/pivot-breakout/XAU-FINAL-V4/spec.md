> Copied as found from `originals/gann_bot_500/fable-backtesting/STRATEGY_SPECIFICATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# STRATEGY SPECIFICATION — Dual-Timeframe Zone-Flip Gold System
_Canonical, fact-checked record. Supersedes any externally drafted report._
_All figures verified against harness outputs (2026-07-02/03). Eras:_
_**old/virgin = 2015-06-19→2021-06-18**, **new/tuning = 2021-06-19→2026-06-19**,_
_extra virgin window 2010-06→2015-06. Costs 20pts/trade unless stated; all $_
_figures per 1.00 lot XAUUSD ($100 per $1 move)._

## 1. Executive summary
A 17-round research program turned a breakeven idea ("enter when a zone
flips") into a validated dual-timeframe breakout system. The edge: an H1/H4
close beyond the **prior UTC-day's R3/S3 pivot extension** is a momentum
event — but only when **both timeframes confirm the same direction the same
day** ("conviction"). Solo signals are net losing in both eras. The live
implementation (flip_bot v1.1, demo, MAGIC 20260703) backtests at 71–75% WR,
10 of 11 years profitable, worst year -$1,105.

## 2. Signal definitions
- Pivots from previous **UTC day** H/L/C: PP=(H+L+C)/3; **R3=PP+(H−L)**;
  **S3=PP−(H−L)**. (R1/S1/R2/S2/fibs tested and rejected — see §4.)
- Flip/breakout: H1-UTC close > R3 → BUY; close < S3 → SELL. Closes at
  12/16/20 UTC are simultaneously the UTC-H4 candle close (same price) —
  they fire BOTH arms (tie conviction).
- Baseline dead-check: level already breached by any of the last 10 UTC-H4
  closes before today → no signal on it today.
- Filters: no Mondays; session closes 12:00–20:00 UTC only; max 1 trade per
  direction per day; single open position.
- DIRECTION IS BREAKOUT, NOT FADE — continuation validated, fading rejected.

## 3. Exits and sizing (v5.1 stack, all validated cross-era)
- TR_t = max(H−L, |H−C_prev|, |L−C_prev|); ATR = Wilder-smoothed TR(14) on
  H1: ATR_t = (13·ATR_{t−1} + TR_t)/14, seeded by 14-bar SMA.
- TP = entry ± **0.8×ATR**; hard SL = entry ∓ **2.4×ATR** (server-side).
- Loss compression: **hivol** (ATR > 90-day median of the H1-ATR series):
  close HALF at first close ≤ −1.2×ATR adverse. **lovol**: close ALL at
  market if ≤ −1.0×ATR adverse after 8h. Everything closes at 24h.
- Sizing: risk = 1% equity (0.5% while equity <95% of peak) × 0.5 if D1
  ADX(14) ≤ 22 × 1.5 on FOMC/NFP/CPI days × 0.5 in lovol regime.
- Daily breaker: realized day P&L ≤ −1.5% equity → no new entries today.
- Rejected (failed validation): breakeven moves (train 2.07→test 0.94),
  trailing stops, pyramiding-always, re-entry after SL, retest entries,
  scale-in (cuts wins as much as losses), loss-streak throttle,
  concentration caps, ML trade filtering (inverted OOS), news blackout
  (news days are the BEST trades: PF 2.40 new era, consistent old era).

## 4. Zone/filter evidence table (verified)
| Test | n | Result | Verdict |
|---|---:|---|---|
| R1 flips | 369 | PF 1.00 | noise — rejected |
| Fib-level flips | 74–155 | PF 0.63–0.79 | ANTI-signal — rejected |
| R3/S3 flips | 354 (H4) | PF ~1.2 base | ACCEPTED |
| Monday trades | 107 | PF 0.81, −$11.1k | excluded; replicated on virgin era |
| H4-bias agreement | 326 | PF 1.12 (opposed: 2.88, n=28) | rejected — hurts |
| Session 12/16/20 UTC | both eras | PF 1.63→1.84 / 1.14→1.26 | ACCEPTED |
| ADX>25 pyramid gate | both eras | ungated −$3.0k → gated +$5.0k (old) | optional module |

## 5. Conviction (round 16, no-hindsight) — the core discovery
Enter only on the LATER signal once the other arm fired same direction today.
| Window | n | WR | PF | Net |
|---|---:|---:|---:|---:|
| old era | 335 | 68.1% | **1.38** | $20,291 |
| new era | 271 | 73.8% | **1.93** | $62,980 |
| 2026 H1 | 20 | **85.0%** | **3.93** | $15,274 |
| SOLO discards (old) | 77 | 42.9% | **0.32** | **−$13,269** |
| SOLO discards (new) | 58 | 58.6% | 0.94 | −$1,304 |
Note: these $ counted BOTH arms' trades per event (≈2 risk units/event).

## 6. flip_bot v1.1 as-coded backtest (round 17, post tie-fix; 1 unit/event)
| Window | Trades | W/L | WR | PF | Net | maxDD |
|---|---:|---|---:|---:|---:|---:|
| old era | 267 | 190/77 | 71.2% | 1.27 | $8,499 | $3,391 |
| new era | 205 | 154/51 | 75.1% | 1.62 | $32,026 | $6,732 |
| 2025 | 42 | 33/9 | 78.6% | 2.25 | $13,563 | $3,041 |
| 2026 H1 | 18 | 14/4 | 77.8% | 1.32 | $5,700 | $6,732 |
Per-unit this reconciles with §5 (§5 ÷ 2 ≈ §6). Only losing year: 2016
(−$1,105). A pre-fix bug (12/16/20 closes labeled h4-only, missing tie
convictions) degraded old-era PF to 1.10 and made 2025 negative — caught by
backtesting the implementation, fixed in bot + harness.

## 7. Portfolio result (rounds 12–13)
v3(H4 arm) × v5.1(H1 arm) monthly correlation **0.37** → combined
**$97,943/11y** (+75% profit vs best solo, +40% DD). Daily breaker adds
+$5,320 and cuts 2026 DD 27% → **$103,705, 993 trades, 71% WR, maxDD
$6,407** (FINAL_portfolio_by_year.csv). 2010–15 extra-virgin window: PF
1.08, ≈flat — system goes dormant in dead regimes, survives without blowup.

## 8. Production architecture (flip_bot v1.1, live on demo)
- **UTC alignment layer**: boot-measured broker offset (measured **UTC+3**),
  all pivots/baselines/ADX built from H1 bars shifted to UTC; DST recheck
  daily. Pre-fix v1.0 built levels on wrong day boundaries.
- **Fill-mode autodetect**: broker measured **FOK-only** — hardcoded IOC
  would have failed retcode 10030 on the first order; retry-alternate on
  10030.
- Exact backtest ATR-regime math (full Wilder series vs 90d median).
- Journal (flip_bot_journal.csv) with per-trade **MAE**; Telegram notify
  (3s timeout, off critical path); 60pt spread guard; demo-only hard guard;
  run via run_bot_F.bat self-restart loop; state atomic-write heartbeat.
- --check mode prints offset/levels/regime/ADX/fill without trading
  (2026-07-03: R3 4213.63, S3 3986.93, ATR $20.1, lovol, ADX 43).

## 9. Open questions (the real roadmap)
1. **Real-cost GO/NO-GO** — 1-day Dukascopy sample: median spread $0.72 vs
   $0.20 assumed. Cost engine + regression-proven rerun harness ready; tick
   download self-starts when Dukascopy's rate-limit cooldown lifts. Bars:
   REALISTIC-regime PF ≥1.2 new era, ≥1.0 old era. Caveat: Dukascopy
   dynamics anchored to broker's observed 13pt baseline.
2. Meta-labeling (execution features, purged CV) — gated on (1).
3. "First flip after news release" sub-strategy (raw material PF 2.40).
4. Market expansion: XAUEUR/XAUGBP/XAUCHF/XAUAUD, XAGUSD (frozen spec, own
   cost matrix, no per-market tuning). FX/NASDAQ proven negative — never
   retest.
5. Forward test: judge at N≥20 trades by **winner-MAE** (structural edge if
   winners rarely exceed ~0.5× the ATR-scaled risk adverse), not raw WR
   (binomial noise at N=20). Run only via run_bot_F.bat.

## 10. Files
Harnesses: run_flip_scalp.py, tune_r3s3.py, innovate_r3s3.py,
regime_switch.py, news_blackout.py, blueprint_filters.py, adaptive_v3.py,
h1_flip_test.py, bimodal_v4.py, bail_exit_v5.py, forensics_v5.py,
conviction_clean.py, bot_spec_backtest.py. Data/results: events*.jsonl,
*_trades*.csv, grid_summary.json, FINAL_portfolio_by_year.csv. Infra:
flip_bot.py, run_bot_F.bat, news_calendar.py, bi5_downloader.py,
cost_engine.py, rerun_real_costs.py, DATA_PLAN.md, MASTER_SUMMARY.md.
