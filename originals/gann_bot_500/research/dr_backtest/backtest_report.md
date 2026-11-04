# Historical D/R backtest — entry-signal edge + veto screen

_Generated 2026-07-01T10:33:19Z._
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
| **D** | 1353 | 1351 | 292 | 514 | 299 | 246 | 1 | 1 |
| **R** | 1013 | 1012 | 207 | 364 | 241 | 200 | 1 | 0 |

### Aggregate stats per profile (IS 70% / OOS 30%, chronological)

| Profile | Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **D** | ALL | 1351 | 0.62 | 1.326 | 97.1 | 637.3 | -782.5 | 18030.3 |
| **D** | IS | 946 | 0.589 | 1.409 | 88.4 | 517.2 | -525.6 | 8446.7 |
| **D** | OOS | 405 | 0.691 | 1.241 | 117.5 | 876.2 | -1582 | 18030.3 |
| **R** | ALL | 1012 | 0.64 | 1.06 | 24.8 | 682.2 | -1145.5 | 24266.4 |
| **R** | IS | 708 | 0.607 | 1.078 | 23.6 | 539.6 | -774.6 | 15842.6 |
| **R** | OOS | 304 | 0.717 | 1.042 | 27.6 | 963.4 | -2344.5 | 24266.4 |

### Validation flags

**Profile D:**
- (no flags)

**Profile R:**
- IS: PF 1.078 < 1.20 — no edge threshold
- OOS: PF 1.042 < 1.20 — no edge threshold

## Veto screen against backtest population

Headline K (pre-registered): **1.0**. Others reported for sensitivity; do NOT pick K by best result.

### Profile D

- eligible trades: **1351**; trades with an opposing unswept level found: **1254** (no opposing pool: 97 — treated as KEPT for every K)

| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | Vetoed MDD | Kept n | Kept win% | Kept avg (pts) | Kept PF | Kept MDD | % vetoed | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.5 | 10 | 0.5 | 191.3 | 1.908 | 1445.2 | 1341 | 0.62 | 96.4 | 1.323 | 19682 | 1% | NO CONCLUSION (n<15) |
| 1 | 77 | 0.545 | 14.4 | 1.043 | 5731.7 | 1274 | 0.624 | 102.1 | 1.346 | 16291.2 | 6% | **HEADLINE** directional only (n<100) |
| 1.5 | 215 | 0.563 | 31.7 | 1.101 | 10429.3 | 1136 | 0.63 | 109.5 | 1.372 | 14627.4 | 16% |  |
| 2 | 428 | 0.582 | 71.2 | 1.242 | 16794.7 | 923 | 0.637 | 109.1 | 1.365 | 22467 | 32% |  |

### Profile R

- eligible trades: **1012**; trades with an opposing unswept level found: **875** (no opposing pool: 137 — treated as KEPT for every K)

| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | Vetoed MDD | Kept n | Kept win% | Kept avg (pts) | Kept PF | Kept MDD | % vetoed | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.5 | 15 | 0.467 | -188.4 | 0.632 | 5826.4 | 997 | 0.643 | 28 | 1.068 | 24411.1 | 1% | directional only (n<100) |
| 1 | 125 | 0.648 | 70.6 | 1.189 | 9728.8 | 887 | 0.639 | 18.3 | 1.044 | 31026.6 | 12% | **HEADLINE** |
| 1.5 | 321 | 0.642 | 5.1 | 1.012 | 16778 | 691 | 0.64 | 33.9 | 1.084 | 18442.4 | 32% |  |
| 2 | 492 | 0.642 | 23.7 | 1.056 | 21135.1 | 520 | 0.638 | 25.8 | 1.064 | 19346.2 | 49% |  |

## How to read this

- **Entry-edge tables:** the aggregate stats are unthrottled — read as signal-quality ratios, not live equity. If the ALL-window PF is < 1.20, the ENTRY SIGNAL itself doesn't have edge under the current config. If IS PF > 1.20 but OOS < 1.00, the strategy is regime-dependent (REJECT).
- **Veto screen:** the veto has value iff VETOED shows negative avg / PF < 1 AND kills a workable fraction (roughly <60%). Positive avg or PF > 1 in the VETOED bucket means the rule throws away winners; do not promote.
- **NO CONCLUSION rows** are dominated by noise — reported for honesty, not for action.
- D and R are NOT pooled — their entry gates differ (D uses polarity, R does not), so their trade populations aren't comparable in aggregate.

## Bottom-line findings

**Entry-signal edge (this closes the 'no historical backtest on current D/R configs' gap):**
- **Profile D has real edge under the current config.** n=1351, PF 1.326, expectancy 97.1 pts/entry. IS PF 1.409 → OOS PF 1.241 — both clear the 1.20 threshold and OOS win-rate (0.691) is higher than IS (0.589), suggesting the polarity + partial-close model is not regime-fragile within this window.
- **Profile R entry edge is thin under the current config.** n=1012, PF 1.06, expectancy 24.8 pts/entry. IS PF 1.078 and OOS PF 1.042 both fail the 1.20 threshold. WR is fine (0.64), but partial-BE + shallow avg-win makes the expectancy small. Note this is UNTHROTTLED entry-signal edge — live R's zone-reentry gates + 3% daily loss cap could still produce a workable live result by filtering the marginal population.

**Veto screen at headline K=1.0:**
- **D (K=1.0):** vetoes 77 / 1351 = 6% of trades. VETOED PF 1.043 (avg 14.4 pts) vs KEPT PF 1.346 (avg 102.1 pts). The veto DOES remove marginal trades (KEPT PF slightly better than baseline PF 1.326), but the effect is small — 6% of trades filtered, PF up from 1.326 to 1.346. Vetoed sample size (n=77) is still under the n<100 'directional only' threshold — treat as a plausible tilt, not a proven edge. **Not compelling enough to promote given D's already-solid baseline.**
- **R (K=1.0):** vetoes 125 / 1012 = 12% of trades. VETOED PF 1.189 (avg 70.6 pts) vs KEPT PF 1.044 (avg 18.3 pts). VETOED is BETTER than KEPT — the rule would throw away R's best trades. n=125 (above 100) so this signal is directional-plus. **Do NOT deploy the veto to R.**

**Combined recommendation:** the veto rule as specified (opposing unswept liquidity within K×ATR) is not a promotion candidate for either profile at K=1.0. D's edge is in the entry gates already; R's shortfall is elsewhere (partial-BE payoff geometry). Investigate R's exit model separately before touching entries.

## Artifacts

- `trades_D.jsonl`, `trades_R.jsonl` — per-trade record with gate context, exit outcome, and veto info.
- `polarity_pure.py` — the one mirrored function (guard against drift on any structure.py edit).
- `backtest.py`, `data_prep.py`, `exit_sim.py`, `metrics.py`, `veto_screen.py`, `run.py` — the harness.
