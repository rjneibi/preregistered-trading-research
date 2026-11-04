# PREREGISTRATION — goldbot verdict protocol (H1 rerun + H2 regime filter)

**Freeze protocol (do this first, before building the cost matrix or viewing any
filtered result):** fill in the Trials Ledger below, then
`git add PREREGISTRATION.md && git commit -m "preregister: H1 pins + H2 regime filter"`.
Record the commit hash in `results/DECISIONS.log`. After this commit, no number in
this file may change. Any deviation = a new trial, logged in the ledger, with gates
re-deflated. This document exists because the moment to fix thresholds is *now*,
while the per-era cost rerun is still unknown.

Honesty note: the specific numbers below (1.20, 10/15, 0.50, 252, 0.15, 40, ...)
are pinned **by fiat, a priori** — that arbitrariness is the point of
pre-registration. They were chosen before any filtered or per-era-cost result was
seen by either Rashed or the assisting models.

---

## H1 — original hypothesis, rerun under decision-grade costs

*The conviction dual-arm H1+H4 breakout (`final` variant, flip_bot v1.1 rules,
UTC-00:00 pivot day-cut, news blackout OFF per prior research) has positive net
edge on XAUUSD across the full 2015–2026 history.*

**Cost basis for the rerun (pinned):** per-year × UTC-hour spread matrix built by
`cost_matrix.py` from Dukascopy ticks; slippage = `k_slip = 0.5 ×` bucket spread
per side (ASSUMPTION — ticks measure spread, not slippage; k is unmeasurable until
live and 0.5 is a modeling choice, flagged as such); commission per current broker
schedule (verify the actual figure — [BROKER]).

**H1 PASS requires ALL of:**
1. Full-period PF ≥ 1.20 at matrix costs.
2. ≥ 10 of 15 purged combinatorial splits with positive net expectancy.
3. Each era (2015–21, 2021–26) PF ≥ 1.00 — no era catastrophically negative.
4. Total trades ≥ 300 (currently 472 → satisfied unless the rerun changes the set).

Anything less = H1 FAIL. (The original registration said "clear majority of
splits" without a number; 10/15 is pinned now, before results — sharpening an
ambiguous pre-registration before seeing outcomes is legitimate; loosening one
after would not be.)

## H2 — volatility-regime filter (trial #2, mechanistic contingency)

*Mechanism claim: a breakout strategy requires volatility/trend to pay for its
stops; the 2015–19 compressed-range regime starves it. If true, an ex-ante
volatility gate should rescue the old era's filtered-in trades — not merely
date-fence them off.*

**Filter definition (pinned):**
- Indicator: relative ATR = ATR(14) / close, computed on **daily bars cut at
  UTC-00:00** (matching the strategy's pivot day-cut — the percentile depends on
  this convention, so it is registered here).
- Score: percentile rank of the **last completed day's** relative ATR against the
  trailing **252 strictly prior completed days** (fraction strictly below). A
  signal during day D uses day D−1's percentile — a day's ATR is unknowable
  intraday, so this is the no-lookahead form.
- Trade only if percentile ≥ **0.50** (primary threshold).
- **Design property (understand before committing):** a trailing percentile
  re-normalizes inside any homogeneous-vol era, passing ≈50% of days there. The
  filter therefore selects *relative expansion*, not absolute vol level — it
  CANNOT act as a date fence that excises 2015–19 wholesale; it will roughly
  halve the old era and bet the surviving half is better. That is exactly what
  the mechanism control tests, which is why the control is a real experiment and
  not a formality. A further consequence: ATR percentile is heavily
  autocorrelated, so filtered-in trades arrive in multi-week clusters — lumpier
  split counts (the 11/15 gate absorbs this) and bunched exposure, which is an
  additional reason H2's Phase-2 sizing is halved.
- **Warm-start (pinned):** compute the daily relATR/percentile series on the full
  tick-era history from 2010 onward, so the 252-day window is already warm when
  the 2015 strategy window opens; events remain 2015+ only.
- Plateau robustness (counts as 2 additional trials): thresholds 0.40 and 0.60
  must each yield PF ≥ 1.10 and within ±0.15 of the primary PF. A knife-edge
  result at 0.50 that dies at its neighbors is a FAIL.

**H2 PASS requires ALL of (bars deflated because this is trial ≥ #2):**
1. Filtered full-period PF ≥ **1.25** at matrix costs.
2. ≥ **11 of 15** purged splits on filtered events positive.
3. Worst-case-cost check: PF ≥ **1.10** using p90 bucket spreads.
4. **Mechanism control (the scientific heart):** old-era filtered-IN PF minus
   old-era filtered-OUT PF ≥ **0.15**, with filtered-in old-era n ≥ **40**.
   If n < 40 → verdict is "insufficient evidence", not pass. If filtered-in
   old-era trades are no better than filtered-out ones, the volatility story is
   false and the filter is just a date proxy → FAIL regardless of headline PF.
5. Filtered total trades ≥ **150** and plateau condition above.

If H1 passes outright, H2 is demoted to an optional enhancement study (no gate).

## Trials Ledger (Rashed: complete this honestly before committing)

| # | Trial | Outcome |
|---|-------|---------|
| 1 | R3/S3 fade → breakout evolution (ancestor `base`) | superseded |
| 2 | Conviction dual-arm `final` (H1) | provisional fail at measured costs |
| 3 | News blackout on/off | off (rejected; see caveat: cost model must be hour-conditional for this to stand) |
| 4 | Skip-Monday variant | tested (ancestor) |
| 5–7 | H2 thresholds 0.40 / 0.50 / 0.60 | pending |
| 8 | All-zones immediate-entry flip; TP-only-no-SL variant | rejected (PF~1.05; net negative) |
| 9 | Zone hierarchy: R1 / R2+S2 / fib retracements / far-Gann / PP | rejected (noise / anti-signal / n too small); R3-S3 only accepted |
| 10 | Fade vs breakout direction | breakout accepted, fade rejected |
| 11 | H4-bias agreement filter | rejected (hurts) |
| 12 | Retest/pullback limit entries | rejected (miss 25-36% of flips) |
| 13 | H1 granularity (FINAL_v4 arm) | adopted |
| 14 | Conviction dual-arm + solo-discard analysis (round 16) | adopted (core discovery) |
| 15 | Skip-Monday | adopted (replicated on virgin era) |
| 16 | Session 12/16/20 UTC → H1 12–20 UTC closes | adopted (both eras) |
| 17 | Dollar-trend (DTWEXBGS 50d) filter | rejected (era mirage) |
| 18 | VIX>25 buys-only filter | rejected |
| 19 | Round-number avoidance | rejected (no effect) |
| 20 | Overshoot/fresh-break filter | rejected (regime bet) |
| 21 | ML trade filtering (monthly_and_ml) | rejected (inverted OOS) |
| 22 | tune_r3s3 exit grid (~22 train variants: TP10/SL10, TP8/SL12, ATR-scaled, time stops, breakeven move +$5) | TP8/SL12+ts24h kept; breakeven move = train-champion/test-failure overfit |
| 23 | Trailing stops (all forms) | rejected (died at test) |
| 24 | EOD exit | rejected (died at train) |
| 25 | ATR exits 1.4/2.1 (FINAL_v3) and 0.8/2.4 (FINAL_v4) | adopted per arm |
| 26 | Bail grid: bail(4h,1.0) / bail(8h,1.0) / bail(4h,1.4) / half(1.2) / COMBO_regime (round 8) | COMBO_regime adopted (v5.1) |
| 27 | Pyramid +$4 always; re-entry after SL; composites | rejected (regime bets — passed train+test, failed virgin) |
| 28 | ADX>25-gated pyramid | optional module, not core |
| 29 | Scale-in (v6) | rejected (cuts wins as much as losses) |
| 30 | Loss-streak throttle | rejected (worsens DD) |
| 31 | Concentration caps | rejected |
| 32 | Equity-%-risk + DD governor sizing | adopted |
| 33 | Vol-regime bimodal sizing (ATR vs 90d median) | optional module |
| 34 | Portfolio v3×v5.1 + daily −1.5% breaker (rounds 12–13) | adopted for portfolio view |
| 35 | 2010–15 extra-virgin window probe | PF 1.08 ≈ flat (dormant, survives) |
| 36 | Round-17 as-coded backtest + tie-labeling fix | adopted (parity basis) |
| 37 | goldbot phase-1: gap_open vs barrier_level fill; flat/optimistic/realistic/worst regimes on thin matrix | trial #2's provisional fail (this document's reason to exist) |

| 38 | H-S scalp falsification: configs A/B × 3 geometries × 2 sessions (12 configs, HS_PREREGISTRATION.md) | pending |
| 39 | H-S permutation baseline machinery | n/a (control) |

| 40 | H-M meta-label filter (8 pinned features, pinned HGB, CPCV) — HM_PREREGISTRATION.md | pending |
| 41 | H-M shuffled-label control | n/a (control) |

(Rows 38-39 appended 2026-07-06 via the sanctioned new-trial mechanism —
"new ideas → new ledger row → deflated gates → new commit" — before any H-S
run; no frozen threshold touched. Predictions on record: Claude FAIL,
Rashed PASS.)

Ledger confirmed complete by Rashed 2026-07-06 against optimization_report.md,
STRATEGY_SPECIFICATION.md, MASTER_SUMMARY.md. Commission verified: **$7 per
1.0 lot round trip [BROKER]** (matches the 20pt legacy model: 13 spread + 7
commission). Tick-coverage deviation known at freeze time: 2019–2025 ticks
absent (download started at freeze); missing years fall back per the pinned
chain and the partial-coverage run is low-confidence for the new era until
the confirmation rerun on full coverage.

The true trial count is known only to Rashed and his repo history; it is almost
certainly larger than this table, and the gates above assume it is. For a formal
treatment of selection-bias deflation, see Bailey & López de Prado, "The Deflated
Sharpe Ratio" (Journal of Portfolio Management, 2014) — I believe this citation is
accurate; verify before quoting it in any paper.

## Decision tree (committed responses — no others permitted)

- **H1 PASS** → arm Phase 2 executor, unfiltered strategy. Demo ≥ 4–8 weeks; ops
  pass = measured demo spread/slippage consistent with matrix (update config to
  measured, re-run H1 once — a confirmation, not a new trial), zero guard/kill
  misfires, rollover flatten verified. Then Phase 3 at registered risk limits.
- **H1 FAIL, H2 PASS** → arm Phase 2 with the **filtered** strategy only, at
  **half** the registered `risk_per_trade_pct`, demo ≥ 8 weeks. Confidence is
  structurally lower on a contingency hypothesis; sizing reflects that.
- **BOTH FAIL** → STOP the goldbot-breakout line. Archive results. Salvage
  candidates each require a fresh pre-registration before any backtest is run:
  (a) intraday-only variant, (b) XAU/XAG OU pair leg (pending silver ticks),
  (c) meta-label filter study on whichever event set survives.
- **Anti-gate-shopping clause:** no threshold, window, variant, or cost-parameter
  edits after any result is viewed. "It almost passed" triggers nothing. New ideas
  → new ledger row → deflated gates → new commit.

## Known-unverified inputs carried into the rerun (do not silently upgrade)

k_slip = 0.5 (assumption); commission figure ([BROKER] — verify current schedule);
Dukascopy tick column format (verify against `bi5_downloader.py` output before
trusting the matrix); demo fills do not measure real news-time slippage — I
believe MT5 demo servers fill at quote without genuine liquidity, so demo
validates logic/ops, not fill quality; only small live size measures that.
