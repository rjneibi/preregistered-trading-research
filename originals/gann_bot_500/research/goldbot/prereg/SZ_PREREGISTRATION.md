# SZ_PREREGISTRATION — sizing policy (the HR cycle's headline finding)

**STATUS: FROZEN 2026-07-06** (blind protocol followed: Rashed's prediction
collected before Claude's was revealed; no policy outcome computed). Per the pre-committed
design constraints (DECISIONS.log 2026-07-06 protocol amendment + review):
ONE primary mechanism hypothesis, secondaries under a multiple-testing
correction, metric pinned before any policy outcome is computed,
era-stratified evaluation so the favorable-OOS problem is not inherited.

**The finding under repair:** constant-dollar-risk ATR sizing (lots ∝ 1/ATR)
flips the conviction system from 1-lot PF 1.051 to sized PF 0.985 (IS) —
the edge's returns are concentrated in high-ATR trades and 1%-flat sizing
structurally shorts them.

## Primary hypothesis (mechanism, chosen a priori)
**Regime-allocation artifact:** the R-unit edge is regime-dependent (hivol >
lovol — the round-9 cross-era finding already deployed in the live bot's
sizing tilt), so a constant risk fraction misallocates. The repair is the
PUBLISHED v5.1 tilt applied to the sizing module:
- **P (primary): risk_fraction = 1.0% when hivol, 0.5% when lovol** —
  zero new parameters; both numbers are the live bot's published spec.

## Secondaries (distinct mechanism claims, deflated)
- **S1 (tail artifact):** divisor ATR capped — effective_atr = min(atr, CAP)
  with **CAP = 3.9344** (IS trade-ATR p75, calibrated 2026-07-06 on the
  pre-cutoff subset only, recorded here).
- **S2 (superlinearity/timing artifact):** partial equalization — lots ∝
  1/sqrt(ATR): stop input = 2.4 × sqrt(atr × A0) with **A0 = 2.8789**
  (IS trade-ATR median, same calibration discipline).
- Correction: a secondary may displace the primary ONLY if it clears every
  gate AND beats the primary's sized PF by ≥ +0.03 in BOTH eras.

## Metric + evaluation design (pinned before any policy outcome computed)
- Basis: chronological equity walk over the FULL 2015–2026 conviction trade
  set (472 trades, matrix costs), $10k start, floor-only sizing, 0-lot=skip.
- No policy parameter is fitted (all constants above are pinned), so the
  full window is admissible as the test set; evaluation is **era-stratified**
  (old 2015–21 / new 2021–26 separately) — the design that avoids judging a
  defensive policy only on a favorable window.
- Pinned metrics per era: sized PF, and **risk-adjusted ratio = sized net /
  sized maxDD** compared to the same ratio for the baseline policy.
- Contamination disclosure: per-trade 1-lot nets have been seen in aggregate
  across H1/H-N/H-P/H-B analyses; NO sized-policy outcome has ever been
  computed. Clean w.r.t. the policies; degraded w.r.t. the base stream.

## Gates — primary policy P PASSES only if ALL hold in BOTH eras
1. sized PF(P) ≥ sized PF(baseline 1%-flat) + 0.05.
2. sized PF(P) ≥ 1-lot PF(same era) − 0.02  (inversion eliminated).
3. (sized net / sized maxDD)(P) ≥ (sized net / sized maxDD)(baseline)
   (risk-adjusted never worse).

## Decision tree (committed)
- P PASSES → the live bot's sizing tilt is re-validated at measured costs on
  the module implementation; the position_size wiring adopts the tilt in any
  future Phase-2 configuration. No secondary is examined further unless it
  displaces P under the correction rule.
- P FAILS → sizing line closed for this cycle; the inversion stands as a
  known cost of vol-normalized sizing; NO ad-hoc third mechanisms.

## Registered predictions (BLIND protocol: Rashed's collected first, with
confidence, before Claude's is revealed)
- Rashed: PASS (confidence: HIGH) — collected blind, first.
- Claude (Fable 5): PASS (confidence: MEDIUM) — revealed after; the tilt is
  the one candidate with prior cross-era validation; the old-era +0.05 gate
  is the risk. First blind agreement of the program.

## Ledger delta (at freeze): | 49 | SZ sizing policy (P + S1 + S2, corrected) | pending |
