# PA-30-MAX5

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-23. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Small targets on M30 work.

Family: price action. Market: XAUUSD. Timeframe: M30. Idea source: the author.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
This is a follow-up to [PA-15-30](../../../experiments/price-action/PA-15-30/README.md). The author asked for M30 with a profit of at most $5. The same four setups, entries, stops, costs, twins and same-bar rule were re-run on M30 with targets of $1, $2, $3, $4 and $5. Only the target changes ([pa30.py](../../../originals/gann_bot_500/research/pa_lab/pa30.py) lines 1-7). All 20 tests failed.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M30, built from M15 pairs on the half hour ([pa_lab/pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) lines 40-45; pa30.py line 21).
- Data source and file(s): `ta_lab/data/XAU_M15.npy`, MetaTrader 5 broker bars ([pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) lines 4, 36; [data/manifest.csv](../../../data/manifest.csv) line 512, group `broker_mt5`).
- Period: 2022-07-11 to 2026-10-12, 50,017 M30 bars (as in [the PA-15-30 log](../../../audit/phaseC/logs_L1/recorded.pa_lab.pa1_py.log)).
- In-sample / out-of-sample: no fitting. Halves split at 2024-09-01 (pa30.py line 6; pa1.py line 31).

## Rules
- Entry: identical to PA-15-30, imported from [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) (`run`, pa30.py line 15). All setups enter at the next bar's open, buying at ask and selling at bid.
  - PIN: wick ≥ 2/3 of the range, range ≥ ATR14.
  - ENG: engulfing, range ≥ ATR14.
  - IB: break of the mother bar within 3 bars.
  - BO20: close beyond the 20-bar high or low.
- Exit (stop, target, time):
  - Stop: wick + $0.50 (PIN), two-bar extreme + $0.50 (ENG), the other side of the mother bar (IB), 1 × ATR14 (BO20).
  - Stop distance: below $2 is widened to $2; above $15, the trade is skipped.
  - Target: $1, $2, $3, $4 or $5 (pa30.py line 17).
  - Time stop: 24 h.
  - A bar touching both stop and target counts as the stop (pa1.py lines 110-127, 142-145).
- Filters: one trade at a time per setup.
- Position sizing: 1 lot; P&L in $ per lot.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Setups and stops | as PA-15-30 (PIN, ENG, IB, BO20; ATR14; $0.50 buffers; 1 ATR) | [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) lines 60-105 |
| Targets | $1, $2, $3, $4, $5 | [pa30.py](../../../originals/gann_bot_500/research/pa_lab/pa30.py) line 17 |
| Stop distance limits | min $2, skip above $15 | pa1.py lines 142-145 |
| Time stop | 24 h (48 M30 bars) | pa1.py line 112 |
| Twins | 1,000 coin-flip runs, seed 20261022 | pa1.py line 159; pa30.py line 29 |

## Costs
As PA-15-30: the bar spread × 0.01 in dollars, floored at $0.22, with M30 taking the larger M15 spread. It is paid by buying at ask, and shorts are exited on ask ([pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) lines 39, 45, 117-119, 140-141). No commission. No financing.

## Tuning and selection
- Search: 5 targets × 4 setups.
- Configurations run (counted from the code/results): 20 ([recorded.pa_lab.pa30_py.log](../../../audit/phaseC/logs_L1/recorded.pa_lab.pa30_py.log)). Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 112, n_variants): 20. They agree. The four $5 rows repeat PA-15-30's M30 TP$5 cells (pa30.py line 7), and they match the PA-15-30 log exactly. So 4 of the 20 are not new trials.
- How the reported variant was chosen: not applicable.
- Preregistered: pre-declared in the script docstring (README cites [pa30.py](../../../originals/gann_bot_500/research/pa_lab/pa30.py), sha 81ca5e0b52d8). PASS = n ≥ 150; net > 0 and PF ≥ 1.2 in both halves; beating ≥ 95% of twins; and t ≥ 3.0 (lines 6-7, 30-31). The code matches.

## Results
All rows: $ per 1 lot, after spread.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All 20 tests | 1,408 to 4,932 per test | 20/20 FAIL | [recorded.pa_lab.pa30_py.log](../../../audit/phaseC/logs_L1/recorded.pa_lab.pa30_py.log) |
| $1 targets (all setups) | 1,545 to 4,932 | win 69-80%, PF 0.46-0.85, all net negative | same |
| Best: M30 IB TP$5 | 3,257 | PF 1.06, t +1.5, so FAIL (same as PA-15-30) | same |
| M30 IB TP$4 | 3,434 | PF 1.01, t +0.2 | same |
| Worst: M30 BO20 TP$1 | 4,932 | PF 0.46, net -$405,038, t -17.9 | same |
| Average loss per losing trade | all cells | -$461 to -$587 per lot | same |
| Audit, true UTC | not run separately | broker data unaffected by the clock fix | [audit/VERDICTS.md](../../../audit/VERDICTS.md) lines 71, 139 |

Verdict: original FAILED; audit VERIFIED, reruns exact ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 71).

## Code and how to rerun
- Code: [pa30.py](../../../originals/gann_bot_500/research/pa_lab/pa30.py), which imports [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py).
- Audit rerun stage: `l1_queue` (`recorded pa_lab pa30.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)).
- Public data enough? No. `XAU_M15.npy` is a `broker_mt5` export ([data/manifest.csv](../../../data/manifest.csv) line 512).

## Corrections from the release review
- "Costs: see code" should state the cost: bar spread × 0.01 with a $0.22 floor, paid at ask, no commission ([pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py) line 39).
- "Rules: Targets $1-5" leaves out that setups, entries and stops are PA-15-30's, imported from [pa1.py](../../../originals/gann_bot_500/research/pa_lab/pa1.py). These include the $2 minimum and $15 skip on stop distance, and the 24 h time stop.
- "Data: 2022-07 to 2026-10" leaves out that the data are MetaTrader 5 broker M15 bars, not published.
- "Stored: 20/20 FAIL" gives no n. n is 1,408 to 4,932 per test, and the best cell is M30 IB TP$5, PF 1.06 on n=3,257.
- "Variants counted in the ledger: 20" includes the four $5 cells that repeat PA-15-30 ([pa30.py](../../../originals/gann_bot_500/research/pa_lab/pa30.py) line 7).
- "Source: user" is chat residue. The request came from the author.
- The provenance cites only `DECISIONS.log (not published)`, and the script path appears only as text. The script is published: [pa30.py](../../../originals/gann_bot_500/research/pa_lab/pa30.py).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 20/20 FAIL |
| Rerun, recorded clock | 20/20 FAIL |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
