# Common rules for Phase D and Phase E

Frozen 2026-10-31 before any data was loaded for these experiments. All changes after the first run are bug fixes, logged with before and after.

## Slices
Time-ordered per instrument: dev first 50%, validation next 20%, holdout last 30%, by calendar span of the usable data.
Order: dev, then validation if dev passes, then holdout once if validation passes. A slice that was not reached stays sealed and is reported as sealed.

## Gates for a strategy experiment
On each slice, net of costs:
1. PF >= 1.20
2. PF at 2x costs >= 1.00
3. n >= 100
4. Random-entry twin (same count, same holding time, 2,000 draws, seed 7) one-sided p < 0.05

On holdout, also 5. Deflated Sharpe >= 0.95 at the ledger trial count. The family-count DSR is reported beside it and does not decide.
A slice with n < 100 is `INSUFFICIENT SAMPLE`, which stops progress the same as a fail, and is not called a fail.
A pass means a candidate for the forward test. It is not a claim about future returns.

## Costs
Reported at 1x, 1.5x and 2x. Each spec lists its model.

## Data handling
Clock: Dukascopy, Binance and Yahoo stamps are UTC. Any use of the HistData gold file goes through `phaseC/clockfix.py`. 2010-2012 are `ASSUMED-CLOCK`.
Seeds fixed. Inputs and outputs hashed in `phaseE/MANIFEST.sha256`. Every run gets a ledger row, including fixes and failures.
Environment: `infrastructure/requirements_audit_env.txt`.

## Trial accounting
Ledger rows use the variant count stated in each spec. No variant is added after the first run.
