# E4-NEWS

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Event spreads change the verdicts.

Family: execution. Market: XAUUSD. Timeframe: ticks. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
An audit-phase cost check, run 2026-10-31. It measured gold tick spreads around NFP, CPI and FOMC releases, then repriced three already-failed rules (H1, FINAL_v3, FINAL_v4) with those spreads and with a news blackout. The question was whether event spreads change any verdict ([audit/prereg/E4-NEWS.md](../../../audit/prereg/E4-NEWS.md)). It is a cost revision, not a new strategy.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): ticks for spreads; trade lists from the H1 rule (H1+H4 signals) and the FINAL_v3/v4 rules.
- Data source and file(s): Dukascopy XAUUSD ticks `fable-backtesting/download/xauusd-bi5-*.csv`, 2015-01 to 2026-06 ([audit/phaseE/e4_news.py](../../../audit/phaseE/e4_news.py) line 23; prereg line 5). Trades: true-UTC rebuilds from Phase C, `audit/phaseC/h1_true_utc_trades.csv` (written by h1_clock.py, not shipped), [fable_v3_true.csv](../../../audit/phaseC/fable_v3_true.csv), [fable_v4_true.csv](../../../audit/phaseC/fable_v4_true.csv) (e4_news.py lines 132, 144). Event dates come from `fable-backtesting/build_calendar.py` (e4_news.py lines 20, 26-49).
- Period: 2015-01 to 2026-06 for spreads. Trades after 2026-06 use 2026 values (prereg).
- In-sample / out-of-sample: none. Full trade lists are repriced.

## Rules
- Entry: no new entries. Trades are the stored rule trades.
- Events: FOMC at 14:00 New York and CPI at 08:30 New York, dates from build_calendar.py. CPI dates exist only for 2015 and 2025-26 ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 42). NFP dates are generated as the first Friday of each month 2015-01 to 2026-07, at 08:30 New York, not taken from the release calendar (e4_news.py lines 37-43). Counted events: NFP 139, FOMC 94, CPI 29 ([e4_result.json](../../../audit/phaseE/e4_result.json)).
- Windows (minutes from release): -30..-5, -5..0, 0..1, 1..5, 5..30, 30..60 (e4_news.py line 22).
- Event-aware cost: a trade entry or exit inside a window pays that window's p90 spread for its event type and year instead of the matrix spread. FINAL_v3/v4 save no exit time, so only their entries are re-costed; the exit uses the entry-hour matrix spread (e4_news.py lines 150-152).
- Blackout: drop trades whose entry is within 30 minutes of an event. The list is filtered, not regenerated (prereg).
- Exit (stop, target, time) and position sizing: unchanged from each rule; costs per 1 lot (100 oz).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Windows | -30..-5, -5..0, 0..1, 1..5, 5..30, 30..60 min | [e4_news.py](../../../audit/phaseE/e4_news.py) line 22 |
| Spread statistic charged | p90 per event type, window and year (falls back to previous year) | e4_news.py lines 112-119 |
| Non-event baseline | median spread at the same UTC hours (12, 13 for NFP/CPI; 18, 19 for FOMC) on non-event days of the same year, every 20th tick | e4_news.py lines 74-78, 160-168 |
| Blackout | entry within +/-30 min (1,800 s) of an event | e4_news.py lines 121-124 |
| Gate | PF >= 1.20 at these costs (H1's frozen gate) | [audit/prereg/E4-NEWS.md](../../../audit/prereg/E4-NEWS.md) |

## Costs
Per trade, per lot: 100 x (average of entry and exit spread + 0.5 x (entry spread + exit spread)) + $7 commission. That is one spread, plus slippage of 0.5 x spread per side, plus $7/lot round trip. Spreads come from the frozen cost matrix (median, k_slip 0.5, $7/lot), replaced by the event p90 inside a window ([e4_news.py](../../../audit/phaseE/e4_news.py) lines 109, 136-137, 146-148). A 2x-cost PF is also reported.

## Tuning and selection
- Search: 3 rules x 2 treatments (event-aware, blackout).
- Configurations run (counted from the code/results): 6. Ledger count (registry/trial_ledger.csv n_variants): 6 (row AUD-E4). They match. A first run ([e4_result_first_run.json](../../../audit/phaseE/e4_result_first_run.json)) repriced FINAL_v3/v4 from their flat-cost PF instead of the frozen matrix basis; it is superseded and logged as AUD-E4-FIX with 0 variants.
- How the reported variant was chosen: no selection. All six figures are reported.
- Preregistered: yes, [audit/prereg/E4-NEWS.md](../../../audit/prereg/E4-NEWS.md). Deviations stated in [audit/DECISIONS.md](../../../audit/DECISIONS.md) item 53: exits use the matrix spread for v3/v4; CPI dates only for 2015 and 2025-26. The first-Friday NFP rule is not listed as a deviation.

## Results
From [audit/phaseE/e4_result.json](../../../audit/phaseE/e4_result.json).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| H1, matrix cost | 481 | PF 1.009 | e4_result.json |
| H1, event-aware | 481 (7 touch a window) | PF 1.008; extra cost $150 | same |
| H1, blackout | 480 | PF 1.007 (event-aware) | same |
| H1, 2x event-aware cost | 481 | PF 0.659 | same |
| FINAL_v3, matrix cost | 436 | PF 1.056 | same |
| FINAL_v3, event-aware | 436 (0 in a window) | PF 1.056 | same |
| FINAL_v3, blackout | 436 | PF 1.056 | same |
| FINAL_v4, matrix cost | 577 | PF 0.899 | same |
| FINAL_v4, event-aware | 577 (15 in a window) | PF 0.898; extra cost $229 | same |
| FINAL_v4, blackout | 562 | PF 0.923 | same |
| First-minute spread ratio to non-event same hours | NFP 139, CPI 29, FOMC 94 events | NFP 1.49x, CPI 1.43x, FOMC 1.51x | same |
| CPI 0..1 min p90 spread | 29 events | $2.41 (median of yearly p90). INSUFFICIENT SAMPLE | same |

No rule reaches PF 1.20. The blind prediction of 3x-6x spreads was wrong; the measured first-minute ratio is about 1.4x-1.5x. The prediction that PFs fall by under 0.03 was right.

## Code and how to rerun
- Code: [audit/phaseE/e4_news.py](../../../audit/phaseE/e4_news.py) (`measure` reads ticks and writes [e4_spreads.json](../../../audit/phaseE/e4_spreads.json); `rerun` writes e4_result.json), [audit/phaseE/lib.py](../../../audit/phaseE/lib.py).
- Audit rerun stage: `e4m` (measure) and `e4r` (rerun) ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)). They need the earlier stages `h1_clock` and `fable_true` for the trade lists.
- Public data enough? yes. Manifest group `dukascopy_ticks` (public); the HistData M1 used to rebuild the trade lists is `histdata_xau` (public).

## Corrections from the release review
- README Provenance: "`audit/phaseE` (not published)". Wrong. The folder is in the repo: [e4_news.py](../../../audit/phaseE/e4_news.py), [e4_result.json](../../../audit/phaseE/e4_result.json), [e4_spreads.json](../../../audit/phaseE/e4_spreads.json).
- README Splits: "see prereg". The prereg has no split. This is a cost revision of full trade lists.
- README Rules, Costs and Gates all say "see prereg". The rules, windows, cost formula and the PF >= 1.20 gate should be stated (see above).
- README Verdict quotes PF 1.008 / 1.056 / 0.898 with no n. The n are 481, 436 and 577.
- README Verdict: "Exits use the matrix spread because no exit time is saved." True for FINAL_v3 and v4 only. H1 saves exit times and its exits are event-repriced (e4_news.py lines 133-137).
- Not disclosed anywhere: NFP dates are generated by a first-Friday rule, not taken from the release calendar ([e4_news.py](../../../audit/phaseE/e4_news.py) lines 37-43). An import-time check printed in the audit logs reads "NFP first-Friday rule vs exact 2015: 9/12 match" ([audit/phaseC/logs_L1/recorded.cross_market.crypto_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.crypto_lab_py.log) line 1). So some NFP windows sit on the wrong day.
- README Source: "audit brief". It should say this is an audit-phase test of the author's frozen rules.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No rule reaches its gate. See audit/phaseE/e4_result.json. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. FAILED. On the frozen cost basis H1 PF 1.008, FINAL_v3 1.056, FINAL_v4 0.898. Events take off under 0.01 of PF: 7, 0 and 15 trades enter in a window. First-minute spreads run 1.43x to 1.51x same-hour non-event days, so the 3x to 6x blind prediction was wrong. Exits use the matrix spread because no exit time is saved.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
