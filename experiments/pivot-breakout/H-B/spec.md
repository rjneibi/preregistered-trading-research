> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HB_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HB_PREREGISTRATION — arm B (FINAL_v3 H4) solo at measured costs

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; only the
already-disclosed H-P byproduct numbers had been seen).

**Taint disclosure (why the gates are stiffened):** arm B's headline at
partial-coverage matrix costs was OBSERVED post-hoc inside the H-P run
before this prereg existed: full PF 1.459, old era 1.012, n=432. This is
post-hoc selection — the same move that produced round 10's inversion —
so (a) the observed pooled numbers cannot carry the verdict; the gates
lean on UNSEEN dimensions (purged-split stability, p90 stress, era
knife-edge), and (b) the bars sit above H1's.

**Hypothesis:** *the published FINAL_v3 H4 arm (zero parameters tuned here)
has standalone edge at measured costs, robust across purged splits and
cost stress.*

**Registered predictions:**
- Claude (Fable 5): PASS (lean) on the preliminary; binding run on the
  full-coverage matrix is the real risk — 2019–25 costs rise from the
  fallback level and the old-era 1.2% margin is a knife edge.
- Rashed: FAIL tonight (split stability / p90 stress kill it).
  (Recorded 2026-07-06 pre-commit.)

## Pinned spec (published, FINAL_v3, optimization_report.md round 4)
H4-close breakout of prior-UTC-day R3/S3 · skip Monday · closes at
12/16/20 UTC only · max 1 trade/day · TP 1.4×ATR(H1) / SL 2.1×ATR / 24h
time stop · no bail · gap_open fills · dead-level check as the harness ·
exactly the hp_runner.py arm-B implementation, unchanged.

## Two pinned runs (both committed now)
1. **Preliminary (tonight, partial-coverage matrix):** decisive ONLY if
   FAIL (partial coverage biases costs optimistic — a FAIL survives the
   bias a fortiori). A PASS is provisional and confers nothing.
2. **Binding (auto-fired after the confirmation watcher completes the
   full-coverage matrix rebuild):** same code, same gates, decisive both
   ways. No re-run beyond these two.

## Gates — ALL required (per run)
1. Full-period PF ≥ 1.35 at matrix costs.
2. Each era PF ≥ 1.00.
3. ≥ 11/15 purged CPCV splits (H1 protocol) with positive expectancy.
4. p90 stress: full PF ≥ 1.15 AND old-era p90 PF ≥ 0.90.
5. n ≥ 300.

## Decision tree (committed)
- Binding PASS → arm B becomes a SECOND-MAGIC demo forward-test candidate
  alongside the conviction arm (the round-11 A/B plan), at registered risk,
  demo-only; explicitly NOT a portfolio claim (H-P's correlation verdict
  stands — this is a parallel trial, not diversification).
- Binding FAIL (or preliminary FAIL) → arm B solo closed; no variant
  shopping; the conviction arm remains the only line.

## Ledger delta: | 47 | H-B arm-B solo at matrix costs (post-hoc taint disclosed) | pending |
