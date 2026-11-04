# BOT-LAB-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** ICT tags, news, daily trend or session drift pass.

Family: mixed. Market: XAUUSD. Timeframe: M1/D1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
BOT-LAB-1 (2026-10-13) was the author's search for any gold rule worth putting in a bot. Four groups were tried on XAUUSD. ICT-style tags were added as filters on the old "Profile D" trades. News trading around NFP, FOMC and CPI releases was tested. Daily time-series momentum and session drift (holding long through a block of broker hours) were also run. One cell, the NFP pre-release range breakout, met the news pass rule at a $0.80 spread. A later slippage stress brought it to PF 0.98, and nothing was adopted.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 for news ([news_lab.py](../../../originals/gann_bot_500/research/d_revival/news_lab.py)); H1 for session drift and D1 for TSMOM ([anomalies.py:6](../../../originals/gann_bot_500/research/d_revival/anomalies.py)); the Asia checks use D1 day starts with M1 prices ([asia.py:3-17](../../../originals/gann_bot_500/research/d_revival/asia.py)).
- Data source and file(s): `d_revival/m1.npz`, a splice of HistData M1 bid (2010-01 to 2026-06-19) and the broker MT5 export `ta_lab/data/XAU_M1.npy` (from 2026-06-26), stored in broker time UTC+2/+3 ([data.py:1-26](../../../originals/gann_bot_500/research/d_revival/data.py)); group `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv) line 427). News dates: FOMC from the fable calendar, NFP from a first-Friday-in-days-1-10 rule checked against the 15:30 bar, CPI only where exact (2015, 2025-26) ([news_lab.py:1-8,52](../../../originals/gann_bot_500/research/d_revival/news_lab.py)).
- Period: 2010-01 to 2026-10. NFP events 2010-01-08 to 2026-10-02 (176); FOMC 2015-01-28 to 2026-06-17 (94); CPI 2025-02-12 to 2026-06-10 (17) ([recorded.d_revival.news_lab_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.news_lab_py.log)).
- In-sample / out-of-sample: no fitting. Results are split into halves by count (news, anomalies, Asia), or at 2018-01-01 (ICT tags) (news_lab.py:149; anomalies.py:11-15; ict_mix log header).

## Rules
- Entry and exit, news (part C, news_lab.py:7-12): at broker 15:30 (NFP, CPI) or 21:00 (FOMC). MOM-k: after k minutes trade in the direction of the move since release, stop at the far side of the first-k-minute range. FADE-k: the opposite direction, stop at the first-k extreme plus half that range. BRK: stop orders at the 30-minute pre-release high and low; the first side touched is entered, the stop is the other side. All exit after `hold` minutes.
- Entry and exit, TSMOM (part D, anomalies.py:1-3,19-30): hold long or short by the sign of the N-day return, or of close vs SMA N, decided at the close and held over the next day; also a long-only version.
- Entry and exit, session drift (anomalies.py:31-37; asia.py, asia2.py): long from broker hour a to hour b each weekday; blocks 01-09, 09-15, 15-23, 19-01, and Asia variants 01-05, 05-09, 03-09, 1.25-9, 2-9, 1.25-5, 2-5, 1.25-7, with and without SMA50/SMA200 filters.
- ICT tags (part A): each Profile D trade from [sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py) is tagged order block, FVG, sweep, swing S/R, discount/premium, score >= 2, or all three, and tagged vs untagged trades are compared ([recorded.d_revival.ict_mix_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.ict_mix_py.log)). The script that did this, `ict_mix.py`, is not in the published files.
- Position sizing: news and ICT results in R; TSMOM and session drift in $ per oz.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| News rules | MOM k = 1, 5, 15; FADE k = 5, 15; BRK k = 0 | news_lab.py:131 |
| News hold | 30, 120, 360 min | news_lab.py:132 |
| BRK pre-range | 30 min before release | news_lab.py:11 |
| News twin | same rule, same clock time, every non-event weekday | news_lab.py:7,143 |
| TSMOM lookback | 20, 50, 100, 200 days; return sign or SMA | anomalies.py:19-20 |
| Session blocks (broker hours) | 01-09, 09-15, 15-23, 19-01 | anomalies.py:33 |
| Asia variants | see Rules | asia.py, asia2.py:2-4 |
| NFP stress grid | slippage $0, 0.5, 1, 2, 3, 5 x spread $0.80, $2.00 | [news_slip.py](../../../originals/gann_bot_500/research/d_revival/news_slip.py), log |

## Costs
- News: entry spread $0.80 inside the first 15 minutes after a release, else $0.35; exit $0.35 (news_lab.py:13). The twin is costed at $0.35 entry (news_lab.py:143).
- NFP stress: spread $0.80 or $2.00 at entry plus slippage $0-$5 on entry and on stops within 15 minutes ([news_slip.py:6-22](../../../originals/gann_bot_500/research/d_revival/news_slip.py)).
- TSMOM: $0.35 per change of side, swap ignored (anomalies.py:3,26). Session drift: $0.35 per day (anomalies.py:36). Asia: $0.35 or $0.60 per trade (asia2.py:3).
- ICT tags: Profile D replay costs, spread $0.35 in its "NET" run ([split.py](../../../originals/gann_bot_500/research/d_revival/split.py)); the ict_mix settings are not published.

## Tuning and selection
- Search: printed cells in the logs: news 48 (NFP 18, FOMC 12, CPI 18), NFP stress 12, TSMOM 16, session blocks 4, Asia 10 + 12, ICT tags 14 (7 tags x 2 entry modes). About 116 in all.
- Configurations run (counted from the code/results): about 116 printed cells. Ledger count (registry/trial_ledger.csv n_variants): 12, basis "minimum, see entry". They differ: the ledger understates the search by about 10 times. TSMOM alone has 16 cells.
- How the reported variant was chosen: the NFP BRK cell was singled out after the news grid by its pass mark; the stress test was then run on it alone. Not recorded whether the stress test was planned before the run.
- Preregistered: partly. news_lab.py fixes a pass rule "before the run": PF >= 1.15 in both halves, n >= 30 per half, event mean above 95% of random equal-size twins (news_lab.py:14-15). anomalies.py, asia.py, asia2.py and the ICT tags have no written pass rule in the published code.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| NFP BRK, hold 30 / 120 / 360, $0.80 | 175 each | PF 2.29 / 1.99 / 2.06; halves above 1.9; beats 100% of twins; meets news pass rule | [news_lab log](../../../audit/phaseC/logs_L1/recorded.d_revival.news_lab_py.log) |
| NFP BRK stress, spread $2.00 + slip $0.50 | 176 | PF 0.98, avg -0.012R | [news_slip log](../../../audit/phaseC/logs_L1/recorded.d_revival.news_slip_py.log) |
| NFP BRK stress, spread $0.80, slip $0 | 176 | PF 1.91 | same |
| Other NFP MOM/FADE cells | 171-175 | PF 0.65-1.23; none pass | news_lab log |
| FOMC, all cells | 78-92 | PF 0.43-1.31; none pass. INSUFFICIENT SAMPLE | same |
| CPI, all cells | 16-17 | INSUFFICIENT SAMPLE | same |
| TSMOM long/short, 8 cells | daily series | Sharpe -0.04 to +0.38 vs buy and hold +0.55 | [anomalies log](../../../audit/phaseC/logs_L1/recorded.d_revival.anomalies_py.log) |
| Session long Asia 01-09, $0.35 | 4,066 | PF 1.26, halves 1.11 / 1.33 | [asia log](../../../audit/phaseC/logs_L1/recorded.d_revival.asia_py.log) |
| Asia from 01:15 (1.25-9), $0.35 / $0.60 | 4,062 | PF 1.04 / 0.96 | [asia2 log](../../../audit/phaseC/logs_L1/recorded.d_revival.asia2_py.log) |
| ICT tags on Profile D (1,432 trades) | 11-634 tagged | tagged PF 0.07-1.47 by era; no tag lifts both eras above 1 | [ict_mix log](../../../audit/phaseC/logs_L1/recorded.d_revival.ict_mix_py.log) |

The Asia 01-09 result falls to PF 1.04 when entry moves 15 minutes later, to 01:15 (asia2 log). This fits the README caveat that it came from the broker's 01:00 reopen.

## Code and how to rerun
- Code: [news_lab.py](../../../originals/gann_bot_500/research/d_revival/news_lab.py), [news_slip.py](../../../originals/gann_bot_500/research/d_revival/news_slip.py), [anomalies.py](../../../originals/gann_bot_500/research/d_revival/anomalies.py), [asia.py](../../../originals/gann_bot_500/research/d_revival/asia.py), [asia2.py](../../../originals/gann_bot_500/research/d_revival/asia2.py), [sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py), [data.py](../../../originals/gann_bot_500/research/d_revival/data.py). `ict_mix.py` (part A) is not published, although its audit log is.
- Audit rerun stage: `l1_queue` (d_revival lines in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); clock-variant runs in `no1012_run` ([no1012.d_revival.anomalies.py.log](../../../audit/phaseC/logs_L1/no1012.d_revival.anomalies.py.log), [no1012.d_revival.asia.py.log](../../../audit/phaseC/logs_L1/no1012.d_revival.asia.py.log)).
- Public data enough? No. It needs `d_revival/m1.npz` or `ta_lab/data/XAU_M1.npy` (group `broker_mt5`).

## Corrections from the release review
- "Rules: A tags, B news, C daily trend, D session drift" has the parts wrong. news_lab.py:1 calls news "part C". anomalies.py:1 calls TSMOM and session drift together "part D". What part B was is not recorded in the published files.
- "Costs: $0.80 to $2 spread + slip" fits only the news tests. TSMOM and session drift use $0.35; Asia uses $0.35 or $0.60.
- "Variants counted in the ledger: 12" understates the search. The logs print about 116 cells; TSMOM alone has 16.
- "Nothing passes" needs a qualifier. Three NFP BRK cells met the pre-set news pass rule (PF 1.99-2.29, n=175). They were rejected after a slippage stress whose plan is not recorded.
- "Stored: ... PF 2.0-2.3 at $0.80" gives no n. It is n=175 per cell (176 in the stress run).
- "Data: M1 2010-2026" does not say it is a splice of HistData and a broker export, stored in broker time (data.py:1-26).
- The part-A code (`ict_mix.py`) is missing from the published files; only its log is published.
- The README links no code. All scripts above except ict_mix.py are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Nothing passes; NFP pre-range breakout PF 2.0-2.3 at $0.80, 0.98 at $2+$0.50 |
| Rerun, recorded clock | NFP PF 1.99-2.29 at $0.80 |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
Asia-long 'edge' was a broker 01:00 reopen artefact.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
