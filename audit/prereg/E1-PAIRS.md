# E1 Statistical pairs

Blind prediction (Claude): all nine cells FAIL, 90%. XAU/XAG most likely to fail at cost, BTC/ETH on cointegration frequency.

## Pairs and data
- XAU/XAG H1: Dukascopy M1 mid, 2015-01 to 2026-10. Gold from `london-breakout/data/m1/XAUUSD.npz`, silver from `_copy/data/dk_xag`.
- BTC/ETH H1: Binance spot 1h, `cross_market` files, 2017-08 to 2026-10.
- Gold vs GDX D1: GDX Yahoo adjusted daily, gold M1 sampled at 16:00 New York. From 2015-01.
If a source fails, that pair is reported as skipped. No other instrument is substituted.

## Variants, one config each
- V1 OLS hedge, trade only in months where both tests pass.
- V2 Kalman hedge, same filter. State is beta with random-walk variance 1e-5 and observation variance 1e-3 on log prices, seeded from the formation OLS.
- V3 OLS hedge, no cointegration filter. It exists to measure how results depend on cointegration.

## Formation and tests
Re-estimated on the first bar of each month. Formation is the trailing 90 calendar days for H1 pairs, 252 trading days for D1.
Tests at 5%: Engle-Granger (`statsmodels.tsa.stattools.coint`), Johansen trace with det_order 0, k_ar_diff 1. Spread is log A - beta log B, with an intercept in the OLS.
OU half-life comes from AR(1) on the formation spread. An invalid fit means no entries that month.

## Trading
Z uses formation mean and sd, or Kalman innovations scaled by the formation sd of innovations. Signal on bar close, fill at next bar open.
Entry |z| >= 2, exit at crossing 0, stop |z| >= 4. Holding limit 3 half-lives, capped at 10 days for H1 pairs and 60 days for D1.
Cointegration breakdown: V1 and V2 close at the next open if the month's retest fails. One position per pair.
Return per trade is on gross notional, with leg weights 1/(1+|beta|) and |beta|/(1+|beta|).

## Costs, both legs
- XAU, XAG: half the bar spread per side for entry and exit plus k_slip 0.5 times spread per side, $7 per lot round trip, $5 per lot night admin fee [ESTIMATE].
- BTC, ETH: 0.10% round trip per leg, as CR-1, plus 15%/yr on the short leg. E5 covers venue detail.
- GDX: $0.01 per share per side. Gold leg as above.

## Reporting
Per pair and variant: gates per slice, share of months where EG, Johansen and both pass, trade result inside and outside cointegrated months (V3), and half-life distribution.
Ledger: 9 variants.
