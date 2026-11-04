# Research agenda

Where this work could go next. The views and the ranking below come from an independent review written for the release by a separate reviewer that had not seen the work before. They are suggestions, not results, and nothing here has been run. Each item names the files to start from. To take one on, see [CONTRIBUTING.md](CONTRIBUTING.md).

## What decided the verdicts

Three things, none of them about the signal itself:

1. **Costs.** Where an edge appeared it was about the size of the spread. FINAL_v3 falls from PF 1.254 to 1.040 at the measured cost matrix.
2. **Data timing.** The HistData clock bug moved several gold results, see [audit/findings/CLOCK_BUG.md](audit/findings/CLOCK_BUG.md), and one sweep result was a look-ahead leak.
3. **Selection.** At least 179,000 variants were tried, so a pass at the full-ledger deflated Sharpe needs a t-statistic of about 6.

## Directions that look exhausted

At retail CFD costs on intraday bars:

- gold intraday level and pattern rules: pivots, ICT/SMC sweeps, CRT/FVG, session-box breakouts, opening-range breakouts, M15 and M30 price action and scalping;
- large indicator grid searches (TVS-1);
- social-media and public-channel signals;
- moving gold-tuned rules to silver or FX;
- machine learning on price-only features, and meta-labelling on top of failed rules.

More variants in these families would mostly raise the trial count.

## Directions that look under-explored

- **Short-horizon index mean reversion** (RSI(2), IBS) across many markets at once, not one market at a time. It is the only family here with any life, and pooling markets gives samples in the thousands.
- **Low-turnover risk premia**, such as carry, time-series momentum and volatility targeting, where costs stop dominating.
- **Cost and data-quality research as a product in itself:** the event-spread measurements, the year-by-hour spread matrix and the clock-fix method.
- **Regime conditioning that starts from a rule with positive unconditional evidence** and states its statistical power in advance. The regime tests here were small checks on rules that had already failed.

## Method changes worth making

- **Use a side-matched random twin for long-only rules.** The twin in [audit/phaseE/lib.py](audit/phaseE/lib.py) (`twin_p`) picks a random side for each twin trade. A long-only rule can then beat it on market drift alone. This makes the twin gate easier to pass, not harder, so it cannot have created a false failure.
- **Report the t-statistic and a multiple-testing haircut beside the deflated Sharpe.** The required t grows with the log of the trial count: for a sample of 124 trades, about 5.0 at 1,000 trials and 6.3 at 179,000, by the reviewer's check with [src/dsr.py](src/dsr.py). Family-wise tests (Romano-Wolf stepdown, SPA or CSCV over a whole search) are more informative than arguing about the exact count.
- **State the detectable effect at 80% power in every preregistration.** Several tests here could never have reached 100 trades.
- **Use point-in-time universes.** The EDGE-1-F6 coin list was chosen in hindsight.

## Ranked suggestions

1. **Re-grade the random-twin gate with side-matched twins.** Implement side-matched and long-only twins, rerun the twin gate on every entry that used it, and publish the differences. *Start from:* `audit/phaseE/lib.py`, `audit/phaseE/e1_pairs.py`, `audit/phaseE/e2_silver.py`, `audit/phaseE/e7_indicators.py`, `audit/stats/gate_table.py`.
2. **Replicate the forward-test rules on public data.** Run XM-1-A1, SW-1 and TUNE-1-DIP on Dukascopy daily index bars up to the freeze date, with the common gates, both deflated Sharpe columns and the one-bar delay. This closes the gap that the headline survivors rest on a broker feed. *Start from:* `audit/forward/forward_update.py`, `audit/forward/strategies.json`, `audit/forward/parity_rules.py`, `audit/stats/pass_audit.py`, `audit/prereg/COMMON.md`.
3. **Add a forward-test analysis plan.** A pre-stated rule for when to stop or continue, a power curve per strategy, and scoring on daily marked-to-market returns. The frozen rules stay untouched. *Start from:* `audit/FORWARD_TEST.md`, `audit/forward/summarize.py`, `audit/forward/rule_groups.json`, `tests/test_forward.py`.
4. **Test short-term reversal across a broad cross-section.** One frozen RSI(2) or IBS rule on 20 to 50 liquid indices and ETFs, pooled and per market, split before and after the rule's publication date, against side-matched twins. *Start from:* `audit/stats/pass_audit.py`, `audit/phaseE/lib.py`, `audit/forward/rule_overlap.py`, `audit/phaseE/fetch_public.py`.
5. **Estimate the effective trial count and run family-wise tests.** Cluster TVS-1 configurations and LBO-1 cells by return correlation, and report the deflated Sharpe at the effective count beside a Harvey-Liu-Zhu haircut and a Romano-Wolf or SPA test. *Start from:* `audit/stats/trial_count.py`, `registry/trial_ledger.csv`, `src/dsr.py`, `audit/phaseC/tvs_recheck.py`, `originals/london-breakout/src/lbo/robustness.py`.
6. **Split gross from net for the gold families.** Run the twin test on gross returns, to separate "no signal" from "signal smaller than the spread". This says whether cheaper execution could ever matter. *Start from:* `audit/phaseC/dr_matrix.py`, `audit/phaseC/h1_clock.py`, `audit/phaseC/l2_recompute.py`, `originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py`, `audit/engine/nbe.py`.
7. **Build a general vendor-clock detector.** Turn the news-release, maintenance-break and cross-feed checks into a tool that reports the clock rule of any bar file against a reference feed. *Start from:* `audit/phaseC/clock_anchors.py`, `audit/phaseC/clock_map_all.py`, `audit/infrastructure/clock_cross.py`, `audit/infrastructure/data_profile.py`, `src/clock.py`, `tests/test_clock.py`.
8. **Test low-turnover crypto premia on point-in-time universes.** Funding carry and time-series momentum on a top-N-by-volume universe rebuilt monthly, with funding costs. *Start from:* `audit/phaseE/e5_crypto.py`, `audit/stats/pass_audit.py`, [experiments/trend/EDGE-1-F6/](experiments/trend/EDGE-1-F6/README.md).
9. **Extend the event-spread measurements.** More events, the missing CPI dates for 2016 to 2024, and more instruments, published as a dataset of spread multipliers. *Start from:* `audit/phaseE/e4_news.py`, `audit/phaseE/e4_spreads.json`, `audit/prereg/E4-NEWS.md`, [FUTURE_WORK.md](FUTURE_WORK.md).
10. **Start archiving Google Trends vintages now.** A scheduled job that stores raw pulls unchanged, so that a test free of look-ahead becomes possible in a year or two. *Start from:* [FUTURE_WORK.md](FUTURE_WORK.md), `.github/workflows/forward.yml`.
