# H-M

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** HGB meta-label filter lifts PF.

Family: ML/meta-label. Market: XAUUSD. Timeframe: H1+H4. Idea source: the author's notes (not published): meta-labeling on the primary signal. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
H-M asks whether a small, fixed machine-learning filter can drop enough losing H1 conviction trades to lift profit factor out of sample. The model is a gradient-boosted classifier with Platt calibration. It is trained under 15 purged combinatorial splits, with the keep-threshold picked on training folds only. A shuffled-label run is the control. It was the author's second attempt at an ML trade filter.

## Instruments and data
- Instruments: XAUUSD, 1 lot per trade.
- Timeframe(s): the H1 trade set (H1/H4 signals, M1 exits); daily context features on UTC days ([meta_lab.py:68-84](../../../originals/gann_bot_500/research/goldbot/prereg/meta_lab.py)).
- Data source and file(s): HistData XAUUSD M1 (group `histdata_xau`), the tick cost matrix [results/cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json), and [news_days.json](../../../originals/gann_bot_500/fable-backtesting/calendar/news_days.json) ([hm_runner.py:66-80](../../../originals/gann_bot_500/research/goldbot/prereg/hm_runner.py)).
- Period: the H1 trades, 2015-07 to 2026-06 (recorded clock, n=472). Context series use M1 from 2010 for warm-up ([hm_runner.py:1-6](../../../originals/gann_bot_500/research/goldbot/prereg/hm_runner.py)).
- In-sample / out-of-sample: CPCV with 6 time groups, 2 test groups (15 splits). Training rows within 24h before or 40h after a test group are purged ([meta_lab.py:25,155-167](../../../originals/gann_bot_500/research/goldbot/prereg/meta_lab.py)). Each trade is out of sample in 5 of the 15 splits.

## Rules
- Entry: the H1 conviction trades, rebuilt with the same code as H1 ([hm_runner.py:41-64](../../../originals/gann_bot_500/research/goldbot/prereg/hm_runner.py); see [H1](../../../experiments/pivot-breakout/H1/README.md)). A trade is kept if the calibrated probability is at least the split's threshold tau ([meta_lab.py:176-178](../../../originals/gann_bot_500/research/goldbot/prereg/meta_lab.py)).
- Exit (stop, target, time): as H1 (TP 0.8 x ATR, SL 2.4 x ATR, 24h, bail; [config.yaml:20-35](../../../originals/gann_bot_500/research/goldbot/config.yaml)).
- Filters: the ML filter above. Label: net P&L at matrix median costs > 0 ([hm_runner.py:85](../../../originals/gann_bot_500/research/goldbot/prereg/hm_runner.py)).
- Position sizing: 1 lot.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Features (8, fixed) | hour (UTC), weekday, tie_entry (hour % 4 == 0), hivol (ATR > 90d median), vol_pctile_prevday (relative ATR rank over 252 prior days, previous day), adx_d1 (Wilder ADX(14) on D1, previous day), news_day, overshoot_atr = abs(entry - level)/ATR | meta_lab.py:24-26,87-109; HM_DESIGN.md §3 |
| Model | HistGradientBoostingClassifier: max_depth 3, max_iter 200, learning_rate 0.05, min_samples_leaf 25, l2 1.0, early_stopping on, validation_fraction 0.15, random_state 42 | meta_lab.py:18-21 |
| Calibration | Platt sigmoid, CalibratedClassifierCV(cv=3), train fold only | meta_lab.py:119-125 |
| Threshold grid | tau in {0.45, 0.50, 0.55, 0.60, 0.65, 0.70}; max train-fold PF with train retention >= 40%; ties to lower tau | meta_lab.py:22-23,128-139 |
| CPCV | 6 groups, k=2, purge 24h before, 40h after | meta_lab.py:25 |
| Control | labels permuted with seed 42, evaluated on true P&L | meta_lab.py:141-149 |

## Costs
As H1: 100 oz x [mean of entry and exit bucket spread + 0.5 x (entry + exit spread)] + $7 per lot, at the matrix median; p90 for gate 6 ([hm_runner.py:69-84](../../../originals/gann_bot_500/research/goldbot/prereg/hm_runner.py); [cost_matrix.py:124-128](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py)). The stored result used the partial tick matrix, which the prereg says biases toward a pass ([spec.md](../../../experiments/ml-meta-label/H-M/spec.md), "Known-unverified inputs").

## Tuning and selection
- Search: no hyperparameter search. Inside each split the threshold tau is picked from 6 values on the training fold.
- Configurations run (counted from the code/results): 1 pipeline plus 1 shuffled control. Ledger count (registry/trial_ledger.csv n_variants): 2 (GB-40 and GB-41). They agree.
- How the reported variant was chosen: fixed before the run. Thresholds are chosen on training folds only.
- Preregistered: yes, [spec.md](../../../experiments/ml-meta-label/H-M/spec.md) (copy of `HM_PREREGISTRATION.md`, commit 0a84ca3 in private history, not verifiable here), with design in [HM_DESIGN.md](../../../originals/gann_bot_500/research/goldbot/prereg/HM_DESIGN.md). Gates, all required: filtered OOS PF >= 1.40; uplift >= +0.15; old-era filtered PF >= 1.05; retention >= 40% and kept n >= 200; >= 11/15 splits positive; p90 filtered PF >= 1.15; shuffled control fails. A suspicion clause voids the run if overshoot_atr ranks first in importance and flips sign across eras.

## Results
"Pooled" PF is over all 15 test folds, so each trade appears up to 5 times (stored run: 1,935 kept rows from 468 distinct trades, [HM_run.json](../../../originals/gann_bot_500/research/goldbot/results/HM_run.json)).
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Partial matrix (stored), unfiltered -> filtered | 472 trades; 468 distinct kept | PF 1.236 -> 1.206, uplift -0.030; old 0.941, new 1.394; p90 1.123; 10/15 splits; FAIL | HM_run.json, [logs_partial/hm_runner.log](../../../audit/phaseC/logs_partial/hm_runner.log) |
| Partial matrix, shuffled control | 472 distinct kept | PF 1.236 -> 1.256, uplift +0.020 | same |
| Full matrix, recorded clock | 472; 468 distinct kept | PF 1.130 -> 1.102, uplift -0.028; old 0.888, new 1.251; p90 1.020; 7/15 splits; FAIL | [logs_recorded/hm_runner.log](../../../audit/phaseC/logs_recorded/hm_runner.log) |
| Full matrix, recorded, control | 472 | PF 1.130 -> 1.148, uplift +0.018 | same |
| Full matrix, true UTC | 481 (guard edited, see below); 480 distinct kept | PF 1.009 -> 0.999, uplift -0.010; old 0.814, new 1.114; p90 0.927; 8/15 splits; FAIL | [logs_true/hm_runner.log](../../../audit/phaseC/logs_true/hm_runner.log) |
| Full matrix, true UTC, control | 481 | PF 1.009 -> 1.006, uplift -0.003 | same |

Suspicion clause not triggered in any run (overshoot rank 8/8). In all three logs the printed importance order is exactly the feature-list order; the importance values themselves are not printed.

## Code and how to rerun
- Code: [hm_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hm_runner.py), [meta_lab.py](../../../originals/gann_bot_500/research/goldbot/prereg/meta_lab.py), [regime.py](../../../originals/gann_bot_500/research/goldbot/prereg/regime.py), [test_hm_pack.py](../../../originals/gann_bot_500/research/goldbot/prereg/test_hm_pack.py), [HM_DESIGN.md](../../../originals/gann_bot_500/research/goldbot/prereg/HM_DESIGN.md).
- Audit rerun stage: `goldbot_both` (full matrix, both clocks) and `goldbot_partial` (partial matrix) ([run_all.sh:32-33](../../../audit/tools/run_all.sh)). The true-clock sandbox changes the trade-count assert from 472 to 481; no rule changed ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 21).
- Public data enough? Yes: group `histdata_xau`; matrix and calendar are committed.

## Corrections from the release review
- The stored line "PF 1.236 -> 1.206 ... retention 99%" is the partial-matrix run. At full cost coverage the stored-clock figure is 1.130 -> 1.102 (logs_recorded/hm_runner.log). The README gives both but does not say which matrix the stored JSON used.
- "Retention 99%" overstates how much the filter keeps per split. It counts a trade as kept if any of its 5 test folds kept it (`kept_unique`, meta_lab.py:180,206-207). Per-split retention ranged from 65% to 100% (HM_run.json `splits`).
- The README gives PFs without n. The base set is 472 trades (481 on true UTC); 468 distinct trades were kept on the stored run.
- Features, model parameters and threshold rule are only in HM_DESIGN.md and meta_lab.py, which the README does not link.
- The earlier page cited an internal note as its source, which a reader cannot see.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | PF 1.236 -> 1.206, uplift -0.030, retention 99% |
| Rerun, recorded clock | Filtered 1.102, uplift -0.028 |
| Rerun, true UTC | 0.999, uplift -0.010 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Stored 1.206 reproduces on the partial matrix. Guard patched in the true sandbox, DECISIONS 21.

## Audit caveats
ML filter closed a second time.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HM_run.json](../../../originals/gann_bot_500/research/goldbot/results/HM_run.json)
