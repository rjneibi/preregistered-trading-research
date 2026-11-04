# PA-1B

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** D1 inside-bar breakout transfers.

Family: price action. Market: XAG, US500, US30, USTEC. Timeframe: D1. Idea source: PA-1 near miss. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
PA-1's closest result, the D1 inside-bar breakout on gold, was re-run unchanged on silver and three US indices. The question was whether it is a general price-action edge or a gold-specific result ([PREREG_IB.md](../../../originals/gann_bot_500/research/price_action/PREREG_IB.md); [ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py) line 1). It failed on every market.

## Instruments and data
- Instruments: XAGUSD, US500, US30, USTEC ([ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py) lines 99-104).
- Timeframe(s): signals on broker D1 bars. Trades are walked on H1 for XAGUSD and on M1 for the indices (same lines).
- Data source and file(s): MetaTrader 5 demo exports in `research/cross_market/data/` (`*_D1.npz`, `XAGUSD_H1.npz`, `*_M1.npz`) (ib_confirm.py lines 8, 13-15; [data/manifest.csv](../../../data/manifest.csv), group `broker_mt5`, for example lines 317-325).
- Period: XAGUSD 2018-2026, US500 and US30 2012-2026, USTEC 2022-2026 ([recorded log](../../../audit/phaseC/logs_L1/recorded.price_action.ib_confirm_py.log)). The prereg gives XAG H1 from 2018-05, US500/US30 M1 from 2012-08, USTEC M1 from 2022-07.
- In-sample / out-of-sample: no fitting. Each market's trades are split at the median trade time into two halves (ib_confirm.py line 117).

## Rules
- Entry: D1 inside bar (high < prior high, low > prior low). OCO stop entries at the mother-bar high and low for the next 3 D1 bars (ib_confirm.py line 58). If both sides fill on one fine bar, the trade is skipped. The fill bar's favourable extreme is ignored ([PREREG_IB.md](../../../originals/gann_bot_500/research/price_action/PREREG_IB.md)).
- Exit (stop, target, time): stop at the other side of the mother bar, floored at 0.25 × ATR (ib_confirm.py line 69). Target 2R (line 32). Otherwise close after 10 × 24 h (line 10). If one fine bar holds both stop and target, the stop is taken.
- Filters: one position at a time.
- Position sizing: results in R per trade.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | Wilder 14 on D1, seeded by the 14-bar mean | [ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py) lines 19-25 |
| Entry window | 3 D1 bars after the inside bar | ib_confirm.py line 58 |
| Stop floor | 0.25 × ATR | ib_confirm.py line 69 |
| Target / hold | 2R / 10 days | ib_confirm.py lines 10, 32 |
| Twins | 20, random direction, rng seed 11 | ib_confirm.py lines 113-114 |
| Swap long / short | XAG -0.0023 / +0.0002 $/oz; US500 -0.31 / -0.26; US30 -2.21 / -1.99; USTEC -0.82 / -0.75 per unit per night | ib_confirm.py lines 99-104 |

## Costs
1.5 × the median recorded spread of the fine-bar file, per round trip ([ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py) line 110). The values are: XAG 0.021, US500 0.750, US30 2.250, USTEC 1.500 (recorded log). Financing is charged per calendar night held, at the symbol's swap (line 82). Gold is re-shown with a swap of -0.126 long / -0.046 short $/oz per night (line 88).

## Tuning and selection
- Search: none. The rule was copied unchanged from PA-1.
- Configurations run (counted from the code/results): 4 markets × 1 rule ([recorded log](../../../audit/phaseC/logs_L1/recorded.price_action.ib_confirm_py.log)). Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 110, n_variants): 4. They agree.
- How the reported variant was chosen: not applicable.
- Preregistered: yes ([PREREG_IB.md](../../../originals/gann_bot_500/research/price_action/PREREG_IB.md), sha 5136c45a7b96 per README). PASS requires all of: (1) net avg R > 0 in ≥ 3 of 4 markets; (2) pooled real − twin ≥ 0.05R with t ≥ 2.0; (3) net avg R > 0 in both halves. The prereg words (3) as "pooled ... in both halves of each market's sample". The code requires both halves > 0 in every single market (ib_confirm.py lines 118, 129), which is the stricter reading.

## Results
All rows: net of spread and swap, in R.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| XAGUSD | 191 | net -0.045R (twin -0.043R); halves -0.096 / +0.005 | [recorded.price_action.ib_confirm_py.log](../../../audit/phaseC/logs_L1/recorded.price_action.ib_confirm_py.log) |
| US500 | 268 | net -0.124R (twin -0.093R); halves -0.221 / -0.027 | same |
| US30 | 298 | net -0.023R (twin -0.023R); halves -0.006 / -0.039 | same |
| USTEC | 78 | net -0.019R (twin +0.003R). INSUFFICIENT SAMPLE | same |
| Pooled, 4 markets | 835 | net -0.060R vs twin -0.048R; diff -0.012R, t -0.30; 0/4 markets > 0. FAIL | same |
| Gold re-shown with swap | 387 | net +0.114R (long +0.243, short -0.025) | same |
| Audit, true UTC | 835 pooled | identical market rows, FAIL; gold re-shown +0.117R | [true.price_action.ib_confirm_py.log](../../../audit/phaseC/logs_L1/true.price_action.ib_confirm_py.log) |

Verdict: original FAILED; audit VERIFIED ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 69).

## Code and how to rerun
- Code: [ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py); diagnostics in [ib_diag.py](../../../originals/gann_bot_500/research/price_action/ib_diag.py); prereg [PREREG_IB.md](../../../originals/gann_bot_500/research/price_action/PREREG_IB.md).
- Audit rerun stage: `l1_queue` (`recorded price_action ib_confirm.py` and `true price_action ib_confirm.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)).
- Public data enough? No. All four markets are `broker_mt5` exports ([data/manifest.csv](../../../data/manifest.csv)).

## Corrections from the release review
- "Splits: n/a" is wrong. Gate 3 splits each market's trades into halves at the median trade time ([ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py) lines 117-118).
- "Data: H1/M1" leaves out the source. The data are MetaTrader 5 broker exports, not published, so the public tier cannot regenerate the result. Signals use broker D1 bars.
- "Costs: with swaps" should state: 1.5 × median spread per round trip plus per-night swap at the symbol's current rate (lines 99-110).
- "Stored: 0/4 markets >0" gives no n or R. The per-market n and net R are above. USTEC n=78 is INSUFFICIENT SAMPLE.
- "Rerun, true UTC: ib_confirm FAIL" is right, but the true-UTC market rows are identical to the recorded ones. Only the gold re-show changes (+0.117R).
- The provenance cites only `DECISIONS.log (not published)`. [ib_confirm.py](../../../originals/gann_bot_500/research/price_action/ib_confirm.py) and [PREREG_IB.md](../../../originals/gann_bot_500/research/price_action/PREREG_IB.md) are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0/4 markets >0 |
| Rerun, recorded clock | 0/4 > 0 |
| Rerun, true UTC | ib_confirm FAIL |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
Gold-specific, drift-driven.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
