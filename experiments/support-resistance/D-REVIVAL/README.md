# D-REVIVAL

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-13. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Profile D has edge when replayed faithfully.

Family: support/resistance. Market: XAUUSD. Timeframe: M1. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
D-REVIVAL replayed the author's live support/resistance Profile D ("Core + Polarity") on M1 bars from 2010 to 2026, copying the live code paths as they ran on demo in June and July 2026. That includes the live pullback-entry check, which the docstring calls a bug, a $9 fixed target, a partial close, breakeven and trailing stops. Results are in R (initial stop distance). Exit and gate variants were also run.

## Instruments and data
- Instruments: XAUUSD bid bars; ask = bid + spread ([sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py) line 26).
- Timeframe(s): M1, bucketed into H1, H4 and D1 in broker time (sim.py `Bars`).
- Data source and file(s): [d_revival/data.py](../../../originals/gann_bot_500/research/d_revival/data.py): HistData M1 2010-01 to 2026-06-19 shifted +2 h, plus `ta_lab/data/XAU_M1.npy` from 2026-06-26 shifted +3 h, stored as broker time and cached as `d_revival/m1.npz` (data.py lines 1-2, 15-26). Manifest groups: `histdata_xau` (public) and `broker_mt5` for XAU_M1.npy and m1.npz ([data/manifest.csv](../../../data/manifest.csv)).
- Period: 2010-03-01 to 2026-10-13 by default (sim.py `args`, `--start`, `--end`).
- In-sample / out-of-sample: none in sim.py. [battery.py](../../../originals/gann_bot_500/research/d_revival/battery.py) reports each variant split at 2020-01-01 (2010-19 / 2020-26). [split.py](../../../originals/gann_bot_500/research/d_revival/split.py) splits diagnostics at 2018-01-01.

## Rules
From the sim.py docstring (lines 1-25) and defaults (`args`):
- Entry: zones rebuilt at the first tick of each new UTC day from Gann Square-of-9 levels off the broker D1 open, Fibonacci pivots off the previous broker D1 bar, and a Fibonacci retracement over the last 50 H4 bars. Zone = level +/- 0.3 x ATR(H1, 14); levels more than 10 x ATR away are dropped. Signals only at the first tick of each new H1 bar: price inside a zone; side re-evaluated from the last 10 closed H4 closes (polarity); H4 bias (last close vs EMA50 over 200 H4 bars) must agree with the zone side; the last closed H1 body must straddle the level. Default entry mode "bug": the live pullback check on the forming M1 bar, modelled as a fill with probability 0.4 when the bar opens inside the band [zone mid, H1 close], up to 15 M1 bars, cancelled if price runs 1.5 x ATR beyond the zone mid. Alternatives: "intended" (closed M1 bar, next open) and "immediate" (H1 open).
- Exit (stop, target, time): SL 1.0 x ATR; TP fixed $9 from the trigger price; 50% partial at +1 ATR, then SL to entry; breakeven at max(ATR, $15); trail max(ATR, $15); stop first inside a bar. No time stop by default (`--max-hold 0`).
- Filters: one open position; one trade per zone per UTC day; no trading Saturday or Sunday UTC.
- Position sizing: results in R per trade; no lot sizing.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Gann degrees | 45, 90, 135, 180, 225, 270, 315, 360 | sim.py line 38 |
| Fibonacci levels | 0.382, 0.500, 0.618, 0.786 | sim.py line 39 |
| ATR | Wilder 14 on H1, over 43 bars including the forming one | sim.py docstring line 8 |
| Zone width | 0.3 x ATR (`--zone-mult`) | sim.py `args` |
| H4 bias EMA | 50, SMA seed, 200 H4 bars (`--ema`) | sim.py docstring line 9 |
| Polarity lookback | last 10 closed H4 closes | sim.py docstring line 13 |
| Entry mode / fill probability | bug / 0.4; 15 bars; runaway 1.5 x ATR | sim.py `args` |
| SL / TP | 1.0 x ATR / $9.00 fixed | sim.py `args` |
| Breakeven / trail floors | $15 / $15 | sim.py `args` |
| Zone trades per day | 1 | sim.py `args` |
| Random-direction control | `--random-dir 1`, seed 7 | sim.py `args`, `run` |

## Costs
Spread $0.35 per round trip (ask = bid + 0.35), default `--spread 0.35` (sim.py `args`). No commission or slippage. The audit's diag run puts this at 0.05R to 0.14R per trade depending on era ([logs_L1/recorded.d_revival.diag_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.diag_py.log), Q4).

## Tuning and selection
- Search: the switches in sim.py `args` (entry mode, SL multiple, TP mode fixed/ATR/none, partial, breakeven/trail, runner distances, max hold, polarity, bias, confirmation, EMA, zone width, zones per day, invert, random direction). battery.py takes variant command lines as arguments; the lines actually run are not in any published file.
- Configurations run (counted from the code/results): Not recorded in the published files. Ledger count (registry/trial_ledger.csv n_variants): 20.
- How the reported variant was chosen: the headline is the default "faithful" replay of the live configuration, not a chosen variant (sim.py `__main__`).
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| D faithful, full 2010-2026 | 1,432 | PF 0.87; net -91.7R; avg -0.064R; max DD 100.0R; win 50% | [logs_L1/recorded.d_revival.sim_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.sim_py.log) |
| D faithful, by year | 60 to 101 per year | PF 0.49 (2021) to 1.21 (2015); every year INSUFFICIENT SAMPLE alone | same log |
| Audit "true" sandbox run (New York sensitivity per VERDICTS) | 1,428 | PF 0.88; net -81.4R | [logs_L1/true.d_revival.sim_py.log](../../../audit/phaseC/logs_L1/true.d_revival.sim_py.log) |
| Audit run without 2010-2012 | 1,159 | PF 0.86; net -78.4R | [logs_L1/no1012.d_revival.sim.py.log](../../../audit/phaseC/logs_L1/no1012.d_revival.sim.py.log) |
| Zero-spread breakdown, by level family and era | 10 to 482 per cell | sums near 0R; gross PF not printed | [logs_L1/recorded.d_revival.split_py.log](../../../audit/phaseC/logs_L1/recorded.d_revival.split_py.log) |
| Plain stop/target barrier test (intended entry) | 1,142 to 1,230 | gross win rates within 1.2 points of the random-walk prediction | diag log, Q3 |

## Code and how to rerun
- Code: [sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py) (`python sim.py`, defaults = faithful replay), [data.py](../../../originals/gann_bot_500/research/d_revival/data.py), [battery.py](../../../originals/gann_bot_500/research/d_revival/battery.py), [split.py](../../../originals/gann_bot_500/research/d_revival/split.py), [diag.py](../../../originals/gann_bot_500/research/d_revival/diag.py).
- Audit rerun stage: `l1_queue` (jobs `recorded d_revival sim.py` and `true d_revival sim.py` in [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh)) and `no1012_run`.
- Public data enough? Partly. 2010 to 2026-06-19 needs only `histdata_xau`; the part from 2026-06-26 needs `ta_lab/data/XAU_M1.npy`, group `broker_mt5`.

## Corrections from the release review
- README "Rules: Faithful M1 replay plus exit and gate variants" states none of the rules. They are in the sim.py docstring: Gann/pivot/retracement zones at 0.3 x ATR, EMA50 H4 bias, polarity, H1 confirmation, "bug" pullback entry, SL 1 x ATR, TP $9, partial, breakeven and trail at max(ATR, $15) (sim.py lines 1-25).
- README does not say this "Profile D" differs from the one in GANN-PROFILE-D-BASE. Here the TP is a fixed $9 (sim.py line 23); the earlier base test used TP 3 x ATR ([config.py](../../../originals/gann_bot_500/config.py) lines 57-70 show TP_FIXED_POINTS 900 replacing the ATR target).
- README "Parameters and tuning: many" and "Variants counted in the ledger: 20" cannot be checked: the variant command lines given to battery.py are not published.
- README "gross PF1.00" has no published output file behind it. The zero-spread split log prints net R by cell, not a PF (split_py.log).
- README caveats "Replica matched 5/12 live signals" and "Random direction about equal" are not in any published output. Not recorded in the published files.
- README "Gates: both halves" is not defined anywhere; sim.py has no gate, and battery.py only prints the two halves.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | n=1432 PF0.87 -92R; gross PF1.00 |
| Rerun, recorded clock | n=1432 PF 0.87, -91.7R |
| Rerun, true UTC | New York sensitivity n=1428 PF 0.88 |

## Verdict
VERIFIED. File is broker time from 2019, DECISIONS 20.

## Audit caveats
Replica matched 5/12 live signals. Random direction about equal.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/d_revival/sim.py](../../../originals/gann_bot_500/research/d_revival/sim.py)
