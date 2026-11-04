# HR

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Regime routing lifts OOS PF.

Family: routing overlay. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
HR tested a regime router on the goldbot "final" R3/S3 breakout. Each H1 bar gets a state (MOMENTUM, NEUTRAL, MEAN_REVERSION) from the Kaufman efficiency ratio with hysteresis. Only trades whose signal bar is in MOMENTUM are kept. Thresholds were calibrated on the first 70% of the period; the routing rule was then scored once on the last 30%.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): base trades from the H1 + H4 strategy; ER and states on H1 closes ([hr_is_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hr_is_runner.py) lines 104-105).
- Data source and file(s): base trades [results/verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv) (hr_is_runner.py line 89); HistData XAUUSD M1 for H1 bars ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7).
- Period: 2015-06-19 (hr_is_runner.py line 49) to the last trade in verdict_trades.csv.
- In-sample / out-of-sample: IS = first 70% of calendar time from 2015-06-19 to the last trade. Stored cutoff 2023-02-23 18:24 UTC; 334 IS trades, 138 OOS trades ([HR_is_manifest.json](../../../originals/gann_bot_500/research/goldbot/results/HR_is_manifest.json); hr_is_runner.py lines 91-93). IS M1 bars are loaded only up to the cutoff (line 103).

## Rules
- Entry: the base goldbot "final" trades, unchanged: R3/S3 = PP +/- (H - L) of the prior day; H1 close beyond a live level with H1 and H4 arms agreeing; H1 closes 12-20 UTC; skip Monday; 10-H4-close dead-level check; 1 per direction per day; 24 h re-entry block ([events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py) `generate_events_final`; config.yaml lines 9-15).
- Exit (stop, target, time): TP 0.8 x ATR(14 H1), SL 2.4 x ATR, 24 h time stop, bail overlay (config.yaml lines 20-35).
- Filters: ER = |close_t - close_{t-14}| / sum of absolute 1-bar changes ([modules/regime.py](../../../originals/gann_bot_500/research/goldbot/modules/regime.py) lines 2-5, 32). State machine with separate enter and exit thresholds and a 2-bar confirmation (regime.py lines 92-140). The state at the H1 close equal to the trade's signal time is used (hr_is_runner.py lines 111-115). Keep the trade only if the state is MOMENTUM ([hr_oos_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hr_oos_runner.py) lines 74-75).
- Position sizing: all gates on 1 lot per trade ([spec.md](../../../experiments/routing-overlay/HR/spec.md) lines 70-72). A sized diagnostic on IS only: 1% of equity risked over a 2.4 x ATR stop, $10,000 start, 0.01-lot step, floor to step, skip if below 0.01 lot ([modules/sizing.py](../../../originals/gann_bot_500/research/goldbot/modules/sizing.py) lines 105-129; config.yaml lines 106-115).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ER window | 14 H1 closes | config.yaml line 94 |
| Confirmation bars | 2 | config.yaml line 95 |
| Calibration quantiles (IS ER distribution) | mr_enter 0.20, mr_exit 0.35, mom_exit 0.55, mom_enter 0.75 | config.yaml lines 96-100 |
| Frozen thresholds | enter_mr 0.0962, exit_mr 0.1716, exit_mom 0.2832, enter_mom 0.4217 | HR_is_manifest.json; spec.md lines 34-39 |
| Route set | MOMENTUM only | config.yaml line 101 |
| IS fraction | 0.70 | config.yaml line 105 |
| Sizing (diagnostic) | risk 1%, start $10,000, stop 2.4 x ATR | config.yaml lines 106-109 |
| Base exits | TP 0.8 ATR, SL 2.4 ATR, 24 h, bail | config.yaml lines 22-30 |

## Costs
From the base trades: per-year x UTC-hour median spread, slippage 0.5 x spread per side, $7 per lot round trip; p90 spreads for gate 4 ([run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) lines 83-86; [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py) `trade_cost_usd`). The stored HR results match the audit rerun on the earlier partial cost matrix (commit 977fff5), not the full matrix ([run_goldbot_partial.sh](../../../audit/phaseC/run_goldbot_partial.sh) header; [logs_partial/hr_oos_runner.log](../../../audit/phaseC/logs_partial/hr_oos_runner.log)). The partial matrix used fallback spreads for years without ticks ([logs_partial/run_verdict.log](../../../audit/phaseC/logs_partial/run_verdict.log): "fallback hits").

## Tuning and selection
- Search: on IS only, four route variants were printed: routing off, MOMENTUM, MEAN_REVERSION, NEUTRAL (hr_is_runner.py lines 125-128). Thresholds come from fixed quantiles of the IS ER distribution, not from a search.
- Configurations run (counted from the code/results): 1 rule scored OOS; 4 IS diagnostic rows. Ledger count (registry/trial_ledger.csv n_variants): 1. The ledger counts the one OOS rule.
- How the reported variant was chosen: MOMENTUM-only was fixed at freeze. The stated reasons were the breakout nature of the base rule and IS evidence (78% of IS trades in MOMENTUM; NEUTRAL IS PF 0.847, n=60) (spec.md lines 41-45). The choice used IS data and was made by hand. The MEAN_REVERSION IS row (n=13) was barred from being added later (spec.md lines 58-62).
- Preregistered: yes. [spec.md](../../../experiments/routing-overlay/HR/spec.md), copied from [HR_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/HR_PREREGISTRATION.md), frozen 2026-07-06. Gates: routed OOS PF >= 1.35; routed minus unrouted OOS PF >= +0.10; routed n >= 70; routed p90 PF >= 1.15 (spec.md lines 80-84). The prereg discloses that the author already knew the post-cutoff period was favourable for the base (spec.md lines 8-18).

## Results
1-lot basis. Slices under 100 trades are INSUFFICIENT SAMPLE.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored IS, routing off | 334 | PF 1.051 (sized PF 0.985) | [HR_is_manifest.json](../../../originals/gann_bot_500/research/goldbot/results/HR_is_manifest.json) |
| Stored IS, MOMENTUM | 261 | PF 1.074 (sized 1.035) | spec.md line 51 |
| Stored IS, NEUTRAL | 60 | PF 0.847 (INSUFFICIENT SAMPLE) | spec.md line 53 |
| Stored IS, MEAN_REVERSION | 13 | PF 2.093 (INSUFFICIENT SAMPLE) | spec.md line 52 |
| Stored OOS, unrouted | 138 | PF 1.421 | [HR_oos_run.json](../../../originals/gann_bot_500/research/goldbot/results/HR_oos_run.json) |
| Stored OOS, routed MOMENTUM | 107 | PF 1.484, p90 1.423, uplift +0.063; gate 2 FAIL, others pass | HR_oos_run.json |
| Audit rerun, partial matrix | 107 | PF 1.484, uplift +0.063 (matches stored) | [logs_partial/hr_oos_runner.log](../../../audit/phaseC/logs_partial/hr_oos_runner.log) |
| Audit rerun, full matrix, recorded clock | 107 (of 138) | PF 1.336, p90 1.237, uplift +0.054; gates 1 and 2 FAIL | [logs_recorded/hr_oos_runner.log](../../../audit/phaseC/logs_recorded/hr_oos_runner.log) |
| Audit rerun, full matrix, true UTC | 105 (of 146) | PF 1.075, p90 0.994, uplift +0.007; gates 1, 2, 4 FAIL. Cutoff moves to 2023-02-28 18:48 | [logs_true/hr_oos_runner.log](../../../audit/phaseC/logs_true/hr_oos_runner.log) |
| Audit rerun, full matrix, IS routing off, recorded clock | 334 | PF 0.976 | [logs_recorded/hr_is_runner.log](../../../audit/phaseC/logs_recorded/hr_is_runner.log) |

## Code and how to rerun
- Code: [hr_is_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hr_is_runner.py), [hr_oos_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hr_oos_runner.py), [modules/regime.py](../../../originals/gann_bot_500/research/goldbot/modules/regime.py), [modules/sizing.py](../../../originals/gann_bot_500/research/goldbot/modules/sizing.py), [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml). Base trades from [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py).
- Audit rerun stage: `goldbot_both` (full matrix, both clocks) and `goldbot_partial` (partial matrix) ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. Manifest group `histdata_xau`. Both cost matrices are committed ([cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json), [cost_matrix_977fff5.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix_977fff5.json)).

## Corrections from the release review
- README "Rules: Routing overlay." does not state the rule. The rule is: keep a base trade only if the ER(14) hysteresis state at its H1 signal close is MOMENTUM, with 2-bar confirmation and the four frozen thresholds (spec.md lines 27-39; hr_oos_runner.py lines 66-75).
- README "Splits: IS then OOS" omits the cutoff. IS is the first 70% of calendar time, cutoff 2023-02-23 18:24 UTC, 334 IS and 138 OOS trades (HR_is_manifest.json).
- README stored result "Routed PF 1.484 vs 1.421" gives no n. Routed n=107 of 138 OOS trades (HR_oos_run.json).
- README "Costs: per-year x UTC-hour Dukascopy spread matrix" is misleading for the stored numbers. The stored 1.484 is on the earlier partial matrix with fallback spreads. On the full matrix the routed PF is 1.336 (n=107), which also fails gate 1 (logs_recorded/hr_oos_runner.log).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Routed PF 1.484 vs 1.421, uplift +0.063 |
| Rerun, recorded clock | Routed n=107 PF 1.336, uplift +0.054 |
| Rerun, true UTC | n=105 PF 1.075, uplift +0.007 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Stored 1.484 reproduces on the partial matrix.

## Audit caveats
Baseline was known favourable at freeze; a future era-stratified test would be a new trial.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HR_oos_run.json](../../../originals/gann_bot_500/research/goldbot/results/HR_oos_run.json)
