> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HV_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HV_PREREGISTRATION — regime-of-validity: the absolute-volatility gate

**STATUS: FROZEN 2026-07-07** (blind protocol; Rashed collected first).
Mechanism-first per the standing disclosure: the question is WHAT ex-ante
condition separates the profitable regime from the flat one — not what
threshold maximizes PF. Literature basis: research/era_mechanism/
ERA_MECHANISM_RESEARCH.md (Xu et al. 2020: gold intraday predictability
significant only when realized vol is HIGH; SZ post-mortem: the era artifact
is ABSOLUTE vol level; H2's percentile design could not see level shifts, so
its failure does not test this hypothesis).

**Hypothesis (primary):** *the conviction edge exists when gold's ABSOLUTE
volatility level is high — specifically, trades taken when relative ATR
(day-build H1 ATR / price) is above a parameter-free reference are
profitable at measured costs, and trades below it are not, WITHIN eras as
well as across them.*

## Pinned indicators (the ENTIRE space — one primary, one secondary)
- **V (primary, price-only):** ATR% = day-build ATR / entry price. Gate ON
  when ATR% > FULL-SAMPLE MEDIAN of the daily ATR% series computed over the
  entire M1 history (2010-2026). The median is a parameter-free convention
  (Xu et al. use median splits), computed once, disclosed in the results —
  NOT tuned, NOT searched. No other threshold may be evaluated.
- **Y (secondary, macro):** rolling 90-day correlation of daily gold returns
  vs Δ(10y TIPS real yield) from FRED DFII10, lagged one day; gate ON when
  corr > -0.30 (the "decoupled" state; -0.30 is pinned a priori as the
  midpoint between the published regime means ~-0.75 and ~+0.03).
  Displacement rule: Y replaces V only if it clears every gate AND beats
  V's gate-1 PF by ≥ +0.05 in both eras.

## Gates — ALL required for the primary
1. Gate-ON trades: full-period PF ≥ 1.30 at matrix costs, n ≥ 150.
2. Gate-OFF trades: full-period PF ≤ 1.05 (separation — the edge must be
   ABSENT when the indicator says off).
3. **Within-era mechanism control (the H2 lesson, the heart of the test):**
   ON-minus-OFF PF gap ≥ +0.20 inside the NEW era alone, AND ON ≥ OFF
   inside the OLD era alone. A gate that only separates eras is a date
   fence and FAILS regardless of headline numbers.
4. p90 stress: gate-ON PF ≥ 1.15.

## Decision tree (committed)
- PASS → the regime-of-validity condition is identified; it becomes (a) a
  standing risk disclosure resolver, (b) a candidate live kill-switch for
  the demo bot (trade only when ON) under a follow-up ops prereg, and (c)
  the inherited context for every future overlay test.
- FAIL → the era boundary remains unexplained; the live-deployment risk
  disclosure stands unresolved and hardens (an edge whose regime cannot be
  identified ex ante); no threshold shopping, no third indicator.

## Registered predictions (BLIND: Rashed first, confidence attached)
- Rashed: FAIL (confidence: LOW) — collected blind, first.
- Claude (Fable 5): FAIL (confidence: MEDIUM) — revealed after. Expected
  failure path: gate 3's within-era controls on thin samples, because the
  absolute-vol gate is nearly collinear with the era boundary — if the
  mechanism is confounded with the era, the control should (correctly)
  refuse to certify it. Blind agreement #2, both FAIL.

## Ledger delta (at freeze): | 50 | HV absolute-vol regime gate (V primary, Y secondary) | pending |
