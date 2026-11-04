# E3 Portfolio, descriptive only

Per the user's instruction, nothing here selects or passes anything. No PASS verdict can come from E3.

Inputs: the four REPRODUCES-BUT-FRAGILE results, using saved trades in `trade_checks/`: XM-1-A1, SW-1 and TUNE-1-DIP (mean reversion), EDGE-1-F6 (trend).
Daily return: each trade's return booked on its exit date. Calendar union of 2012-01 onward, zero on days with no exit.
Reports: correlation matrix, share of each strategy's worst 10% days and worst drawdown spells that overlap another's, and an equal-risk combination.
Equal-risk means each stream is scaled by the inverse of its full-sample daily sd. That uses the full sample, so the combination is an information figure only, and its weights are not optimised.
Ledger: 0 variants, because nothing is selected.
