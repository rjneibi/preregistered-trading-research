# HM_PREREGISTRATION — ML meta-label filter on the conviction event set (H-M)

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; no real-data
number seen at freeze time). Design rationale: HM_DESIGN.md. This is salvage
candidate (c) from the frozen decision tree (commit 35deedc) and the SECOND
attempt at ML trade filtering (round 10 failed, OOS-inverted) — gates deflated
accordingly.

**Hypothesis under test:** *a small, pinned-capacity classifier on 8 pinned
regime-stable features, trained under purged CPCV with calibration and
train-fold-only thresholding, can drop enough losing conviction-dual-arm
trades to lift out-of-sample PF at measured costs by a pre-stated margin —
including making the old era non-negative.*

**Registered predictions (fill BEFORE committing):**
- Claude (Fable 5): MARGINAL-FAIL — expect positive but sub-gate uplift
  (pooled OOS filtered PF ~1.30–1.38 vs gate 1.40) and old era short of 1.05;
  n=472 is too thin for the filter to clear deflated bars, and round 10's
  inversion risk is only mitigated, not eliminated.
- Rashed: MARGINAL — real uplift appears but at least one gate falls short.
  (Recorded 2026-07-06, pre-commit.)

**Pre-declared trial-42 candidates (contingent, NOT part of this trial; run
only under a fresh further-deflated prereg and only if this trial lands
MARGINAL):** (a) sample-weighted classification (weights = |net_med|, AFML
return-attribution style); (b) retention-quantile threshold policy ("drop
bottom X% by probability") replacing the τ grid. Rejected as additions now to
avoid expanding the trial-40 search space. Rejected outright: volume/liquidity
features (no historical volume data exists in this repo); pullback-sweep
fallback (retest entries rejected in round 1).

## Pinned inputs (the ENTIRE search space)
- Event set: the 472 bot-spec conviction trades (verdict basis), extended with
  the `level` column; exits/costs exactly as the H1 verdict run
  (gap_open, matrix median + p90 stress).
- Features: the 8 in HM_DESIGN.md §3, verbatim. No additions, no interactions
  engineered by hand.
- Label: net_med > 0.
- Model/calibration/threshold policy/split protocol: HM_DESIGN.md §4, verbatim
  (pinned params; τ grid {0.45..0.70 step .05}; train retention ≥ 40%;
  CPCV(6,2) purge 24h margin 40h).
- Controls: shuffled-label run (seeded) alongside the real run.

## Gates — H-M PASS requires ALL of
1. Pooled OOS filtered PF ≥ **1.40** at matrix costs.
2. Pooled OOS uplift vs unfiltered same-fold baseline ≥ **+0.15** PF.
3. Old-era pooled OOS filtered PF ≥ **1.05**.
4. Retention ≥ **40%** and kept OOS n ≥ **200**.
5. ≥ **11/15** splits with positive kept-fold expectancy.
6. p90-cost filtered OOS PF ≥ **1.15**.
7. Shuffled-label control fails gates 1–6 (harness sanity; a control that
   "passes" voids the run).

Suspicion clause: if permutation feature importance ranks `overshoot_atr`
first AND its partial effect flips sign between eras, the result is voided
regardless of gates (that is round 10's failure signature).

## Decision tree (committed at freeze)
- **PASS** → shadow mode on the live demo bot ≥ 8 weeks: compute p and
  keep/drop at signal time, LOG ONLY, no trade altered. Shadow gate: live
  keep-fraction within ±15pp of backtest and no calibration inversion
  (kept-trade WR ≥ dropped-trade WR on ≥ 20 logged events). Then enforcing
  mode on demo at unchanged risk settings.
- **FAIL** → ML-filter line closed a second time. No third attempt until the
  forward journal holds ≥ 950 events (≈2× current sample), and that attempt
  trains on forward data only.
- Anti-gate-shopping: no feature, parameter, threshold, or gate edits after
  any real-data number is seen. A "config 9th feature" = new prereg, further
  deflated.

## Ledger delta (append to master Trials Ledger at freeze)
| # | Trial | Outcome |
|---|-------|---------|
| 40 | H-M meta-label filter (8 pinned features, pinned HGB, CPCV) | pending |
| 41 | H-M shuffled-label control | n/a (control) |

## Known-unverified inputs (carried)
k_slip = 0.5; $7/lot RT [BROKER]; 2019–2025 tick gap (matrix fallback
understates that span's costs — biases the filtered result optimistic, so a
FAIL survives the bias a fortiori); n=472 sample-size risk documented in
HM_DESIGN.md §6; sklearn added to the research venv (research-only, no live
dependency change).
