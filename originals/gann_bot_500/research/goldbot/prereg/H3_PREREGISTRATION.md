# H3_PREREGISTRATION — XAU/XAG OU spread (frozen BEFORE silver data exists locally)

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; frozen while
ZERO silver bars exist on local disk — quarantine violation impossible). Freezing now is the
whole point: the XAGUSD download completes tomorrow; committing thresholds
before a single silver bar is on disk makes quarantine violation impossible.
External context: recent work confirms long-run GC–SI cointegration with
regime filtering (SSRN 5710242, 2025), but the ratio's April-2025 blowout
past 100 (a once-in-modern-history extreme) is exactly the months-long
wander that kills tradeable half-lives at retail cost and leverage.

**Hypothesis:** *log(XAU) − β·log(XAG) is a valid OU process with a
tradeable half-life, and a ±2σ reversion strategy clears two-leg measured
costs out of sample.*

**Registered predictions:**
- Claude (Fable 5): FAIL — the OU validity gates (stationarity t-gate or
  half-life band) reject the spread, or the carry test fails: half-life in
  weeks × two-leg costs + swap-free admin fees out-earn the reversion at
  retail scale.
- Rashed: FAIL. (Recorded 2026-07-06 pre-commit — unanimous with Claude.)

## Pinned protocol (the ENTIRE search space)
- Data: XAGUSD ticks → M1 (bi5 pipeline, same integrity gates), aligned with
  the existing XAUUSD M1; H1 bars; analysis window = common coverage.
- Spread: z_t = log(XAU) − β·log(XAG); β re-estimated monthly by OLS on a
  trailing 90-day window (causal; no full-sample β).
- Validity gates (from goldbot/ou_estimator.py, unchanged): fit valid=True
  (0<φ₁<1, σ-recovery, stationarity t ≥ 3) on the IS segment AND
  **half-life ∈ [4h, 10 days]** — shorter is microstructure, longer is
  untradeable carry.
- Strategy (single pinned config, no grid): enter when |z-score| ≥ 2.0
  (z from trailing 90d OU σ_stationary), exit at z = 0, hard stop |z| ≥ 4,
  time stop 10 days. One position at a time, 1 lot gold leg, β lots silver.
- Costs: gold leg = per-year matrix; silver leg = its own tick-built matrix
  (same builder); $7/lot RT each leg; Islamic admin fee [ESTIMATE] × nights
  held on BOTH legs (multi-day holds are the norm here — the fee bites).
- Split: IS = first 70%, OOS = last 30%.

## Gates — ALL required
1. OU validity gates pass on IS (else STOP — no trading conclusion).
2. OOS PF ≥ 1.20 after full two-leg costs.
3. OOS n ≥ 30; IS and OOS not inverted.
4. Carry test (run_spread_research.py): expected reversion capture ≥ 2× the
   all-in round-trip cost including admin fees for the fitted half-life.

## Decision tree (committed)
- FAIL at validity gates → H3 closed cleanly ("the spread is not OU at
  tradeable horizons" is a real answer, cheaply obtained).
- FAIL at cost/OOS gates → H3 closed; no threshold shopping.
- PASS → paper/demo two-leg forward test design becomes the next prereg
  (execution risk on two legs is its own problem — never skipped).

## Ledger delta: | 46 | H3 XAU/XAG OU spread (single pinned config) | pending |
