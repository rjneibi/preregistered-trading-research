# EXIT-2-FLIP

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Letting flip_bot winners run beats the 24h close.

Family: exits. Market: XAUUSD. Timeframe: M1. Idea source: the author. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Entries were fixed: the author's flip_bot v1.2 "conviction" breakout on gold. Only the profit side of the exit was varied. The question was whether the live exit (take-profit +0.8 ATR, hard close at 24 hours) cut winners short, and whether letting them run turns the entries into an edge ([spec.md](../../../experiments/exits/EXIT-2-FLIP/spec.md); copy of [PREREG.md](../../../originals/gann_bot_500/research/exit2/PREREG.md), frozen 2026-10-14 before any run).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 for entries and exit walks; H1 (and H4) bars built from M1 in UTC ([PREREG.md](../../../originals/gann_bot_500/research/exit2/PREREG.md) lines 10-11).
- Data source and file(s): `research/d_revival/m1.npz`, XAUUSD M1 bid. It is a splice of HistData M1 (2010-01 to 2026-06-19) and a broker MT5 export (from 2026-06-26), stored in broker time ([d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2, 17-27). exit2.py converts it to UTC by a US-DST rule: -3h in US DST, -2h otherwise ([exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py) lines 22-36). The manifest classes m1.npz as `broker_mt5` ([data/manifest.csv](../../../data/manifest.csv) row 427).
- Period: entries 2010-01-06 to 2026-09-16 (714 entries) ([audit/phaseC/logs_L1/recorded.exit2.exit2_py.log](../../../audit/phaseC/logs_L1/recorded.exit2.exit2_py.log) line 1).
- In-sample / out-of-sample: none. Three windows, all must pass: A = 2010-2017, B = 2018-2026, C = 2023 onward (C is inside B) (PREREG.md line 30; exit2.py line 155).

## Rules
- Entry (flip_bot v1.2): previous UTC day pivots PP = (H+L+C)/3, R3 = PP + (H-L), S3 = PP - (H-L). Conviction = an H1 close at 12, 16 or 20 UTC beyond R3 (buy) or S3 (sell). Skip Mondays. Skip a level crossed by any of the last 10 H4 closes before 08:00 UTC that day ("dead"). Max 1 trade per direction per day. Enter at the next M1 open (PREREG.md lines 13-17; exit2.py lines 60-85).
- Exit (stop, target, time): stop 2.4 ATR in every variant. Risk managers in every variant: in high volatility, close half at -1.2 ATR; in low volatility, bail at -1.0 ATR after 8 hours. Stop checked before target on the same bar. Profit side per variant:
  - E0 (live): TP +0.8 ATR, hard close 24h
  - E1: no TP, hard close 24h
  - E2: no TP, hard close 72h
  - E3: no TP; at +1 ATR move stop to entry, then trail 2.4 ATR behind the best price; max 5 days
  - E4: TP +0.8 ATR, no time limit (max 10 days)
  - E5: TP +2.4 ATR, hard close 72h
  (PREREG.md lines 17-27; exit2.py lines 15-18).
- Filters: hivol = ATR above its median over the last 90 days of H1 bars (PREREG.md line 14; exit2.py line 83).
- Position sizing: results in R, with risk = 2.4 ATR.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Pivots | PP, R3 = PP + range, S3 = PP - range, previous UTC day | [PREREG.md](../../../originals/gann_bot_500/research/exit2/PREREG.md) line 13 |
| ATR | Wilder 14 on UTC H1 | PREREG.md line 14 |
| Hivol median | 90 days (90 x 24 H1 bars) | [exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py) line 83 |
| Signal hours | H1 closes at 12, 16, 20 UTC | PREREG.md line 15 |
| Dead-level lookback | 10 H4 closes before 08:00 UTC | exit2.py lines 70-73 |
| Stop | 2.4 ATR | PREREG.md line 17 |
| Hivol half-out / lovol bail | -1.2 ATR / -1.0 ATR after 8h | PREREG.md line 18 |
| Variants (TP ATR, max hours, trail) | E0 (0.8, 24, no); E1 (none, 24, no); E2 (none, 72, no); E3 (none, 120, yes); E4 (0.8, 240, no); E5 (2.4, 72, no) | exit2.py lines 15-18 |
| Twin | same days, random H1 close 12-20 UTC, random side, same stop and exit; 20 seeds (0-19) | PREREG.md lines 28-29; exit2.py lines 144-145, 170 |

## Costs
$0.50 per round trip (spread plus slippage), converted to R per trade; stress test at $1.00 ([exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py) line 13; PREREG.md line 27). The stored [exit2_trades.csv](../../../originals/gann_bot_500/research/exit2/exit2_trades.csv) is pre-cost; the gate table in the log is net.

## Tuning and selection
- Search: the 6 exit variants above, fixed before the run. "No variant is added after the run" (PREREG.md line 35).
- Configurations run (counted from the code/results): 6 in exit2.py. Ledger count (registry/trial_ledger.csv n_variants): 6. They match. Not counted in the ledger: a same-day descriptive stop sweep, [own_sweep.py](../../../originals/gann_bot_500/research/exit2/own_sweep.py), with stops of 1.2, 2.4, 3.6 and 4.8 ATR, and a forensic add-on, [forensics.py](../../../originals/gann_bot_500/research/exit2/forensics.py). Both are labelled descriptive, not gates.
- How the reported variant was chosen: no selection. A variant passes only if, in each of A, B and C, avgR beats E0, beats its twin by at least +0.05R, and is net positive at $1.00 cost; and the full-sample twin difference has t >= 2 (PREREG.md lines 31-35).
- Preregistered: yes, [PREREG.md](../../../originals/gann_bot_500/research/exit2/PREREG.md) (sha debb6c97 per the registry). Blind prediction by the assistant: all FAIL, 70%. The author's prediction was not recorded.

## Results
Recorded-clock rerun, net of $0.50, from [recorded.exit2.exit2_py.log](../../../audit/phaseC/logs_L1/recorded.exit2.exit2_py.log).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| E0 live, all | 714 | avg -0.019R, PF 0.90; vs twin t +3.42 (baseline) | recorded log |
| E1, all | 707 | avg -0.021R, PF 0.94; vs twin t -1.47; FAIL | same |
| E2, all | 665 | avg -0.009R, PF 0.98; t -1.11; FAIL | same |
| E3, all | 696 | avg -0.030R, PF 0.89; t -0.83; FAIL | same |
| E4, all | 714 | avg -0.011R, PF 0.95; t +3.70; FAIL | same |
| E5, all | 714 | avg +0.005R, PF 1.01; t +2.00; FAIL | same |
| E5, window A / B / C | 365 / 349 / 149 | avg -0.010 / +0.020 / -0.016R; twin -0.056 / -0.055 / -0.026R | same |
| E5, true UTC clock, all | 715 | avg +0.000R, PF 1.00; t +1.94 | [true.exit2.exit2_py.log](../../../audit/phaseC/logs_L1/true.exit2.exit2_py.log) |
| Own-sweep stop 2.4 ATR (live, simplified exit) | 714 | avg -0.019R; twin -0.081R. Descriptive | [recorded.exit2.own_sweep_py.log](../../../audit/phaseC/logs_L1/recorded.exit2.own_sweep_py.log) |
| Audit | | VERIFIED, reruns exact | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 66 |

All six variants fail. The entries beat their random-time, random-side twins (E0, E4, E5 t above 2), but the margin is about the size of the cost.

## Code and how to rerun
- Code: [exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py) (prints the gate table, writes exit2_trades.csv), [forensics.py](../../../originals/gann_bot_500/research/exit2/forensics.py), [own_sweep.py](../../../originals/gann_bot_500/research/exit2/own_sweep.py); data loader [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py).
- Audit rerun stage: `l1_queue` ([audit/phaseC/run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) lines 39-41 and 71).
- Public data enough? no. m1.npz is group `broker_mt5`. The HistData part (group `histdata_xau`, public) covers only to 2026-06-19.

## Corrections from the release review
- README Data: "M1 2010-01 to 2026-09". Incomplete. The file is a splice of HistData bid and a broker MT5 export, stored in broker time and converted to UTC by a US-DST rule ([d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2; [exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py) lines 22-36). It is not public data.
- README Rules: "6 exits." The six exits, the fixed entry rule and the gate should be stated (see above).
- README Results: "E5 PF 1.01 n=714". Correct for the net log, but [exit2_trades.csv](../../../originals/gann_bot_500/research/exit2/exit2_trades.csv) is pre-cost (PF 1.088 per review 02 item 47). The README should say which.
- README Caveat: "Entries beat a twin with the same exit by 0.05-0.09R". Not supported as a range. Per-window gaps in the log run from 0.010R (E5, window C) to 0.097R (E4, window B).
- README Source: "user". Chat wording; should read "the author" (review O-13).
- The descriptive own-sweep (4 stop sizes) ran on the same data the same day and is not in the ledger count.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | ALL 6 FAIL; n=714 |
| Rerun, recorded clock | All 6 FAIL; E5 PF 1.01 n=714 |
| Rerun, true UTC | E5 PF 1.00 n=715 |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
Entries beat a twin with the same exit by 0.05-0.09R: real but cost-sized.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/exit2/exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py)
