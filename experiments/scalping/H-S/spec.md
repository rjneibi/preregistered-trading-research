> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HS_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HS_PREREGISTRATION — the scalping falsification test (hypothesis H-S)

**Freeze protocol:** same as before. Fill the ledger delta, then
`git add HS_PREREGISTRATION.md && git commit -m "preregister: H-S scalp falsification"`
BEFORE running anything below. Append hash to results/DECISIONS.log.

**Hypothesis under test:** *some configuration in the pinned family below extracts
positive net edge from XAUUSD at scalp scale (fixed small $ targets, minutes-scale
holds, many trades) after measured costs.*

**Registered predictions (falsifiable, on record before any run):**
- Claude (Fable 5): FAIL — required win rates at measured costs sit above anything
  a taker-side retail scalper can sustain; frequency multiplies (edge − cost)
  including its sign.
- Rashed: PASS — at least one of the 12 configs clears the bar-level gates.
  (Recorded 2026-07-06, pre-commit, before any exhibit or result was computed.)

**Asymmetric evidence design (the point of this test):** the barrier engine
resolves any bar where both barriers are touched as a LOSS, and at scalp-sized
targets that is the common case — so the bar-level harness is deliberately
PESSIMISTIC for scalping. Therefore: bar-level FAIL = decisive, scalping line
closed with evidence. Bar-level PASS = weak by construction; it does NOT validate
the strategy, it only unlocks the tick-level re-simulation stage (2015–18 tick
archive, same frozen thresholds). Only a tick-level pass reaches the standard
demo/live gates. No outcome leads directly to capital.

## Pinned configuration family (12 configs — the ENTIRE search space; all count)

Signals (computed on closed M1 bars, entry next bar open):
- A: z-score fade — z of close vs rolling(60) mean/std; short z > +2, long z < −2.
- B: momentum burst — long on close > max(high of prior 20), short mirror.

TP/SL geometry ($/oz, fixed): (0.50, 0.50) · (1.00, 1.00) · (1.50, 0.75).
Sessions: {all hours} · {12:00–20:00 UTC closes only}.
Horizon cap: 30 M1 bars. Event de-dup: min gap 5 bars.
2 signals × 3 geometries × 2 sessions = 12. Nothing outside this set may be run.

## Cost basis (pinned)
Per-year × UTC-hour matrix (median stat), k_slip = 0.5, $7/lot RT commission —
identical to the H1 basis. p90 stress column alongside. The frontier exhibit
(descriptive, no gate): required win rate w* = (SL + c) / (TP + SL) per config at
matrix costs, plus the measured |move|-per-horizon vs cost table from the real M1
data — cost as a fraction of the move available at each holding horizon.

## Gates — H-S bar-level PASS requires, for at least one config, ALL of:
1. OOS PF ≥ 1.30 at matrix costs under the same purged split protocol as H1
   (config selection on the training folds only; the SAME config evaluated OOS).
2. Each era (2015–21 / 2021–26) OOS PF ≥ 1.10.
3. p90-cost OOS PF ≥ 1.10.
4. n(OOS trades) ≥ 500 for that config.
5. Permutation reality check: the winning config's OOS PF must exceed the 95th
   percentile of the best-of-12 PF distribution over ≥ 200 replicates of
   time-randomized entries with matched trade counts, sides, and geometry —
   i.e., it must beat selection luck, not just zero. (Self-contained permutation
   design; conceptually in the spirit of data-snooping reality checks — I believe
   the canonical reference is White, "A Reality Check for Data Snooping,"
   Econometrica 2000, but verify that citation before quoting it formally.)

## Decision tree (committed)
- Bar-level FAIL → scalping/HFT line CLOSED with evidence. DECISIONS.log gets the
  frontier table so the reason is numeric, not rhetorical. Proceed to H3 (XAU/XAG
  OU) as previously committed.
- Bar-level PASS → no celebration, no sizing: unlocks tick-level re-simulation on
  the 2015–18 archive (and 2019+ when the download lands) with these same
  thresholds. Tick-level FAIL → closed. Tick-level PASS → standard demo/live
  gates apply, with slippage-k measurement as the first live job.
- Anti-gate-shopping: no configs, geometries, sessions, or thresholds added or
  edited after any result is seen. "Config 13" = new prereg, further deflated.

## Quarantine reminder
The XAGUSD download remains untouched by this test. Nothing here constructs the
XAU/XAG spread. H3's headline result stays unseen until H3 is frozen.

## Ledger delta (append to the master Trials Ledger before committing)
| # | Trial | Outcome |
|---|-------|---------|
| +1..12 | H-S configs A/B × 3 geometries × 2 sessions | pending |
| +13 | H-S permutation baseline machinery | n/a (control) |

## Known-unverified inputs (carried, unchanged)
k_slip = 0.5 assumption; commission $7/lot RT ([BROKER] confirmed by Rashed);
2019–2025 tick gap → matrix fallbacks understate that span's costs (biases the
new era optimistic — i.e., toward PASS, so a FAIL survives this bias a fortiori);
bar-level fill pessimism documented above (biases toward FAIL — which is why only
FAIL is decisive at this stage and PASS escalates to ticks).
