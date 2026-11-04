# CRT-FVG-1: "CRT + HTF FVG" backtest. Plan and pre-registration

STATUS: FROZEN 2026-10-30 when the user said "run everything" after reading the draft. That approves the rule
interpretations as listed, pooled selection, and the $0.25 XAU spread default. Before the freeze, the only real-data
runs were signal-count and look-ahead checks on XAUUSD 2014-2016 (no P&L computed). Rashed's blind prediction was NOT
collected (the user went straight to "run"), so this run does not count toward the calibration ledger.

Rules: `config.yaml` (every threshold), `crt_fvg/rules.py`, `crt_fvg/engine.py`. Tests: `tests/test_rules.py` (15 pass).
No live-trading code is touched. Everything lives in `research/crt_fvg/`.

## Kill-list context (DECISIONS.log)
- HCRT (2026-07-07): D1 CRT on XAUUSD FAIL. Its decision tree says "no timeframe migration; FVG/QT/SMT inherit the
  negative prior".
- HSW (2026-07-07): intraday sweep-reclaim FAIL.
- SWEEP-MTF-1 (2026-10-26): H1 swing sweep with an M5 close back inside FAIL. Gross matched the random-direction twin,
  and the cost was about 0.29R per trade on M5 stops.
- This request is a new combination: a 4H bias, a 15m CRT streak, a 1H FVG area of interest and a CRT entry, on
  4 symbols. Under the anti-annexation rule it therefore gets its own pre-registration, and it starts with that
  negative prior.

## Data (no download needed)
- Dukascopy M1 bid/ask for XAUUSD, EURUSD, GBPUSD and NAS100, 2013-01 to 2026-10, already cached as
  `originals/london-breakout/data/m1/*.npz` (mid OHLC + per-bar spread, UTC).
- That is 13.8 years at about 85 MB per symbol, so the 2 GB download question does not arise.
- These are cached as npz rather than parquet because pyarrow is not installed and the cache already exists.
- 5m, 15m, 1H and 4H bars are built from M1 in code, aligned to UTC midnight.
- Known gap: NAS100 has no overnight prices from 2015 to mid-2018. 07-20 UTC is complete, but 4H bars and the EMA in
  those years are built from fewer bars.

## Rule interpretations (please check these; each one is a config switch)
1. **Swing (N=2):** strictly above or below the N bars on each side, so ties are not pivots. The pivot is usable
   from bar j+N+1.
2. **CRT reference:** the most recent confirmed swing low (bull case).
   - A newer confirmed pivot replaces it.
   - The first bar trading below it is the sweep, and the level is used up at that point.
   - K counts from the sweep bar, so K=1 means the sweep candle itself must close back above.
   - Sweep extreme = the lowest low from the sweep bar to the confirming bar.
   - Decision time = close of the confirming bar.
3. **Bias:** the last CRT on the 4H that is known at decision time is bullish, AND the close of the confirming entry
   bar is above the EMA50 of closed 4H bars. Alternative: compare the last closed 4H close.
4. **Rule 1:** the last 2 setup-TF (15m) CRTs known strictly before the entry decision are both in the bias
   direction, and the second sweep extreme is higher (bull) / lower (bear).
   - "Strictly before" makes a 15m entry CRT "new".
   - The streak never expires. Only a newer CRT can break it.
5. **Rule 2:** a 1H FVG in the bias direction, known before the entry sweep bar opens, and not invalidated as of
   the decision time.
   - Invalidated = a 1H candle closes beyond the far edge.
   - Any size by default; no expiry.
6. **Rule 3:** the entry CRT's sweep extreme lies inside that FVG zone. If several qualify, the newest FVG is used.
7. **Entry:** open of the next M1 minute after the confirming close.
   - Skipped if that bar is more than 60 minutes away, if it falls outside 07:00-20:00 UTC, or if it is a Friday at
     or after 20:45.
   - Only one open trade per symbol; signals that arrive during a trade are dropped.
8. **Stop:** sweep extreme ∓ 0.1 × ATR(14) on the entry TF.
   - Fixed targets are 1, 1.5, 2 and 3R, measured from the fill.
   - **liq** = the nearest swing on 15m that was known at the decision, is still unswept (checked on M1) and lies
     beyond the entry. With no such swing, there is no trade in that mode.
9. **Exits:** flat at the first M1 bar at or after Friday 20:45 UTC.
   - Positions are otherwise held overnight. Swap costs are not modelled.

## Costs and fills
- **Default spreads:**
  - XAUUSD: $0.25 spread + $7/lot round trip, i.e. $0.07/oz.
  - EURUSD: 0.5 pip + $7.
  - GBPUSD: 1.0 pip + $7.
  - NAS100: 1.5 pts and no commission.
- **Slippage:** 1 tick on the entry and on stop exits. Targets are limit fills with no slippage.
- **Stop fills:** a stop that gaps fills at the open. When stop and target are hit in the same M1 bar, the stop is
  taken.
- **Sensitivity runs:**
  - 0× costs (gross).
  - 2× costs.
  - Dukascopy's measured per-bar spread. The median XAU session spread was $0.30 in 2016 and $0.58 in 2025, i.e.
    above the $0.25 default.

## Validation
- **Split:** in-sample is the first 70% of calendar time per symbol (about 2013-01 to 2022-09). Out-of-sample is the
  last 30%, opened once, after the freeze.
- **Tuning grid (IS only):** 108 configs:
  - swing_n {2,3,5}
  - crt_k {1,2,3}
  - fvg_min_atr {0, .25, .5}
  - bias_tf {4H, 1H}
  - sl_buffer {.1, .25}
- **Grid size:** × 3 entry TFs × 5 TP modes × 4 symbols = **6,480 backtests**, all declared here.
- **Selection rule (recommended):** one config per entry TF × TP mode, picked by the pooled IS expectancy of the
  4 symbols, with ≥ 30 IS trades per symbol.
  - Reason: a single symbol has about 80 IS trades on 5m, and 108 configs is enough to fit noise.
  - The alternative is a per-symbol pick, which is reported too.
  - The untuned spec defaults are always reported alongside.
- **Walk-forward:** 6m train / 2m test, rolling. Config selection is pooled across symbols, with ≥ 10 train trades.
- **Monte Carlo:** 1,000 shuffles of the trade order, giving a max-drawdown distribution (1% risk, $100k).
- **Random direction:** same entries, stop distance and target R, with the direction set by a coin flip. 1,000 runs,
  giving a one-sided p-value.
- **Prop check:** FTMO-style rules on rolling 30-day windows, one start per trading day:
  - +10% target, −5% day, −10% total.
  - Each window is reported as pass, fail or "neither".
  - Expected to be mostly "neither": at roughly 1 trade a month, +10% in 30 days needs about 10R.
- **Outputs:**
  - Per symbol × entry TF × TP mode: n, win%, avg R (= expectancy in R), $ expectancy, PF, max DD, Sharpe (daily,
    √252), longest losing streak and trades per month.
  - Equity PNGs, `trades.csv` and `REPORT.md`.

## Power warning (measured, rules only, no P&L)
- On XAUUSD 2014-2016 the spec rules give 25 signals on 5m and 11 on 15m in 3 years, i.e. about 8 and 4 per year.
- Rule 1 (two monotonic 15m CRTs) is the main filter. Relaxing it to a streak of 1 gives about 7× more signals.
- Per-symbol OOS samples will be about 30 trades or fewer, so the gates are judged on the 4-symbol pool.

## Gates (frozen at sign-off, before any P&L)
- **Unit:** one cell = entry TF × TP mode, pooled over the 4 symbols, using the IS-selected config. That gives
  15 cells.
- **A cell PASSES if all of these hold:**
  - G1: OOS net avg R > 0 with n ≥ 50.
  - G2: OOS PF ≥ 1.15.
  - G3: OOS net avg R > 0 at 2× costs.
  - G4: it beats random direction on OOS with one-sided p < 0.05, after Holm correction over the 15 cells.
  - G5: the concatenated walk-forward net avg R > 0.
  - G6: XAUUSD's own OOS net avg R > 0.
- **Verdict:** "edge" requires ≥ 1 passing cell. Anything else is "no edge".

## Predictions (blind protocol)
- Rashed's prediction is collected first, with a confidence level.
- Claude's prediction is sealed in `prediction_claude.sealed.txt`. Its sha256 is given in chat and it is opened after
  Rashed's prediction is recorded.
