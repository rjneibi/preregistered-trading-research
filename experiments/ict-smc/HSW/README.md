# HSW

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Intraday sweep-reclaim at PDH/PDL has edge.

Family: ICT/SMC. Market: XAUUSD. Timeframe: intraday. Idea source: liquidity sweep literature, Osler kernel. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
An intraday "failed sweep" reversal on gold. Price trades through the previous day's low (or high) during London/New York hours, then closes back inside within 60 minutes; trade the reversal at the next M1 open. Sweep depth was the only searched parameter (three values), with two pinned exit families, a touch-only baseline and a mirror (continuation) arm as controls. It failed 6 of 8 gates.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 for signals and exits; ATR on H1; levels from UTC-midnight trading days ([spec.md](../../../experiments/ict-smc/HSW/spec.md), "Pinned universe").
- Data source and file(s): `research/data/xauusd_m1_histdata.csv` (data/manifest.csv group `histdata_xau`, public), read as UTC (originals/gann_bot_500/research/goldbot/config.yaml `data_tz: UTC`).
- Period: M1 2010-01-03 23:00 to 2026-06-19 17:57 as loaded; 4,248 trading days kept, 859 partial days (fewer than 300 M1 bars) dropped (audit/phaseC/logs_recorded/hsw_runner.log; [hsw_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hsw_runner.py) line 6).
- In-sample / out-of-sample: no train/test split. Era table OLD < 2021-06-19 00:00 UTC / NEW, crossed with a vol axis (day T-1 ATR% vs full-sample median 1.3424%) (spec.md "Era stratification"; HSW_run.json `vol_median_atr_pct`). PBO by CSCV, S=8 blocks, C(8,4)=70 combinations, 24h embargo (spec.md gate 5; HSW_run.json `pbo`).

## Rules
From spec.md "Signal" and "Exits", plus runner-build pins in hsw_runner.py lines 3-27. Long case; short is the mirror at PDH.
- Entry:
  - Penetration start: first M1 bar of day T with low < PDL, bar open 07:00-19:59 UTC.
  - Sweep extreme: lowest low from penetration start through the reclaim bar.
  - Reclaim: first M1 close > PDL, with reclaim-bar open no more than 60 minutes after penetration start. No reclaim: no signal, and the level is spent for the day.
  - Depth: (PDL - sweep extreme) >= d x ATR(H1,14), d in {0.05, 0.15, 0.30}.
  - Void if the opposite level was penetrated at or before the reclaim bar.
  - Enter at the open of the next M1 bar after the reclaim close. Max 1 trade per day; no re-entry.
- Exit (stop, target, time):
  - E1 (primary at d=0.15): SL = sweep extreme, widened to at least 0.5 x ATR(H1,14) from entry; TP = prior-day midpoint (PDH+PDL)/2. Hard close 24h after entry.
  - E2: TP +0.8 x ATR(H1,14), SL -2.4 x ATR(H1,14), 24h close.
  - Gap-open fills; an M1 bar touching both barriers counts as a stop (spec.md).
- Filters: anti-scalp guard, a signal is void in all arms if (midpoint - entry) < 0.5 x ATR at the actual entry open. Session window 07:00-19:59 UTC. Controls: touch baseline (fade any first penetration, no reclaim or depth, E2 exits) and mirror continuation (same entries, opposite direction, E2 exits). An Asia-window arm is named in the prereg as disclosure-only; only a count of Asia-window events (1,437) is stored (HSW_run.json `diag`).
- Position sizing: 1.0 lot per trade; results in net USD per lot (goldbot/backtest.py line 6).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Reference level | previous kept trading day high/low | spec.md; hsw_runner.py line 7 |
| ATR | ATR(H1, 14) Wilder, SMA seed, last completed H1 bar before penetration start | spec.md |
| Sweep depth d (only searched value) | 0.05, 0.15, 0.30 x ATR | spec.md; HSW_run.json `arms` |
| Reclaim window | 60 minutes | spec.md |
| Session window | 07:00-19:59 UTC | spec.md |
| E1 stop floor / target guard | 0.5 x ATR / 0.5 x ATR | spec.md |
| E2 TP / SL | 0.8 / 2.4 x ATR(H1,14) | spec.md |
| Time stop | 24 h | spec.md |
| DSR trials N | 6 | spec.md gate 4; HSW_run.json `dsr_primary.n_trials` |
| Era split / vol median | 2021-06-19 / 1.3424% | spec.md; HSW_run.json |

## Costs
Same cost model as HCRT: `goldbot.costs.CostModel` ([costs.py](../../../originals/gann_bot_500/research/goldbot/goldbot/costs.py); hsw_runner.py line 49) with [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) `costs`:
- Spread from [cost_matrix.json](../../../originals/gann_bot_500/fable-backtesting/cost_matrix.json) by UTC hour and weekday, falling back to the overall figure when a cell has fewer than 50 ticks. The matrix holds 1,986 ticks; overall median $0.72, p95 $0.79.
- Realistic (headline): half spread plus 5 points ($0.05) slippage per side, plus $7/lot round-trip commission. Breakeven about $0.89/oz (logs_recorded/hsw_runner.log line 4).
- Stress (gate 6): p95 spread plus 10 points slippage per side; stricter than the prereg's p90, disclosed at hsw_runner.py lines 22-24.
- Admin fee $5/lot/night (ESTIMATE) if a rollover is crossed.

## Tuning and selection
- Search: depth d {0.05, 0.15, 0.30} x exit {E1, E2} = 6 selectable trials (spec.md).
- Configurations run (counted from the code/results): 8 arms in HSW_run.json (6 selectable + mirror_E2 + touch_baseline_E2). Ledger count (registry/trial_ledger.csv, HSW): 1. The ledger is below the prereg's own DSR N=6.
- How the reported variant was chosen: E1 at d=0.15 was fixed as primary before the run. Displacement required clearing every gate; none did (HSW_run.json `displace_by: null`).
- Preregistered: yes ([HSW_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/HSW_PREREGISTRATION.md), freeze 2f7599a, copied as spec.md). Runner-build pins (listed in hsw_runner.py lines 3-27) include the p95 stress instead of p90. DSR at N=12 "disclosed as stress": Not recorded in the published files.

## Results
Gates (spec.md): n >= 100; PF >= 1.30; reclaim E2 PF minus touch-baseline PF >= +0.10; PF >= 1.00 in OLD and NEW and no mirror inversion; DSR >= 0.95 at N=6; PBO < 0.50; stress PF >= 1.15.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| E1 d=0.15 (primary), full period | 885 | PF 0.827, net -$42,087 per lot; DSR 0.014; stress PF 0.775 | [HSW_run.json](../../../originals/gann_bot_500/research/goldbot/results/HSW_run.json) |
| E1 d=0.15, OLD / NEW | n per era not recorded | PF 0.746 / 0.941 | HSW_run.json |
| E1 d=0.05 / d=0.30 | 1,181 / 605 | PF 0.747 / 0.935 | HSW_run.json |
| E2 d=0.05 / 0.15 / 0.30 | 1,181 / 885 / 605 | PF 0.626 / 0.634 / 0.718 | HSW_run.json |
| Touch baseline (E2) | 1,759 | PF 0.638; uplift of reclaim = -0.004 (needed +0.10) | HSW_run.json |
| Mirror continuation (E2) | 885 | PF 0.716, above the reversal arm's 0.634: inversion, gate 3 fails | HSW_run.json |
| PBO over 6 columns | 70 combinations | 0.000 (passes; every column loses) | HSW_run.json `pbo` |
| 2x2 era x vol, E1 primary | 348 / 301 / 117 / 119 | PF 0.69 / 0.79 / 0.81 / 1.00 (old-LO, old-HI, new-LO, new-HI) | HSW_run.json `table_2x2` |
| Audit rerun, recorded clock | 885 | 135 of 135 stored keys identical | [goldbot_compare.json](../../../audit/phaseC/goldbot_compare.json) `HSW_run.json` |
| Audit rerun, true UTC clock, primary | 841 | PF 0.854, DSR 0.014, PBO 0.029; still fails | goldbot_compare.json `true` (third value) |

## Code and how to rerun
- Code: [hsw_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hsw_runner.py), synthetic tests [test_hsw_pack.py](../../../originals/gann_bot_500/research/goldbot/prereg/test_hsw_pack.py), shared modules [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py), [dsr.py](../../../originals/gann_bot_500/research/goldbot/goldbot/dsr.py), [costs.py](../../../originals/gann_bot_500/research/goldbot/goldbot/costs.py). Audit driver [run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh).
- Audit rerun stage: `goldbot_both` (both clocks), then `c_compare_goldbot` (audit/tools/run_all.sh).
- Public data enough? Yes. Needs manifest group `histdata_xau` (public) and the shipped cost matrix. Not in audit/tools/stages_broker.txt.

## Corrections from the release review
- README "Timeframe: intraday" is vague. Signals and exits are on M1, ATR on H1, levels on D1 (spec.md).
- README "Data: ... 2015-2026" is wrong. The runner uses the full HistData file, 2010-01-03 to 2026-06-19 (spec.md; logs_recorded/hsw_runner.log).
- README "Splits: old 2015-2021 / new 2021-2026; 15 purged combinatorial splits" is wrong. OLD is everything before 2021-06-19. PBO is CSCV with 70 combinations (HSW_run.json `pbo.n_combinations`).
- README "Costs: per-year x UTC-hour Dukascopy spread matrix, k_slip 0.5" is wrong for this runner. It uses goldbot/costs.py: a 1,986-tick matrix (median $0.72), plus 5 points slippage per side and $7/lot (costs.py; config.yaml).
- README "Gates: as HCRT" is misleading. HSW's gate 2 compares against a touch baseline, DSR uses N=6, and PBO covers 6 columns (spec.md "Gates").
- README "Variants counted in the ledger: 1" understates the search. The prereg sets N=6 selectable trials; 8 arms were run (HSW_run.json).
- README "Rerun, true UTC | PF 0.854" gives no n. The true-UTC primary has n=841 (goldbot_compare.json).
- README caveat names the author by first name; house style is "the author". The fact itself is correct: the author predicted PASS, the AI model predicted FAIL (spec.md "Registered predictions").
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link hsw_runner.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | n=885 PF 0.827 |
| Rerun, recorded clock | n=885 PF 0.827 |
| Rerun, true UTC | PF 0.854 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Rises slightly, still fails.

## Audit caveats
First blind disagreement: Rashed PASS, Claude FAIL.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HSW_run.json](../../../originals/gann_bot_500/research/goldbot/results/HSW_run.json)
