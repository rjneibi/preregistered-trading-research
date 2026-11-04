# Audit verdicts

Each verdict rests on the true-UTC column where the clock matters. Both clocks are shown. Original verdicts are kept in the second column.
A verdict says how far a stored claim holds up. It does not say a strategy works. Nothing here is a statement about future returns.
`REPRODUCES-BUT-FRAGILE` means the numbers are exact but fail the ledger-count deflated Sharpe, DECISIONS 23.
A figure from fewer than 100 trades is `INSUFFICIENT SAMPLE` whether or not the row says so. `same` means the experiment does not use the HistData gold file. `ledger N` is 114,500 variants in Phase C notes. Years 2010-2012 of the gold file are `ASSUMED-CLOCK`, see the last section.

Counts: VERIFIED 38, VERIFIED-WITH-CORRECTIONS 24, UNVERIFIED 11, REPRODUCES-BUT-FRAGILE 4, INVALID 1. 18 entries are excluded by the author's decision and not tested: EXCLUDED-01, EXCLUDED-02, EXCLUDED-03, EXCLUDED-04, EXCLUDED-05, EXCLUDED-06, EXCLUDED-07, EXCLUDED-08, EXCLUDED-09, EXCLUDED-10, EXCLUDED-11, EXCLUDED-12, EXCLUDED-13, EXCLUDED-14, EXCLUDED-15, EXCLUDED-16, EXCLUDED-17, EXCLUDED-18.

| ID | Original | Recorded clock | True UTC | Audit verdict | Note |
|---|---|---|---|---|---|
| ARB-BTC-PAPER | NOT RUN | no result exists | n/a | **UNVERIFIED** | Scaffold. |
| BINANCE-TESTNET-P1 | NOT RUN | no result exists | n/a | **UNVERIFIED** | Infrastructure. |
| GANN-PROFILE-D-BASE | FAILED | MT5 bars not cached | n/a | **UNVERIFIED** | Reported figure only. |
| HA-ADDITIONS | INCONCLUSIVE | MT5 bars not cached | n/a | **UNVERIFIED** | Reported tables only. |
| VP-FILTER | FAILED | Baselines 1.025 / 1.027 | not on the SUSPECT list; not rerun on true UTC | **VERIFIED** | all_summaries identical. |
| FX-TRANSFER-1 | FAILED | 0/9; best 0.90, all 6 D/R files exact | no gold clock | **VERIFIED** | Recomputed from stored trades. R EURUSD OOS PF 1.03 is a single cell. |
| NQ-TRANSFER | UNVERIFIED | no output located | n/a | **UNVERIFIED** |  |
| DR-EDGE-SCREEN | FAILED | D n=1351 PF 1.326; R n=1012 PF 1.06 | D n=1307 PF 1.505; R n=1025 PF 1.014 | **VERIFIED-WITH-CORRECTIONS** | No spread in the original. D at matrix cost: 0.974 recorded, 1.099 true, 1.001 true at p90. Unthrottled and overlapping, so not a strategy. Remains FAILED. |
| LABELSIZING-CORE | NOT RUN | all gating asserts pass, synthetic data | n/a | **VERIFIED** | Rerun in its own pinned environment. No market result. |
| XAU-FLIP-RAW | FAILED | TP5/SL5 0.965, TP5/SL15 1.057 | TP5/SL5 1.024, TP5/SL15 1.147 | **VERIFIED-WITH-CORRECTIONS** | Grid byte-identical on the recorded clock. Still not a tradable result at 20-point cost and above. |
| XAU-R3S3-FADE | FAILED | V3 geometry PF 0.651 | PF 0.736 | **VERIFIED-WITH-CORRECTIONS** | No harness survives. L2 rebuild on V3 entries confirms the rejection. |
| XAU-FINAL-V4 | FAILED | n=565 PF 1.331; 2025 n=51 86.3%, PF 2.90 | n=577 PF 1.145; 2025 n=52 76.9%, PF 1.13 | **VERIFIED-WITH-CORRECTIONS** | Second engine within 1.4%. The 86% year does not survive. Both 2025 slices are INSUFFICIENT SAMPLE. |
| XAU-FINAL-V3 | FAILED | n=432 PF 1.667, net $70,596, DD $6,935 | n=436 PF 1.254, net $33,520, DD $14,959 | **VERIFIED-WITH-CORRECTIONS** | Second engine 428/432 and 427/436 trades within 50c; net differs by gap policy. Spot checks 20/20. Headline is the true-UTC column. |
| DESIGN-A-MODULES | UNVERIFIED | 18 tests pass | n/a | **VERIFIED** | Design B has no artifact. |
| H1 | FAILED | n=472 PF 1.130, old 0.897, p90 1.045 | n=481 PF 1.009, old 0.831, p90 0.933 | **VERIFIED-WITH-CORRECTIONS** | Measured-spread PF 0.952 on true UTC. Spot checks 20/20. Earlier Phase B figure n=478 PF 1.012 is withdrawn. |
| H2 | FAILED | n=193 PF 1.174 | n=200 PF 1.035, old 0.658 | **VERIFIED-WITH-CORRECTIONS** | Partial-matrix claim PF 1.25 also reproduces. |
| H-S | FAILED | Winner OOS PF 0.200, n=56,260 | PF 0.197, n=55,477 | **VERIFIED-WITH-CORRECTIONS** | Stored PF 0.307 reproduces on the partial matrix. |
| H-M | FAILED | Filtered 1.102, uplift -0.028 | 0.999, uplift -0.010 | **VERIFIED-WITH-CORRECTIONS** | Stored 1.206 reproduces on the partial matrix. Guard patched in the true sandbox, DECISIONS 21. |
| FR-M | FAILED | M0 0.102, M4 0.372 exact | M0 0.086, M4 0.350 | **VERIFIED-WITH-CORRECTIONS** | Stored run used the partial matrix. Full matrix: M0 0.019, M4 0.173 recorded; 0.018, 0.165 true. |
| FR-L | FAILED | Reference n=679 PF 0.587 | n=623 PF 0.497 | **VERIFIED-WITH-CORRECTIONS** | Exact on the recorded clock. The PF 2.90 at n=9 is `UNVERIFIED` and `INSUFFICIENT SAMPLE`, is in no file found, and is not a result of this audit. |
| H-N | FAILED | n=66 PF 1.443, old 1.13 | n=65 PF 0.914, old 0.724 | **VERIFIED-WITH-CORRECTIONS** | News-day narrative retired. Both slices are INSUFFICIENT SAMPLE. |
| H-P | FAILED | n=902 PF 1.279, old 0.965 | n=915 PF 1.033, old 0.841 | **VERIFIED-WITH-CORRECTIONS** | Stored PF 1.373 reproduces on the partial matrix. On the full matrix gate 2 reads false. |
| H-B | FAILED | n=432 PF 1.376, old 0.977 | n=436 PF 1.040, old 0.847 | **VERIFIED-WITH-CORRECTIONS** | Binding run exact. |
| HR | FAILED | Routed n=107 PF 1.336, uplift +0.054 | n=105 PF 1.075, uplift +0.007 | **VERIFIED-WITH-CORRECTIONS** | Stored 1.484 reproduces on the partial matrix. |
| SZ | FAILED | One lot old 0.897, new 1.276 | old 0.831, new 1.114 | **VERIFIED-WITH-CORRECTIONS** | Stored tilt figures reproduce on the partial matrix. |
| HV | FAILED | All gates fail | V2 and V3 true, still FAIL: on old 0.879, new 1.288 | **VERIFIED-WITH-CORRECTIONS** | Gate result differs by clock, verdict does not. |
| HCRT | FAILED | n=599 PF 0.86 | n=605 PF 0.913 | **VERIFIED-WITH-CORRECTIONS** | Rises on true UTC, still fails. |
| HSW | FAILED | n=885 PF 0.827 | PF 0.854 | **VERIFIED-WITH-CORRECTIONS** | Rises slightly, still fails. |
| HPF | FAILED | OOS n=27 PF 0.518 | not on the HistData clock | **VERIFIED** | INSUFFICIENT SAMPLE. Identical on the recorded clock. |
| H3-SILVER | NOT RUN | half-life 488h, gate needs 4h to 240h | half-life 504h, gate needs 4h to 240h | **VERIFIED** | Completed in Phase D as frozen. Result: FAILED at validity gate 1, so no trading conclusion. The 504h is an artefact: 57% of the joined spread's movement comes from month-end beta jumps, and with one beta there is no mean reversion. The 4.4% valid share is mostly test power. Both blind predictions were FAIL. |
| H-20 | NOT RUN | not run | not run | **UNVERIFIED** | Withdrawn. The audit did not open the sealed prediction. Premise gone on true UTC. |
| CYCLES-1-10 | INCONCLUSIVE | Net sup-F 2.40 at 2018-12-19; Sidak 0.182, 0.110 | Net 3.65 at 2019-10-24; Sidak 0.954, 0.999 | **VERIFIED-WITH-CORRECTIONS** | Recomputed without swap, so 3.36 and 0.385, 0.206 stay as stored. Cost break exact at 144.43. Cash-close story retired. |
| DOOR-3 | INCONCLUSIVE | 0 of 360 reach $20, max $17.60 | 4 of 353, max $37.86 | **VERIFIED-WITH-CORRECTIONS** | Zero-of-360 claim fails on true UTC. |
| FLIP-BOT-DEFECTS | PASSED | 15 tests pass | n/a | **VERIFIED** | Bot refuses non-demo accounts. No goldbot, flip_scalp or dr_backtest script imports flip_bot.py; the last two import the live levels and signals modules. |
| FORWARD-FLIP-DEMO | INCOMPLETE | no closing report | n/a | **UNVERIFIED** | INCOMPLETE. |
| TA-LAB-R1-R2 | FAILED | -0.19R; +0.04R; +0.06R vs random +0.07R | same, clean clock | **VERIFIED** | Real-gap fills change these by under 0.5R. |
| TA-LAB-R4-SWEEP | FAILED | +0.048/+0.235R; fixed M15 -0.092R PF 0.78 | same, clean clock | **INVALID** | Original figures are a look-ahead leak. The corrected figure in round 12 stands. |
| TA-LAB-R5-R9 | FAILED | All no edge | same, clean clock | **VERIFIED-WITH-CORRECTIONS** | Rounds 8 and 9 reuse the leaky build, so their positive printed figures are invalid. The rejection stands. |
| TA-LAB-R11 | FAILED | n=64 PF 0.73; n=42 PF 1.15 | same, clean clock | **VERIFIED** | Both slices are INSUFFICIENT SAMPLE. Not a test of FINAL_v4: it uses the classic floor R3 and S3 on M15 bars, while FINAL_v4 uses R3 = PP + (H - L) on H1 (found by the second release review). |
| D-REVIVAL | FAILED | n=1432 PF 0.87, -91.7R | New York sensitivity n=1428 PF 0.88 | **VERIFIED** | File is broker time from 2019, DECISIONS 20. |
| BOT-LAB-1 | FAILED | NFP PF 1.99-2.29 at $0.80 | same | **VERIFIED** | Reruns exact. |
| WHY-1 | PASSED | 48.2 / 50.0 / 49.8, VR 0.94-1.05 | same | **VERIFIED** | Claim said 1.06 in the registry; rerun reads 1.05. |
| ML-1 | FAILED | AUC 0.519, shuffled 0.503 | lower thresholds in 2020-26, no skill | **VERIFIED** | Embargo is label resolved before the test year, which exceeds the label horizon. |
| XM-1-A1 | PASSED | n=124, next open PF 2.37, halves 1.65/3.45; close fill 2.54, halves 1.72/3.79 | no HistData dependence | **REPRODUCES-BUT-FRAGILE** | Rewrite exact. PBO 0.508 on a grid the audit chose. 4 of 14 years lose. In market 11% of days: 4.1%/yr against buy-and-hold 12.3%, with a similar Sharpe and a smaller drawdown. One-bar delay PF 1.80. Spot checks 20/20. DSR in the table below. |
| XM-1-OTHERS | FAILED | All fail, abs(corr) < 0.03 | same | **VERIFIED** | Reruns exact. |
| SW-1 | PASSED | n=397 PF 1.50/2.02 p=0.004 | no HistData dependence | **REPRODUCES-BUT-FRAGILE** | Rewrite exact. PBO 0.167, which flatters: 10 rules on one market, not the 50 cells searched. One-bar delay PF 1.29. Without 2020, PF 1.54. Spot checks 20/20. DSR in the table below. |
| SC-1 | FAILED | n=987 PF 1.22/1.30 p=0.001 | no HistData dependence | **VERIFIED** | Rewrite exact, spot checks 20/20, twin p 0.0025. Realistic entries PF 1.247. DSR 0.81 at N=18, 0.03 at ledger N. 2026 PF 0.88, sealed PF 0.87. Former PASS stays failed. |
| VS-1 | FAILED | All FAIL | same | **VERIFIED** | Reruns exact. |
| CR-1 | FAILED | All FAIL twin gate | same | **VERIFIED** | Reruns exact. |
| EDGE-1-F1 | FAILED | Net Sharpe -0.27 | same | **VERIFIED** | Reruns exact. |
| EDGE-1-F2 | NOT RUN | not run | n/a | **UNVERIFIED** | 4 of 9 ETFs have history. |
| EDGE-1-F3-F5-F7 | FAILED | All FAIL | same | **VERIFIED** | Reruns exact. |
| EDGE-1-F6 | PASSED | Sharpe 1.52 vs 0.96, DD 26.6/48.3 | no HistData dependence | **REPRODUCES-BUT-FRAGILE** | Rewrite exact. PBO 0.742 on 5 variants, all with Sharpe 1.03 to 1.52, so it shows which neighbour won and not whether trend works. Delay barely matters: 1.52, 1.50, 1.43 at lags 1, 2, 3. Sharpe 0.33 since 2025. The twelve coins stay hindsight picks, so survivorship is not cleared. E5: Sharpe 1.36 to 1.49 on real cost tiers, 1.51 with eight collapsed coins added. Spot checks 20/20. |
| EDGE-1-F9 | INCONCLUSIVE | Sharpe 3.01, DD 1.9% on 5 streams | same | **VERIFIED-WITH-CORRECTIONS** | Script later added TSMOM, which reads 2.58. Stays INCONCLUSIVE. Replaced by the descriptive E3, which gives no verdict. |
| EXIT-2-FLIP | FAILED | All 6 FAIL; E5 PF 1.01 n=714 | E5 PF 1.00 n=715 | **VERIFIED** | Reruns exact. |
| GOLD-LIT-1 | FAILED | All 6 FAIL | unchanged | **VERIFIED** | Reruns exact. |
| PA-1 | FAILED | 18/18 FAIL; D1 IB +0.134R | +0.137R | **VERIFIED** | Reruns exact. |
| PA-1B | FAILED | 0/4 > 0 | ib_confirm FAIL | **VERIFIED** | Reruns exact. |
| PA-15-30 | FAILED | 16/16 FAIL | same | **VERIFIED** | Reruns exact. |
| PA-30-MAX5 | FAILED | 20/20 FAIL | same | **VERIFIED** | Reruns exact. |
| TVS-1 | FAILED | Phase 1: 1,296 rows, trade metrics 100%; Phase 2 stored 0/20 on 64,521 configs | same | **VERIFIED-WITH-CORRECTIONS** | The stored search cannot be replayed: its grid seed uses Python's salted hash, a defect. All 1,020 stored configs checked re-evaluate exactly, including the top 20. A new draw of 64,431 configs also gives 0/20. Random-baseline columns are unseeded and differ. TVS-1's own DSR counts its own configs, not the ledger, and its best config reads 0.957 stored and 0.969 rerun. A pass needed eight conditions at once, and no config met them all. |
| SWEEP-MTF-1 | FAILED | 4/4 FAIL | same | **VERIFIED** | Reruns exact. |
| TUNE-1-DIP | PASSED | HOLD-T n=122 PF 3.05; HOLD-M n=2,158 PF 1.59 raw, n=2,195 PF 1.36 split-adjusted | same | **REPRODUCES-BUT-FRAGILE** | The registered test failed: 0 of 3 finalists passed. PASSED in the registry attaches to the live baseline, which had no gate, and which is the same rule as XM-1-A1, so this is not a fourth independent result. HOLD-M 1.59 came from a reverse split in raw ETF prices, one EWJ trade booking +295%. Adjusted HOLD-M PF is 1.36 with 83% of markets above 1. Holdout CONTAMINATED. Spot checks 20/20 did not reach HOLD-M. |
| TUNE-1-ORB | FAILED | Live ORB-30 n=245 PF 0.87 | same | **VERIFIED** | Holdout CONTAMINATED. Byte-identical. |
| CRT-FVG-1 | FAILED | 0/15 PASS, cells and 3,829 trades exact | true UTC data | **VERIFIED** | Gap asymmetry at most 0.0045R per cell. |
| LBO-1 | FAILED | OOS -0.0083R n=204 PF 0.98 | true UTC data | **VERIFIED** | Second out-of-sample read happens in a sandbox only, DECISIONS 28. Frozen rule has no target exits. |
| TAEVAL-1 | INCOMPLETE | no result | n/a | **UNVERIFIED** | INCOMPLETE. Stopped by the author before it finished. |
| HLCOPY-1 | INCOMPLETE | no journal | n/a | **UNVERIFIED** | INCOMPLETE. |
| CHANNEL-A | FAILED | P1 PF 0.58 | same | **VERIFIED** | Real beats 1.4% of twins. |
| CHANNEL-C | FAILED | All FAIL | same | **VERIFIED** | Output identical. |
| CHANNEL-B-SCORE | UNVERIFIED | scored file missing | n/a | **UNVERIFIED** | scored_calls.json not found. Its figures stay out of every summary. |
| E1-PAIRS | FAILED OR INSUFFICIENT SAMPLE | new | new | **VERIFIED** | Nothing reached validation, so validation and holdout were not evaluated. On the frozen rule 7 cells are INSUFFICIENT SAMPLE at dev and 2 FAIL: XAU/XAG V3 n=109 PF 0.03, BTC/ETH V3 n=310 PF 0.618. The 2-to-4 entry band is a logged deviation, shown beside the frozen rule, and all its cells are INSUFFICIENT SAMPLE. Bugs fixed and logged in CHANGES. |
| E2-SILVER-TRANSFER | FAILED | new | new | **VERIFIED** | FAILED. H1 PF 0.487, FINAL_v3 0.683, FINAL_v4 0.450 at silver costs. Twins for FINAL rules reuse H1 holding times. Night fees were not added; all three fail before them. |
| E3-PORTFOLIO | DESCRIPTIVE | new | new | **VERIFIED** | Descriptive only. It cannot produce a pass. |
| E4-NEWS | FAILED | new | new | **VERIFIED** | FAILED. On the frozen cost basis H1 PF 1.008, FINAL_v3 1.056, FINAL_v4 0.898. Events take off under 0.01 of PF: 7, 0 and 15 trades enter in a window. First-minute spreads run 1.43x to 1.51x same-hour non-event days, so the 3x to 6x blind prediction was wrong. Exits use the matrix spread because no exit time is saved. |
| E5-CRYPTO | CORRECTION | new | new | **VERIFIED** | Cost correction of opened slices. No verdict moves. No trend rule passes. MR3 clears CR-1's gate at spot VIP0 at n=82, INSUFFICIENT SAMPLE, and stays failed: these slices were already opened, so a verdict cannot improve, and p 0.003 against 0.007 and 0.008 on the other tiers is noise. F6 Sharpe 1.36 to 1.49. Coin history stays incomplete: only 8 dead coins added. |
| E6-PAPER | INSUFFICIENT SAMPLE | new | new | **VERIFIED** | INSUFFICIENT SAMPLE. 6 of 19 demo trades matched. Median exit gap on those 6 is $11.66, mostly because the bot trails and the backtester does not. |
| E7-INDICATORS | FAILED | new | new | **VERIFIED** | FX FAILED at dev. Gold INSUFFICIENT SAMPLE at dev and CONTAMINATED in advance. FX costs are charged on mid prices with a measured spread, which suits a rule this size. |

## Results with PF above 1.1 that are not passes

A PF above 1.1 here does not mean a pass. Each row names what it fails. FINAL_v3's 1.254 and FINAL_v4's 1.145 use a flat assumed cost, and measured costs take them far lower.

| Result | PF | Basis | Fails | Why it does not count |
|---|---:|---|---|---|
| XAU-FINAL-V3 | 1.254 | true UTC, flat 20-pt cost, n=436 | H-B gate 1, PF >= 1.35 at matrix costs: 1.040, short by 0.310; H-B gate 2, each era PF >= 1.00: old era 0.847, short by 0.153; H-B gate 3, 11 of 15 splits positive: 9, short by 2; H-B gate 4, p90 PF >= 1.15: 0.989, short by 0.161; old-era p90 >= 0.90: 0.811 | The 1.254 uses an assumed flat cost well under measured spreads. H-B is the same rule at measured costs, and n matches at 436. |
| XAU-FINAL-V4 | 1.145 | true UTC, flat 20-pt cost, n=577 | Programme gate 1, PF >= 1.20: 1.145 at flat cost, short by 0.055; Approximate matrix cost, entry hour used for both sides: PF 0.899, short by 0.301; Same approximation at p90: PF 0.843 | No pre-registered gate exists for V4, so H1's gate is used. The check on V3 by the same approximation gives 1.056 against H-B's 1.040. |
| DR-EDGE-SCREEN D | 1.505 | true UTC, no spread in the screen, n=1,307 | Programme gate 1, PF >= 1.20 at matrix cost: 1.099, short by 0.101; At p90 cost: 1.001 | Unthrottled entry screen, not a strategy. The 1.505 has no spread. |
| XAU-FLIP-RAW TP5/SL15 | 1.147 | true UTC, raw grid cell, flat 20-pt cost | Programme gate 1, PF >= 1.20: 1.147, short by 0.053; One cell of a grid, no gate of its own | Grid cell picked after the fact. |
| SC-1 ORB-30 | 1.259 | no HistData dependence, n=987 | Later sealed read of the live ORB baseline in TUNE-1: PF 0.87, losing; DSR at ledger N 0.03 against 0.95; 2026 PF 0.88 | Stays failed. |
| XM-1-A1 | 2.372 | no HistData dependence | DSR >= 0.95 at ledger N: 0.29, short by 0.660 | Numbers exact. Fragile by the stored PBO, delay and benchmark results. |
| SW-1 | 1.741 | no HistData dependence | DSR >= 0.95 at ledger N: 0.207, short by 0.743 | Numbers exact. Fragile by the stored PBO, delay and benchmark results. |
| TUNE-1-DIP | 3.05 | no HistData dependence | DSR >= 0.95 at ledger N: 0.489, short by 0.461; Registered test: 0 of 3 finalists passed; Trades cluster in 60 weeks. Averaged by week, ledger DSR is 0.142 | PF 3.05 is an unregistered read of the baseline, the same rule as XM-1-A1. It is not a fourth independent result. |
| EDGE-1-F6 | n/a | Sharpe 1.52, daily | DSR >= 0.95 at ledger N: 0.52, short by 0.430; PBO 0.742 on 5 variants | Numbers exact. E5 reads Sharpe 1.36 to 1.49 on real cost tiers. |
| TA-LAB-R4 fixed, 2025+ | 1.29 | slice, n=398 | <2025 slice PF 0.78, below 1.0; Beats 45% of twins; Same-bar worst case PF 1.15 | A later slice of a failed rule. |
| TA-LAB-R11, 2025+ | 1.15 | slice, n=42 | INSUFFICIENT SAMPLE | Under 100 trades. |

## Deflated Sharpe, two counts

Primary DSR uses the ledger count, now 179,000 variants. Phase C files hold the same statistic at 114,500. Secondary DSR uses the variants in the programme that produced the result, and it decides nothing. The dated column uses the ledger as it stood on the result's own date. Read all of these as orders of magnitude: `stats/TRIAL_COUNT.md`.

| Result | Primary DSR, ledger N | Secondary DSR, family N | Family N | DSR at dated N | Dated N |
|---|---:|---:|---:|---:|---:|
| XAU-FINAL-V3 | 0.002 | 0.285 | 41 |  |  |
| XAU-FINAL-V4 | 0.0 | 0.12 | 41 |  |  |
| XM-1-A1 | 0.29 | 0.934 | 17 | 0.705 | 569 |
| SW-1 | 0.207 | 0.867 | 50 | 0.659 | 569 |
| TUNE-1-DIP | 0.489 | 0.695 | 3960 | 0.537 | 71185 |
| EDGE-1-F6 | 0.52 | 0.993 | 34 | 0.928 | 625 |

TUNE-1-DIP's trades cluster in 60 weeks. Averaged by week, its ledger DSR is 0.142. EDGE-1-F6 clears 0.95 only on the secondary count, and the verdict uses the primary.

## ASSUMED-CLOCK: 2010-2012

2010-2012 HistData stamps have no Dukascopy overlap. The US switch rule there is an assumption, supported only by reopen and break hours.

| Result | With 2010-2012 | Without 2010-2012 |
|---|---|---|
| D-REVIVAL | D faithful n= 1432 win=50% PF=0.87 net= -91.7R avg=-0.064R maxDD=100.0R | D faithful n= 1159 win=50% PF=0.86 net= -78.4R avg=-0.068R maxDD=95.7R |
| WHY-1 pivots | pivot n= 10678 bounce 48.2% by era 47.5% 48.7% 48.6% 48.2% | pivot n= 8750 bounce 48.1% by era 43.0% 48.7% 48.6% 48.2% |
| BOT-LAB-1 buy & hold control | buy & hold total $ 3069/oz sharpe +0.55 halves +0.20 / +0.89 maxDD $1435 | buy & hold total $ 2504/oz sharpe +0.48 halves -0.07 / +0.92 maxDD $1435 |
| BOT-LAB-1 Asia long | long 01-09 spread 0.6 n=4066 win=50% PF=1.17 halves 0.97/1.26 total $2047/oz DD $558 | long 01-09 spread 0.6 n=3285 win=50% PF=1.20 halves 0.91/1.29 total $2036/oz DD $558 |
| EXIT-2-FLIP E5 | ALL: n714 avg+0.005R PF1.01 vs twin t=+2.00 | ALL: n570 avg-0.011R PF0.97 vs twin t=+1.13 |
| GOLD-LIT-1 H-A1 | ALL net t=-0.14 by year $/oz: 10:+39 11:-26 12:-13 13:+23 14:-6 15:+4 16:+22 17:-58 18:-188 19:-129 20:-100 21:+179 22:-151 23:-57 24:+137 25:+358 26:-161 | ALL net t=-0.14 by year $/oz: 13:+23 14:-6 15:+4 16:+22 17:-58 18:-188 19:-129 20:-100 21:+179 22:-151 23:-57 24:+137 25:+358 26:-161 |
| PA-1 H4 PIN | H4 PIN n 1766 gross +0.034 IC -0.011 net -0.048R win 37% | A n773 -0.128 tw-0.082 | B n993 +0.015 tw-0.026 | C n436 -0.076 tw-0.028 | t +0.07 -> FAIL | H4 PIN n 1476 gross +0.058 IC +0.013 net -0.024R win 38% | A n483 -0.102 tw-0.096 | B n993 +0.015 tw-0.037 | C n436 -0.076 tw-0.054 | t +0.90 -> FAIL |
| SWEEP-MTF-1 variant A | ALL 2010-26 n12149 win 34% avgR gross +0.014 IC -0.163 net -0.307 stress -0.628 | twin -0.296 | PF 0.64 maxDD 3749.1R streak 21 | ALL 2010-26 n 9942 win 34% avgR gross +0.008 IC -0.169 net -0.313 stress -0.635 | twin -0.293 | PF 0.64 maxDD 3127.3R streak 21 |

No pass or fail line changes in any of these reruns. Results not touching those years: H-family, FINAL_v3, FINAL_v4, XAU-R3S3-FADE: start 2015-06; DR-EDGE-SCREEN: 2021-06 on; FR-M: 2021-06 on; XAU-FLIP-RAW: 2021-06 on; FR-L: see its script; TA-LAB, PA-15-30, PA-30-MAX5: 2022-07 on; ML-1: 2014 on; CRT-FVG-1, LBO-1: Dukascopy, measured clock.
