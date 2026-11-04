# FR_PREREGISTRATION — fleet review: Micro grid (FR-M) + London TP rescale (FR-L)

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; committed before
any run). Same protocol as the goldbot preregs: no variant, threshold, or gate
edits after any result is seen; new ideas = new prereg with deflated gates.

**Registered predictions:**
- FR-M (Micro): Claude = ALL VARIANTS FAIL (escalation-into-extension is the
  disease; filters treat symptoms). Rashed = SOME VARIANT PASSES.
- FR-L (London): Claude = STILL FAILS (a TP rescale cannot rescue a 5.2%
  base win rate). Rashed = ATR TP RESCUES IT.

## FR-M — Micro pyramiding grid, backtested at SPEC size

Entry stream (pinned): the 1,353 replayed D-gate entries in
`research/dr_backtest/trades_D.jsonl` (Micro's entry gates = D's, per
CODEBASE_TRUTH). Fields used: entry_ts, direction, zone_source, atr.
Coverage is 2021-06 → 2026-06 (single era — noted limitation; OOS gate below
compensates).

Grid simulation (pinned, M1 bars, research/data/xauusd_m1_histdata.csv):
- Tranche sizes [5,10,20,30,35] × 0.10 lot at FULL SPEC (no margin caps —
  tests the DESIGN, not the crippled demo).
- Tranche 1 fills at the open of the first M1 bar at/after entry_ts; all
  trades in a tranche share that bar's open price (0.5s stagger ≈ one bar).
- A tranche takes profit when favorable excursion from its entry ≥ TP
  (BUY: high ≥ entry + TP); the next tranche fills at the NEXT bar's open.
- Timer: at entry_ts + 600s, all open tranches close at that bar's CLOSE.
- Pessimistic resolution: if a bar could both TP and hit SL/timer, the
  adverse exit wins (house convention).
- Costs: per-trade round trip = 2 × matrix median spread (entry-hour,
  per-year matrix `research/goldbot/results/cost_matrix.json`) × 10 oz
  + $0.70 commission (0.1 lot at $7/lot RT).

Variant family (the ENTIRE search space — 5):
- M0: as-designed baseline (TP $1.00, timer 600s, no SL).
- M1: M0 + zone filter: fire ONLY on R3/S3 zone_source.
- M2: M0 + grid stop: close ALL at market when adverse excursion from
  tranche-1 entry ≥ 1.0×ATR(H1 at entry) — intrabar, at the level
  (gap-through → bar open); timer retained.
- M3: M0 with ATR-scaled TP: TP = max(0.30×ATR, $0.40) per tranche.
- M4: M1 + M2 + M3 combined.

FR-M PASS requires, for at least one variant, ALL of:
1. Full-period PF ≥ 1.20 at matrix costs.
2. OOS (last 30% of events by time) PF ≥ 1.00.
3. Worst single-zone loss ≥ −$5,000 (at spec size).
4. n(zones simulated) ≥ 300.

## FR-L — London ICT with scaled TP (the repo-nominated un-run experiment)

Harness (pinned): `research/ict_london_lab.py` detection verbatim (the same
code the live bot locks to), 16.5y HistData M1, London kill-zone only,
lab cost convention (spread charged per round trip, max(median, 25pt)).

Variant family (the ENTIRE search space — 5): TP = {1.0, 1.5, 2.0}×ATR(14 at
setup) and {0.30%, 0.50%} of entry price, replacing fixed 1500pt. SL, OTE,
sweep, displacement, session, cancel rules UNCHANGED.

FR-L PASS requires, for at least one variant, ALL of (the lab's own gates):
1. OOS (last 30%) PF ≥ 1.20.
2. OOS n ≥ 15.
3. Max drawdown ≤ 25% (fixed 1.00 lot on the lab's $10k basis).
4. IS and OOS not inverted (both sides of the split positive or the pass is void).

## Decision tree (committed)
- FR-M all fail → recommend RETIRE Micro (bot stays stopped; operator
  confirms retirement). Any pass → fix the three implementation bugs
  (10019 margin sizing, 10016 stop distance, journal TZ), then demo forward
  test of the passing variant at minimum size; no live sizing from this.
- FR-L fail → recommend RETIRE the London line (stop run_bot_L; operator
  confirms). Pass → update ict_london_bot.py TP to the winning variant and
  continue the demo forward test (which currently has ZERO fills anyway).
- Bugs found during harness work are logged, never silently "fixed into"
  a passing result.

## Ledger delta (goldbot master ledger, appended at freeze)
| # | Trial | Outcome |
|---|-------|---------|
| 42 | FR-M Micro grid variants M0-M4 | pending |
| 43 | FR-L London TP rescale (5 variants) | pending |

## Known-unverified inputs
Matrix 2019-2025 gap still filling (understates that span's costs → biases
Micro/London results optimistic → a FAIL survives the bias a fortiori;
confirmation watcher will land full gold coverage ~03:00). HistData is
bid-only, different feed from the broker (22% same-window agreement for
London setups — documented). trades_D.jsonl is a replay, not broker fills.
