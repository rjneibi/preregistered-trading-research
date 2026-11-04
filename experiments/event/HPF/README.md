# HPF

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-07-08. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Fading the Powell presser has edge.

Family: event. Market: XAUUSD. Timeframe: M1. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Whether fading the gold price move that follows the 14:00 ET FOMC statement, during the 14:30 ET press conference, made money after costs in the Powell era, and whether that held out of sample in 2023-2026. The idea comes from published work on Treasuries and equities; gold is the author's extension ([spec.md](../../../experiments/event/HPF/spec.md) lines 9-18). One primary config was gated; eleven others were run as family diagnostics.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): ticks around each event.
- Data source and file(s): Dukascopy decoded tick streams `fable-backtesting/download/xauusd-bi5-YYYY-MM.csv` (ms UTC, ask, bid) ([powell_lab.py](../../../originals/gann_bot_500/research/powell/powell_lab.py) lines 9-11). Event list: [powell_events_is.csv](../../../originals/gann_bot_500/research/powell/powell_events_is.csv).
- Period: scheduled FOMC press-conference meetings. Yellen 2015-2017 (control, n=12), Powell 2018-03 to 2026-04, one Warsh meeting 2026-06-17 reported without a gate (powell_lab.py lines 13-16; [spec.md](../../../experiments/event/HPF/spec.md) lines 41-45).
- In-sample / out-of-sample: IS = events before 2023-01-01 (45 measured, 2015-2022; months 2018-09 and 2020-09 missing). OOS = Powell meetings 2023-01-01 to 2026-04-29, locked until the freeze was committed (spec.md lines 33-45). The runner uses an end date of 2026-05-31 ([powell_verdict.py](../../../originals/gann_bot_500/research/powell/powell_verdict.py) line 23); no meeting falls in between. Excluded: unscheduled meetings 2019-10-04, 2020-03-03, 2020-03-15.

## Rules
- Entry: statement move = mid at 14:29:59 ET minus mid at 13:58:55 ET. Enter at the first tick at or after 14:30:00 ET (must be by 14:32). Fade = trade against the statement move; momentum = with it. Skip events whose |move| is below the threshold or is zero ([spec.md](../../../experiments/event/HPF/spec.md) lines 47-50; [powell_verdict.py](../../../originals/gann_bot_500/research/powell/powell_verdict.py) lines 36-44).
- Exit (stop, target, time): time exit only, at 15:30 or 16:00 ET. No stop, no target.
- Filters: |statement move| threshold $0, $3 or $6 per oz.
- Position sizing: 1 oz; results in $/oz ([powell_lab.py](../../../originals/gann_bot_500/research/powell/powell_lab.py) lines 156-161).
- Primary (only gated) config: fade_t0_1600ET = fade, no threshold, exit 16:00 ET.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Direction | fade, momentum | [spec.md](../../../experiments/event/HPF/spec.md) line 48 |
| Threshold on |statement move| | $0, $3, $6 per oz | spec.md line 49 |
| Exit time | 15:30 ET, 16:00 ET | spec.md line 49 |
| Statement-move window | mid(13:58:55) to mid(14:29:59) ET | spec.md line 50 |
| Entry time | first tick >= 14:30:00 ET, <= 14:32 | spec.md line 50 |
| Slippage levels | $0.00 / $0.10 / $0.30 per oz per side | [powell_lab.py](../../../originals/gann_bot_500/research/powell/powell_lab.py) line 67 |
| Permutation test | 1,000 sign-randomised replicates, 95th percentile, seed 20260708 | [powell_verdict.py](../../../originals/gann_bot_500/research/powell/powell_verdict.py) lines 28-31 |
| Min OOS events | 22 | powell_verdict.py line 27 |

## Costs
Real Dukascopy bid/ask at the actual tick timestamps (buy at ask, sell at bid), plus slippage per side: optimistic $0.00, realistic $0.10, worst $0.30 per oz. Gates use realistic and worst ([spec.md](../../../experiments/event/HPF/spec.md) lines 56-62; [powell_lab.py](../../../originals/gann_bot_500/research/powell/powell_lab.py) lines 67, 156-161). The prereg notes that Dukascopy spreads (about $0.35-0.55/oz in these windows) understate retail news spreads.

## Tuning and selection
- Search: 2 directions x 3 thresholds x 2 exits = 12 configs, pinned before OOS ([spec.md](../../../experiments/event/HPF/spec.md) lines 47-55).
- Configurations run (counted from the code/results): 12 (the prereg ledger delta lists +1 primary and +2..12 family diagnostics, spec.md lines 86-91). Ledger count (registry/trial_ledger.csv n_variants): 7. The ledger understates the pinned family by 5.
- How the reported variant was chosen: on IS data. The prereg says fade_t0_1600ET "was the strongest robust IS config" (spec.md lines 51-54). The pre-freeze lab docstring named fade / $0 / 15:30 as the literature primary ([powell_lab.py](../../../originals/gann_bot_500/research/powell/powell_lab.py) line 27); the frozen primary is the 16:00 exit. OOS was not used for selection.
- Preregistered: yes, [spec.md](../../../experiments/event/HPF/spec.md) (copy of `HPF_PREREGISTRATION.md`, commit dd4b486 per the registry). Blind predictions by the author and the assistant were both FAIL, low confidence.

## Results
All OOS rows are INSUFFICIENT SAMPLE (fewer than 100 events).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| IS Powell era, primary, realistic slip | 33 | PF 1.44, mean +$1.60/oz. INSUFFICIENT SAMPLE | [spec.md](../../../experiments/event/HPF/spec.md) lines 33-39 |
| IS Yellen control, primary | 12 | PF 0.037, mean -$5.15/oz. INSUFFICIENT SAMPLE | same |
| OOS primary fade_t0_1600ET, realistic | 27 | PF 0.518, total -$178.52/oz, win 40.7%. INSUFFICIENT SAMPLE | [HPF_run.json](../../../originals/gann_bot_500/research/powell/HPF_run.json) |
| OOS primary, worst slip | 27 | PF 0.498, total -$189.33/oz | same |
| OOS fade family, realistic | 13-27 per config | 0 of 6 with PF >= 1.00 (PF 0.273 to 0.518) | same |
| OOS permutation | 27 | actual mean -$6.61 vs p95 random +$8.63; fail | same |
| Gates | | 1 pass (n >= 22); 2, 3, 4, 5 fail; HPF FAIL | same |
| Warsh 2026-06-17 (no gate) | 1 | fade -$57.78/oz | same |
| Powell era all years, momentum configs (diagnostic) | 27-60 | PF 1.13 to 1.58 | [audit/phaseC/logs_L1/recorded.powell.powell_lab_py_--oos.log](../../../audit/phaseC/logs_L1/recorded.powell.powell_lab_py_--oos.log) |

## Code and how to rerun
- Code: [powell_lab.py](../../../originals/gann_bot_500/research/powell/powell_lab.py) (IS, and `--oos`), [powell_verdict.py](../../../originals/gann_bot_500/research/powell/powell_verdict.py) (gates; `test` runs a self-test).
- Audit rerun stage: `l1_queue` ([audit/phaseC/run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) lines 66-67). The rerun reproduces OOS n=27, PF 0.518 ([audit/phaseC/logs_L1/recorded.powell.powell_verdict_py.log](../../../audit/phaseC/logs_L1/recorded.powell.powell_verdict_py.log)).
- Public data enough? yes. Manifest group `dukascopy_ticks` (public) in [data/manifest.csv](../../../data/manifest.csv).

## Corrections from the release review
- README Parameters: "1 primary + 6 family. Variants counted in the ledger: 7." Wrong. The prereg pins 12 configs (2 directions x 3 thresholds x 2 exits) and its ledger delta counts 12 ([spec.md](../../../experiments/event/HPF/spec.md) lines 47, 86-91).
- README Costs: "realistic". Vague. Costs are Dukascopy bid/ask at tick times plus $0.10/oz per side (realistic) or $0.30 (worst) (spec.md lines 56-62).
- README Data: "Powell press conference events 2023-26". That is the OOS only. IS used 2015-2022 events, including a Yellen control (spec.md lines 33-39).
- README Results "Rerun, true UTC: not on the HistData clock" is not a result. The data is Dukascopy ticks; no clock rerun applies.
- README Results do not give the IS n (33) next to "IS 1.44".
- The spec copy names the author by first name in the prediction section. House style elsewhere is "the author" (style only).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | OOS n=27, PF 0.518, sign flip vs IS 1.44 |
| Rerun, recorded clock | OOS n=27 PF 0.518 |
| Rerun, true UTC | not on the HistData clock |

## Verdict
VERIFIED. INSUFFICIENT SAMPLE. Identical on the recorded clock.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/powell/HPF_run.json](../../../originals/gann_bot_500/research/powell/HPF_run.json)
