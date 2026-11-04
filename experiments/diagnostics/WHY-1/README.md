# WHY-1

**Audit verdict: VERIFIED.** Original verdict: PASSED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Why do price-only rules fail?

Family: diagnostics. Market: XAUUSD. Timeframe: M1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A diagnostic, not a strategy. It asked four questions about why price-only gold rules fail: (Q1) are returns predictable (autocorrelation, variance ratio); (Q2) do daily pivot, Gann and fib levels make price bounce more than placebo levels; (Q3) does a plain stop/target version of the author's Profile D bot win more often than a driftless random walk predicts; (Q4) how much of the stop the spread eats ([diag.py](../../../originals/gann_bot_500/research/d_revival/diag.py) lines 1-8).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 bars, resampled to M5, M15, H1, H4, D1 for Q1 (diag.py lines 24-25).
- Data source and file(s): a splice. HistData XAUUSD M1 bid CSV from 2010-01 to 2026-06-19, plus a broker MT5 export (`ta_lab/data/XAU_M1.npy`) from 2026-06-26. Both are shifted to broker time (UTC+2/+3) and cached as `d_revival/m1.npz` ([d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2, 17-27). The manifest classes m1.npz as `broker_mt5`, access "broker" ([data/manifest.csv](../../../data/manifest.csv) row 427).
- Period: 2010-01 to 2026-10 (data.py line 1).
- In-sample / out-of-sample: none. Results are shown by four eras: 2010-2013, 2014-2017, 2018-2021, 2022-2026 (diag.py line 17).

## Rules
- Entry: Q1, Q2 none. Q3 uses the Profile D replay in [sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py) with `--entry intended` (closed M1 bar, enter at the next open), no partial, no break-even/trail (diag.py lines 100-103; sim.py lines 1-22).
- Exit (stop, target, time): Q3: stop 1 x ATR(H1); target 0.5, 1, 2 or 3 x stop. Q2: a touch counts as a bounce if price moves k = 0.5 x ATR(H1) back away before moving k through, within 600 M1 bars; ambiguous bars are dropped (diag.py lines 37-39, 74-87).
- Filters: Q2 skips levels within k of the day's open and days with fewer than 600 M1 bars (diag.py lines 47-48, 64-65).
- Position sizing: none (results in R or in percent).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Autocorrelation | lag 1 of log returns | [diag.py](../../../originals/gann_bot_500/research/d_revival/diag.py) lines 26-30 |
| Variance ratio | VR(4) = var(4-bar return) / (4 x var(1-bar return)) | diag.py lines 31-32 |
| ATR | Wilder, 43 H1 bars | diag.py line 50 |
| Bounce distance k | 0.5 x ATR(H1) | diag.py line 51 |
| Pivots | fib pivots from previous D1: PP, R/S at 0.382, 0.618, 1.0 x range | [sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py) lines 111-115 |
| Gann levels | Square-of-9 from the D1 open, degrees 45-360 step 45 | sim.py lines 36, 97-108 |
| Fib retracement | 0.382, 0.5, 0.618, 0.786 of the last 50 H1 bars' swing | sim.py lines 37-38; diag.py lines 55-57 |
| Placebo | each pivot and fib level shifted by +/- U(0.3, 0.7) x previous-day range, seed 3 | diag.py lines 36-40, 61 |
| Barrier targets | 0.5, 1, 2, 3 x stop | diag.py line 100 |

## Costs
Spread $0.35 per trade (sim.py default, line 412). Q3 also reports gross at zero spread. Q4 reports $0.35 divided by the median stop (diag.py lines 113-119).

## Tuning and selection
- Search: none. Four fixed questions.
- Configurations run (counted from the code/results): 4 questions; 4 barrier targets in Q3. Ledger count (registry/trial_ledger.csv n_variants): 0. That is consistent: nothing was selected.
- How the reported variant was chosen: not applicable.
- Preregistered: no (diagnostic).

## Results
From the audit reruns [audit/phaseC/logs_L1/recorded.d_revival.diag_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.diag_py.log) and [true.d_revival.diag_py.log](../../../audit/phaseC/logs_L1/true.d_revival.diag_py.log).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Q1 autocorrelation, all TFs and eras | n/a | -0.040 to +0.049 | recorded log |
| Q1 VR(4), all TFs and eras | n/a | 0.94 to 1.06 (1.06 is D1 2018-2021) on both clocks | recorded and true logs |
| Q2 pivot touches | 10,678 | bounce 48.2% | recorded log |
| Q2 Gann touches | 758 | bounce 47.5% | recorded log |
| Q2 fib touches | 6,091 | bounce 50.0% | recorded log |
| Q2 placebo touches | 14,672 | bounce 49.8% | recorded log |
| Q3 target 0.5 x stop | 1,230 | predicted win 66.7%, actual gross 66.1%; net -0.106R | recorded log |
| Q3 target 1 x stop | 1,213 | predicted 50.0%, actual 51.1%; gross +0.022R, net -0.060R | recorded log |
| Q3 target 2 x stop | 1,173 | predicted 33.3%, actual 34.5%; gross +0.032R, net -0.064R | recorded log |
| Q3 target 3 x stop | 1,142 | predicted 25.0%, actual 25.6%; net -0.105R | recorded log |
| Q4 spread share of stop | n/a | 0.053R (2022-2026) to 0.136R (2014-2017) per trade | recorded log |
| Audit | | VERIFIED | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 53 |

Level bounce rates match placebo, and win rates match the random-walk prediction. Costs then make the net result negative.

## Code and how to rerun
- Code: [d_revival/diag.py](../../../originals/gann_bot_500/research/d_revival/diag.py), [d_revival/sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py), [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py).
- Audit rerun stage: `l1_queue` ([audit/phaseC/run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) lines 30 and 69).
- Public data enough? no. The input m1.npz is group `broker_mt5` (broker access). The HistData part (group `histdata_xau`, public) covers 2010-01 to 2026-06-19; the tail from 2026-06-26 is a broker export.

## Corrections from the release review
- README Data: "M1 2010-2026". Incomplete. It is a splice of HistData bid (to 2026-06-19) and a broker MT5 export (from 2026-06-26), with a one-week gap, stored in broker time ([data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2, 17-27). The cached file is broker-only data ([data/manifest.csv](../../../data/manifest.csv) row 427).
- README Verdict: "Claim said 1.06 in the registry; rerun reads 1.05." Wrong. Both rerun logs print VR(4) = 1.06 for D1 2018-2021, so the range is 0.94 to 1.06 as the registry said.
- README Rules list "barrier math" but not the four barrier targets, the k = 0.5 x ATR bounce rule or the placebo shift (0.3-0.7 x range). These are in diag.py lines 1-8, 36-40.
- README omits the Gann level result (n=758, bounce 47.5%).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | VR(4) 0.94-1.06; pivots 48.2%, fib 50.0%, placebo 49.8% |
| Rerun, recorded clock | 48.2 / 50.0 / 49.8, VR 0.94-1.05 |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Claim said 1.06 in the registry; rerun reads 1.05.

## Audit caveats
Explanatory result, not a strategy.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/d_revival/diag.py](../../../originals/gann_bot_500/research/d_revival/diag.py)
