# XM-1-OTHERS

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Turn of month, pre-FOMC, overnight, CFD 12m trend and leaders of gold work.

Family: mixed. Market: indices, gold. Timeframe: D1/H1. Idea source: published anomalies.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
XM-1 (2026-10-13) tested documented market effects outside gold, with rules and pass bars written in the docstring first. This entry covers everything in XM-1 except A1, which has its own page (XM-1-A1). A2 is turn-of-month and A3 is the pre-FOMC drift, both on US500 and US30. A4 splits overnight from intraday returns. B is a 12-month trend portfolio on six markets. C asks whether other markets lead gold's next bar. Nothing here passed.

## Instruments and data
- Instruments: A2-A4 US500, US30; B XAUUSD, XAGUSD, US500, US30, TLT, EURUSD; C XAUUSD, TLT, US500, XAGUSD, EURUSD, each against gold's next bar ([xm_lab.py:1-18,141-145,179-184](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).
- Timeframe(s): D1 for A2, B and C-D1; H1 for A3, A4 and C-H1.
- Data source and file(s): MT5 broker demo feed, `cross_market/data/<SYM>_D1.npz` and `_H1.npz`, server time UTC+2/+3 ([xm_lab.py:1-2,26,33-38](../../../originals/gann_bot_500/research/cross_market/xm_lab.py); group `broker_mt5` in [data/manifest.csv](../../../data/manifest.csv)). FOMC dates come from [build_calendar.py](../../../originals/gann_bot_500/fable-backtesting/build_calendar.py).
- Period: the script labels A2 "2012-2026", A3/A4 "2018-2026", B "2005-2026" (B data from 2004-06-01, returns from 2005-06-01), C D1 from 2005-01-01 and C H1 from 2018-06-01 ([xm_lab.py:146,171,180,200-208](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)). Exact first and last dates per file are not printed.
- In-sample / out-of-sample: no fitting. "Halves" are the first and second half of each test's own trades or bars, split by count, not by date ([xm_lab.py:46-51,165,192](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).

## Rules
- Entry and exit:
  - A2: buy at the close of the last trading day of each month, sell at the close 4 trading days later (`hold_ret(c, i, i + 4)`, [xm_lab.py:99](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)). That is the close of the 4th trading day of the new month.
  - A3: return from the open of the 21:00 server-time H1 bar (14:00 ET by the docstring) on the day before an FOMC statement to the same bar on the statement day ([xm_lab.py:104-119](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).
  - A4: long overnight = close of the 22:00 server bar to the open of the next session's 17:00 bar; long intraday = 17:00 open to 22:00 close ([xm_lab.py:121-136](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).
  - B: each day, sign of the 252-day return per market, times weight 10%/(60-day annualised vol), capped at 2; decided at yesterday's close; equal average across available markets ([xm_lab.py:149-163](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).
  - C: no trades. Correlation of each market's bar return with gold's next-bar log return ([xm_lab.py:185-196](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).
- Filters: none.
- Position sizing: A2-A4 one unit per trade, returns in percent; B vol targeting as above.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| A2 hold | last close of month to 4 trading days later | xm_lab.py:97-99 |
| A3 window | 24 h before the 21:00 server bar on FOMC days | xm_lab.py:108-117 |
| A4 split | 22:00 close / 17:00 open, server time | xm_lab.py:121-122 |
| B trend | 252-day return sign; 60-day vol; 10% target per asset; cap 2x | xm_lab.py:150-153 |
| C | lag 1 bar; pass if abs(corr) >= 0.03 with the same sign in both halves | xm_lab.py:17,194 |
| Twins | A2: 1,000 random 4-day holds; A3: 2,000 draws of non-FOMC same-hour returns; seed 7 | xm_lab.py:30,64-73,100,118 |

## Costs
Spread = 1.5 x the median recorded spread of the file loaded (D1 or H1), charged once per hold; financing 5% a year on longs and 1.5% on shorts per calendar night ([xm_lab.py:5-6,29,38,57-61](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)). The docstring says "median recorded H1 spread", but for A2 and B the code uses the D1 file's spread. B uses at least 2 bp of price (TLT has no recorded spread) ([xm_lab.py:147](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)).

## Tuning and selection
- Search: none. One pre-declared rule per family.
- Configurations run (counted from the code/results): A2 x 2 markets, A3 x 2, A4 x 2 x 2 (overnight and intraday, ungated), B x 1, C x 5 markets x 2 timeframes = 21 printed cells. Ledger count (registry/trial_ledger.csv n_variants): 5, one per family. The ledger counts families, not cells.
- How the reported variant was chosen: not applicable.
- Preregistered: partly. The docstring states the rules and the PASS bar "written before any result was seen": net mean > 0 and net PF >= 1.15 in both halves, n >= 30 per half, and twin p < 0.05; B needs net Sharpe >= 0.5 in both halves and above long-only; C needs abs(corr) >= 0.03, same sign in both halves ([xm_lab.py:4-17](../../../originals/gann_bot_500/research/cross_market/xm_lab.py)). There is no separate prereg file. A4 is run with the gate switched off (`gate=False`, lines 136-137), so it can only print "fail".

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| A2 US500 | 169 | PF 1.37 / 1.43 by half; twin p 0.198; fail | [recorded.cross_market.xm_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.xm_lab_py.log) |
| A2 US30 | 169 | PF 1.39 / 1.51; twin p 0.140; fail | same |
| A3 US500 pre-FOMC | 67 | PF 1.66 / 2.35; twin p 0.107; fail. INSUFFICIENT SAMPLE | same |
| A3 US30 pre-FOMC | 67 | PF 1.47 / 2.21; twin p 0.159; fail. INSUFFICIENT SAMPLE | same |
| A4 US500 overnight / intraday (net) | 2,115 / 2,111 | PF 1.04, 1.04 / 0.94, 1.04 | same |
| A4 US30 overnight / intraday (net) | 2,119 / 2,114 | PF 1.06, 1.04 / 0.96, 1.08 | same |
| B trend portfolio | daily series | Sharpe -0.45 / -0.15 by half (long-only 0.07 / 0.17); fail | same |
| C D1 (5 markets) | 3,575 to 5,537 bars | abs(corr) <= 0.025; none pass | same |
| C H1 (5 markets) | 12,260 to 45,260 bars | abs(corr) <= 0.025; none pass | same |

## Code and how to rerun
- Code: [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) (functions `a1_a2`, `a3_a4`, `b_trend`, `c_leadlag`); FOMC list from [build_calendar.py](../../../originals/gann_bot_500/fable-backtesting/build_calendar.py). Importing build_calendar also rewrites `calendar/news_days.json` (first lines of the log).
- Audit rerun stage: `l1_queue` ("recorded cross_market xm_lab.py" in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); split-adjusted run in `adj_run` ([adj.cross_market.xm_lab.py.log](../../../audit/phaseC/logs_L1/adj.cross_market.xm_lab.py.log)).
- Public data enough? No. It needs group `broker_mt5` D1 and H1 files. [REPRODUCE.md](../../../REPRODUCE.md) names XM-1 among results that cannot be regenerated publicly.

## Corrections from the release review
- "Rules: See log" points to DECISIONS.log, which is not published. The rules are in xm_lab.py:1-18 and the functions above.
- "Turn of month" is coded as last-day close to the close 4 trading days later (xm_lab.py:99), not "close of last day -> close of 3rd day" as the docstring says (line 11).
- "Results: All fail; |corr|<0.03" gives no n. A3 has n=67 per market, INSUFFICIENT SAMPLE. A4 had no gate at all (`gate=False`).
- "Market: indices, gold" is incomplete. B also trades silver, TLT and EURUSD; C tests TLT, US500, silver, EURUSD and gold.
- "Costs: CFD financing" leaves out the spread: 1.5 x the file's median recorded spread per hold, plus 5%/1.5% a year financing.
- "Ledger 5" counts families. The script prints 21 cells.
- The README links no code. xm_lab.py is published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | All fail; |corr|<0.03 |
| Rerun, recorded clock | All fail, abs(corr) < 0.03 |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
