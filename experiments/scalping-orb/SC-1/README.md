# SC-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Intraday rules clear costs.

Family: scalping/ORB. Market: indices, gold. Timeframe: M1. Idea source: Zarattini, Gao et al..

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
SC-1 ran a battery of classic intraday and scalping rules, taken from published work, on three US index CFDs and on gold. Each rule takes at most one trade per day and is flat by the session end. A rule passed if its profit factor was at least 1.15 in both halves of the sample, with at least 100 trades per half, and it beat 2,000 random-direction twins. One cell passed: the 30-minute opening-range breakout on USTEC. A later sealed holdout in TUNE-1 found the live version of that rule losing, so SC-1 is recorded as FAILED.

## Instruments and data
- Instruments: US500, USTEC, US30 (index CFDs); XAUUSD ([scalp_lab.py](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py) lines 3-5).
- Timeframe(s): M1, converted to New York time (scalp_lab.py line 3).
- Data source and file(s): indices from `research/cross_market/data/<sym>_M1.npz`, a broker demo feed with server time read as Europe/Athens (scalp_lab.py lines 39-44); manifest group `broker_mt5`. Gold from [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py): HistData M1 2010-01 to 2026-06-19 plus `ta_lab/data/XAU_M1.npy` from 2026-06-26 (data.py lines 1-2, 15-23), shifted to New York time by -7 h (scalp_lab.py line 57). The XAU_M1.npy file and the cached `d_revival/m1.npz` are manifest group `broker_mt5`.
- Period: US500 and US30 2012-08-05 to 2026-10-13; USTEC 2022-07-06 to 2026-10-13; gold 2010 to 2026 ([logs_L1/recorded.cross_market.scalp_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.scalp_lab_py.log)).
- In-sample / out-of-sample: none. Each rule's trades are split into a first and second half by count (scalp_lab.py `report`, `h = len(r) // 2`).

## Rules
All index rules use the 09:30-16:00 New York session and exit by 16:00 at the latest. If a bar hits both stop and target, the stop is taken first (scalp_lab.py lines 64-76). Days need a clean open and at least 300 session bars (scalp_lab.py `rules_index`).
- Entry and exit, index rules (scalp_lab.py lines 8-18 and `rules_index`):
  - O1 ORB-range N = 5, 15, 30 min: range of the first N minutes; first break of the high goes long, of the low goes short, entered at the range edge; skip the day if one bar breaks both; stop at the other side of the range; exit 16:00.
  - O2 ORB-candle: direction of the first 5-min candle; enter 09:35; stop 10% of the 14-day mean daily range; exit 16:00.
  - M1 intraday momentum: sign of the move from the previous 16:00 close to 10:00; trade that direction 15:30 to 16:00.
  - G1 gap fade: if |09:30 open - previous 16:00 close| > 0.3%, fade at 09:30; target the previous close; stop one gap further; exit 16:00.
  - X1 stretch fade: 10:30-15:00, if price is more than 2.5 x a 30-minute range scale from the session's running mean of typical price, fade at the next open; target the mean; stop 1.25 x that scale further; first signal only.
  - R1 first-hour reversal: fade the 09:30-10:30 move from 10:30 to 16:00; no stop.
- Entry and exit, gold rules (scalp_lab.py lines 19-22 and `rules_gold`):
  - L1 Asia range 19:00-02:59 NY; first break 03:00-11:00 NY; stop other side; exit 11:00.
  - L2 London 15-min ORB 03:00-03:15 NY; stop other side; exit 11:00.
  - L3 NY-open 15-min ORB 09:30-09:45; stop other side; exit 16:00.
- Filters: one trade per rule per day (scalp_lab.py line 6).
- Position sizing: none; returns are fractions of the entry price, reported in basis points (scalp_lab.py `trade`).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ORB window N | 5, 15, 30 min | scalp_lab.py line 8 |
| O2 stop | 0.10 x 14-day mean daily range, lagged 1 day | `rules_index` (`atr`, `st`) |
| G1 gap threshold | 0.3% | scalp_lab.py line 12 |
| X1 stretch / stop | 2.5 x / 1.25 x the 30-bar range scale | scalp_lab.py lines 14-15; `rules_index` |
| Gold windows | Asia 19:00-02:59, London 03:00-11:00, NY 09:30-16:00 (New York time) | scalp_lab.py lines 19-22 |
| Twin replicates | 2,000, seed 5 | scalp_lab.py line 31 and `twin_p` |
| Pass rule | PF >= 1.15 both halves, n >= 100 per half, twin p < 0.005 | scalp_lab.py lines 24-25; `report` |
| Index confirmation | PF > 1.0 on both other indices | scalp_lab.py line 25 |

## Costs
Indices: 1.5 x the median in-session M1 spread of that symbol, charged once per trade; stop exits pay 0.5 x that cost extra (scalp_lab.py lines 4-5, 45-48, `trade`). The rerun log gives 0.45 points for US500, 1.35 for USTEC and 1.50 for US30. Gold: a fixed $0.35 per trade, plus 0.5 x that on stop exits (scalp_lab.py line 59).

## Tuning and selection
- Search: 8 index rules (O1 counted three times for N) on 3 indices, plus 3 gold rules. No parameter was tuned.
- Configurations run (counted from the code/results): 27 rule-market cells (rerun log). Ledger count (registry/trial_ledger.csv n_variants): 18. They differ, and no published file says how 18 was counted.
- How the reported variant was chosen: no selection beyond the pass rule. USTEC O1 30 min was the only cell to pass, and its PF on US500 (1.09) and US30 (1.10) was above 1.0, so it met the confirmation rule (rerun log).
- Preregistered: partly. The rules and pass gate were written in the docstring "before any result was seen" (scalp_lab.py line 1). There is no separate frozen prereg file.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| USTEC O1 ORB 30 min | 987 | PF 1.22 / 1.30 by half; avg +6.79 bp; twin p 0.001: PASS | [logs_L1/recorded.cross_market.scalp_lab_py.log](../../../audit/phaseC/logs_L1/recorded.cross_market.scalp_lab_py.log) |
| USTEC O1 ORB 5 / 15 min | 994 / 995 | PF 1.11/1.32 and 1.12/1.28; twin p 0.007 / 0.006: fail | rerun log |
| US500 O1 ORB 30 min | 2,285 | PF 1.05 / 1.13: fail | rerun log |
| US30 O1 ORB 30 min | 2,276 | PF 1.14 / 1.07: fail | rerun log |
| All other index cells | 274 to 2,319 each | all fail (X1 on USTEC n=274, X1 on US30 n=575) | rerun log |
| Gold L1 / L2 / L3 | 4,110 / 4,312 / 4,068 | PF 1.05/1.08, 0.96/0.90, 1.01/1.00: fail | rerun log |
| Audit independent rewrite, USTEC ORB 30 | 987 | PF 1.259 full; twin p 0.0025; 20 of 20 spot checks; 3.2% of entries were beyond the edge; real-entry PF 1.247 | [sc1_check.json](../../../audit/trade_checks/sc1_check.json) |
| Same, by year 2026 | 191 | PF 0.88 | sc1_check.json `by_year` |
| Same, deflated Sharpe | 987 | 0.81 at N=18; 0.19 at N=2,000; 0.026 at N=114,500 | sc1_check.json `dsr` |
| TUNE-1 sealed holdout of the live ORB-30 baseline (HOLD-T) | 245 | PF 0.87; twin p 0.761 | [logs_L1/recorded.tune1.tune_orb_py_final.log](../../../audit/phaseC/logs_L1/recorded.tune1.tune_orb_py_final.log) line 1 |

## Code and how to rerun
- Code: [scalp_lab.py](../../../originals/gann_bot_500/research/cross_market/scalp_lab.py) (run as a script; it prints every cell), gold loader [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py). Audit check: [sc1_check.py](../../../audit/trade_checks/sc1_check.py), trades [SC-1-ORB30.csv](../../../audit/trade_checks/SC-1-ORB30.csv).
- Audit rerun stage: `l1_queue` (job `recorded cross_market scalp_lab.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)) and `sc1`. `sc1` is in [stages_broker.txt](../../../audit/tools/stages_broker.txt).
- Public data enough? No. The index files and the 2026-06-26+ gold file are manifest group `broker_mt5`. Only the HistData part of the gold data (group `histdata_xau`) is public.

## Corrections from the release review
- README "Variants counted in the ledger: 18" does not match the code. The battery is 8 index rules x 3 indices + 3 gold rules = 27 cells (rerun log); no file explains 18.
- README "Rules: ORB, candle ORB, momentum, gap fade, stretch fade, first-hour reversal" omits every parameter and the three gold rules. They are listed above (scalp_lab.py lines 8-22).
- README "Gates: twin" is incomplete. The gate is PF >= 1.15 in both halves, n >= 100 per half, twin p < 0.005, and for index rules PF > 1.0 on both other indices (scalp_lab.py lines 24-25).
- README "Data: MT5 M1" omits the ranges and the gold source. USTEC covers only 2022-07-06 to 2026-10-13; gold is HistData plus a broker file (rerun log; data.py).
- README "DSR ... 0.03 at ledger N" is mislabelled. 0.0263 is at N=114,500 (sc1_check.json), not the current ledger N used for primary DSR.
- README provenance lists only the unpublished DECISIONS.log. The code, rerun log and audit check are published.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | USTEC ORB-30m n=987 PF 1.22/1.30 p=0.001; others fail |
| Rerun, recorded clock | n=987 PF 1.22/1.30 p=0.001 |
| Rerun, true UTC | no HistData dependence |

## Verdict
VERIFIED. Rewrite exact, spot checks 20/20, twin p 0.0025. Realistic entries PF 1.247. DSR 0.81 at N=18, 0.03 at ledger N. 2026 PF 0.88, sealed PF 0.87. Former PASS stays failed.

## Audit caveats
PASS at the time, but TUNE-1 part 2 found live ORB-30 PF 0.87 n245 over the last 12 months. Recorded FAILED on forward holdout; show both.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
