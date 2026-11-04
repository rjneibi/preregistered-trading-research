# H-B

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Arm B solo stands.

Family: pivot/breakout. Market: XAUUSD. Timeframe: H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
H-B asks whether "arm B", the FINAL_v3 H4 breakout, has an edge on its own at measured costs. The rule was not changed: an H4 close beyond the prior UTC day's R3/S3 at 12, 16 or 20 UTC, no Mondays, one trade a day, TP 1.4 x ATR, SL 2.1 x ATR, 24 hours. The author had already seen this arm's headline inside the H-P run, so the prereg raised the gates. There was a preliminary run on a partial cost matrix and a binding run on the full matrix.

## Instruments and data
- Instruments: XAUUSD, 1.0 lot per trade ([triple_barrier.py:22-23](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py)).
- Timeframe(s): M1 resampled to H1 (ATR), H4 (signal) and UTC D1 (pivots) ([hp_runner.py:50-54](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py)).
- Data source and file(s): HistData XAUUSD M1 ([config.yaml:5-7](../../../originals/gann_bot_500/research/goldbot/config.yaml); [data/manifest.csv](../../../data/manifest.csv) line 428). Cost matrix [results/cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json) from Dukascopy ticks.
- Period: 2015-06-19 to the end of the data, in two eras, old to 2021-06-18 and new from 2021-06-19 (`ERAS` imported by hp_runner.py; same as [run_verdict.py:41-43](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py)).
- In-sample / out-of-sample: no fit. Eras plus 15 purged CPCV splits (6 groups, 2 test, 24h horizon and embargo, 40h feature lookback) ([hb_runner.py:51-61](../../../originals/gann_bot_500/research/goldbot/prereg/hb_runner.py)). Both eras had been used to design FINAL_v3, and the pooled result had been seen before the prereg ([spec.md](../../../experiments/pivot-breakout/H-B/spec.md), "Taint disclosure").

## Rules
- Entry: R3 = PP + (H - L), S3 = PP - (H - L) of the prior UTC day ([pivots.py:1-14](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py)). Any H4 close above a live R3 is a BUY, below a live S3 a SELL ([events.py:119-170](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py)). Only events at 12, 16, 20 UTC are kept, and only the first of each UTC day ([hp_runner.py:55-57](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py)). Entry at the open of the first M1 bar at or after the close.
- Exit (stop, target, time): TP 1.4 x ATR, SL 2.1 x ATR, 24h time stop, no bail, `gap_open` fills, stop checked first in a bar ([hp_runner.py:58-59](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py); [triple_barrier.py:5-21](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py)).
- Filters: no Mondays; dead-level check over the last 10 H4 closes before 00:00 UTC; at least 50 H4 bars of history ([config.yaml:12-15](../../../originals/gann_bot_500/research/goldbot/config.yaml); [events.py:134-151](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py)).
- Position sizing: 1.0 lot per trade, fixed.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| R3 / S3 | PP ± 1.0 x prior UTC-day range | pivots.py:1-14 |
| ATR | Wilder ATR(14) on H1, last H1 bar closed before 00:00 UTC | hp_runner.py:54; events.py:40-48 |
| TP / SL / time | 1.4 / 2.1 x ATR / 24 h | hp_runner.py:58 |
| Session | H4 closes at 12, 16, 20 UTC | hp_runner.py:56 |
| Max trades | 1 per UTC day | hp_runner.py:57 |
| Dead check | 10 H4 closes | config.yaml:13 |
| CPCV | 6 groups, k=2, 15 splits | hb_runner.py:51-52 |

## Costs
Per trade, per lot: 100 oz x [mean of entry and exit bucket spread + 0.5 x (entry + exit spread)] + $7 commission. Median bucket for the main figure, p90 bucket for the stress gate ([cost_matrix.py:124-128](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py); [hb_runner.py:40-43](../../../originals/gann_bot_500/research/goldbot/prereg/hb_runner.py); [hp_runner.py:63-69](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py)). The preliminary run used a matrix with tick years 2015-2018 and 2026 only; the binding run had 2015-2026 ([HB_run_preliminary.json](../../../originals/gann_bot_500/research/goldbot/results/HB_run_preliminary.json), [HB_run_binding.json](../../../originals/gann_bot_500/research/goldbot/results/HB_run_binding.json), `matrix_years`).

## Tuning and selection
- Search: none. "zero parameters tuned here" ([spec.md](../../../experiments/pivot-breakout/H-B/spec.md)).
- Configurations run (counted from the code/results): 1 rule, run twice (preliminary and binding matrix). Ledger count (registry/trial_ledger.csv n_variants): 1, basis "minimum, see entry"; GB-47 maps to it. They agree for this entry. The geometry itself came from the FINAL_v3 search (see XAU-FINAL-V3).
- How the reported variant was chosen: the arm was picked after its result was seen inside H-P. The prereg discloses this and stiffens the gates.
- Preregistered: yes, [spec.md](../../../experiments/pivot-breakout/H-B/spec.md) (copy of `HB_PREREGISTRATION.md`, commit a734cd7 in private history, not verifiable here). Gates: PF >= 1.35; each era PF >= 1.00; >= 11/15 splits positive; p90 full PF >= 1.15 and old-era p90 PF >= 0.90; n >= 300. The binding run decides.

## Results
Dollar figures per 1 lot, matrix median costs unless stated.
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Preliminary (partial matrix), full | 432 | PF 1.459, old 1.012, new 1.837, p90 1.395, 12/15 splits; provisional PASS | [HB_run_preliminary.json](../../../originals/gann_bot_500/research/goldbot/results/HB_run_preliminary.json) |
| Binding, recorded clock, full | 432 | PF 1.376, net $43,681, win 66.0%; old 0.977, new 1.705; p90 1.309 (old 0.934); 12/15 splits; FAIL (era gate) | [HB_run_binding.json](../../../originals/gann_bot_500/research/goldbot/results/HB_run_binding.json), [logs_recorded/hb_runner.log](../../../audit/phaseC/logs_recorded/hb_runner.log) |
| Binding, true UTC, full | 436 | PF 1.040, net $5,638, win 62.4%; old 0.847, new 1.162; p90 0.989 (old 0.811); 9/15 splits; FAIL on 4 of 5 gates | [logs_true/hb_runner.log](../../../audit/phaseC/logs_true/hb_runner.log) |
| Flat 20-pt reference | 432 / 436 | PF 1.649 / 1.240 | same logs |

The per-era trade counts are not printed in the logs or JSON. Not recorded in the published files.

## Code and how to rerun
- Code: [hb_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hb_runner.py), [hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py) (`build_arm_b`), [events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py), [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py), [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py), [hb_binding_watcher.py](../../../originals/gann_bot_500/research/goldbot/prereg/hb_binding_watcher.py).
- Audit rerun stage: `goldbot_both` ([run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh) runs `hb_runner.py --tag binding` on both clocks). The preliminary run is not in the partial-matrix stage list ([run_goldbot_partial.sh](../../../audit/phaseC/run_goldbot_partial.sh)).
- Public data enough? Yes: group `histdata_xau`; the cost matrix is committed.

## Corrections from the release review
- "Rules: Arm B alone" does not define the rule. Arm B is FINAL_v3: H4 close beyond R3/S3 (PP ± range), 12/16/20 UTC, no Mondays, 1 a day, TP 1.4 / SL 2.1 x ATR, 24h, no bail, gap-open fills (hp_runner.py:55-59).
- Position sizing is not stated. It is 1 lot per trade.
- The preliminary run has no audit rerun; only the binding run was regenerated (run_goldbot_both.sh, run_goldbot_partial.sh).
- The README links only DECISIONS.log (not published) and HB_run_binding.json. The runner code and logs above are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Provisional PASS PF 1.459; binding FAIL PF 1.376, old 0.977 |
| Rerun, recorded clock | n=432 PF 1.376, old 0.977 |
| Rerun, true UTC | n=436 PF 1.040, old 0.847 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Binding run exact.

## Audit caveats
Third pass killed by confirmation at full cost coverage.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HB_run_binding.json](../../../originals/gann_bot_500/research/goldbot/results/HB_run_binding.json)
