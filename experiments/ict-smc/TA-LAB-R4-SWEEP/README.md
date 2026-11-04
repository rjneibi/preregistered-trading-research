# TA-LAB-R4-SWEEP

**Audit verdict: INVALID.** Original verdict: FAILED. Dated 2026-10-12. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Asia-range sweep fade has edge.

Family: ICT/SMC. Market: XAUUSD. Timeframe: M15/M5. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A fade of a sweep of the Asia-session range on gold. The Asia range is the high and low of 00:00-06:00 UTC. Later in the day, a bar that trades past one side and closes back inside triggers a trade in the opposite direction at the next open. Settings were chosen on data before 2025 and checked on 2025 onward. Round 12 later found a look-ahead leak in the range build; the corrected rule loses before 2025 and matches random twins after.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M15 for the grid and the 2025+ test; M5 as a finer check ([round4.py](../../../originals/gann_bot_500/research/ta_lab/round4.py) docstring).
- Data source and file(s): broker MT5 demo feed, `research/ta_lab/data/XAU_M15.npy` and `XAU_M5.npy`, bid prices with a per-bar spread column; time shifted to UTC in the loader ([lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) lines 1-10, 29-41). data/manifest.csv classes both files `broker_mt5` (not public).
- Period: M15 2022-07 to 2026-10; M5 2025-05 to 2026-10 (round4.py docstring).
- In-sample / out-of-sample: train before 2025-01-01 UTC; test 2025-01-01 onward (round4.py `CUT`).

## Rules
From round4.py `build` and round12.py `build_fixed`.
- Entry: Asia range = high/low of bars with UTC hour < 6 (at least 2.5 hours of bars needed). In the window 06:00 to `win_end` UTC, the first bar whose high exceeds the Asia high and closes below it gives a short (mirror for the low gives a long). Market entry at the next bar's open. One trade per day.
- Exit (stop, target, time): stop = signal bar's wick plus $0.30 buffer, widened to at least `min_stop_atr` x ATR. Exit mode `ladder`: at each +k x step R the stop moves to +k x step R. Or mode `tp`: fixed target at step R, stop to breakeven at +1R. Time cap 24 hours of bars (`max_hold=24*bph`) (round4.py `run`; lab.py `simulate`). Within one bar the stop is checked before any favourable move (lab.py docstring).
- Filters: one position at a time (lab.py `one_at_a_time`).
- Position sizing: results in R, each trade's own initial risk (lab.py docstring).
- The leak: round 4 built each day from the 96 M15 bars after the day start. A UTC gold day has about 92, so the "Asia range" also held the next day's 00:00-01:00 bars (round12.py lines 1-3). Round 12 uses bars of the same UTC day only.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Asia range | UTC hour < 6 | round4.py `build` |
| Trade window end (`win_end`) | grid 10, 13, 16, 20; chosen 20 | round4.py grid; log |
| Min stop (`min_stop_atr`) | grid 0.3, 0.5, 0.8 x ATR; chosen 0.5 | round4.py |
| ATR | ATR(14), recursive with alpha 1/14, on the bar TF, scaled by sqrt(bars per hour) | lab.py `atr`; round4.py `A = atr(d,14)*np.sqrt(bph)` |
| Stop buffer | $0.30 beyond the wick | round4.py `buf=0.3` |
| Exit | ladder step {0.4, 0.6, 1.0} R or tp {1.0, 1.5, 2.0} R; chosen ladder 0.4R | round4.py grid |
| Trades per day | 1 | round4.py `per_day=1` |
| Twin (round 12) | random bar in 06:00-20:00 same day, random direction, same stop in ATR terms, 20 seeds | round5.py `twin`; round12.py |

## Costs
- Spread: per-bar spread from the feed, floored at $0.20, paid on entry for buys and on exit for sells (lab.py `load`, `simulate`).
- Slippage: $0.30 subtracted from every trade, converted to R (round4.py `SLIP`, `run`).
- No commission or swap modelled in the code.

## Tuning and selection
- Search: win_end {10, 13, 16, 20} x min_stop {0.3, 0.5, 0.8} x (ladder step {0.4, 0.6, 1.0} or tp {1.0, 1.5, 2.0}) (round4.py lines 64-65).
- Configurations run (counted from the code/results): 72. Ledger count (registry/trial_ledger.csv, TA-LAB-R4-SWEEP): 4. They differ: the ledger counts 4, the code searched 72.
- How the reported variant was chosen: sorted by train (pre-2025) `net / (maxDD + 5)` and the top one taken: window 06-20, min stop 0.5 ATR, ladder 0.4R (round4.py line 72; audit/phaseC/logs_L1/recorded.ta_lab.round4_py.log "chosen: (20, 0.5, 0.4, 'ladder')"). Selection used pre-2025 data only. The M5 check and round 12 reuse this tuple.
- Preregistered: no.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Round 4 (leaky), M15 train <2025 | 624 | +0.048R avg, PF 1.14. INVALID (look-ahead) | audit/phaseC/logs_L1/recorded.ta_lab.round4_py.log |
| Round 4 (leaky), M15 test 2025+ | 362 | +0.235R avg, PF 1.90. INVALID | same log |
| Round 4 (leaky), M5 2025-05+ | 296 | +0.131R avg, PF 1.51. INVALID | same log |
| Round 12 FIXED, M15 <2025 | 591 | -0.092R avg, PF 0.78; twins -0.021R, beats 5% of twins | audit/phaseC/logs_L1/recorded.ta_lab.round12_py.log |
| Round 12 FIXED, M15 2025+ | 398 | +0.096R avg, PF 1.29; twins +0.102R, beats 45% of twins | same log |
| Round 12 FIXED, M5 2025+ | 333 | +0.031R avg, PF 1.09; twins +0.030R, beats 50% | same log |
| Audit same-bar worst ordering, FIXED M15 2025+ | 398 | net +19.4R, PF 1.15 | [talab_pess.json](../../../audit/phaseC/talab_pess.json) |
| Audit same-bar worst ordering, FIXED M15 <2025 | 591 | net -148.5R, PF 0.72 | talab_pess.json |

## Code and how to rerun
- Code: [round4.py](../../../originals/gann_bot_500/research/ta_lab/round4.py) (grid and choice), [round12.py](../../../originals/gann_bot_500/research/ta_lab/round12.py) (leak fix and twins), [round5.py](../../../originals/gann_bot_500/research/ta_lab/round5.py) (`twin`, `halves`), [lab.py](../../../originals/gann_bot_500/research/ta_lab/lab.py) (loader, simulator). Audit: [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh), [talab_gap.py](../../../audit/phaseC/talab_gap.py), [talab_pess.py](../../../audit/phaseC/talab_pess.py).
- Audit rerun stage: `l1_queue` (rounds 4 and 12); sensitivities `talab_gap_make`/`talab_gap_run` and `talab_pess_make`/`talab_pess_run`/`talab_pess_rep` (audit/tools/run_all.sh).
- Public data enough? No. Needs manifest group `broker_mt5` (`ta_lab/data/XAU_M15.npy`, `XAU_M5.npy`). `talab_gap_make` is listed in audit/tools/stages_broker.txt and `phaseC/talab_pess.json` in outputs_broker.txt.

## Corrections from the release review
- README "Data: M15, M5" gives no source or dates. The data are broker MT5 demo exports (not public), M15 2022-07 to 2026-10 and M5 2025-05 to 2026-10 (lab.py; round4.py; data/manifest.csv).
- README "Parameters and tuning: chosen on <2025. Variants counted in the ledger: 4" understates the search. round4.py ran a 72-config grid and picked the top config by train net/(maxDD+5) (round4.py lines 64-72).
- README "Costs: $0.30 slip" is incomplete. A per-bar spread floored at $0.20 is also charged (lab.py `load`, `simulate`).
- README rules omit the minimum stop of 0.5 x ATR and the 24-hour time cap (round4.py).
- README "Gates: random twin" states no threshold. No pass threshold is recorded in the code; round 12 prints the share of 20 twins beaten.
- README results give no n for the corrected figures. Fixed M15 <2025 is n=591 (PF 0.78); fixed M15 2025+ is n=398, PF 1.29, beats 45% of twins (round12 log). audit/VERDICTS.md:106 says "Beats 50%", which is wrong; 50% is the M5 row.
- README caveat "Show original and corrected side by side" is an editing note, not a caveat.
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link round4.py or lab.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Originally +0.048/+0.235R; corrected M15 <2025 -0.092R PF0.78 |
| Rerun, recorded clock | +0.048/+0.235R; fixed M15 -0.092R PF 0.78 |
| Rerun, true UTC | same, clean clock |

## Verdict
INVALID. Original figures are a look-ahead leak. The corrected figure in round 12 stands.

## Audit caveats
LOOK-AHEAD LEAK found in round 12: 24*bph bars pulled next-day bars into the Asia range. Show original and corrected side by side.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/ta_lab/round12.py](../../../originals/gann_bot_500/research/ta_lab/round12.py)
