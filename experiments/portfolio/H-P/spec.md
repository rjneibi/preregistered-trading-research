> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HP_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HP_PREREGISTRATION — validated portfolio (v3 H4 arm × v5.1 conviction) at measured costs

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; no result seen). This is the most direct
PF/net upgrade available without new tuning: rounds 12–13 already validated the
two-arm portfolio (+$103,705/11y at flat costs, monthly correlation 0.37,
daily −$1,500 breaker adds money AND cuts DD). It has never been priced at
measured matrix costs. No parameter is tuned here — both arms are frozen
published specs; this trial only re-prices them.

**Hypothesis:** *the v3(H4) × v5.1(H1-conviction) portfolio with the daily
breaker retains its edge at per-year matrix costs, including the old era.*

**Registered predictions:**
- Claude (Fable 5): PASS (lean) — v3's larger ATR targets (1.4×ATR) make its
  cost fraction smaller than v5.1's, and diversification + breaker should lift
  the old era above the solo arm's 0.95. Confidence moderate, not high.
- Rashed: FAIL. (Recorded 2026-07-06 pre-commit. First head-to-head
  disagreement with Claude's PASS-lean today.)

## Pinned specs (both published, zero degrees of freedom)
- Arm A (v5.1 conviction): the exact H1-verdict engine — conviction dual-arm,
  TP 0.8×ATR / SL 2.4×ATR / 24h, regime bail, gap_open fills.
- Arm B (FINAL_v3, optimization_report.md round 4): H4-close breakout of live
  R3/S3, skip Monday, closes at 12/16/20 UTC only, max 1 trade/day,
  TP 1.4×ATR / SL 2.1×ATR / 24h time stop, no bail, gap_open fills.
- Portfolio: both arms at 1.00 lot, independent positions; daily breaker =
  no NEW entries (either arm) once combined realized day P&L ≤ −$1,500.
- Costs: per-year matrix median (+ p90 stress column), $7/lot RT, exactly the
  H1-verdict wiring. Eras and data as the H1 verdict.

## Gates — ALL required
1. Portfolio full-period PF ≥ 1.20 at matrix costs.
2. Each era PF ≥ 1.00.
3. Portfolio net > best single arm's net (the combination must ADD, not dilute).
4. Monthly-return correlation between arms ≤ 0.60 (diversification rationale intact).
5. p90-stress portfolio PF ≥ 1.05.

## Decision tree (committed)
- PASS → the portfolio becomes the Phase-2 demo configuration candidate
  (second magic for the H4 arm), still gated by the overnight H1 confirmation
  rerun's cost picture and normal demo-ops gates. No live sizing from this.
- FAIL → conviction solo remains the only line; portfolio idea closed at
  measured costs.

## Ledger delta: | 44 | H-P portfolio at matrix costs | pending |
