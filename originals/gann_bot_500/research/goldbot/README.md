# goldbot — Phase 1 (local research)

Local-first XAUUSD research stack implementing the converged plan: rule-based
R3/S3 pivot edge + triple-barrier outcomes + purged combinatorial validation,
with an exact-OU XAU/XAG spread diagnostic, all netted against a cost model whose
every number is tagged `[VERIFIED] / [BROKER] / [ESTIMATE]` in `config.yaml`.

**Honesty banner:** backtest numbers here are an *upper bound*. Fills are at
barrier prices, slippage is a flat estimate, and spreads don't widen around news
in simulation (the live layer avoids news instead). Demand a margin of safety.

## Quickstart

```bash
py -3.11 -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/python _isolation_check.py              # "ISOLATION OK"
.venv/Scripts/python tests/run_tests.py               # all self-checks must pass
.venv/Scripts/python tests/run_tests.py --full        # + parity vs bot_spec_trades.csv
.venv/Scripts/python run_phase1.py ../data/xauusd_m1_histdata.csv
.venv/Scripts/python run_spread_research.py --selftest
```

Expected data: CSV/Parquet with `time,open,high,low,close[,volume]`. **Set
`data.data_tz` in `config.yaml` first** — MT5 exports are usually broker server
time, not UTC, and pivot levels silently change if the day-cut is wrong.
(Numeric `time` is epoch seconds and inherently UTC; the local HistData M1 file
already is.)

## The signal is NOT a fade — deviations from the original spec

The spec shipped `pivots.py::r3s3_fade_events` as a placeholder to be replaced
by the validated rules. Porting them changed three things (all documented,
none silent):

1. **Breakout, not fade.** 11 years of XAUUSD testing rejected fading R3/S3;
   the validated edge is the polarity flip — BUY on a close ABOVE R3, SELL on
   a close BELOW S3 (`fable-backtesting/STRATEGY_SPECIFICATION.md`). The
   placeholder stub remains in `pivots.py` and raises with a pointer to the
   two real generators in `goldbot/events.py`:
   - `generate_events_final` — conviction dual-arm H1+H4 (live spec, flip_bot
     v1.1, including the 12/16/20-UTC tie-hour fix), ATR exits + regime bail;
   - `generate_events_base` — the simpler H4-close ancestor (fixed-$ exits).
   Select with `strategy.variant` in config.
2. **Day boundary default is UTC 00:00, not 5 PM NY.** Every validated number
   was produced on UTC-midnight pivots. `ny17` is available in config
   (`pivots.day_boundary`) and `clock.py` still implements the NY rollover —
   but ONLY the fee/flatten clock uses it by default. Switching the pivot
   boundary invalidates parity with all historical results.
3. **News blackout defaults OFF.** Tested and rejected for this strategy —
   news days are the *best* trades (new-era PF 2.40); the live layer sizes
   1.5× on news instead. The guard is implemented (`goldbot/guards.py`) for
   Phase 2 experimentation, `enabled: false`.

## Module map

- `goldbot/ou_estimator.py` — exact AR(1)↔OU fit (θ, μ, σ, half-life) with validity
  gates: the σ-recovery term, the 0<φ₁<1 condition, and a stationarity t-gate
  (a finite-sample random walk fits to φ₁ *just below* 1 and would otherwise
  pass). Exact-transition simulator for tests.
- `goldbot/pivots.py` — R3/S3 on the previous *trading* day, shifted to kill
  lookahead; formula is the validated Fibonacci-style `PP ± (H−L)` with 2dp
  rounding applied exactly once (the live bot's convention).
- `goldbot/events.py` — the validated event generators (see above).
- `goldbot/triple_barrier.py` — label generator **and** exit engine (single source
  of truth): next-bar-open entries, gap-through-barrier fills at the open
  (`fill_mode: gap_open`; `barrier_level` = exact Sim5 parity), ambiguous bars
  resolved conservatively as stops and counted, optional validated bail overlay
  (hivol half-out at −1.2×ATR / lovol 8h bail at −1.0×ATR). Returns GROSS P&L;
  costs are netted downstream so one trade set prices under every regime.
- `goldbot/cpcv.py` — purged + embargoed combinatorial splits (AFML ch. 7/12),
  C(6,2)=15 splits / 5 paths; full backtest-path reconstruction out of scope.
- `goldbot/costs.py` — measured tick-spread matrix (read-only from
  `fable-backtesting/cost_matrix.json`) + commission + Islamic admin-fee model;
  prints the breakeven move/oz per regime. The `flat` regime reproduces the
  historical 20pt assumption for parity only.
- `goldbot/clock.py` — 5 PM New York rollover via `zoneinfo` (22:00 UTC winter,
  21:00 UTC summer, automatically), night counting, flatten-window check.
- `goldbot/guards.py` — Phase 2 toxicity guards: rolling-median spread gate
  (calibrate the defaults on YOUR broker's ticks) and news blackout from a
  weekly-exported UTC calendar CSV. Both default OFF.
- `goldbot/backtest.py` — cost-netted stats with honestly-labeled metrics
  (per-trade Sharpe is not annualized; expectancy is per 1.0 lot, pre-leverage).

## Phase gates (go/no-go)

1. **Phase 1 → 2 (demo):** clear majority of purged splits with positive net
   expectancy, sane dispersion, realistic-regime PF ≥ 1.2 (new era) and ≥ 1.0
   (old era) — the repo's pre-registered bar — ambiguous-bar count small. If it
   works in only a few splits, that's regime luck — stop.
2. **Phase 2 (MT5 demo, ≥4–8 weeks):** measured slippage and spread distribution
   consistent with config estimates (update config to *measured* values and
   re-run Phase 1); zero guard/kill-switch misfires; rollover flattening verified
   across a DST boundary if the window allows.
3. **Phase 3 (small live):** only after 2, with risk limits enforced by code,
   and only capital whose total loss is acceptable.

## Broker verification checklist (do before Phase 3)

1. Islamic T&Cs: admin fee schedule for XAUUSD, grace period length, **per-position
   or per-account**, weekend billing, and the anti-abuse/revocation clause wording.
   (`islamic_admin_fee_usd_per_lot_night` is a tagged `[ESTIMATE]` until then.)
2. Onboarding entity and its regulator → your actual gold leverage and margin.
3. Contract specs: contract size, min stop distance, freeze levels, daily candle
   cut time — read from MT5 symbol info, never hardcoded.
4. Measure your own tick spread distribution for a week, rebuild
   `cost_matrix.json` (`fable-backtesting/cost_engine.py`), re-run Phase 1.
   **The current matrix is a THIN 1-day sample — the single largest open risk.**

## Known limitations / deliberately not included

- XAGUSD data is not on disk yet — `run_spread_research.py --selftest` proves
  the pipeline; download silver ticks with `fable-backtesting/bi5_downloader.py`
  (already XAG-aware) for the real run.
- CPCV events are serially dependent through the 24h re-entry block; embargo
  covers it. The 90-day ATR-median regime input is NOT purged by default
  (Phase 1 fits no model); set `cpcv.strict_regime_purge: true` to widen.
- HistData M1 is bid-only — all spread costs come from the cost model.
- Live MT5 executor / order manager (Phase 2), meta-label training (Phase 1.5,
  only if the raw edge passes), Kalman rolling hedge, VPS deployment.
