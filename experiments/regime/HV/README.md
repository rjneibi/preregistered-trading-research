# HV

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Volatility explains the era boundary.

Family: regime. Market: XAUUSD. Timeframe: H1+H4. Idea source: literature pass, ERA_MECHANISM_RESEARCH. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
HV asked whether absolute volatility explains why the goldbot "final" breakout did well after 2021 and not before. The primary gate V switched trades ON when the trade's ATR / entry price was above the median daily ATR% of the whole 2010-2026 M1 history. A secondary gate Y used the 90-day correlation of gold returns with changes in the 10-year real yield. Both ran on the same 472 base trades. No threshold was searched.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): base trades from the H1 + H4 strategy; ATR on H1; gate series on daily bars ([hv_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hv_runner.py) lines 66-73).
- Data source and file(s): base trades read from [results/verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv) (hv_runner.py line 63). HistData XAUUSD M1 for the ATR% median (line 66; [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7). Y fetches FRED series DFII10 live over the network at run time (hv_runner.py lines 90-91). DFII10 is not in [data/manifest.csv](../../../data/manifest.csv).
- Period: trades 2015-06-19 to the end of the M1 file (inherited from the H1/H2 verdict run, [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) lines 41-43). The V median uses the whole M1 history, 5,105 days in the recorded-clock rerun ([logs_recorded/hv_runner.log](../../../audit/phaseC/logs_recorded/hv_runner.log)).
- In-sample / out-of-sample: none. Results are split by era: old 2015-06-19 to 2021-06-18, new from 2021-06-19 (run_verdict.py lines 41-43).

## Rules
- Entry: the base trades of the goldbot "final" variant, unchanged (R3/S3 = PP +/- (H - L) of the prior day; H1 close beyond a live level with H1 and H4 arms agreeing; H1 closes 12-20 UTC; skip Monday; 10-H4-close dead-level check; 1 trade per direction per day; 24 h re-entry block) ([events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py) `generate_events_final`; config.yaml lines 9-15).
- Exit (stop, target, time): TP 0.8 x ATR, SL 2.4 x ATR, 24 h time stop, bail overlay (half at -1.2 ATR in high vol; all at -1.0 ATR after 8 h in low vol) (config.yaml lines 20-35).
- Filters: V ON when trade ATR / entry price > median daily ATR%. Daily ATR% = H1 Wilder ATR(14) of the last H1 bar before the day opens, divided by the day's open (hv_runner.py lines 68-79). Y ON when the rolling 90-day correlation of daily gold returns with daily change in DFII10, lagged one day, is > -0.30 (lines 97-105).
- Position sizing: 1.0 lot per trade ($100 per $1 move, [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py) line 35). Not restated in the HV files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | Wilder 14 on H1 | hv_runner.py line 68 |
| V threshold | median of daily ATR% over full M1 history: 0.2468% stored | [HV_run.json](../../../originals/gann_bot_500/research/goldbot/results/HV_run.json) `v_median` |
| Y correlation window | 90 days, lagged 1 day | hv_runner.py line 101 |
| Y threshold | corr > -0.30 | hv_runner.py line 104; [spec.md](../../../experiments/regime/HV/spec.md) lines 26-29 |
| Base exits | TP 0.8 ATR, SL 2.4 ATR, 24 h, bail 1.2 / 8 h-1.0 | config.yaml lines 22-30 |

## Costs
Inherited from the base trades: per-year x UTC-hour median spread from the Dukascopy tick matrix, slippage 0.5 x spread per side, $7 per lot round trip; p90 spreads for the stress gate ([run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) lines 83-86, 114-119; [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py) `trade_cost_usd`). HV reads the `net_med` and `net_p90` columns (hv_runner.py lines 39-45).

## Tuning and selection
- Search: none. One primary indicator (V) and one secondary (Y), each with one pinned threshold (spec.md lines 20-31).
- Configurations run (counted from the code/results): 2 gates (V, Y). Ledger count (registry/trial_ledger.csv n_variants): 1. The ledger does not count the secondary Y.
- How the reported variant was chosen: no choice. V is the primary. Y could replace V only if it passed every gate and beat V's ON PF by 0.05 in both eras (spec.md lines 30-31; hv_runner.py lines 110-115). It did not.
- Preregistered: yes. [spec.md](../../../experiments/regime/HV/spec.md), copied from [HV_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/HV_PREREGISTRATION.md), frozen 2026-07-07. Gates: ON PF >= 1.30 with n >= 150; OFF PF <= 1.05; new-era ON minus OFF PF >= +0.20 and old-era ON >= OFF; p90 ON PF >= 1.15 (spec.md lines 33-41). One implementation note: the prereg says the median is over "2010-2026"; the code uses whatever the M1 file holds. No other deviation found.

## Results
Every era slice has fewer than 100 trades or sits just above it; slices under 100 are INSUFFICIENT SAMPLE.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored V, ON old era | 68 | PF 0.752 (INSUFFICIENT SAMPLE) | [HV_run.json](../../../originals/gann_bot_500/research/goldbot/results/HV_run.json) |
| Stored V, ON new era | 79 | PF 1.413 (INSUFFICIENT SAMPLE) | HV_run.json |
| Stored V, OFF old era | 199 | PF 1.037 | HV_run.json |
| Stored V, OFF new era | 126 | PF 1.074 | HV_run.json |
| Stored V, ON full / OFF full | 147 / 325 | PF 1.187 (p90 1.119) / 1.058 | [logs_recorded/hv_runner.log](../../../audit/phaseC/logs_recorded/hv_runner.log) (HV_run.json has no full-period PF) |
| Stored V gates | - | all 4 FAIL | HV_run.json |
| Stored Y, ON full | 165 | PF 1.148; all 4 gates FAIL; does not displace V | HV_run.json |
| Audit rerun, recorded clock | same as stored | identical | logs_recorded/hv_runner.log |
| Audit rerun, true UTC, V ON full / OFF full | 143 / 338 | PF 1.166 (p90 1.102) / 0.845; ON old n=64 PF 0.879, ON new n=79 PF 1.288; gates V2 and V3 pass, V1 and V4 fail: FAIL | [logs_true/hv_runner.log](../../../audit/phaseC/logs_true/hv_runner.log) |
| Audit rerun, true UTC, Y ON full | 167 | PF 0.995; FAIL | logs_true/hv_runner.log |

## Code and how to rerun
- Code: [hv_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hv_runner.py); base trades from [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py); [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml). Audit driver: [run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh).
- Audit rerun stage: `goldbot_both` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Partly. V needs manifest group `histdata_xau` only. Y needs a live download of FRED DFII10, which is not in the manifest and not hash-pinned, so a later fetch may differ.

## Corrections from the release review
- README "Rules: Vol gate." is too vague to reproduce. The rule is: ON when trade ATR / entry price > the median daily ATR% of the full M1 history (0.2468% stored), with a secondary real-yield correlation gate at -0.30 (hv_runner.py lines 74-79, 101-105).
- README "Data: HistData M1 + Dukascopy tick cost matrix 2015-2026" is incomplete. The V median uses the full 2010+ M1 history, and Y uses FRED DFII10 fetched live at run time, which is not in data/manifest.csv (hv_runner.py lines 66, 90).
- README "Variants counted in the ledger: 1" undercounts. Two pre-registered gates (V and Y) were computed and gated (HV_run.json `v` and `y`).
- README results give no n. ON n=147 and OFF n=325 (stored); era slices of 68 and 79 are INSUFFICIENT SAMPLE.
- README does not say the base strategy or its exits. They are the goldbot "final" rules in config.yaml lines 9-40.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All 4 gates FAIL |
| Rerun, recorded clock | All gates fail |
| Rerun, true UTC | V2 and V3 true, still FAIL: on old 0.879, new 1.288 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Gate result differs by clock, verdict does not.

## Audit caveats
Cycle 3 later showed no significant performance break exists, so HV searched for a mechanism behind an untested premise.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HV_run.json](../../../originals/gann_bot_500/research/goldbot/results/HV_run.json)
