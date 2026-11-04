# E2 Silver transfer

Blind prediction (Claude): all three FAIL, 85%.

No gold rule has passed, so "verified" here means verified code and verified numbers, not verified edge. The rules are the three headline gold rules with verified or corrected true-UTC runs: H1 (goldbot `final`), FINAL_v3 and FINAL_v4.
No parameter changes. ATR multiples are unit-free. Any rule constant in gold dollars stays unchanged and is listed in the results, so a reader sees where a literal transfer is not meaningful.

Data: Dukascopy XAGUSD M1 bid and ask, 2015-06-19 to 2026-10-29. Same era split as gold, using the boundary in `run_verdict.py`.
Costs: per-year, per-hour spread matrix built from these M1 bars (median and p90 of bar spreads), k_slip 0.5, $7 per 5,000-oz lot, admin fee as H3. The tick feed returned 503 at the needed rate, so the matrix uses M1 spreads, which understates peak spread inside a minute.

These rules were designed on gold, and silver is untouched by them, so the whole span is a single test with no dev slice.
Gates: PF >= 1.20, 2x cost PF >= 1.00, each era PF >= 1.00, n >= 100, twin p < 0.05, p90 PF >= 1.00.
Ledger: 3 variants.
