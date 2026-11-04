# H2

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** ATR percentile gate rescues the old era.

Family: regime filter. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The base strategy is the goldbot "final" R3/S3 breakout (the H1 experiment). H2 added one filter: trade only when yesterday's daily ATR(14)/close sits at or above the 50th percentile of the prior 252 days. The claim was that this volatility gate would rescue the weak 2015-2021 era. Thresholds 0.40 and 0.60 were run as a plateau check.

## Instruments and data
- Instruments: XAUUSD (spot gold).
- Timeframe(s): M1 bars resampled to H1, H4 and UTC-midnight D1 ([run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) lines 99-103). Exits are simulated on M1.
- Data source and file(s): HistData XAUUSD M1, `research/data/xauusd_m1_histdata.csv` ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7). Costs from the Dukascopy tick spread matrix [results/cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json) (run_verdict.py line 40).
- Period: events from 2015-06-19 to the end of the M1 file (run_verdict.py lines 41-43). The manifest gives the HistData range as 2010 to 2026-06 ([data/MANIFEST.md](../../../data/MANIFEST.md)). The ATR percentile is warmed up on data from 2010 onward ([spec.md](../../../experiments/regime-filter/H2/spec.md) line 69).
- In-sample / out-of-sample: no IS/OOS split. Two eras: old 2015-06-19 to 2021-06-18, new 2021-06-19 to data end (run_verdict.py lines 41-43). Plus 15 combinatorial purged splits, 6 groups, 2 test groups, 24 h label horizon, 24 h embargo, 40 h feature lookback (run_verdict.py lines 54-55).

## Rules
- Entry (base "final" variant, [events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py) `generate_events_final`): daily levels R3 = PP + (H - L), S3 = PP - (H - L) from the previous trading day ([pivots.py](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py) lines 6-12). Buy when an H1 close is above a live R3, sell when below a live S3. The entry fires when both arms agree: an H1 close at an hour divisible by 4 counts as both H1 and H4. Only H1 closes from 12 to 20 UTC count. Mondays are skipped. A level is "dead" if any of the last 10 H4 closes already breached it. One trade per direction per day, and a 24 h re-entry block ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 9-15).
- Exit (stop, target, time): TP 0.8 x ATR, SL 2.4 x ATR, time stop 24 h. Bail overlay: in high-vol regime (ATR above its 90-day median) close half at the first M1 close 1.2 x ATR adverse; in low-vol regime close all after 8 h if an M1 close is 1.0 x ATR adverse. Fill mode `gap_open` (config.yaml lines 20-35; run_verdict.py lines 104-109).
- Filters: H2 gate. Relative ATR = ATR(14)/close on UTC-midnight daily bars. Score = fraction of the 252 strictly prior completed days with a lower value. A signal on day D uses day D-1's score. Trade only if score >= 0.50 ([spec.md](../../../experiments/regime-filter/H2/spec.md) lines 50-58; [prereg/regime.py](../../../originals/gann_bot_500/research/goldbot/prereg/regime.py)).
- Position sizing: 1.0 lot per trade, $100 per $1 move ([triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py) line 35). Results are in dollars per lot.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Pivot levels | R3/S3 = PP +/- (H - L), previous day, UTC-00 day cut | pivots.py lines 6-12; config.yaml line 18 |
| Session (H1 closes) | 12-20 UTC inclusive | config.yaml line 11 |
| Skip weekday | Monday | config.yaml line 12 |
| Dead-level check | last 10 H4 closes | config.yaml line 13 |
| Re-entry block | 24 h | config.yaml line 14 |
| ATR (exits) | Wilder 14 on H1, regime median over 2,160 H1 bars, min 200 | config.yaml lines 31-35 |
| TP / SL / time stop | 0.8 x ATR / 2.4 x ATR / 24 h | config.yaml lines 23-25 |
| Bail | hivol half at -1.2 ATR; lovol all at -1.0 ATR after 8 h | config.yaml lines 26-30 |
| H2 indicator | ATR(14)/close, daily | spec.md line 51 |
| H2 percentile window | 252 prior days | spec.md lines 54-57 |
| H2 threshold | 0.50 primary; 0.40 and 0.60 plateau | spec.md lines 58, 72 |

## Costs
Per trade, per lot: 100 oz x ((entry spread + exit spread)/2 + 0.5 x (entry spread + exit spread)) + $7 commission ([cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py) `trade_cost_usd`). Spreads are the per-year x UTC-hour median from the tick matrix; a p90 version is the stress check (run_verdict.py lines 83-86). k_slip = 0.5 is an assumption, flagged in the prereg (spec.md lines 26-30). A flat $20 column is printed for comparison only (run_verdict.py line 120). Mean cost per trade in the recorded-clock rerun: $80.87 ([logs_recorded/run_verdict.log](../../../audit/phaseC/logs_recorded/run_verdict.log)).

## Tuning and selection
- Search: threshold 0.40, 0.50, 0.60. Nothing else varied.
- Configurations run (counted from the code/results): 3 (run_verdict.py, H2_050.json and H2_plateau.json). Ledger count (registry/trial_ledger.csv n_variants): 3. They agree.
- How the reported variant was chosen: not chosen. 0.50 was fixed before any result as the primary threshold; 0.40 and 0.60 serve only as a plateau check (spec.md lines 58, 72-74).
- Preregistered: yes. [spec.md](../../../experiments/regime-filter/H2/spec.md), copied from [PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md), commit 35deedc per the registry. Gates: filtered PF >= 1.25; >= 11 of 15 splits positive; p90 PF >= 1.10; old-era filtered-in PF minus filtered-out PF >= 0.15 with filtered-in n >= 40; filtered n >= 150 and plateau (0.40 and 0.60 each PF >= 1.10 and within 0.15 of the primary) (spec.md lines 72-85). No deviation found.

## Results
All PFs are at matrix median costs unless stated. Old-era and new-era rows each have fewer than 100 trades: INSUFFICIENT SAMPLE.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored, 0.50, full | 193 | PF 1.174, 9 of 15 splits positive, p90 PF 1.103 | [H2_050.json](../../../originals/gann_bot_500/research/goldbot/results/H2_050.json) |
| Stored, 0.50, old era | 96 | PF 0.838 (INSUFFICIENT SAMPLE) | H2_050.json |
| Stored, 0.50, new era | 97 | PF 1.325 (INSUFFICIENT SAMPLE) | H2_050.json |
| Stored, mechanism control (old era) | in 96 / out 171 | PF in 0.838 vs out 0.952, gap -0.113 (gate needs +0.15) | [H2_mechanism.json](../../../originals/gann_bot_500/research/goldbot/results/H2_mechanism.json) |
| Stored, 0.40 | 229 | PF 1.252, p90 1.173 | [H2_plateau.json](../../../originals/gann_bot_500/research/goldbot/results/H2_plateau.json) |
| Stored, 0.60 | 157 | PF 1.126, p90 1.057 | H2_plateau.json |
| Stored gate outcome | - | FAIL on gates 1, 2, 4; pass on 3 and 5 | [logs_recorded/run_verdict.log](../../../audit/phaseC/logs_recorded/run_verdict.log) |
| Audit rerun, recorded clock | 193 | PF 1.17, identical to stored | logs_recorded/run_verdict.log |
| Audit rerun, true UTC clock | 200 | PF 1.03, old n=97 PF 0.66, new n=103 PF 1.23, p90 0.97, plateau 1.08/0.94 FAIL, mechanism gap -0.401; all 5 gates fail | [logs_true/run_verdict.log](../../../audit/phaseC/logs_true/run_verdict.log) |
| Audit rerun, partial cost matrix (commit 977fff5) | 193 | PF 1.25, 11 of 15, p90 1.20, gap -0.137; fails only the mechanism gate | [logs_partial/run_verdict.log](../../../audit/phaseC/logs_partial/run_verdict.log) |
| Base H1 (unfiltered), recorded clock | 472 | PF 1.13, old n=267 PF 0.90 | logs_recorded/run_verdict.log |

## Code and how to rerun
- Code: [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py), [prereg/regime.py](../../../originals/gann_bot_500/research/goldbot/prereg/regime.py), [events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py), [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py), [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py), [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml). Audit scripts: [run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh), [run_goldbot_partial.sh](../../../audit/phaseC/run_goldbot_partial.sh).
- Audit rerun stage: `goldbot_both` (recorded and true clock) and `goldbot_partial` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. Needs manifest group `histdata_xau`. The cost matrix JSON is committed. Neither stage is in [stages_broker.txt](../../../audit/tools/stages_broker.txt).

## Corrections from the release review
- README "Gates: PF>=1.25, >=11/15, p90>=1.10, mechanism gap>=0.15" is incomplete. The prereg also requires filtered-in old-era n >= 40, filtered total n >= 150, and the 0.40/0.60 plateau (PF >= 1.10 and within 0.15) (spec.md lines 72-85).
- README "Rules: Trade only if trailing 252d percentile >= 0.50" does not name the indicator or the base. The indicator is daily ATR(14)/close, scored with the previous day's value. The base is the H1 "final" R3/S3 breakout with the exits listed above (spec.md lines 50-58; config.yaml lines 9-40).
- README "Data: ... 2015-2026" hides that the percentile is warmed up from 2010 (spec.md line 69).
- README gives no n for the true-UTC rerun eras. Old-era n=97 and new-era n=103 (logs_true/run_verdict.log). The old-era figure is INSUFFICIENT SAMPLE.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | PF 1.17, p90 1.10, 9/15, n=193, gap -0.113 |
| Rerun, recorded clock | n=193 PF 1.174 |
| Rerun, true UTC | n=200 PF 1.035, old 0.658 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Partial-matrix claim PF 1.25 also reproduces.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/H2_050.json](../../../originals/gann_bot_500/research/goldbot/results/H2_050.json)
