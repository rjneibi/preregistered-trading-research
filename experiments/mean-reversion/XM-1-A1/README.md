# XM-1-A1

**Audit verdict: REPRODUCES-BUT-FRAGILE.** Original verdict: PASSED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Short-term dip buying above SMA200 has edge.

Family: mean-reversion. Market: US500 + 4 untouched markets. Timeframe: D1. Idea source: published RSI2 family.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A published short-term mean-reversion rule on stock indices: buy when the 2-day RSI is below 10 and the close is above the 200-day average; sell when the close rises above the 5-day average or after 10 days. It was one of several pre-declared tests in the XM-1 lab and passed on US500 only. A follow-up script (XM-1b) then tried to break it with next-open fills, cost stress, a parameter grid and other markets. The audit reproduced it exactly and graded it fragile.

## Instruments and data
- Instruments: pre-declared test on US500 and US30 ([xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) docstring, line 10). Stress script adds US30, USTEC, IWM, EWA as "never fitted" markets ([a1_stress.py](../../../originals/gann_bot_500/research/cross_market/a1_stress.py) lines 1-7).
- Timeframe(s): D1.
- Data source and file(s): broker MT5 demo feed, `research/cross_market/data/{US500,US30,USTEC,IWM,EWA}_D1.npz` (xm_lab.py `DD`, `load`). Server time UTC+2/+3 (xm_lab.py docstring). Manifest group `broker_mt5`, not public.
- Period: US500 2012-2026 (xm_lab log "A1/A2 daily index effects (2012-2026)"); USTEC from 2022; IWM and EWA from 2003 (a1_stress.py docstring).
- In-sample / out-of-sample: no fitting in the pre-declared test. Halves = first and second half of each test's own trades (xm_lab.py docstring; a1_stress.py `h = len(r) // 2`).

## Rules
From xm_lab.py docstring and a1_stress.py `rsi2_trades`; audit rewrite audit/stats/pass_audit.py `a1()` lines 59-79.
- Entry: at day i close, if RSI2 < 10 and close > SMA200, go long. Stored original fills at the signal close; the tradable version (a1_stress "next-day open", audit default) fills at the next open.
- Exit (stop, target, time): first close > SMA5, or after 10 days; filled at that close (original) or the next open (tradable). No stop.
- Filters: SMA200 trend filter only. One position at a time.
- Position sizing: 100% of notional per trade; results as per-trade % returns (a1_stress.py docstring item 5).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| RSI(2) | ewm alpha 0.5 recursion on up/down moves; threshold 10 | xm_lab.py; pass_audit.py `rsi2` (review 02_truth confirms both use the same recursion) |
| Trend filter | close > SMA200 | xm_lab.py; a1_stress.py `trend=200` |
| Exit MA | close > SMA5 | `exit_ma=5` |
| Max hold | 10 days | `maxd=10` |
| Stress grid | RSI threshold {5, 10, 15, 25} x exit MA {3, 5, 10} = 12 cells, next-open fills | a1_stress.py lines 56-62 |
| No-trend variant | SMA200 filter removed | a1_stress.py |

## Costs
From xm_lab.py docstring and `load`: spread = 1.5 x the median recorded spread (a1_stress falls back to 2 bp of the median close if no spread is recorded), charged once per trade; financing on longs 5%/yr of notional per calendar night (shorts 1.5%/yr, not used here). Stress: spread x2 and financing 7%/yr (a1_stress.py); audit also 2x and 3x costs (pass_audit.json `cost_2x`, `cost_3x`).

## Tuning and selection
- Search: the rule is the published Connors form; thresholds were not tuned in the pre-declared test. The 12-cell grid in a1_stress.py is shown in full as a neighbourhood check ("no picking").
- Configurations run (counted from the code/results): pre-declared A1 on 2 markets; stress grid 12 cells plus baseline, next-open, cost-stress and no-trend rows, plus 4 extra markets (a1_stress log). Ledger count (registry/trial_ledger.csv, XM-1-A1): 12. audit/VERDICTS.md line 117 uses family N = 17.
- How the reported variant was chosen: fixed in advance (xm_lab.py docstring "PRE-DECLARED (written before any result was seen)"). Selection used no tuning.
- Preregistered: partly. Gates and rules are pre-declared in the xm_lab.py docstring; there is no separate prereg document. The pre-declared test covered US500 and US30; it passed on US500 only.

## Results
Pre-declared PASS (xm_lab.py docstring): net mean > 0 and net PF >= 1.15 in both halves, n >= 30 per half, and beats a random twin of the same exposure (permutation p < 0.05).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| US500, original signal-close fill | 124 | halves PF 1.72 / 3.79; twin p 0.000; PASS | [xm_lab log](../../../audit/phaseC/logs_L1/recorded.cross_market.xm_lab_py.log) |
| US30, pre-declared | 122 | halves PF 1.40 / 1.48; twin p 0.081; fail | same |
| US500, next-open fill (tradable) | 124 | PF 2.372, halves 1.655 / 3.453; win 77.4%; 70.1% compounded total | [pass_audit.json](../../../audit/stats/pass_audit.json) `XM-1-A1`; [a1_stress log](../../../audit/phaseC/logs_L1/recorded.cross_market.a1_stress_py.log) |
| US500, next open + 2x spread + 7% financing | 124 | halves PF 1.51 / 3.24 | a1_stress log |
| US500, 2x / 3x costs (audit) | 124 | PF 2.312 / 2.254 | pass_audit.json |
| US500, no SMA200 filter | 169 | halves PF 0.89 / 2.93 | a1_stress log |
| US500 grid, 12 cells | 54 to 288 per cell | half1 PF 0.80 to 1.92; PBO 0.508 (CSCV, 252 splits, 12 variants) | a1_stress log; pass_audit.json `cscv` |
| US30 / USTEC / IWM / EWA, next open | 122 / 37 / 158 / 150 | halves PF 1.33/1.56, 3.32/2.28, 1.30/1.54, 1.54/1.30. USTEC INSUFFICIENT SAMPLE | a1_stress log |
| IWM 2003-2011 only | 54 | halves PF 1.23 / 0.90. INSUFFICIENT SAMPLE | a1_stress log |
| US500 per year | 2 to 13 per year | 4 of 14 years lose (2018, 2020, 2022, 2023) | pass_audit.json `by_year` |
| Exposure and return | 124 | in market 11.5% of days; 4.1%/yr vs buy-and-hold 12.26%/yr | pass_audit.json |
| DSR | 124 | 0.29 at ledger N; 0.934 at family N 17 | audit/VERDICTS.md:102, 117 |
| One-bar delay | 124 | PF 1.80 | audit/VERDICTS.md:55 |

The headline result is on 124 trades over about 13 years.

## Code and how to rerun
- Code: [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) (pre-declared tests), [a1_stress.py](../../../originals/gann_bot_500/research/cross_market/a1_stress.py) (stress and grid), audit rewrite [pass_audit.py](../../../audit/stats/pass_audit.py) `a1()`. Audit queue [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh).
- Audit rerun stage: `l1_queue` (xm_lab.py, a1_stress.py), `pass_audit`; split-adjusted sensitivity `adj_make`/`adj_run` (audit/tools/run_all.sh).
- Public data enough? No. Needs manifest group `broker_mt5`. `pass_audit` is in audit/tools/stages_broker.txt.

## Corrections from the release review
- README "Market: US500 + 4 untouched markets" is wrong. US30 was in the pre-declared A1 test and failed it (twin p 0.081); only USTEC, IWM and EWA were untouched (xm_lab.py line 10; xm_lab log).
- README "12-cell grid + stress" does not link a1_stress.py or state the grid: RSI threshold {5,10,15,25} x exit MA {3,5,10} (a1_stress.py lines 56-62).
- README "Stored: n=124 PF 1.72/3.79" are signal-close fills, which a live order cannot get. The tradable next-open halves are 1.65/3.45, PF 2.37 (a1_stress log; pass_audit.json).
- README "Costs: spread, financing, 2x stress" gives no figures: 1.5 x median spread, 5%/yr long financing; stress 2x spread and 7%/yr (xm_lab.py; a1_stress.py).
- README "Gates: PF both halves, twin" omits net mean > 0, PF >= 1.15 and n >= 30 per half (xm_lab.py docstring).
- README verdict "In market 11% of days" rounds 0.115; it is 11.5% (pass_audit.json `exposure`).
- README verdict "with a similar Sharpe and a smaller drawdown" had no source when the review began: pass_audit.json holds no Sharpe or drawdown. [xm1.py](../../../audit/review_f/xm1.py) was rerun unchanged and saved as [review_f/out/xm1.out](../../../audit/review_f/out/xm1.out): daily Sharpe 0.78 against 0.76 for buy-and-hold, maximum drawdown -14.3% against -34.8%, in the market 11.4% of days (audit DECISIONS 63).
- README "Preregistration: pre-declared gates in xm_lab.py" is fair, but there is no separate prereg document.
- Provenance lists `DECISIONS.log`, which is not in the repository.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | n=124 PF 1.72/3.79; next-open PF 1.65/3.45 |
| Rerun, recorded clock | n=124, next open PF 2.37, halves 1.65/3.45; close fill 2.54, halves 1.72/3.79 |
| Rerun, true UTC | no HistData dependence |

## Verdict
REPRODUCES-BUT-FRAGILE. Rewrite exact. PBO 0.508 on a grid the audit chose. 4 of 14 years lose. In market 11% of days: 4.1%/yr against buy-and-hold 12.3%, with a similar Sharpe and a smaller drawdown. One-bar delay PF 1.80. Spot checks 20/20. DSR: see the deflated Sharpe table in audit/VERDICTS.md.

## Audit caveats
Original note, since superseded: not yet deflated by programme trial count. audit/VERDICTS.md now gives both DSRs. ~9 trades/yr. IWM 2003-2011 flat.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/cross_market/xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)
