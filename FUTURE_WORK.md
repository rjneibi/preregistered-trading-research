# Future work

## H-20: left unrun

H-20 asked whether the 20:00 UTC concentration was an hour effect or an overnight-holding effect. It was frozen on
2026-08-23 and withdrawn unrun in cycle 4 under its own power gate. The smallest difference it could detect at 80% power
was 0.347 ATR, against an effect of about 0.114 ATR, so the test was underpowered by about 3x. Its sealed
prediction stays closed.

The audit adds a second reason. The hour-20 cohort came from HistData stamps that sit one hour ahead for most of the year. On true
UTC the cohort shrinks from PF 1.793 to 1.081 at p90 cost, and its Sidak p since 2023 goes from 0.110 to 0.999. The premise no longer holds.

## Google Trends: not tested

The earlier research suggested two uses: a contrarian gold signal from India-region search spikes, and a volatility
filter. Neither was tested. Google Trends values are rescaled and revised each time they are pulled, and no archive of
past vintages exists here. A download today would use information unavailable on the historical date, so any
backtest would carry lookahead that cannot be measured or removed. An honest test needs vintages collected forward,
pulled on a fixed schedule and stored unchanged from the first date of the test.

## MT5-only experiments: skipped for this release

Profile D baseline, the HA additions and the NQ transfer used bars that only came from MT5 and were never cached. The audit
does not log in to a broker, so they stay UNVERIFIED. If bars are exported later, those runs count as re-implemented, not
reproduced. They can join a later release.

## Added at the end of the audit, 2026-10-31

- **iFVG NY-open model.** Not specified and not tested. No spec is published in this release. A test would need a new preregistration written and frozen before any data is looked at.
- **Live bot code.** Code that runs the index rules is not in this release. It could be published later with those results.
- **Depth-based slippage for crypto.** No free historic order-book data was available for E5.
- **CPI dates for 2016-2024.** The event calendar has CPI for 2015 and 2025-26 only, so E4 undercounts CPI.
- **Silver ticks after 2022-09.** The feed refused the rate needed, so E1 and E2 use M1 spreads.
- **REEL-1.** A separate study of two social-media strategies, a Fibonacci 78.6-88.6 pullback on gold and a weekly profile on the Nasdaq-100, finished on 2026-10-31 after the registry closed. It found no edge. It is not audited or counted here, so the ledger total is a floor. It can join a later release.
