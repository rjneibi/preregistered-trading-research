# SWEEP-MTF-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-26. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Two-timeframe swing sweep has edge.

Family: ICT/SMC. Market: XAUUSD. Timeframe: H1->M5, H4->M15. Idea source: ICT video. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A two-timeframe "liquidity sweep" setup from a video: a higher-timeframe swing high (or low) is swept on the lower timeframe, then a lower-timeframe bar closes back on the other side of the level; enter against the sweep. Four variants (A-D) were pre-registered, each with a 2R or 3R target chosen in-sample. All four failed.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): A and C, D: H1 levels, M5 entries; B: H4 levels, M15 entries. All bars built from M1 in UTC; exits simulated on M1 ([spec.md](../../../experiments/ict-smc/SWEEP-MTF-1/spec.md); [sweep_mtf.py](../../../originals/gann_bot_500/research/sweep_mtf/sweep_mtf.py) `VARIANTS`).
- Data source and file(s): `research/d_revival/m1.npz`, XAU M1 bid. It is a splice: HistData M1 to 2026-06-19 plus a broker MT5 export (ta_lab `XAU_M1.npy`) from 2026-06-26, stored in broker time (UTC+2/+3) ([data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2, 17-22). data/manifest.csv classes `d_revival/m1.npz` as `broker_mt5` (not public). sweep_mtf.py converts to UTC by subtracting 2 h, or 3 h in US daylight time (`to_utc`, lines 32-46).
- Period: 2010-01 to 2026-10-12 (sweep_mtf.py `END`).
- In-sample / out-of-sample: MAIN = 2023-10-12 to 2026-10-12. IS = first 2 years of MAIN (to 2025-10-12), OOS = last 12 months. HIST = 2010-01 to 2016-12 and 2017-01 to 2023-10-11, used only for gates (spec.md "Windows"; sweep_mtf.py `MAIN0`, `OOS0`, `WIN`).

## Rules
From spec.md "Rules" and sweep_mtf.py. Short side shown; longs mirror on swing lows.
- Entry: HTF swing high = bar j with high strictly above the highs of the 3 bars on each side, usable after bar j+3 closes. Sweep = first LTF bar after confirmation with high > level; the level is then consumed. Confirmation = first LTF bar, within 12 bars from the sweep bar, with high > level and close < level; otherwise cancelled. Enter short at the next LTF bar's open; skipped if that bar starts more than 60 minutes later.
- Exit (stop, target, time): stop = highest LTF high from sweep bar to confirmation bar + $0.20 (skipped if entry >= stop). Target 2R or 3R. Stop and target on the same M1 bar = stop; a gap through the stop fills at the open. Time cap 288 LTF bars, then exit at the close.
- Filters: one open position at a time per variant. C adds an H4 trend filter (short only if the last closed H4 close < H4 EMA50). D adds entry time 07:00-20:00 UTC.
- Position sizing: results in R (risk = entry-to-stop distance per oz) (sweep_mtf.py line 253, `(pnl - COST) / risk`).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| HTF swing N | 3 bars each side | sweep_mtf.py `SWING_N` |
| Confirmation window | 12 LTF bars | `CONFIRM_BARS` |
| Stop buffer | $0.20 | `STOP_BUF` |
| Targets | 2R, 3R | `TARGETS` |
| Time cap | 288 LTF bars | `CAP_BARS` |
| Max entry gap | 3,600 s | `MAX_GAP` |
| Trend filter (C) | H4 EMA50, last closed H4 bar | sweep_mtf.py lines 89-105 |
| Session (D) | 07:00-20:00 UTC | spec.md |
| Twin seeds | 20 | `SEEDS` |

## Costs
Flat cost per round trip, subtracted per oz before dividing by risk (sweep_mtf.py `COSTS`, line 21): base $0.40/oz ($0.30 spread + $0.10 slippage, bid-only data) for all gates. Also shown: $0, $0.22 ("IC"), and stress $0.80 (spec.md "Data").

## Tuning and selection
- Search: 4 pre-registered variants; for each, target 2R vs 3R.
- Configurations run (counted from the code/results): 8 cells (4 variants x 2 targets); 4 judged ([summary.txt](../../../originals/gann_bot_500/research/sweep_mtf/results/summary.txt)). Ledger count (registry/trial_ledger.csv, SWEEP-MTF-1): 4. The ledger counts judged cells only, not the 8 run.
- How the reported variant was chosen: per variant, the target with the higher IS net avg R (sweep_mtf.py line 206, "IS-only pick"). Picks: A 2R, B 3R, C 3R, D 2R (summary.txt). No OOS or HIST data were used to pick.
- Preregistered: yes ([PREREG.md](../../../originals/gann_bot_500/research/sweep_mtf/PREREG.md), copied as spec.md, dated 2026-10-26 "before any run"). No deviation found in the code.

## Results
PASS per variant needs all of: IS net avg R > 0; OOS net avg R > 0 with n >= 30; real minus twin >= 0.05R in IS and in OOS; HIST net avg R > 0 in both halves; t(real vs twin, 2010-2026) >= 2.8 (spec.md).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| A 2R, MAIN 3y | 2,095 | net -0.239R, PF 0.70; twin -0.189R | summary.txt |
| A 2R, IS / OOS | 1,427 / 668 | net -0.307R / -0.094R | summary.txt |
| A 2R, ALL 2010-26 | 12,149 | gross +0.014R, net -0.307R, PF 0.64; t -0.80; FAIL | summary.txt; [trades_A_2R.csv](../../../originals/gann_bot_500/research/sweep_mtf/results/trades_A_2R.csv) |
| B 3R, MAIN / ALL | 530 / 3,151 | net -0.136R / -0.188R, PF 0.83 / 0.78; t -1.51; FAIL | summary.txt |
| C 3R, MAIN / OOS / ALL | 841 / 270 / 5,046 | net -0.152R / +0.033R / -0.262R; PF 0.82 / 1.04 / 0.72; t +0.80; passes only the OOS and OOS-twin gates; FAIL | summary.txt |
| D 2R, MAIN / ALL | 1,373 / 8,623 | net -0.231R / -0.301R, PF 0.71 / 0.65; t -1.59; FAIL | summary.txt |
| Verdict | | 0 of 4 pass | summary.txt |
| Audit rerun, recorded clock | | identical to stored summary | audit/phaseC/logs_L1/recorded.sweep_mtf.sweep_mtf_py.log |
| Audit rerun, true clock | e.g. B 3R MAIN 532 | 4 of 4 FAIL; small number changes (B 3R MAIN net -0.132R vs -0.136R) | audit/phaseC/logs_L1/true.sweep_mtf.sweep_mtf_py.log |

## Code and how to rerun
- Code: [sweep_mtf.py](../../../originals/gann_bot_500/research/sweep_mtf/sweep_mtf.py) (writes results/summary.txt, trades_*.csv, report_data.json), [report.py](../../../originals/gann_bot_500/research/sweep_mtf/report.py), data loader [data.py](../../../originals/gann_bot_500/research/d_revival/data.py). Audit queue [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) (jobs `recorded sweep_mtf sweep_mtf.py` and `true sweep_mtf sweep_mtf.py`).
- Audit rerun stage: `l1_queue` (audit/tools/run_all.sh).
- Public data enough? No. `d_revival/m1.npz` is manifest group `broker_mt5`. Its HistData part (group `histdata_xau`) is public; the tail from 2026-06-26 comes from a broker export (data.py).

## Corrections from the release review
- README "Data: 2010-2026" hides the source. It is a splice of HistData M1 bid (to 2026-06-19) and a broker MT5 export (from 2026-06-26), stored in broker time and converted to UTC in code; the file is classed `broker_mt5`, so it is not public (data.py lines 1-2, 17-22; data/manifest.csv).
- README "Rules: Variants A-D" gives no rules. The swing, sweep, 12-bar confirmation, stop, target and time-cap rules are in spec.md and sweep_mtf.py.
- README "Gates: t>=2.8, twin" is incomplete. Each variant also needs IS net > 0, OOS net > 0 with n >= 30, real minus twin >= 0.05R in IS and OOS, and both HIST halves net > 0 (spec.md).
- README "Stored: net -0.24R" gives no n and no window. It is variant A 2R on the MAIN 3-year window, n=2,095. On 2010-2026 the same cell is n=12,149, net -0.307R, PF 0.64 (summary.txt).
- README "Rerun, true UTC: same" is loose. The verdict is the same (4 of 4 FAIL), but some numbers move slightly (true.sweep_mtf.sweep_mtf_py.log).
- README "Variants counted in the ledger: 4" counts judged cells. 8 cells (4 variants x 2 targets) were run, with the target picked on IS (sweep_mtf.py line 206).
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link sweep_mtf.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 4/4 FAIL; net -0.24R |
| Rerun, recorded clock | 4/4 FAIL |
| Rerun, true UTC | same |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/sweep_mtf/results/summary.txt](../../../originals/gann_bot_500/research/sweep_mtf/results/summary.txt)
