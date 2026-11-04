# FABLE BACKTESTING — Zone-Flip Strategy Research Program
_Session of 2026-07-02. Seven optimization rounds, one day. This folder is
the complete, self-contained record._

## THE FINAL STRATEGIES (deployment-ready specs)

### FINAL_v4 — high-win-rate arm (answers "max WR, minimal losses")
- **Entry:** first H1 close beyond an unflipped R3 or S3 daily pivot
  (zones built at UTC 00:00 exactly like live bot.py; flip rule =
  structure.check_zone_polarity). Session window: H1 closes 12:00–20:00 UTC
  only. Skip Mondays. Max 1 trade/day. BUY on break above R3-as-resistance,
  SELL on break below S3-as-support.
- **Exit:** TP = 0.8×ATR(H1,14 at day build) · SL = 2.4×ATR · close at
  market after 24h.
- **Results:** 2025: 51 trades, **86.3% WR, 7 losses, PF 2.90, +$21,768**/lot.
  2021-26: 79.4% WR, PF 1.40, $30,448. **2015-21 validation: 78.6% WR,
  PF 1.21 ✅, $9,427.**

### FINAL_v3 — conservative arm (best risk-adjusted, demo A/B partner)
- **Entry:** H4-close flips of R3/S3, same filters (no Mon, 12/16/20 UTC
  closes, 1/day).
- **Exit:** TP 1.4×ATR · SL 2.1×ATR · 24h time stop.
- **Sizing:** 1% equity risk/trade, halved while equity >5% below peak.
- **Results:** 2021-26 PF 2.00 ($59,130); 2015-21 PF 1.24 ($11,466);
  pooled 11y PF 1.67, $70,596, maxDD $6,935 fixed-lot / **8.0% of equity**
  with sizing. 2025: $13,260, PF 1.86.

### Optional modules (config flags)
- **ADX pyramid:** add +0.4×ATR-ish unit (orig +$4) when D1 ADX(14)>25.
  New era PF 2.00→ net +38%; old era slight drag but positive. Trending
  regimes only.
- **Vol-regime sizing (bimodal):** full size when ATR>90d median, half
  otherwise — edge concentrates in high-vol in BOTH eras (old-era low-vol
  PF ≈ 1.0-1.16 across all geometries).

## VERIFIED MARKET FACTS (the reusable knowledge)
1. **Raw zone flips have no edge** — enter-on-any-flip is PF~1.05 (spread
   food). TP-only-no-SL hits $10 92% of the time yet loses money
   (avg loss -$131 vs avg win +$9.79). High WR ≠ edge.
2. **Zone hierarchy:** R3/S3 (prior-day full-range extension) = only real
   signal (PF 1.2+). R1 = pure noise (369 flips, PF 1.00). fib_618/786,
   S45 = ANTI-signal (PF 0.63-0.79 — flips through fibs fade).
   Far-Gann (R90+) rare but strong (11/15, n too small).
3. **Monday flips lose** (weekend gap corrupts prior-day pivots) —
   replicated on virgin 2015-21 data. Strongest single finding.
4. **Asian-session entries are dead weight** — London/NY-only filter
   validated both eras (the one useful claim from the user's blueprint doc).
5. **News days (FOMC/NFP/CPI) are the BEST trades** (PF 2.40 new era,
   consistent old era) — H4/H1 closes ride post-news expansion. Do NOT
   blackout. (Caveat: real news spreads > the 20pt cost model.)
6. **Regime bets masquerade as edge:** pyramid-always, re-entry-after-SL,
   trailing stops, dollar-trend filter, H4-bias agreement — ALL passed
   2021-26 train+test and FAILED 2015-21. Only cross-era validation
   catches this.
7. **Breakeven-move = classic overfit** (train PF 2.07 → test 0.94).
   Loss-streak throttle worsens DD. Retest entries miss 25-36% of good
   flips. EOD exits, VIX filter, round-number filter: nothing.
8. **Frequency:** R2/S2 expansion = volume without profit (old era PF
   1.24→1.11). H1 granularity = the only frequency gain that adds net in
   both eras.
9. **Regime is destiny:** trending/high-vol eras (2021-26) → WR 69-86%;
   chop (2015-21) → WR 63-79%, thin PF. The system's job is to survive
   chop and feast on expansion.

## METHODOLOGY (why these results are trustworthy)
- Data: HistData M1 XAUUSD (research/data/xauusd_m1_histdata.csv,
  2010→2026-06-19), UTC, look-ahead-safe resampling (dr_backtest/data_prep).
- Forward-blind flips; conservative same-bar SL-wins; costs 20pts/trade;
  fixed-$ params price-scaled across eras (P0=2531).
- 3-tier protocol: TRAIN (70% of 2021-26) → TEST (30%) → VIRGIN HOLDOUT
  (2015-21, price-scaled). Round-7 caveat: eras consulted repeatedly;
  fresh evidence now requires the demo forward test.

## FILES
- `optimization_report.md` — full audit trail, rounds 1-4 detailed.
- Harnesses: `run_flip_scalp.py` (scanner+grid), `tune_r3s3.py` (3-tier
  tuning), `innovate_r3s3.py` (SimX: trailing/pyramid/re-entry/EOD),
  `regime_switch.py` (ADX gate), `news_blackout.py`+`build_calendar.py`,
  `blueprint_filters.py`, `adaptive_v3.py`, `h1_flip_test.py`,
  `bimodal_v4.py` (FINAL_v4).
- Events: `events.jsonl` (2021-26), `events_2015_2021.jsonl`.
- Trades/results: `final_v2_trades.csv`, `final_candidate_trades.csv`,
  `trades_pnl.csv`, `trades_2025.csv`, `r3s3_trades_1lot.csv`,
  `grid_summary.json`, `per_zone_accuracy.csv`, `tune_*_results.csv`.
- Charts: `final_v2_equity.png` (11y), `equity_2025.png`,
  `r3s3_equity_1lot.png`, `subset_equity.png`, `equity_curve.png`.
- `calendar/` — news_days.json (FOMC exact 2015-26, NFP first-Friday,
  CPI partial), FRED vix.csv + dollar.csv.
- `analysis_scripts/` — session one-off analyses (per-zone, why-losing,
  holdout, composites, final_v3, year_2025, expand_freq...).
- `per_zone_report.md`, `flip_scalp_report.md` — earlier round reports.

## NEXT STEP (the only one that adds information)
Demo forward test, Profile-L playbook: two magics on one demo account —
v3 (H4 conservative) vs v4 (H1 high-WR), vol-regime sizing on both.
6-8 weeks. Live spread/slippage on news days is the key unknown.

> CANONICAL SPEC: see STRATEGY_SPECIFICATION.md (fact-checked 2026-07-03; supersedes external drafts).
