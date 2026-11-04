# Historical D/R backtest — entry-signal edge + veto screen

_Generated 2026-10-31T07:23:45Z._
_Backtest window: 2021-06-19 -> 2026-06-19 (1826 days)._

## Mandatory caveats — read first

1. **Unthrottled != live system.** Every H1 close where all six gates pass is recorded as a distinct entry — no `_fired_zones` (1/zone/day), no `MAX_OPEN_TRADES`, no re-entry gating, no trade cooldown. Aggregate PF / DD / expectancy here are **entry-signal quality**, not live P&L the D and R accounts would have produced. Live throttling would collapse these entry clusters into far fewer trades — the ratios (win-rate, PF) are the interesting part, absolute equity growth is not.
2. **Gate logic — imported vs mirrored.** `signals.evaluate_signal`, `structure.find_swing / h1_close_confirmed / get_h4_bias`, and `levels.gann_levels / fibonacci_pivots / fib_retracements / build_zones` are imported and CALLED DIRECTLY from the live modules (single source of truth). The one mirrored function is `structure.check_zone_polarity` (live calls MT5 for the last 10 closed H4 candles); the replacement in `research/dr_backtest/polarity_pure.py` reads from the pre-loaded H4 DataFrame with identical semantics. **Drift risk on any structure.py edit — re-verify polarity_pure.py mirror.**
3. **HistData is a broker-fill proxy.** Reconstructed levels, ATR, and exit fills approximate the live broker but are not identical to the tick the bot saw. Coverage ends 2026-06-19 17:57 UTC. Historical prices are a single-vendor XAUUSD feed (HistData.com), not the live broker demo feed feed the bots use.
4. **Timezone alignment.** HistData `time` is Unix epoch UTC. All resampling and comparisons happen in UTC. NY-local session windows for the veto screen are computed by `tz_convert('America/New_York')` on the UTC-indexed M1 frame, DST-safe. The D1 boundary is UTC 00:00, matching bot.py's `_today_midnight_ts()`. No broker-server-time drift.
5. **Veto screen is first-order.** Assumes trade independence. Vetoing trade N would not have changed the state or P&L of trade N+1 in this analysis (no path dependence). Frame conclusions accordingly.
6. **Regime coherence.** Window is the last ~5 years (gold ~$1700-$4500). The fixed-point TPs (D=900pts=$9, R=1000pts=$10) are calibrated for the CURRENT $3000-$4500 regime; the early part of this window (2021-2023, gold ~$1700-2000) has a $9 move meaning a ~0.4-0.5% price move vs ~0.2-0.3% today. Expect entry-signal WR to drift lower over time from this mechanical scaling, independent of gate quality.
7. **Skipped vs live.** The Spread gate is skipped (HistData has no bid/ask; live spread is verified ~13 pts, well below the 40-pt cap). ADX is off in both configs (`ADX_THRESHOLD=0`). M5 RSI filter is off (`RSI_FILTER_ENABLED=False`). D's OPTION C M1-pullback entry is skipped — it's an entry-timing improvement, not one of the six gates, and R doesn't have it. All 4 skipped items are consistent with what live actually does.
8. **R's partial-close model.** `config_R.py:PARTIAL_CLOSE_ENABLED=True` — so R also runs the 50%-out-at-1×ATR-then-BE model, not a flat lot as the task brief assumed. Confirmed in config; backtest applies the partial-close model to BOTH profiles.

## Entry-signal edge (unthrottled)

| Profile | Total signals | Eligible | TP | SL | PARTIAL_THEN_TP | PARTIAL_THEN_BE | Ambiguous | Open@horizon |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **D** | 1308 | 1307 | 286 | 476 | 295 | 250 | 1 | 0 |
| **R** | 1026 | 1025 | 198 | 365 | 242 | 220 | 1 | 0 |

### Aggregate stats per profile (IS 70% / OOS 30%, chronological)

| Profile | Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **D** | ALL | 1307 | 0.636 | 1.505 | 135.4 | 634.3 | -735.6 | 16928.6 |
| **D** | IS | 915 | 0.597 | 1.472 | 97 | 507.1 | -509.9 | 7795.8 |
| **D** | OOS | 392 | 0.727 | 1.545 | 225.1 | 878 | -1513.8 | 16928.6 |
| **R** | ALL | 1025 | 0.644 | 1.014 | 5.7 | 662 | -1181.1 | 34318.2 |
| **R** | IS | 718 | 0.62 | 1.088 | 25.7 | 515 | -771.9 | 18227.2 |
| **R** | OOS | 307 | 0.7 | 0.943 | -41 | 966.4 | -2395.5 | 34318.2 |

### Validation flags

**Profile D:**
- (no flags)

**Profile R:**
- IS: PF 1.088 < 1.20 — no edge threshold
- OOS: PF 0.943 < 1.20 — no edge threshold
- OOS: DD 34% > 25% budget

## Veto screen against backtest population

Headline K (pre-registered): **1.0**. Others reported for sensitivity; do NOT pick K by best result.

### Profile D

- eligible trades: **1307**; trades with an opposing unswept level found: **1205** (no opposing pool: 102 — treated as KEPT for every K)

| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | Vetoed MDD | Kept n | Kept win% | Kept avg (pts) | Kept PF | Kept MDD | % vetoed | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.5 | 6 | 0.333 | -36.7 | 0.869 | 1032.4 | 1301 | 0.637 | 136.2 | 1.509 | 16928.6 | 0% | NO CONCLUSION (n<15) |
| 1 | 77 | 0.61 | 118.8 | 1.444 | 4000.9 | 1230 | 0.637 | 136.4 | 1.509 | 16202 | 6% | **HEADLINE** directional only (n<100) |
| 1.5 | 204 | 0.608 | 112 | 1.418 | 5058.1 | 1103 | 0.641 | 139.7 | 1.522 | 16406.1 | 16% |  |
| 2 | 405 | 0.598 | 103.7 | 1.376 | 8936.6 | 902 | 0.653 | 149.7 | 1.566 | 13481.4 | 31% |  |

### Profile R

- eligible trades: **1025**; trades with an opposing unswept level found: **869** (no opposing pool: 156 — treated as KEPT for every K)

| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | Vetoed MDD | Kept n | Kept win% | Kept avg (pts) | Kept PF | Kept MDD | % vetoed | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.5 | 13 | 0.385 | -275.4 | 0.463 | 4580.4 | 1012 | 0.647 | 9.3 | 1.022 | 35318.2 | 1% | NO CONCLUSION (n<15) |
| 1 | 117 | 0.624 | 40.6 | 1.11 | 12275.7 | 908 | 0.646 | 1.2 | 1.003 | 44218.4 | 11% | **HEADLINE** |
| 1.5 | 289 | 0.661 | 41.4 | 1.105 | 10533.7 | 736 | 0.637 | -8.3 | 0.981 | 30117.4 | 28% |  |
| 2 | 461 | 0.659 | 44.6 | 1.112 | 19148.1 | 564 | 0.631 | -26.1 | 0.94 | 33596.6 | 45% |  |

## How to read this

- **Entry-edge tables:** the aggregate stats are unthrottled — read as signal-quality ratios, not live equity. If the ALL-window PF is < 1.20, the ENTRY SIGNAL itself doesn't have edge under the current config. If IS PF > 1.20 but OOS < 1.00, the strategy is regime-dependent (REJECT).
- **Veto screen:** the veto has value iff VETOED shows negative avg / PF < 1 AND kills a workable fraction (roughly <60%). Positive avg or PF > 1 in the VETOED bucket means the rule throws away winners; do not promote.
- **NO CONCLUSION rows** are dominated by noise — reported for honesty, not for action.
- D and R are NOT pooled — their entry gates differ (D uses polarity, R does not), so their trade populations aren't comparable in aggregate.

## Bottom-line findings

**Entry-signal edge (this closes the 'no historical backtest on current D/R configs' gap):**
- **Profile D has real edge under the current config.** n=1307, PF 1.505, expectancy 135.4 pts/entry. IS PF 1.472 → OOS PF 1.545 — both clear the 1.20 threshold and OOS win-rate (0.727) is higher than IS (0.597), suggesting the polarity + partial-close model is not regime-fragile within this window.
- **Profile R entry edge is thin under the current config.** n=1025, PF 1.014, expectancy 5.7 pts/entry. IS PF 1.088 and OOS PF 0.943 both fail the 1.20 threshold. WR is fine (0.644), but partial-BE + shallow avg-win makes the expectancy small. Note this is UNTHROTTLED entry-signal edge — live R's zone-reentry gates + 3% daily loss cap could still produce a workable live result by filtering the marginal population.

**Veto screen at headline K=1.0:**
- **D (K=1.0):** vetoes 77 / 1307 = 6% of trades. VETOED PF 1.444 (avg 118.8 pts) vs KEPT PF 1.509 (avg 136.4 pts). The veto DOES remove marginal trades (KEPT PF slightly better than baseline PF 1.505), but the effect is small — 6% of trades filtered, PF up from 1.505 to 1.509. Vetoed sample size (n=77) is still under the n<100 'directional only' threshold — treat as a plausible tilt, not a proven edge. **Not compelling enough to promote given D's already-solid baseline.**
- **R (K=1.0):** vetoes 117 / 1025 = 11% of trades. VETOED PF 1.11 (avg 40.6 pts) vs KEPT PF 1.003 (avg 1.2 pts). VETOED is BETTER than KEPT — the rule would throw away R's best trades. n=117 (above 100) so this signal is directional-plus. **Do NOT deploy the veto to R.**

**Combined recommendation:** the veto rule as specified (opposing unswept liquidity within K×ATR) is not a promotion candidate for either profile at K=1.0. D's edge is in the entry gates already; R's shortfall is elsewhere (partial-BE payoff geometry). Investigate R's exit model separately before touching entries.

## Artifacts

- `trades_D.jsonl`, `trades_R.jsonl` — per-trade record with gate context, exit outcome, and veto info.
- `polarity_pure.py` — the one mirrored function (guard against drift on any structure.py edit).
- `backtest.py`, `data_prep.py`, `exit_sim.py`, `metrics.py`, `veto_screen.py`, `run.py` — the harness.
