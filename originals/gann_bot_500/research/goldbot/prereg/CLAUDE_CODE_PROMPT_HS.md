# Paste this to Claude Code in the repo root — H-S scalp falsification

Integrate the H-S pack (HS_PREREGISTRATION.md, scalp_lab.py, test_hs_pack.py)
into `research/goldbot/prereg/`. Ordering is load-bearing. Do not add config 13.

1. Run `python prereg/test_hs_pack.py` in the goldbot venv — all must pass.
2. Rashed fills his prediction line in HS_PREREGISTRATION.md; append the ledger
   delta to the master Trials Ledger; commit the prereg BEFORE any run:
   `git commit -m "preregister: H-S scalp falsification"`. Hash → DECISIONS.log.
3. COST WIRING (pin, to avoid double-counting): `pf_net(cost_per_oz=...)` takes
   the matrix per-oz figure EXCLUDING commission (spread × (1+2·k_slip) via
   CostMatrix per entry-hour); the $7/lot RT commission is charged separately by
   pf_net. The frontier exhibit's `c` is all-in per-oz, i.e. matrix per-oz + 0.07.
4. Exhibits first (descriptive, logged to results/): breakeven_frontier at three
   cost levels — the matrix full-period mean, the best-session old-era level, and
   the p90 stress level (compute all three FROM cost_matrix.json; do not hardcode
   my bracket guesses) — plus move_vs_cost on the full real M1 history at the
   matrix mean.
5. Run the 12 pinned configs under the same purged-split protocol as H1: config
   selection on training folds only, the selected config evaluated OOS; per-era
   and p90 columns. The dollar_barrier loop is pure Python — if z-fade event
   counts make it slow, chunk per year or numba-jit it; semantic changes are not
   permitted.
6. Permutation reality check: ≥200 replicates, matched per-config trade counts,
   random sides, same geometries/horizon, at the matrix mean cost. Record the
   best-of-12 95th percentile next to the winning config's OOS PF.
7. Apply the HS gates and decision tree verbatim; verdict + gate lines →
   DECISIONS.log. Bar-level PASS triggers the tick-level re-simulation stage on
   the 2015–18 archive with unchanged thresholds — it does NOT trigger demo,
   sizing, or any live step.
8. The XAGUSD download and anything that would construct the XAU/XAG spread stay
   untouched (H3 quarantine).
