# E6-PAPER

**Audit verdict: VERIFIED.** Original verdict: INSUFFICIENT SAMPLE. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Backtest matches the demo trades.

Family: reconciliation. Market: XAUUSD. Timeframe: M1. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
E6 compared the author's demo-bot trades with what the backtester says the same profiles would have done on the same dates. The demo journal holds 19 closed trades from profiles D and R in June and July 2026. Each demo trade was matched to a backtest entry with the same side within 60 minutes, and entry and exit prices were compared. With 19 trades this is INSUFFICIENT SAMPLE by design and has no gate.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 bars resampled to H1, H4 and UTC D1 for the backtest ([e6_paper.py](../../../audit/phaseE/e6_paper.py) line 28).
- Data source and file(s): demo journal `research/trades.db`, table `trades` only, read-only (e6_paper.py lines 18-19); manifest group `demo_journal`, not published ([data/MANIFEST.md](../../../data/MANIFEST.md)). Prices: Dukascopy M1 `london-breakout/data/m1/XAUUSD.npz` (e6_paper.py line 22; manifest group `dukascopy_m1`), used instead of HistData for the 2026 window (e6_paper.py line 1).
- Period: 2026-06-11 09:00 to 2026-07-03 17:00 UTC (first journal open floored to the hour, last close rounded up) ([e6_result.json](../../../audit/phaseE/e6_result.json) `window`; e6_paper.py line 26). Bars from 120 days before are loaded for warm-up (line 27).
- In-sample / out-of-sample: none.

## Rules
- Entry: backtest side uses the published `dr_backtest` engine and profiles D and R unchanged, run from the audit's true-clock sandbox copy (e6_paper.py lines 11-14, 32-34). Its unthrottled entries are cut to one per (date, zone source) (lines 35-40). The engine's rules are on the [DR-EDGE-SCREEN](../../../experiments/support-resistance/DR-EDGE-SCREEN/README.md) page.
- Exit (stop, target, time): backtest exits by `simulate_trade` with the profile's fixed TP, ATR stop and partial close (e6_paper.py lines 41-42): D TP 900 points, SL 1.0 x ATR; R TP 1000 points, SL 1.5 x ATR; both 50% at 1.0 x ATR then breakeven ([backtest.py](../../../originals/gann_bot_500/research/dr_backtest/backtest.py) lines 82-110). The demo bots trailed their stops; the backtester has no trailing stop ([e6_result.json](../../../audit/phaseE/e6_result.json) `bot_exit_reasons`: 14 of 19 TRAIL).
- Filters: matching rule. A demo trade matches the nearest unused backtest entry on the same side within 3,600 seconds (e6_paper.py lines 47-52).
- Position sizing: n/a. Gaps are compared in $/oz and in R, where R = ATR x the profile's SL multiple (e6_paper.py lines 43, 53-54).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | Wilder 14 on H1 | e6_paper.py line 29 |
| Match window | 60 minutes, same side | e6_paper.py line 48 |
| Backtest throttle | 1 entry per (date, zone source) | e6_paper.py lines 37-40 |
| Profile D | polarity on, TP 900 pts, SL 1.0 x ATR, partial 1.0 x ATR | backtest.py lines 82-94 |
| Profile R | polarity off, TP 1000 pts, SL 1.5 x ATR, partial 1.0 x ATR | backtest.py lines 97-110 |
| Sample label | INSUFFICIENT SAMPLE if n < 100 | e6_paper.py line 30 |

## Costs
None. The comparison is of prices trade by trade; no spread, commission or swap is applied (e6_paper.py; [audit/prereg/E6-PAPER.md](../../../audit/prereg/E6-PAPER.md)).

## Tuning and selection
- Search: none.
- Configurations run (counted from the code/results): 1 comparison over 2 profiles. Ledger count (registry/trial_ledger.csv n_variants): 1, under trial id AUD-E6 (plus AUD-E6-FIX, 0 variants, reporting only). They agree.
- How the reported variant was chosen: n/a.
- Preregistered: yes, [audit/prereg/E6-PAPER.md](../../../audit/prereg/E6-PAPER.md) (copy at [spec.md](../../../experiments/reconciliation/E6-PAPER/spec.md)). Blind prediction: INSUFFICIENT SAMPLE and match rate under 70%. No gate. The prereg says backtest exits must fall before the last journal close; the code limits entries to the window but does not cut exits (e6_paper.py lines 26, 34, 41).

## Results
All rows: INSUFFICIENT SAMPLE (19 demo trades).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All | 19 demo trades | 6 matched, match rate 0.316 | [e6_result.json](../../../audit/phaseE/e6_result.json) |
| Profile D | 9 demo; 21 backtest (1 per zone-day); 26 unthrottled | 4 matched; 5 demo-only; 17 backtest-only; median entry gap $0.16 | e6_result.json |
| Profile R | 10 demo; 11 backtest; 18 unthrottled | 2 matched; 8 demo-only; 9 backtest-only; median entry gap $0.41 | e6_result.json |
| Exit gap, matched trades | 6 | median absolute $11.66/oz | e6_result.json `exit_gap_median_abs_usd` |
| Demo exit reasons | 19 | TRAIL 14, TP 4, MANUAL 1 | e6_result.json |
| Trade-by-trade pairs | 19 rows | entry gap, minutes, exit gap, R both sides | [e6_pairs.csv](../../../audit/phaseE/e6_pairs.csv) |

## Code and how to rerun
- Code: [e6_paper.py](../../../audit/phaseE/e6_paper.py); engine [backtest.py](../../../originals/gann_bot_500/research/dr_backtest/backtest.py), [exit_sim.py](../../../originals/gann_bot_500/research/dr_backtest/exit_sim.py), [data_prep.py](../../../originals/gann_bot_500/research/dr_backtest/data_prep.py).
- Audit rerun stage: `e6` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)). It is listed in [stages_broker.txt](../../../audit/tools/stages_broker.txt), so it is expected to fail on the public tier.
- Public data enough? No. It needs the unpublished demo journal (manifest group `demo_journal`). The M1 prices are public (group `dukascopy_m1`).

## Corrections from the release review
- README provenance "`audit/phaseE` (not published)" is wrong. [e6_paper.py](../../../audit/phaseE/e6_paper.py), [e6_result.json](../../../audit/phaseE/e6_result.json) and [e6_pairs.csv](../../../audit/phaseE/e6_pairs.csv) are in the repo, and run_all.sh runs them as stage `e6`.
- README "Costs: see prereg" is misleading. Neither the prereg nor the code applies any cost; it is a price comparison (e6_paper.py).
- README "Rules: See prereg" and "Splits: see prereg" hide the window and the source. The window is 2026-06-11 09:00 to 2026-07-03 17:00 UTC, and prices come from the Dukascopy M1 file, not HistData (e6_result.json; e6_paper.py lines 1, 22).
- README "Caveats: See audit/DECISIONS.md" gives no caveat. The main one is in the verdict line: the bots trail their stops (14 of 19 exits) and the backtester does not, which drives the $11.66 exit gap (e6_result.json).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 6 of 19 matched. INSUFFICIENT SAMPLE. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. INSUFFICIENT SAMPLE. 6 of 19 demo trades matched. Median exit gap on those 6 is $11.66, mostly because the bot trails and the backtester does not.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
