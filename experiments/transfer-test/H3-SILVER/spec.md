> Copy of the frozen preregistration `audit/prereg/H3-SILVER.md`.

# H3-SILVER, Phase D completion

Source spec: `goldbot/prereg/H3_PREREGISTRATION.md`, frozen 2026-07-06 while no silver bars were on disk. It is not retroactive. Nothing in the spec changes.

## What was missing
Frozen, never run. No verdict, no silver cost matrix, no ledger outcome. Rashed's and Claude's predictions are both FAIL.

## How it runs
- Silver: `xagusd-bi5-*.csv` ticks 2015-01 to 2022-09 (read only) to M1 bid, using bid as the bar series, as the gold M1 does.
- Silver cost matrix: `prereg/cost_matrix.py` `build_matrix`, same builder, same k_slip 0.5, $7 per lot round trip.
- Gold: corrected true-UTC M1. The spec says "existing XAUUSD M1". That file had the clock defect, found after the freeze, so this is the logged bug fix. A recorded-clock run is reported beside it and decides nothing.
- Hours: H1 bars on the common coverage.
- Everything else from the spec: monthly beta on 90 days, z from trailing 90-day OU stationary sd, entry 2, exit 0, stop 4, time stop 10 days, IS first 70%, OOS last 30%, gates 1 to 4, decision tree.

## Judgment calls left open by the spec
1. "Silver lots": 1 lot gold is 100 oz and 1 lot silver is 5,000 oz. Beta lots silver is read as hedge notional: silver notional = beta x gold notional. Volume is treated as continuous.
2. Admin fee: $5 per lot night [ESTIMATE], charged on each leg for its lots, for nights crossing 22:00 UTC.
3. The trailing OU fit that gives z uses the spread under the current month's beta, over the trailing 90 days ending at the last completed bar.
4. A month with an invalid trailing fit takes no new entries. Open positions keep their stops.
5. Validity gate 1 is evaluated with `fit_ou(valid=True)` and half-life in [4h, 10 days] on the IS segment, using the concatenated spread with each month's beta.
6. Slippage on each leg follows the matrix rule, k_slip times bucket spread per side.

The stated order holds: if gate 1 fails, H3 closes with no trading conclusion. Trading numbers are then not computed.
