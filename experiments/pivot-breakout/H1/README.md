# H1

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-07. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Conviction dual-arm breakout has positive net edge 2015-2026.

Family: pivot/breakout. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
H1 is the author's preregistered rerun of the "conviction dual-arm" gold breakout (flip_bot v1.1 rules) at measured costs. A trade fires when an H1 close and an H4 close both break the prior UTC day's R3 (buy) or S3 (sell) on the same day, between 12:00 and 20:00 UTC. Costs come from a per-year, per-UTC-hour spread matrix built from Dukascopy ticks. The audit reran it on the recorded HistData clock and on true UTC.

## Instruments and data
- Instruments: XAUUSD, 1.0 lot per event ($100 per $1 move) ([triple_barrier.py:22-23,35](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py)).
- Timeframe(s): M1 resampled to H1, H4 and UTC D1 ([run_verdict.py:94-99](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py)).
- Data source and file(s): HistData XAUUSD M1, `research/data/xauusd_m1_histdata.csv` ([config.yaml:5-7](../../../originals/gann_bot_500/research/goldbot/config.yaml); [data/manifest.csv](../../../data/manifest.csv) line 428). Cost matrix: [results/cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json), built from Dukascopy ticks by [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py).
- Period: events from 2015-06-19 to the end of the data. The stored trades run from 2015-07-02 to 2026-06-10 ([verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv)). M1 is loaded from 2010 for warm-up; each era gets 100 days of warm-up ([run_verdict.py:41-44,88-96](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py)).
- In-sample / out-of-sample: no fit. Two eras, old 2015-06-19 to 2021-06-18 and new 2021-06-19 to end, plus 15 purged combinatorial splits, CPCV(6,2), label horizon 24h, embargo 24h, feature lookback 40h ([run_verdict.py:41-43,53-63](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py); [config.yaml:43-49](../../../originals/gann_bot_500/research/goldbot/config.yaml)). Both eras had already been used to build the rule (see Tuning).

## Rules
- Entry: pivots from the prior UTC day: PP = (H+L+C)/3, R3 = PP + (H - L), S3 = PP - (H - L), rounded to 2 dp ([pivots.py:1-14](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py)). For each H1 close at 12:00-20:00 UTC (inclusive), a close above R3 labels BUY and below S3 labels SELL. A close at an H4 hour (12, 16, 20) counts as both the H1 and H4 arm. The trade fires on the close where a direction holds both labels ([events.py:51-116](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py)). Entry is the open of the first M1 bar at or after that close ([triple_barrier.py:5-6](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py)).
- Exit (stop, target, time): TP = 0.8 x ATR, SL = 2.4 x ATR, time stop 24h, marked at the last M1 close before entry + 24h. Bail overlay: if ATR is above its 90-day median ("hivol"), close half at the first M1 close at -1.2 x ATR adverse; otherwise ("lovol") close all at an M1 close at -1.0 x ATR adverse once the trade is 8 hours old ([config.yaml:20-35](../../../originals/gann_bot_500/research/goldbot/config.yaml); [triple_barrier.py:7-21](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py)). Fill mode `gap_open`: a bar that opens through a barrier fills at the open. The stop is checked before the target in each bar.
- Filters: no Mondays; a level is dead for the day if any of the last 10 completed H4 closes before 00:00 UTC breached it; at least 50 completed H4 bars of history; one trade per direction per day; a global 24-hour re-entry block ([config.yaml:9-15](../../../originals/gann_bot_500/research/goldbot/config.yaml); [events.py:61-116](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py)). News blackout off ([config.yaml:82-84](../../../originals/gann_bot_500/research/goldbot/config.yaml)).
- Position sizing: 1.0 lot per event, fixed. Results are in dollars per lot.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| R3 / S3 | PP ± 1.0 x prior UTC-day range | pivots.py:1-14 |
| ATR | Wilder ATR(14) on H1, SMA seed; value of the last H1 bar closed before 00:00 UTC | config.yaml:31-33; events.py:40-48 |
| Regime median | rolling median of H1 ATR over 2,160 bars (90 days), min 200 | config.yaml:34-35; events.py:59-60 |
| TP / SL / time stop | 0.8 / 2.4 x ATR / 24 h | config.yaml:22-25 |
| Bail | hivol half-close at -1.2 x ATR; lovol close-all at -1.0 x ATR after 8 h | config.yaml:26-30 |
| Session | H1 closes 12-20 UTC inclusive | config.yaml:11 |
| Dead check | last 10 H4 closes | config.yaml:13 |
| Re-entry block | 24 h | config.yaml:14 |
| CPCV | 6 groups, 2 test, 15 splits | config.yaml:43-49; run_verdict.py:55-56 |

## Costs
Per trade, per lot: 100 oz x [mean of entry and exit spread + 0.5 x (entry spread + exit spread)] + $7 commission. Spreads are the median of the (year, UTC hour) bucket in the tick matrix. A p90 run uses the bucket 90th percentile ([cost_matrix.py:124-128](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py); [run_verdict.py:83-86,112-118](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py)). k_slip = 0.5 is an assumption, not a measurement ([spec.md](../../../experiments/pivot-breakout/H1/spec.md), "Cost basis"). A flat 20-point cost is printed as a comparison only. Mean cost per trade, recorded clock: $80.87 (old $65.51, new $100.88) ([H1_rerun.json](../../../originals/gann_bot_500/research/goldbot/results/H1_rerun.json)).

## Tuning and selection
- Search: none in this run. The rule is the end point of the earlier 17-round programme, listed as trials 1-37 in the prereg ledger ([spec.md](../../../experiments/pivot-breakout/H1/spec.md), "Trials Ledger").
- Configurations run (counted from the code/results): 1 rule (run_verdict.py also runs H2's thresholds, which are a separate experiment). Ledger count (registry/trial_ledger.csv n_variants): 1, basis "minimum, see entry". The prereg says the true count "is almost certainly larger" than its 37-row table.
- How the reported variant was chosen: not chosen here. The rule was built earlier by hand, round by round, using both eras.
- Preregistered: yes, [spec.md](../../../experiments/pivot-breakout/H1/spec.md) (copy of `goldbot/prereg/PREREGISTRATION.md`, commit 35deedc in the author's private history, not verifiable here). Gates: full PF >= 1.20, >= 10 of 15 splits positive, each era PF >= 1.00, n >= 300. Deviation: the first run used a partial tick matrix (2019-2025 ticks absent at freeze, disclosed in the prereg). The full-coverage rerun was committed in advance as the binding check.

## Results
Dollar figures per 1 lot.
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Partial matrix, full period | 472 | PF 1.24, net $20,910; old PF 0.95, new 1.42; 11/15 splits; FAIL (era gate) | [logs_partial/run_verdict.log](../../../audit/phaseC/logs_partial/run_verdict.log) |
| Full matrix, recorded clock, full | 472 | PF 1.130, net $11,811, maxDD $7,108; 11/15 splits; FAIL | [H1_rerun.json](../../../originals/gann_bot_500/research/goldbot/results/H1_rerun.json), [logs_recorded/run_verdict.log](../../../audit/phaseC/logs_recorded/run_verdict.log) |
| Recorded, old era | 267 | PF 0.897, net -$3,632 | same |
| Recorded, new era | 205 | PF 1.276, net $15,443 | same |
| Recorded, p90 spreads | 472 | PF 1.045 | same |
| True UTC, full | 481 | PF 1.009, net $930; 8/15 splits; FAIL | [h1_clock.json](../../../audit/phaseC/h1_clock.json), [logs_true/run_verdict.log](../../../audit/phaseC/logs_true/run_verdict.log) |
| True UTC, old / new | 267 / 214 | PF 0.831 / 1.114 | same |
| True UTC, p90 spreads | 481 | PF 0.933 | same |
| True UTC, spreads measured at each entry and exit | 481 | PF 0.952 (mean cost $93.66 vs matrix $81.22) | [deferred_checks.json](../../../audit/phaseC/deferred_checks.json) `h1_costs` |
| Flat 20-pt comparison, recorded | 472 | PF 1.49 | H1_rerun.json |

Exits, recorded clock: 360 TP, 50 SL, 34 timeout, 28 bail (h1_clock.json). The audit rerun matches the stored 472 trades with the same gross P&L. Trade spot check: [H1-true-utc.csv](../../../audit/trade_checks/H1-true-utc.csv).

## Code and how to rerun
- Code: [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py), [events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py), [pivots.py](../../../originals/gann_bot_500/research/goldbot/goldbot/pivots.py), [triple_barrier.py](../../../originals/gann_bot_500/research/goldbot/goldbot/triple_barrier.py), [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py), [cpcv.py](../../../originals/gann_bot_500/research/goldbot/goldbot/cpcv.py), [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml). Audit: [h1_clock.py](../../../audit/phaseC/h1_clock.py), [run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh).
- Audit rerun stage: `goldbot_both` (both clocks), `goldbot_partial` (partial matrix), `h1_clock` ([run_all.sh:32-34](../../../audit/tools/run_all.sh)).
- Public data enough? Yes: group `histdata_xau`. The cost matrix is committed; rebuilding it needs `dukascopy_ticks`.

## Corrections from the release review
- "Rules: flip_bot v1.1 rules" defines nothing on this page. The rules are in config.yaml:9-35 and events.py:51-116 (listed above). Exits are TP 0.8 x ATR, SL 2.4 x ATR, 24h, with the hivol/lovol bail. Sizing is 1 lot per event.
- "Hypothesis ... has positive net edge 2015-2026" was tested on eras that had already been used to design the rule (spec.md trials 1-37). The run is a cost check, not an out-of-sample test.
- The README's stored line "Partial coverage PF 1.24 ... n=472" does not say the partial run already failed: its old-era PF was 0.95, under the 1.00 gate (logs_partial/run_verdict.log).
- The README correctly withdraws "n=478 PF 1.012", but registry/trial_ledger.csv row AUDIT-H1-TRUEUTC still reads "FAILED, PF 1.012 n=478". The current true-UTC figure is n=481 PF 1.009 (h1_clock.json).
- The prereg commit hash 35deedc is in private history; a reader cannot check it.
- The README links only DECISIONS.log (not published) and H1_rerun.json. The run code and logs above are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Partial coverage PF 1.24 (old 0.95, new 1.42) n=472; full-coverage confirmation PF 1.13 (old 0.90, new 1.28) |
| Rerun, recorded clock | n=472 PF 1.130, old 0.897, p90 1.045 |
| Rerun, true UTC | n=481 PF 1.009, old 0.831, p90 0.933 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Measured-spread PF 0.952 on true UTC. Spot checks 20/20. Earlier Phase B figure n=478 PF 1.012 is withdrawn.

## Audit caveats
A pass on partial cost data was killed by the pre-committed rerun.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/H1_rerun.json](../../../originals/gann_bot_500/research/goldbot/results/H1_rerun.json)
