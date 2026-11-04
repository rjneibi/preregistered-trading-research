# Research log: London Breakout

Newest entries at the bottom. Each entry gives the decision and the reason for it.

## 2026-10-30

**Setup**
- The project lives at `originals/london-breakout` (the user's research drive), under git.
- Prior evidence from the user's own programme (TA-LAB, SC-1, TUNE-1) was read before starting:
  - Gold Asia-range ideas failed. One apparent edge was a look-ahead leak: the Asia window pulled in next-day bars.
  - Opening-range breakout on US index cash opens had weak signal, and the live ORB-30 lost money over the last 12 months.
  - Prior expectation: **no net edge**.
- Literature summary is in `docs/research_summary.md`. Hypotheses H1-H15 were frozen there before any backtest.

**Data**
- Dukascopy M1 bid and ask with tick volume, via `dukascopy-node` 1.51.1 (pinned in `tools/package.json`).
- Seven instruments, 2013 to 2026-10.
- Mid prices are used for signals. The per-bar spread is `max(ask-bid at open, ask-bid at close)`, which is conservative.
- Fills are modelled at bid/ask, so the real spread is in every trade. On top of that:
  - fixed slippage per side;
  - commission on FX and gold.

**Split**
- GER40 data starts 2013-09-30, so 60/20/20 by calendar time gives:
  - in-sample (IS) up to 2021-08-01;
  - validation (VAL) up to 2024-03-15;
  - locked out-of-sample (OOS) from 2024-03-15 to 2026-10-30.
- The config first held rough dates (2021-07-01 / 2024-02-01). They were corrected once the first-bar date was known, before any backtest had run.

**Engine conventions** (all conservative, tested in `tests/test_engine.py` against hand-computed cases)
- A same-bar stop and target counts as the stop.
- On a stop-entry's fill bar, the target is not credited.
- Gapped stops fill at the bar open.
- Exit simulation always runs on 1m bars, even for 5m/15m signals. This resolves most intrabar ambiguity.

**Session times**
- All session times are derived through `zoneinfo`.
- The author's Variant-A Asia window (19:00-04:00 New York) ends *after* the London open: 04:00 NY is 08:00 or 09:00 UTC, while London opens at 07:00 or 08:00 UTC. The box is therefore truncated at the London open. Logged as a gap.

**Data limitation**
- Dukascopy has no overnight GER40/UK100 prices from 2015-01 to about 2018-06, so no Asian box can be built on those days. They are excluded from Variant A.
  - About 860 of 2,691 IS+VAL weekdays are lost.
  - The London/NY sessions of Variant B are unaffected.
  - The NY-session Asia box (Variant B "asia") is likewise empty in those years.
- No free substitute exists. Documented in `docs/data_quality.md`.

**Economic calendar** (`data/calendar/high_impact_events.csv`)
- NFP and US CPI release dates come from BLS release archives (exact).
- ECB monetary-policy meetings come from eco3min.fr's table of every ECB meeting, holds included (cross-checked against the ECB's 2013 schedule).
- BoE: only 2024+ dates were obtainable, so BoE cannot be tested historically. This is a gap.
- FOMC is skipped. It is announced at 19:00-20:00 London, after the 16:30 forced exit, so it cannot touch an intraday London trade.

**Selection rule and pass gates, frozen BEFORE any grid result was looked at** (written while stage 1 was running)

Selection (Variant A and B separately):
1. Eligible: the same config, applied to GER40 and UK100, must have
   - ≥ 150 IS trades on each instrument;
   - IS expectancy > 0 at 1x costs on each.
2. Rank eligible configs by plateau score: the mean IS expectancy (both instruments) of the config and all its one-step neighbours in the grid. This prefers broad plateaus over spikes.
3. Take the top 10 by plateau score and look at VAL. Choose the best VAL expectancy among those with VAL > 0 on both instruments.
   - If none qualifies, the best plateau config goes forward anyway, labelled "failed validation".

Gates for calling it an edge (all on the GER40+UK100 combined trade list):
- **G1:** VAL expectancy at 1x costs > 0, with t ≥ 2.0.
- **G2:** beats random direction at the same entry times, permutation p < 0.05 (IS+VAL).
- **G3:** expectancy > 0 at 2x costs (IS+VAL).
- **G4:** Hansen SPA p < 0.10 across the whole stage-1 grid (IS daily R). This is the multiple-testing guard.
- **G5:** walk-forward (24m train / 6m test, selection over the full grid) stitched expectancy > 0.
- **G6:** the locked OOS run, done once, gives expectancy > 0 at 1x costs.

Verdict mapping:
- All six pass: candidate for paper trading.
- G1-G5 pass but G6 fails: paper trade only, with strong caution.
- Any of G1-G4 fails: no edge, abandon.

**Blind prediction** (Claude, recorded before any grid output was viewed)
- G1-G4 fail for both variants.
- P(any config passes all of G1-G5) ≈ 10%.
- Gross expectancy will sit around +0.03 to +0.08R, and costs will take most or all of it.
- The user's own blind prediction was not collected, because the run was autonomous. Recorded here so it is not mistaken for a blind comparison.

**Stage 1 results (IS+VAL only)**
- **Variant B:** 4,320 configs (2,160 per index).
  - 0 eligible; 0.9% positive IS.
  - SPA p = 0.975, White RC p = 1.0.
  - Asia session: about -2.6R/trade (overnight spread).
  - London and NY sessions: about -0.23R/trade on average.
  - The volume filter does not help.
  - **Variant B is rejected at stage 1.** The B grid was also run on the 5 robustness instruments for H15.
- **Variant A:** 32,544 configs (16,272 per index).
  - 1,850 configs are eligible (IS > 0 on both indices with ≥150 trades each).
  - **None of the top-10 plateau configs is positive in VAL on both indices.**
  - Only 0.28% of all configs are positive in VAL.
  - SPA p = 0.37, so **G4 fails**. White RC p = 0.996.
  - Per the frozen rule, the best plateau config goes forward labelled "FAILED validation": box 23:00-07:00 UTC, 15m bars, range ≥ 1×ATR, whole candle outside, 30-min window, stop 25% inside the box, no target (exit 16:30).
    - IS: +0.083R (n=436).
    - VAL: -0.246R (n=231).
  - An author-literal baseline is also carried for reference: 00:00-07:00 UTC box, 5m, body ≥ 50%, close outside, 120 min, stop 25% inside, RR 2.

**Fix keep-rule (frozen before any fix was run)**

A section-9 fix is kept only if all of these hold:
- it improves pooled expectancy in IS **and** in VAL;
- it improves IS expectancy on **each** index;
- it retains ≥ 40% of trades;
- VAL expectancy after the fix is > 0.

Every fix is counted as an extra trial.

**Deep dive, walk-forward and fixes (IS+VAL)**
- Selected config:
  - IS+VAL: -0.031R (n=667).
  - Gross: +0.051R. Cost break-even at 0.64x the estimated costs.
  - Random-direction p = 0.38; fade -0.054R.
  - Decay: -0.038R per year, t = -2.45.
- Author-literal baseline:
  - IS+VAL: -0.121R (n=3,195).
  - Gross: +0.019R. Break-even at 0.14x costs.
  - Random p = 0.07.
- Walk-forward stitched (24m/6m, selecting over the full grid each window):
  - A: -0.027R (n=664).
  - B: -0.268R (n=594).
- 26 fixes were tried, including break-even, partials, trailing, news, trend, volume, confirmation, retest and box filters.
  - **None meets the keep-rule.** Several improve VAL a little, but VAL stays negative.
- Robustness instruments: the selected rules are gross-positive on US30/XAU/GBPUSD (small n) and net positive only on US30 (+0.10R, n=169).
- Variant B is negative on all 21 instrument×session cells.
- **Gates G1-G5: all FAIL.**

**Freeze**
- `config/final_strategy.yaml` holds the stage-1 pick with no fixes, status "FAILED VALIDATION - NO EDGE".
- Committed before the OOS run.
- OOS is run once for this config.
- The author-literal baseline is run once on OOS as a labelled reference. It is never used for any selection.

**OOS (run once, 2024-03-15 to 2026-10-29)**
- Final config at 1x costs: **-0.008R/trade, n=204, t=-0.09**.
  - Gross: +0.055R.
  - 2x costs: -0.081R.
  - Max DD at 0.5% risk: 7.7%.
- **G6 FAILS.**
- By index:
  - GER40: +0.129R (n=98).
  - UK100: -0.136R (n=106).
  - The GER40-only result is not significant, and was not pre-registered as a hypothesis. Under the anti-annexation rule, a GER40-only version would need a fresh pre-registration and forward data.
- Author-literal reference on OOS: -0.108R (n=1,121, t=-2.6).

**Verdict: no edge.** All six gates fail.

**Replay check**
- `tests/test_replay_equivalence.py` runs `strategy/signal.py` bar by bar on 250 random days per index.
- 85 signal days and all no-signal days match the backtest exactly: time, direction and day presence.
- This confirms no look-ahead in the backtest signal path.

**Deliverables**
- `report.html`
- `docs/gaps.md`, `docs/data_quality.md`
- `config/final_strategy.yaml`, `strategy/signal.py` (+ tests)
- `README.md`, `run_all.py`

**Total configurations evaluated:** 59,778.
- Variant A: 32,544 on the two indices.
- Variant B: 4,320 on the two indices, plus 10,800 on 5 robustness instruments.
- 26 fixes.
- 2 OOS runs: the frozen config and a labelled reference.
- Not counted above: the reruns of the selected rules on 5 robustness instruments.

**Final verdict: no edge. Abandon; do not paper trade.**
