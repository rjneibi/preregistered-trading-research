# HCRT

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Raw CRT-D1 sweep has edge.

Family: ICT/SMC. Market: XAUUSD. Timeframe: D1. Idea source: ICT Candle Range Theory. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A one-pattern falsification test of ICT "candle range theory" on daily gold. Day T-1 sweeps one side of day T-2's range and closes back inside it; trade the reversion at day T's open, in the EMA200 direction. One primary exit (E1) and one secondary exit (E2) were pinned in advance, with a trend-only baseline and a mirror (breakout) arm as controls. It failed 6 of 8 gates.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): HistData M1 resampled to D1 on UTC-midnight days; exits resolved on M1 ([spec.md](../../../experiments/ict-smc/HCRT/spec.md), "Pinned universe"). D1 rows with fewer than 300 M1 bars are dropped as non-trading days (859 dropped) ([hcrt_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hcrt_runner.py) lines 5-6; audit/phaseC/logs_recorded/hcrt_runner.log).
- Data source and file(s): `research/data/xauusd_m1_histdata.csv` (data/manifest.csv group `histdata_xau`, public; "stamps as HistData gave them"). Path set in originals/gann_bot_500/research/goldbot/config.yaml `data.m1_path`, read as UTC (`data_tz: UTC`).
- Period: M1 from 2010-01-03 23:00 to 2026-06-19 17:57 as loaded; 4,248 D1 trading days (audit/phaseC/logs_recorded/hcrt_runner.log). Signals need 200 completed trading days of EMA warm-up (hcrt_runner.py line 12).
- In-sample / out-of-sample: no train/test split; nothing was tuned. Era table: OLD < 2021-06-19 00:00 UTC, NEW on or after (hcrt_runner.py `ERA_SPLIT`), crossed with a volatility axis (day T-1 ATR% above or below the full-sample median, 1.3424%). PBO uses CSCV with S=8 contiguous blocks, C(8,4)=70 combinations, 24h embargo (spec.md "Harness prerequisite"; hcrt_runner.py line 259).

## Rules
From spec.md "Signal" and "Exits", and hcrt_runner.py `find_signals`, `run_e1`, `run_e2`.
- Entry: C1 = day T-2, range CRH/CRL. Long setup: low(C2) < CRL, close(C2) inside [CRL, CRH], high(C2) <= CRH (day T-1). Short is the mirror; a C2 that breaks both sides gives no signal. Enter at market at day T's first M1 bar at or after 00:00 UTC, in the reversion direction. Max 1 trade per day.
- Exit (stop, target, time):
  - E1 (primary): TP = opposite range boundary (long: CRH); SL = C2's sweep extreme; hard close at the next 00:00 UTC (24h). Events where the open gaps at or through a barrier are skipped (10 filtered, 16 raw) (HCRT_run.json `degenerate_e1`).
  - E2 (secondary): TP +0.8 x ATR14(D1, T-1), SL -2.4 x ATR14, same 24h close. E2 could replace E1 only if it cleared every gate and beat E1's PF by 0.05 in both eras (spec.md).
  - Fills: gap-open fills; an M1 bar that touches both barriers counts as a stop (spec.md).
- Filters: long only if close(C2) > EMA200 of D1 closes through T-1; short only if below. Control arms: bias-only (every day in the EMA200 direction, E2 exits) and mirror continuation (same signal days, opposite direction, E2 exits). Raw (unfiltered) arms are disclosure only.
- Position sizing: 1.0 lot per trade; results in net USD per 1.0 lot (originals/gann_bot_500/research/goldbot/goldbot/backtest.py line 6; goldbot/costs.py line 6).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Trend filter | EMA200 of D1 closes (`ewm(span=200, adjust=False)`) | hcrt_runner.py `find_signals` |
| EMA warm-up | 200 trading days | hcrt_runner.py `EMA_WARMUP` |
| ATR | Wilder ATR(14) on D1, at T-1 | hcrt_runner.py; spec.md |
| E2 TP / SL | 0.8 / 2.4 x ATR | hcrt_runner.py `K_TP, K_SL` |
| Time stop | 24 h | hcrt_runner.py `TIME_STOP_H` |
| Minimum M1 bars per D1 day | 300 | hcrt_runner.py `MIN_D1_BARS` |
| Era split | 2021-06-19 00:00 UTC | hcrt_runner.py `ERA_SPLIT` |
| Vol axis | D1 ATR% vs full-sample median (1.3424%) | HCRT_run.json `vol_median_atr_pct` |
| DSR trials N | 2 (E1, E2) | spec.md; HCRT_run.json `dsr_E1.n_trials` |
| PBO | CSCV S=8, 70 combinations, 4 columns, embargo 24h | spec.md; HCRT_run.json `pbo` |

## Costs
The runner uses `goldbot.costs.CostModel` ([costs.py](../../../originals/gann_bot_500/research/goldbot/goldbot/costs.py)) with [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) `costs`:
- Spread: median from [cost_matrix.json](../../../originals/gann_bot_500/fable-backtesting/cost_matrix.json), looked up by UTC hour and weekday; cells with fewer than 50 ticks fall back to the overall figure. The matrix holds 1,986 ticks from two files (2015 and one day of 2026); overall median $0.72, p95 $0.79 (cost_matrix.json `overall`). costs.py lines 18-20 say the realistic regime is in effect the overall median everywhere.
- Realistic (headline): per side, half the spread plus 5 points ($0.05/oz) slippage; plus $7 per lot round-trip commission. Printed breakeven about $0.89/oz per round trip (logs_recorded/hcrt_runner.log line 4).
- Stress (gate 6): p95 spread plus 10 points slippage per side. This is stricter than the prereg's p90 wording, disclosed in hcrt_runner.py lines 14-16.
- Admin fee $5/lot/night if a position crosses a rollover (config.yaml, marked ESTIMATE); E1/E2 close within 24 h.

## Tuning and selection
- Search: none. One pinned signal, two pinned exits. PBO matrix = {E1, E2} x {filtered, raw} = 4 columns; plus 2 control arms (spec.md "Trial matrix").
- Configurations run (counted from the code/results): 6 arms in HCRT_run.json `arms` (E1/E2 filtered, E1/E2 raw, mirror_E2, bias_only_E2); 2 selectable. Ledger count (registry/trial_ledger.csv, HCRT): 1. The ledger is below the prereg's own DSR N=2.
- How the reported variant was chosen: E1 was fixed as primary before the run. E2 did not displace it (HCRT_run.json `displace: false`).
- Preregistered: yes ([HCRT_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/HCRT_PREREGISTRATION.md), freeze c5e042d, copied as spec.md). Runner-build pins added before results are listed in hcrt_runner.py lines 3-18 (partial-day drop, warm-up, degenerate-event skip, p95 instead of p90 stress). DSR at N=10 "disclosed as stress" in the prereg: Not recorded in the published files.

## Results
Gates (spec.md): n >= 100; PF >= 1.30; CRT-filtered PF minus bias-only PF >= +0.10 (E2 exits); PF >= 1.00 in OLD and NEW and no mirror inversion; DSR >= 0.95; PBO < 0.50; stress PF >= 1.15.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| E1 filtered, full period (primary) | 599 | PF 0.860, net -$46,795 per lot; DSR 0.153; PBO 0.557 (70 combinations) | [HCRT_run.json](../../../originals/gann_bot_500/research/goldbot/results/HCRT_run.json) |
| E1 filtered, OLD / NEW era | n per era not recorded | PF 0.891 / 0.832 | HCRT_run.json `arms.E1_filtered` |
| E1 filtered, p95 stress | 599 | PF 0.833 | HCRT_run.json |
| E2 filtered | 609 | PF 0.874; DSR 0.165 | HCRT_run.json |
| Bias-only baseline (E2 exits) | 4,047 | PF 0.923; uplift of E2 filtered = -0.049 (needed +0.10) | HCRT_run.json; spec.md summary |
| Mirror continuation (E2 exits) | 609 | PF 0.796 (below reversion, so no inversion: the one gate passed besides power) | HCRT_run.json |
| E1 / E2 raw (unfiltered) | 1,242 / 1,258 | PF 0.839 / 0.851 | HCRT_run.json |
| 2x2 era x vol cells, E1 | 222 / 177 / 96 / 104 | PF 0.84 / 0.93 / 1.21 / 0.73 (old-LO, old-HI, new-LO, new-HI). INSUFFICIENT SAMPLE for the two new cells | HCRT_run.json `table_2x2` |
| Audit rerun, recorded clock | 599 | 96 of 96 stored keys identical | [goldbot_compare.json](../../../audit/phaseC/goldbot_compare.json) `HCRT_run.json` |
| Audit rerun, true UTC clock, E1 filtered | 605 | PF 0.913, DSR 0.278, PBO 0.714; still fails | goldbot_compare.json `true` (third value) |

## Code and how to rerun
- Code: [hcrt_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hcrt_runner.py) (run from `research/goldbot/prereg/`), [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py), [dsr.py](../../../originals/gann_bot_500/research/goldbot/goldbot/dsr.py), [costs.py](../../../originals/gann_bot_500/research/goldbot/goldbot/costs.py), [data.py](../../../originals/gann_bot_500/research/goldbot/goldbot/data.py). Audit driver [run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh), comparison [compare_goldbot.py](../../../audit/phaseC/compare_goldbot.py).
- Audit rerun stage: `goldbot_both` (both clocks), then `c_compare_goldbot` (audit/tools/run_all.sh).
- Public data enough? Yes. Needs manifest group `histdata_xau` (public) and the cost matrix file shipped in originals. `goldbot_both` is not in audit/tools/stages_broker.txt.

## Corrections from the release review
- README "Data: ... 2015-2026" is wrong. The runner loads the full HistData M1 file, 2010-01-03 to 2026-06-19, with no 2015 cut (spec.md "Pinned universe"; logs_recorded/hcrt_runner.log).
- README "Splits: old 2015-2021 / new 2021-2026; 15 purged combinatorial splits" is wrong. OLD is everything before 2021-06-19 (no 2015 start). PBO is CSCV with S=8 and C(8,4)=70 combinations (hcrt_runner.py line 259; HCRT_run.json `pbo.n_combinations: 70`). "15 splits" is the goldbot config's CPCV (config.yaml `cpcv`), not used here.
- README "Costs: per-year x UTC-hour Dukascopy spread matrix, k_slip 0.5 x spread per side" is wrong for this runner. It uses goldbot/costs.py: a UTC-hour x weekday matrix built from 1,986 ticks (overall median $0.72), in effect a flat $0.72 spread, plus 5 points ($0.05) slippage per side and $7/lot (costs.py lines 18-20, 96-107; config.yaml `slippage_pts`).
- README gate "p95 stress" is right for the code but the prereg pinned p90; the switch to p95 is a disclosed runner pin (hcrt_runner.py lines 14-16). The README does not say so.
- README "Variants counted in the ledger: 1" understates the search. The prereg sets DSR N=2 and a 4-column PBO matrix (spec.md); 6 arms were run (HCRT_run.json).
- README "Rerun, true UTC | PF 0.914" is wrong. The true-UTC E1 PF is 0.913 on n=605 (goldbot_compare.json `arms.E1_filtered.pf_real` 0.9134). 0.914 is another experiment's figure (review 02_truth M1). The README also gives no n for it.
- README does not state that HistData stamps were read as UTC in the stored run (config.yaml `data_tz: UTC`), which is why the true-UTC rerun exists.
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link hcrt_runner.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | n=599 PF 0.86, DSR and PBO gates FAIL |
| Rerun, recorded clock | n=599 PF 0.86 |
| Rerun, true UTC | n=605 PF 0.913 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Rises on true UTC, still fails.

## Audit caveats
Full DSR/PBO applied. FVG, QT, SMT inherit the negative prior.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HCRT_run.json](../../../originals/gann_bot_500/research/goldbot/results/HCRT_run.json)
