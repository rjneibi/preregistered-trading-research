# EDGE-1-F9

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: INCONCLUSIVE. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Near-uncorrelated streams combine.

Family: portfolio. Market: 5 streams. Timeframe: monthly. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
The author combined the strategies that had "passed" their own earlier tests into one equal-risk book of monthly returns. The question was how correlated they are, and what the mix does against any single stream ([combo5.py](../../../audit/phaseC/combo5.py) lines 1-2). It is a descriptive, in-sample portfolio with no gate. The stored figures are for 5 streams. The published original script was later extended with a sixth stream (TSMOM).

## Instruments and data
- Instruments: US500 (two index-dip streams), USTEC (opening-range breakout), 12 coins: BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX (trend and funding carry) ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) line 201).
- Timeframe(s): stream trades on D1 (US500, crypto) and M1 (USTEC ORB), aggregated to monthly returns ([combo5.py](../../../audit/phaseC/combo5.py) lines 17-27).
- Data source and file(s): MetaTrader 5 demo exports, `cross_market/data/US500_D1.npz`, `USTEC_M1.npz`, `data_edge/C_<coin>_D1.npz`, `data_edge/F_<coin>.npz`, and the cached `edge_results.pkl` ([data/manifest.csv](../../../data/manifest.csv) lines 317, 325, 341, 373, 426; group `broker_mt5`, access broker).
- Period: streams start at different times. RSI2 and IBS from 2013-07, crypto trend from 2017-10, carry from 2019-12, ORB from 2022-07. The combined book covers only the months where all five are live: 2022-07 to 2026-10, 52 months ([recorded.cross_market.combo5.log](../../../audit/phaseC/logs_L1/recorded.cross_market.combo5.log)).
- In-sample / out-of-sample: none. Each stream is scaled by its own full-sample volatility (combo5.py line 57), so the book is in-sample.

## Rules
- Entry:
  - "Index dip RSI2" (MR1): long US500 when RSI(2) < 10 and close > SMA200 ([swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 62-63).
  - "Index dip IBS" (MR2): long US500 when IBS = (C − L)/(H − L) < 0.2 (lines 64-65).
  - Both enter at the next open, after 252 warm-up bars (lines 89-103).
  - "Nasdaq ORB": USTEC 30-minute opening range from 09:30 New York. Enter at the range edge on the first break, and skip the day if one bar breaks both sides ([scalp_lab.py](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py) lines 85-110). Trades whose stop distance is under 0.15% of entry are dropped (combo5.py lines 41-43).
  - "Crypto trend": each coin long when close > SMA50, else flat ([edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 256-268).
  - "Crypto funding carry": long spot / short perp on each coin while trailing 7-day mean funding > 0, decided on yesterday's data (edge_lab.py lines 208-220).
- Exit (stop, target, time):
  - MR1: close > SMA5.
  - MR2: IBS > 0.8 or close > the prior high.
  - Both MR streams: max 15 bars (swing_lab.py line 29), exit at the next open.
  - ORB: stop at the opposite range edge, exit by 16:00 New York (scalp_lab.py lines 104-108).
  - Crypto trend and carry: daily rebalancing by signal.
- Filters: as above. No book-level filter.
- Position sizing:
  - MR streams at 1/3 notional (combo5.py line 35).
  - ORB at 0.25% equity risk per trade (line 44).
  - Crypto trend at 2% / 60-day vol per coin, capped at 1, then split equally across coins (edge_lab.py lines 259-265).
  - Carry equal-weight across coins.
  - Each monthly stream is then scaled to 10% annual volatility, and the book is the equal-weight mean (combo5.py lines 57, 64-65).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| RSI | period 2 (EWM alpha 0.5), entry < 10 | [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 41-42, 63 |
| Trend filter / exit MA (MR1) | SMA200 / SMA5 | swing_lab.py lines 38, 60-63 |
| IBS | entry < 0.2, exit > 0.8 or close > prior high | swing_lab.py lines 44, 65 |
| Max hold (MR) | 15 bars | swing_lab.py line 29 |
| Financing (MR) | 5%/yr long, 1.5%/yr short, per night | swing_lab.py line 89, 101 |
| ORB range | 30 min from 09:30 NY | [scalp_lab.py](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py) lines 90, 101-110 |
| ORB min stop | 0.15% of entry | [combo5.py](../../../audit/phaseC/combo5.py) line 42 |
| ORB risk | 0.25% equity per trade | combo5.py line 44 |
| Crypto trend | SMA50, 60-day vol, 2% target per coin | [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py) lines 258-263 |
| Carry | 7-day mean funding > 0, from 2019-12-01 | edge_lab.py lines 218, 223 |
| Stream vol target | 10% per year on monthly returns | combo5.py line 57 |
| Window start | 2012-01-01 (book limited by the latest stream) | combo5.py line 55 |

## Costs
Costs apply inside each stream. The book adds no costs.
- MR streams: spread = 1.5 × median positive spread of the export (floor 0.02% of median price) per trade, plus overnight financing ([xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) line 38; swing_lab.py lines 35-36, 101).
- ORB: 1.5 × median in-session M1 spread (scalp_lab.py line 45).
- Crypto trend: 0.1% of turnover (edge_lab.py line 267).
- Carry: 0.3% per round trip, half charged on each switch (edge_lab.py line 220).

## Tuning and selection
- Search: none at book level. The streams were picked because each had passed its own earlier test (combo5.py line 1). Several of those tests are graded elsewhere as fragile or failed. The README caveat notes that the ORB leg later failed.
- Configurations run (counted from the code/results): 1 five-stream book (stored, regenerated by combo5.py). The published original [combo.py](../../../originals/gann_bot_500/research/cross_market/combo.py) differs from combo5.py at line 50 only: it adds "Multi-asset trend (TSMOM)" as a sixth stream. Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 106, n_variants): 1. With the TSMOM version there are 2 books.
- How the reported variant was chosen: the stored figure is the 5-stream book. Why TSMOM was in or out is not recorded in the published files. The edge_lab.py docstring says F9 is "everything that passes" (line 22). In combo.py's own log, TSMOM shows Sharpe -0.35 on its own.
- Preregistered: no. edge_lab.py lines 1-23 pre-declare the F1-F7 tests, and F9 is described there only as "the combined book". It has no gate.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored, 5-stream book, 2022-07..2026-10 | 52 months; trade counts per stream not recorded | Sharpe 3.01, vol 3.8%, max DD 1.9%, worst month -1.6%, 19% losing months | [recorded.cross_market.combo5.log](../../../audit/phaseC/logs_L1/recorded.cross_market.combo5.log); README |
| Same months, each stream alone | 52 months | Sharpe: RSI2 1.81, IBS 2.05, ORB 1.05, crypto trend 0.80, carry 1.69 | same |
| Monthly correlations | 52+ months | highest pair: crypto trend vs carry 0.53; others between -0.12 and 0.21 | same |
| Book re-levered to 10% vol | 52 months | CAGR +34.0%, max DD 5.0% | same |
| 6-stream book (adds TSMOM) | 52 months | Sharpe 2.58, max DD 2.3% | [recorded.cross_market.combo_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.combo_py.log) |

52 monthly points form a short, mostly rising sample (README caveat). The numbers are not a test result. Verdict: original INCONCLUSIVE; audit VERIFIED-WITH-CORRECTIONS ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 65). This entry was replaced by the descriptive [E3-PORTFOLIO](../../../experiments/portfolio/E3-PORTFOLIO/README.md).

## Code and how to rerun
- Code: [audit/phaseC/combo5.py](../../../audit/phaseC/combo5.py) (5 streams, stored figure), [combo.py](../../../originals/gann_bot_500/research/cross_market/combo.py) (6 streams), [edge_lab.py](../../../originals/gann_bot_500/research/cross_market/edge_lab.py), [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py), [scalp_lab.py](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py), [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py).
- Audit rerun stage: `combo5` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh) line 39). It is listed as a broker stage in [audit/tools/stages_broker.txt](../../../audit/tools/stages_broker.txt). The 6-stream log comes from the `l1_queue` stage (`cross_market combo.py`, [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)).
- Public data enough? No. Every input is in the `broker_mt5` group ([data/manifest.csv](../../../data/manifest.csv)). The numbers can only be checked by hash.

## Corrections from the release review
- "Data: 2022-07 to 2026-10" describes only the common window. The streams start between 2013-07 and 2022-07. The source is MetaTrader 5 broker exports, which are not published ([data/manifest.csv](../../../data/manifest.csv) lines 317-426), and the README does not say so.
- "Rules: RSI2, IBS, ORB, crypto trend, crypto carry at 10% vol" names the streams but gives no rule. The rules and sizing above are in code the page does not link.
- "Costs: stream level" gives no figures. The costs are 1.5 × median spread plus financing (index streams), 1.5 × median session spread (ORB), 0.1% turnover (crypto trend) and 0.3% per switch (carry).
- "Script later added TSMOM, which reads 2.58" needs context. The published original [combo.py](../../../originals/gann_bot_500/research/cross_market/combo.py) is the 6-stream version. The stored 3.01 is regenerated by the audit's [combo5.py](../../../audit/phaseC/combo5.py). The README does not say why TSMOM was left out. TSMOM alone reads Sharpe -0.35.
- The only provenance link is `DECISIONS.log (not published)`. The code and both logs are published: [combo5.py](../../../audit/phaseC/combo5.py), [combo5 log](../../../audit/phaseC/logs_L1/recorded.cross_market.combo5.log), [combo log](../../../audit/phaseC/logs_L1/recorded.cross_market.combo_py.log).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Book Sharpe 3.01, maxDD 1.9% |
| Rerun, recorded clock | Sharpe 3.01, DD 1.9% on 5 streams |
| Rerun, true UTC | same |

## Verdict
VERIFIED-WITH-CORRECTIONS. Script later added TSMOM, which reads 2.58. Stays INCONCLUSIVE. Replaced by the descriptive E3, which gives no verdict.

## Audit caveats
52 bull-heavy months. Includes the ORB leg that later failed, and an in-sample portfolio. Do not headline.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
