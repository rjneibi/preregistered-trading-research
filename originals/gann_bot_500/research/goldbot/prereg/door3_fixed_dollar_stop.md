# PREREG — Door 3: the fixed-dollar stop forced by a $2,000 account

Registered 2026-08-24, BEFORE running the experiment.

## Why this is being tested at all

This is NOT a search for a better edge. It is an engineering feasibility test
with a fail-fast purpose, and it must not be treated as a new hypothesis that
could "rescue" the R3/S3 result.

The user will trade a $2,000 account. Every broker measured so far has
`volume_min = 0.01` on XAUUSD, and `order_calc_profit` confirms $100 per $1/oz
per lot. Therefore the smallest expressible risk is

    min_risk = 0.01 lot x stop x $100

For a 1% budget ($20) that forces

    stop = $20 / (0.01 x 100) = $20.00/oz      <-- NOT chosen, DERIVED

The question is whether the strategy survives having its stop pinned there.

## The single change

FROZEN, identical to the validated spec: entry signal (`generate_events_final`),
session hours, pivots, day boundary, `time_stop_h=24`, `fill_mode=gap_open`,
eras, cost model, TP at `k_tp_atr = 0.8`.

CHANGED, exactly one thing: `k_sl_atr = 2.4` becomes `sl_usd = 20.00`.

No sweep. No optimisation. One value, dictated by the account. If it fails it
is dead — I will not go looking for a stop distance that works, because that
would be tuning to a target and the result would be unusable.

## Mechanism I expect to break it

The spec is high-win-rate / low-payoff: TP is 0.8xATR, SL is 2.4xATR, a 1:3
shape. It wins often precisely BECAUSE the stop sits far enough away to survive
ordinary adverse excursion while a near TP gets picked off.

Pinning the stop at $20 while ATR is ~22 makes SL ~0.9xATR against a TP of
~0.8xATR — roughly 1:1.1. A shape that needed a far stop to work now has a
close one. I expect that to destroy it.

Second mechanism, structural: the bail overlay is written in ATR multiples
(`hivol_half_x = 1.2`, `lovol_bail_x = 1.0`). Whenever ATR > $20 the SL is
nearer than either bail trigger, so the entire overlay becomes unreachable —
door 3 silently deletes a validated part of the exit stack.

## Blind predictions (falsifiable, recorded before seeing any output)

- **P1** Win rate falls by **>= 15 percentage points** vs the 2.4xATR arm.
- **P2** RECENT window (exit_ts >= 2023-01-01) mean net/trade is **NEGATIVE**
  on the same cost basis on which the ATR arm is positive.
- **P3** **>= 60%** of trades lose the bail overlay entirely, i.e. have
  entry ATR > $20.00 so that 1.0xATR adverse sits beyond the stop.
- **P4** Full-sample **gross** per trade is lower for the fixed-$ arm.

## Overall call, stated in advance

**I expect door 3 to FAIL and I expect to kill it.**

If it passes, that is the surprise and it gets the same scrutiny a pass always
gets: Sidak adjustment for every variant tested to date, and it changes nothing
about live capital until it survives a forward test.

## Fail branch

If P1-P4 land as predicted: door 3 is dead, recorded as dead, and the user is
told that a $2,000 account cannot run this strategy on a 0.01-lot broker by
shortening the stop. The remaining doors are (1) a finer-granularity broker and
(2) more equity. I do not invent a door 4 out of a reparameterisation.
