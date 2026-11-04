# PA-15-30

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-22. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Price action on 15/30m makes $5.

Family: price action. Market: XAUUSD. Timeframe: M15/M30. Idea source: the author.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Four simple price-action setups were tested on gold M15 and M30 bars. The author asked for "at least 5 profit" (quoted in the [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) docstring, lines 1-2). So the primary target is +$5 and the second is +$10. The 16 tests and their pass rule were declared in the docstring before any result was seen. All 16 failed.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M15 from the file. M30 is built from M15 pairs on the half hour ([pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) lines 35-45).
- Data source and file(s): `ta_lab/data/XAU_M15.npy`, MetaTrader 5 broker bars (bid, with per-bar spread) (pa1.py lines 4, 36; [data/manifest.csv](../../../data/manifest.csv) line 512, group `broker_mt5`).
- Period: 2022-07-11 to 2026-10-12. That is 99,999 M15 bars and 50,017 M30 bars ([recorded.pa_lab.pa1_py.log](../../../audit/phaseC/logs_L1/recorded.pa_lab.pa1_py.log)).
- In-sample / out-of-sample: no fitting. Two halves for the gate: before and after 2024-09-01 (pa1.py line 31).

## Rules
- Entry: all setups are judged on closed bars. Entry is at the next bar's open, buying at ask (bid + bar spread) and selling at bid (pa1.py lines 7, 140-141).
  - PIN: one wick ≥ 2/3 of the range, and range ≥ ATR14. Long wick below means buy; long wick above means sell.
  - ENG: body opposite to the previous bar's and covering it, with range ≥ ATR14.
  - IB: inside bar, then a stop entry on the first break of the mother high or low within the next 3 bars. If both sides break in one bar, there is no trade (lines 85-96). If price gaps through the level, the fill is at the open.
  - BO20: close above the prior 20-bar high (buy) or below the prior 20-bar low (sell) (lines 97-105).
- Exit (stop, target, time):
  - Stop: beyond the wick + $0.50 (PIN); beyond the two bars' extreme + $0.50 (ENG); the other side of the mother bar (IB); entry ∓ 1 × ATR14 (BO20) (lines 72-83, 97-105).
  - Stop distance: below $2 is widened to $2; above $15, the trade is skipped (lines 142-145).
  - Target: +$5 or +$10.
  - Time stop: 24 h, exit at the bar open (line 112).
  - A bar touching both stop and target counts as the stop (lines 121-123).
- Filters: one trade at a time per setup and timeframe (lines 133-135).
- Position sizing: 1 lot. P&L in $ per lot = price move × 100 (lines 110, 123-127).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | 14 bars | [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) docstring lines 8-14, `atr()` |
| PIN wick | ≥ 2/3 of range; range ≥ ATR14 | pa1.py lines 8, 67-74 |
| Stop buffer (PIN, ENG) | $0.50 | pa1.py lines 72-83 |
| IB entry window | 3 bars | pa1.py line 90 |
| BO20 lookback / stop | 20 bars / 1 × ATR14 | pa1.py lines 97-105 |
| Targets | $5, $10 | pa1.py docstring line 15 |
| Stop distance limits | min $2, skip above $15 | pa1.py lines 142-145 |
| Time stop | 24 h | pa1.py line 112 |
| Twins | 1,000 runs, coin-flip direction, seed 20261022 | pa1.py line 159 |
| Half split | 2024-09-01 UTC | pa1.py line 31 |

## Costs
Spread only: the bar's recorded spread × 0.01 (dollars), with a floor of $0.22. For M30 the larger of the two M15 spreads is used ([pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) lines 39, 45). It is paid by buying at ask, and shorts are stopped and exited on ask (lines 117-119, 127, 140-141). No commission. No financing.

## Tuning and selection
- Search: none. 4 setups × 2 timeframes × 2 targets.
- Configurations run (counted from the code/results): 16 ([recorded log](../../../audit/phaseC/logs_L1/recorded.pa_lab.pa1_py.log)). Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 111, n_variants): 16. They agree.
- How the reported variant was chosen: not applicable. The README's "best PF 1.06" is the M30 IB cells.
- Preregistered: pre-declared in the script docstring (the README cites [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py), sha 34ce42ce6067). PASS per test requires: n ≥ 150; net > 0 and PF ≥ 1.2 in both halves; beating ≥ 95% of twins; and t ≥ 3.0 (lines 19-20, 184-185). The code matches.

## Results
All rows: $ per 1 lot, after spread.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All 16 tests | 1,285 to 7,255 per test | 16/16 FAIL | [recorded.pa_lab.pa1_py.log](../../../audit/phaseC/logs_L1/recorded.pa_lab.pa1_py.log) |
| M30 IB TP$5 (best) | 3,257 | PF 1.06, net +$47,078, t +1.5; halves PF 1.03 / 1.08. Fails PF ≥ 1.2 and t | same |
| M30 IB TP$10 | 2,565 | PF 1.06, t +1.3 | same |
| M15 IB TP$10 | 4,757 | PF 1.02, t +0.5 | same |
| M15 BO20 TP$5 (worst) | 7,255 | PF 0.87, net -$230,727, t -5.4 | same |
| PIN / ENG / BO20, all cells | 1,285 to 7,255 | PF 0.84 to 0.96 | same |
| Audit, true UTC | not run separately | broker data unaffected by the clock fix | [audit/VERDICTS.md](../../../audit/VERDICTS.md) lines 70, 139 |

Verdict: original FAILED; audit VERIFIED, reruns exact ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 70).

## Code and how to rerun
- Code: [pa_lab/pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py).
- Audit rerun stage: `l1_queue` (`recorded pa_lab pa1.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)). No true-UTC log for this script is published. None was needed: the data are broker bars from 2022-07, which the HistData clock fix does not touch ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 139).
- Public data enough? No. `XAU_M15.npy` is a `broker_mt5` export ([data/manifest.csv](../../../data/manifest.csv) line 512).

## Corrections from the release review
- "Costs: see code" should state the cost: bar spread × 0.01 with a $0.22 floor, paid at ask, with no commission ([pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) line 39).
- "Data: 2022-07 to 2026-10" leaves out the source, which is MetaTrader 5 broker M15 bars, not published. The public tier cannot regenerate the result.
- "Rules: PIN, ENG, IB, BO20; TP $5, $10" leaves out the stops (wick + $0.50, two-bar extreme + $0.50, mother bar, 1 ATR), the $2 minimum and $15 skip on stop distance, and the 24 h time stop.
- "best PF 1.06" gives no n. It is M30 IB, n = 3,257 (TP$5) and 2,565 (TP$10).
- "Source: user" is chat residue. The idea came from the author's request, as the docstring records.
- "Rerun, true UTC: same" should say why. The broker M15 data are not affected by the HistData clock fix, so no true-UTC run exists ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 139).
- The provenance cites only `DECISIONS.log (not published)`, and the script path appears only as text. The script is published: [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 16/16 FAIL; best PF 1.06 |
| Rerun, recorded clock | 16/16 FAIL |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
