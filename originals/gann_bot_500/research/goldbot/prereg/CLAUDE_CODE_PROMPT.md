# Paste this to Claude Code in the repo root

Integrate the pre-registration pack (PREREGISTRATION.md, regime.py, cost_matrix.py,
test_prereg_pack.py) for goldbot's verdict run. Ordering below is load-bearing —
the commit must precede any result. Do not reorder, do not edit thresholds.

1. Copy the four files into `research/goldbot/prereg/` as-is (they are
   self-contained by design; do not merge into the goldbot package).
2. Run `python prereg/test_prereg_pack.py` in the goldbot venv. All checks must
   pass before anything else. Do not tighten the wide statistical bands in the
   regime test — the comment explains why (ATR autocorrelation → few effective
   samples → seed-lottery).
3. Trials Ledger: enumerate every variant/parameter trial you can find in repo
   history and STRATEGY_SPECIFICATION.md, present the list to Rashed, and let HIM
   confirm/complete it. Do not fill it by guesswork.
4. Commit the pre-registration BEFORE building the matrix or running anything
   filtered: `git add research/goldbot/prereg/PREREGISTRATION.md && git commit -m
   "preregister: H1 pins + H2 regime filter"`. Append hash + date to
   `research/goldbot/results/DECISIONS.log`.
5. Verify the tick schema against `bi5_downloader.py` output (column names, epoch
   unit) before trusting `build_matrix` defaults (`time_unit="ms"` is an
   assumption). Build the matrix over ALL available tick years (2010+ if present),
   save `results/cost_matrix.json`, print the coverage report, and flag any
   (year,hour) bucket with n < 10,000 or missing hours.
6. Wire `CostMatrix.trade_cost_usd` into the phase-1 cost path (keep the flat
   model as a comparison column, not the verdict basis). Compute the H2 filter
   series ONCE on the full 2010+ M1 history (`daily_rel_atr` +
   `trailing_pct_rank`, warm-start), events remain 2015+ only. Day-cut must match
   the pivots (UTC-00:00).
7. Run in this exact order, writing each result to results/ before starting the
   next: (a) H1 rerun, unfiltered, matrix costs + p90 stress column;
   (b) H2 at 0.50; (c) plateau 0.40 and 0.60; (d) mechanism control on the old
   era (`regime.mechanism_control`). Emit per-era PF tables, the full 15-split
   expectancy lists, mechanism numbers, and fallback-hit counts.
8. Apply PREREGISTRATION.md's decision tree verbatim; append the verdict and each
   gate's pass/fail line to DECISIONS.log. If any input had to deviate (tick
   schema, missing years), log the deviation — it does not license threshold
   changes.
9. Build nothing else (no executor, no new variants) until a verdict line exists.
