> Copy of the frozen preregistration `audit/prereg/E7-INDICATORS.md`.

# E7 Indicator evidence

Blind prediction (Claude): gold 200-day beats buy-and-hold on drawdown and not on return, and fails PF at some slice. FX Bollinger/RSI FAIL at cost, 90%.

The earlier research report is not on disk, so the two rules are the plain textbook forms.

## A. Gold 200-day filter
Data: corrected true-UTC D1 from HistData, 2010-2026, with 2010-2012 ASSUMED-CLOCK. Metrics are shown with and without those years, using the without-case for slices.
Rule: at the D1 close, if close > SMA(200) hold long for the next day, else flat. Filled at next open.
Trades are the long spells. Costs: per-switch matrix spread plus 0.5 slip, and $5 per lot night admin [ESTIMATE].
Benchmark: buy-and-hold with the same financing. Extra gate: Sharpe >= buy-and-hold Sharpe on the slice.
GOLD-LIT-1's H-C monthly momentum overlaps this idea and already opened 2004-2026 monthly gold data. E7A's slices are therefore not unseen data, so it is marked CONTAMINATED in advance, and a pass goes only to the forward test.

## B. FX Bollinger + RSI
Data: Dukascopy M1 EURUSD and GBPUSD, 2013 to 2026-10, resampled to H1 bid with bar spread.
Rule: BB(20, 2) on close and RSI(14) Wilder. Long when close < lower band and RSI < 30. Short when close > upper band and RSI > 70. Fill next open. Exit at first close beyond the middle band, stop 2 x ATR(14), time stop 48 bars.
Costs: bar spread at both fills, 0.5 spread slip per side, $7 per lot round trip, no financing for under one day.
Gates as COMMON, per pair. Ledger: 3 variants.
