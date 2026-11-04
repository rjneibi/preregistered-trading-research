# SW-1

**Audit verdict: REPRODUCES-BUT-FRAGILE.** Original verdict: PASSED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Swing rules beat the twin.

Family: swing. Market: indices, gold, silver. Timeframe: D1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Ten classic daily swing rules (six mean-reversion, four trend/momentum) were run through one engine with the same costs and gates. US500 was the discovery market. A rule that passed on US500 was then checked on four index/ETF markets it had not been gated on. Gold was run for comparison only and was never gated. Only MR2 (buy when the close is in the bottom 20% of the day's range) passed and was confirmed. Source: [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 1-22.

## Instruments and data
- Instruments: US500 (discovery); US30, USTEC, IWM, EWA (confirm); XAUUSD (comparison). No silver is loaded. [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) lines 135, 138.
- Timeframe(s): D1. [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py) line 33.
- Data source and file(s): broker MT5 demo export, `research/cross_market/data/<SYM>_D1.npz` (manifest group `broker_mt5`, access `broker`, not published). [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) lines 2, 36-41; [data/manifest.csv](../../../data/manifest.csv).
- Period: US500 D1 file runs 2012-08-06 to 2026-10-13, 3,630 rows ([data_profile.json](../../../audit/infrastructure/data_profile.json), key `cm_us500_d1`). The first 252 bars are warm-up (swing_lab.py line 92); the first US500 trade is 2013-11-07 ([SW-1-MR2.csv](../../../audit/trade_checks/SW-1-MR2.csv)). XAUUSD D1 runs 2004-06-11 to 2026-10-13 (`cm_xau_d1`). Start and end dates for US30, USTEC, IWM and EWA: Not recorded in the published files.
- In-sample / out-of-sample: no time split. "Halves" are the first and second half of each rule's own trade list by count (swing_lab.py lines 128-131). The out-of-market check is the four confirm markets.

## Rules
- Entry: signal at the daily close of bar i, enter at the open of bar i+1 (swing_lab.py lines 3, 99). Signals are blocked on the first 252 bars (line 92). One position at a time (lines 94-105). MR2 entry: IBS = (close - low)/(high - low) < 0.2 (lines 44, 65). Other rules: MR1 RSI2<10 and close>SMA200; MR3 three down closes and close>SMA200; MR4 close<lower Bollinger(20,2) and close>SMA200; MR5 close = 7-day low and close>SMA200; MR6 RSI2>90 and close<SMA200, short; TR1 close>prior 55-day high; TR2 SMA50>SMA200 and close back above EMA20 after at least 3 closes below; TR3 close = 252-day high; TR4 prior day NR7 and close above that day's high (lines 62-85).
- Exit (stop, target, time): exit at the open after the exit condition, or after 15 days at most (lines 29, 97-99). MR2 exit: IBS>0.8 or close > previous day's high (line 65). Other exits: MR1/MR6 close vs SMA5; MR3 first up close; MR4 close>SMA20; MR5 close = 7-day high; TR1 close<prior 20-day low; TR2 close<SMA50 or close > entry close + 2 ATR; TR3 close<SMA50; TR4 after 5 days (lines 62-85). No price stop.
- Filters: SMA200 trend filter on MR1, MR3, MR4, MR5, MR6 (lines 60-73). None on MR2.
- Position sizing: none. Each trade is a percentage return on unit notional (line 101). The audit also reports a compounded total (208.6%) in [pass_audit.json](../../../audit/stats/pass_audit.json).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| IBS entry / exit threshold | < 0.2 / > 0.8 | swing_lab.py lines 44, 65 |
| RSI | period 2, EWM alpha 0.5; thresholds 10 and 90 | lines 41-42, 63, 73 |
| SMAs | 5, 20, 50, 200 | line 38 |
| EMA | span 20 | line 39 |
| Bollinger | 20, 2 SD | line 45 |
| Channel | 7-day close low/high; 55-day high, 20-day low (shifted 1); 252-day close high | lines 46-48 |
| ATR | 14-day simple mean of true range | lines 50-51 |
| NR7 | range = narrowest of 7 | line 52 |
| Max hold | 15 days | line 29 |
| Warm-up | 252 bars | line 92 |
| Twin draws | 2,000, seed 11 | lines 28, 109 |

## Costs
- Spread: 1.5 x the median recorded spread of the symbol's file, charged once per trade as spread / entry price ([xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py) line 41; swing_lab.py line 101). If the file has no positive spread, 0.0002 x median close is used instead (swing_lab.py lines 35-36). The docstring calls this a "2bp floor", but the code applies it only when the spread is zero.
- Financing: 5%/yr of notional per calendar night on longs, 1.5%/yr on shorts (lines 89, 100-101).
- Commission and slippage: none separate. Cost stress in the audit: PF 1.697 at 2x cost, 1.653 at 3x ([pass_audit.json](../../../audit/stats/pass_audit.json)).

## Tuning and selection
- Search: no parameter search. Ten fixed rules (swing_lab.py line 134), each run on US500, the four confirm markets and XAUUSD (lines 138-157).
- Configurations run (counted from the code/results): 60 (10 rules x 6 markets). Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row SW-1, n_variants): 50, "exact". The ledger counts 10 rules x 5 markets and leaves out the gold column. The audit's PBO uses 10 variants ([pass_audit.json](../../../audit/stats/pass_audit.json) `cscv`).
- How the reported variant was chosen: by the pre-declared gate, not by ranking. PASS on US500 = PF >= 1.15 in both halves, n >= 30 per half, and twin p < 0.005. CONFIRMED = also PF > 1.0 on at least 3 of the 4 confirm markets (swing_lab.py lines 5-7, 147, 154, 158). MR2 is the only rule that passed.
- Preregistered: partly. The gate and rule list are marked "pre-declared" in the code docstring (swing_lab.py line 1). There is no separate prereg file. The original dated record, `DECISIONS.log`, is not in the repo.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| MR2 US500, all | 397 | PF 1.741, win 69.5%, avg +0.298%/trade | [pass_audit.json](../../../audit/stats/pass_audit.json) |
| MR2 US500, half 1 / half 2 | 198 / 199 (by count) | PF 1.50 / 2.02; twin p 0.004 | [recorded.cross_market.swing_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.swing_lab_py.log) |
| MR2 confirm US30 / USTEC / IWM / EWA | 383 / 96 / 722 / 717 | PF 1.24 / 1.99 / 1.29 / 1.02 (USTEC: INSUFFICIENT SAMPLE) | same log |
| MR2 US500, entry delayed 1 bar | 397 | PF 1.293 (2 bars 1.284, 3 bars 1.46) | [deferred_checks.json](../../../audit/phaseC/deferred_checks.json) `shift` |
| MR2 US500, without top 5 trades | 392 | PF 1.558 | pass_audit.json |
| MR2 US500, without 2020 | 355 | PF 1.541 | [review_f/out/f6.out](../../../audit/review_f/out/f6.out) (saved 2026-11-03, audit DECISIONS 63) |
| Other 9 rules, US500 | 29 to 150 each | all "fail"; MR1 n=122 PF 1.52/3.42 p=0.021 closest | swing_lab log |
| XAUUSD, all 10 rules | n not printed | PF by half only; not gated | swing_lab log |
| DSR at ledger N 179,000 / family N 50 | 397 | 0.207 / 0.867 | [VERDICTS.md](../../../audit/VERDICTS.md) line 118 |
| PBO (10 variants) | - | 0.167 | pass_audit.json |

## Code and how to rerun
- Code: [swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py), with loader and costs in [xm_lab.py](../../../originals/gann_bot_500/research/cross_market/xm_lab.py). Audit rewrite: [pass_audit.py](../../../audit/stats/pass_audit.py) lines 204-231. Delay test: [deferred_checks.py](../../../audit/phaseC/deferred_checks.py) line 51. Look-ahead check: [lookahead2.py](../../../audit/phaseC/lookahead2.py) lines 36-66.
- Audit rerun stage: `l1_queue` (job `recorded cross_market swing_lab.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)); `adj_run` for the split-adjusted rerun; `pass_audit` for the statistics ([run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? No. It needs `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv)). `pass_audit` is listed in [stages_broker.txt](../../../audit/tools/stages_broker.txt).

## Corrections from the release review
- README says "Market: indices, gold, silver". Wrong. The code runs US500, US30, USTEC, IWM, EWA and XAUUSD. No silver (swing_lab.py lines 135, 138).
- README says "gold and silver no rule". Wrong on both parts. Silver was not run. Gold was run but never gated, its n is not printed, and four rules (MR3, MR4, MR5, TR3) show PF >= 1.15 in both gold halves (swing_lab log).
- README "Rules: 10 rules." Incomplete. The ten rules and MR2's exact entry and exit are in swing_lab.py lines 9-21, 62-85.
- README "Costs: next-open". Wrong. Next-open is the fill rule. Costs are 1.5x median spread once per trade and financing of 5%/yr long, 1.5%/yr short (xm_lab.py line 41; swing_lab.py lines 89-101).
- README "Gates: twin p<0.005". Incomplete. The gate also needs PF >= 1.15 in both halves, n >= 30 per half, and PF > 1 on 3 of 4 confirm markets (swing_lab.py lines 5-7).
- README "Data: broker demo feed" gives no period. US500 is 2012-08-06 to 2026-10-13 (data_profile.json).
- README "Without 2020, PF 1.54" had no saved output when the review began; only [f6.py](../../../audit/review_f/f6.py) line 53 computed it. The script was rerun unchanged and saved as [review_f/out/f6.out](../../../audit/review_f/out/f6.out): PF 1.541 at n=355 (audit DECISIONS 63).
- README "Variants counted in the ledger: 50". The code ran 60 cells. The gold column is not counted.
- README "Provenance" lists `DECISIONS.log (not published)` and links no audit script, log or trade file. The rerun log, pass_audit.py and SW-1-MR2.csv are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | IBS<0.2 US500 n=397 PF 1.50/2.02 p=0.004; trend rules fail; gold and silver no rule |
| Rerun, recorded clock | n=397 PF 1.50/2.02 p=0.004 |
| Rerun, true UTC | no HistData dependence |

## Verdict
REPRODUCES-BUT-FRAGILE. Rewrite exact. PBO 0.167, which flatters: 10 rules on one market, not the 50 cells searched. One-bar delay PF 1.29. Without 2020, PF 1.54. Spot checks 20/20. DSR: see the deflated Sharpe table in audit/VERDICTS.md.

## Audit caveats
Only MR2 confirmed. Not deflated by programme trial count.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/cross_market/swing_lab.py](../../../originals/gann_bot_500/research/cross_market/swing_lab.py)
