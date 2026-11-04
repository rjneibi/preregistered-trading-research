# E1-PAIRS

**Audit verdict: VERIFIED.** Original verdict: FAILED OR INSUFFICIENT SAMPLE. Dated 2026-10-31. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Cointegrated spreads revert at a profit after two-leg costs.

Family: pairs. Market: XAU/XAG, BTC/ETH, gold/GDX. Timeframe: H1, D1. Idea source: audit brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
E1 is an audit-phase experiment, preregistered by the audit before any data was loaded. It tests whether three price spreads revert at a profit after costs on both legs. The pairs are gold/silver, bitcoin/ether and gold/the GDX miners ETF. Each pair is run three ways: an OLS hedge traded only in months where both cointegration tests pass (V1), a Kalman hedge with the same filter (V2), and an OLS hedge with no filter (V3).

## Instruments and data
- Instruments: XAU/XAG, BTC/ETH, gold vs GDX ([audit/prereg/E1-PAIRS.md](../../../audit/prereg/E1-PAIRS.md); spec copy [spec.md](../../../experiments/pairs/E1-PAIRS/spec.md)).
- Timeframe(s): H1 for XAU/XAG and BTC/ETH; D1 for gold/GDX, with gold M1 sampled at 16:00 New York (spec.md, "Pairs and data").
- Data source and file(s): gold Dukascopy M1 `london-breakout/data/m1/XAUUSD.npz` (group `dukascopy_m1`); silver Dukascopy M1 bid/ask `audit/dk_xag` (group `dukascopy_xag`); BTC and ETH Binance 1h klines in `cross_market/data` (group `binance`); GDX Yahoo adjusted daily `audit/public/GDX_yahoo.json` (group `public_api`) ([e1_pairs.py:20-24,27-40](../../../audit/phaseE/e1_pairs.py); [data/manifest.csv](../../../data/manifest.csv)). Silver 2022-26 comes from M1 candles, not ticks ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 47).
- Period: XAU/XAG 2015-01-01 to 2026-10-29 (69,904 bars); BTC/ETH 2017-08-17 to 2026-10-13 (80,138 bars); gold/GDX 2015-01-02 to 2026-10-29 (2,957 bars) ([e1_result.json](../../../audit/phaseE/e1_result.json)).
- In-sample / out-of-sample: time-ordered dev 50% / validation 20% / holdout 30% by calendar span; a later slice opens only if the earlier one passes ([audit/prereg/COMMON.md](../../../audit/prereg/COMMON.md), "Slices"). Dev ends 2020-11-30 (XAU/XAG, gold/GDX) and 2022-03-16 (BTC/ETH) (e1_result.json `dev_end`).

## Rules
- Entry: hedge and tests re-estimated on the first bar of each month over a trailing 90 calendar days (H1) or 252 trading days (D1). Spread = log A - beta log B with intercept. Z uses the formation mean and sd (or Kalman innovations scaled by their formation sd). Enter when abs(z) >= 2, signal on bar close, fill at the next bar open (spec.md, "Formation and tests", "Trading").
- Exit (stop, target, time): exit when z crosses 0; stop at abs(z) >= 4; time limit 3 half-lives, capped at 10 days (H1) or 60 days (D1). V1 and V2 also close at the next open if the month's retest fails (spec.md; caps 240 and 1,440 hours in [e1_pairs.py:210](../../../audit/phaseE/e1_pairs.py)).
- Filters: V1/V2 trade only in months where Engle-Granger and Johansen (trace, det_order 0, k_ar_diff 1) both pass at 5% and the OU fit is valid. V3 has no cointegration filter.
- Position sizing: return per trade on gross notional, leg weights 1/(1+abs(beta)) and abs(beta)/(1+abs(beta)). One position per pair.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Formation window | 90 calendar days (H1), 252 trading days (D1) | spec.md; e1_pairs.py:210 |
| Cointegration tests | EG (`statsmodels coint`), Johansen trace det_order 0, k_ar_diff 1, at 5% | spec.md; e1_pairs.py:11-12 |
| Kalman | random-walk variance 1e-5, observation variance 1e-3 | e1_pairs.py:25 |
| Entry / exit / stop | abs(z) >= 2 / z crosses 0 / abs(z) >= 4 | spec.md |
| Time limit | 3 OU half-lives, cap 10 d (H1) / 60 d (D1) | spec.md |
| Twin | 2,000 random-entry draws, seed 7, same count and holding times | COMMON.md; [lib.py:40-52](../../../audit/phaseE/lib.py) |

## Costs
Both legs, as a fraction of notional ([e1_pairs.py:94-104](../../../audit/phaseE/e1_pairs.py)):
- XAU and XAG: average of entry and exit spread + 0.5 x (entry + exit spread) + $7 per lot round trip + $5 per lot per night [ESTIMATE]; lots of 100 oz gold, 5,000 oz silver.
- BTC and ETH: 0.10% round trip per leg + 15% a year on the short leg.
- GDX: $0.02 per share round trip; gold leg as above.
- Gates also use 2x costs; 1.5x is reported.

## Tuning and selection
- Search: none. One frozen config per variant. The audit also ran an entry band of 2 <= abs(z) <= 4 beside the frozen rule ([audit/CHANGES.md](../../../audit/CHANGES.md) line 94; DECISIONS items 39, 51).
- Configurations run (counted from the code/results): 3 pairs x 3 variants = 9 frozen, plus 9 band cells = 18 ([e1_pairs.py:222](../../../audit/phaseE/e1_pairs.py)). Ledger count: E1-PAIRS itself has no row in registry/trial_ledger.csv. AUD-E1 has 9 and AUD-E1-BAND has 9, so 18 in all. These agree.
- How the reported variant was chosen: not chosen; all cells are reported.
- Preregistered: yes, [audit/prereg/E1-PAIRS.md](../../../audit/prereg/E1-PAIRS.md) with [COMMON.md](../../../audit/prereg/COMMON.md), frozen in audit commit 0fab84c (DECISIONS item 37). Deviations: the entry band (shown beside, not instead of, the frozen rule); silver spreads from M1; three bug-fix reruns, logged ([CHANGES.md](../../../audit/CHANGES.md) lines 86-88; earlier outputs kept as `e1_result_first_run_buggy.json`, `_second_run_churn.json`, `_third_run_band.json`).

## Results
Dev slice only; no cell passed dev, so validation and holdout stay sealed (e1_result.json).
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| XAU/XAG V1 dev | 8 | PF 0.263. INSUFFICIENT SAMPLE | [e1_result.json](../../../audit/phaseE/e1_result.json) |
| XAU/XAG V2 dev | 24 | PF 0.077. INSUFFICIENT SAMPLE | same |
| XAU/XAG V3 dev | 109 | PF 0.030, 2x-cost PF 0.006, gross PF 0.636, twin p 0.756; FAIL | same |
| BTC/ETH V1 dev | 99 | PF 0.276. INSUFFICIENT SAMPLE | same |
| BTC/ETH V2 dev | 30 | PF 1.43, 2x-cost PF 0.99, twin p 0.047. INSUFFICIENT SAMPLE | same |
| BTC/ETH V3 dev | 310 | PF 0.618, 2x-cost 0.434, twin p 0.716; FAIL | same |
| Gold/GDX V1, V2 dev | 0, 0 | no trades. INSUFFICIENT SAMPLE | same |
| Gold/GDX V3 dev | 3 | INSUFFICIENT SAMPLE | same |
| All 9 band cells, dev | 0 to 34 | all INSUFFICIENT SAMPLE | same, `*_band` |
| Share of months where both tests pass | 139 / 107 / 129 months | 3.6% / 4.7% / 3.1% | same, `cointegration.both` |

Per-trade files: `audit/phaseE/e1_trades_<pair>_<variant>[_band].csv`, e.g. [e1_trades_XAU-XAG_V3.csv](../../../audit/phaseE/e1_trades_XAU-XAG_V3.csv).

## Code and how to rerun
- Code: [e1_pairs.py](../../../audit/phaseE/e1_pairs.py), [lib.py](../../../audit/phaseE/lib.py), [fetch_public.py](../../../audit/phaseE/fetch_public.py), OU fit from [ou_estimator.py](../../../originals/gann_bot_500/research/goldbot/goldbot/ou_estimator.py).
- Audit rerun stage: `e1` ([run_all.sh:63](../../../audit/tools/run_all.sh)), after `e2_prep`.
- Public data enough? Yes: groups `dukascopy_m1`, `dukascopy_xag`, `binance`, `public_api`. `public_api` files grow on every fetch, so the GDX hash will differ.

## Corrections from the release review
- "`audit/phaseE` (not published)" is wrong. [audit/phaseE](../../../audit/phaseE) is published, with e1_pairs.py, e1_result.json and all trade CSVs.
- "Splits: see prereg" and "Gates: see prereg" point to a spec that holds neither. They are in [audit/prereg/COMMON.md](../../../audit/prereg/COMMON.md): dev 50% / validation 20% / holdout 30%; PF >= 1.20, 2x-cost PF >= 1.00, n >= 100, twin p < 0.05, and DSR >= 0.95 on holdout.
- "Variants counted in the ledger: 9" leaves out the 9 band cells (AUD-E1-BAND). The total is 18.
- "Rerun, recorded clock: new" is not a result. This was a new audit run; there is no stored claim to rerun.
- "Source: audit brief" is not a published file.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Frozen rule 7 cells INSUFFICIENT SAMPLE, 2 FAIL at dev. Validation not evaluated. See audit/phaseE/e1_result.json. |
| Rerun, recorded clock | new |
| Rerun, true UTC | new |

## Verdict
VERIFIED. Nothing reached validation, so validation and holdout were not evaluated. On the frozen rule 7 cells are INSUFFICIENT SAMPLE at dev and 2 FAIL: XAU/XAG V3 n=109 PF 0.03, BTC/ETH V3 n=310 PF 0.618. The 2-to-4 entry band is a logged deviation, shown beside the frozen rule, and all its cells are INSUFFICIENT SAMPLE. Bugs fixed and logged in CHANGES.

## Audit caveats
See audit/DECISIONS.md

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [audit/phaseE](../../../audit/phaseE)
