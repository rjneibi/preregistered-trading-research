# FR-L

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** London sweep/FVG with fixed or ATR TP is viable.

Family: ICT. Market: XAUUSD. Timeframe: M1. Idea source: ICT London kill-zone. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Whether the author's London-session ICT scalper (sweep, displacement, fair-value-gap entry) becomes viable if its fixed 1,500-point take-profit is replaced by a target scaled to ATR or to price. Detection, stop and session rules stayed locked. Five TP variants were pinned before the run, with the fixed-1500 rule as reference ([spec.md](../../../experiments/ict/FR-L/spec.md) lines 52-66; copy of [FR_PREREGISTRATION.md](../../../originals/gann_bot_500/research/fleet_review/FR_PREREGISTRATION.md), frozen 2026-07-06).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1.
- Data source and file(s): HistData XAUUSD M1 bid, `research/data/xauusd_m1_histdata.csv`, built by [ict_london_lab.py](../../../originals/gann_bot_500/research/ict_london_lab.py) part B. The lab treats HistData stamps as fixed UTC-5 and maps to New York time with zoneinfo (ict_london_lab.py lines 15-21).
- Period: 5,769,159 M1 bars, New York dates 2010-01-03 to 2026-06-19 ([audit/phaseC/logs_L1/recorded.frl.log](../../../audit/phaseC/logs_L1/recorded.frl.log) line 2).
- In-sample / out-of-sample: 70/30 chronological split by M1 bar count (`split = int(hm1.n * IN_SAMPLE_PCT)`, IN_SAMPLE_PCT = 0.70) ([london_tp_backtest.py](../../../originals/gann_bot_500/research/fleet_review/london_tp_backtest.py) line 42; [ict_scalper_london.py](../../../originals/gann_bot_500/research/ict_scalper_london.py) line 90). The prereg calls it "last 30%".

## Rules
From [ict_scalper_london.py](../../../originals/gann_bot_500/research/ict_scalper_london.py) lines 1-60 and 95-126:
- Entry: London kill zone only, 02:00-05:00 New York. Bias: shorts only after a buy-side sweep above the New York midnight open; longs only after a sell-side sweep below it. Liquidity pools: prior-session high/low and M1 fractal (N=2) extremes over 240 bars, clustered within 0.1 x ATR. Sweep: penetrate a pool by at least 50 points (max 800) and close back within 3 bars. Displacement: an M1 body at least 1.75 x ATR(14) in the reversal direction that breaks the latest opposing micro-swing (searched within 8 bars). Entry: limit at the proximal edge of a 3-candle FVG in the 62-79% retracement band (searched within 6 bars), filled only if traded through by 1 point, cancelled after 10 bars. News blackout 08:25-09:00 New York.
- Exit (stop, target, time): stop beyond the sweep extreme + 0.5 x ATR. Target per variant (below). Other exit and cancel rules unchanged.
- Variants: reference TP = fixed 1,500 points; atr_1.0, atr_1.5, atr_2.0 = TP 1.0/1.5/2.0 x ATR(14) at setup; pct_0.3, pct_0.5 = TP 0.30%/0.50% of entry price ([london_tp_backtest.py](../../../originals/gann_bot_500/research/fleet_review/london_tp_backtest.py) lines 26-32).
- Position sizing: fixed 1.00 lot (100 oz) on a $10,000 basis (ict_scalper_london.py lines 109, 122).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | 14 | [ict_scalper_london.py](../../../originals/gann_bot_500/research/ict_scalper_london.py) line 107 |
| Sweep min / max | 50 / 800 points, close back within 3 bars | lines 98, 115, 97 |
| Displacement | 1.75 x ATR | line 116 |
| Fractal N; pool lookback | 2; 240 M1 bars | lines 95, 104 |
| OTE band | 62-79% retracement | docstring, gate 6 |
| Stop buffer | 0.5 x ATR | line 99 |
| Entry cancel; fill buffer | 10 bars; 1 point | lines 100-101 |
| Kill zone | 02:00-05:00 New York | line 126 |
| TP variants | fixed 1500 pts (reference); 1.0, 1.5, 2.0 x ATR; 0.30%, 0.50% of price | [london_tp_backtest.py](../../../originals/gann_bot_500/research/fleet_review/london_tp_backtest.py) lines 26-32 |
| Split | 70% of M1 bars | ict_scalper_london.py line 90 |

## Costs
The prereg says spread "max(median, 25pt)" charged once per round trip ([spec.md](../../../experiments/ict/FR-L/spec.md) line 56). On the HistData feed the lab sets the spread to the 25-point floor, with median spread 0, since HistData is bid-only ([ict_london_lab.py](../../../originals/gann_bot_500/research/ict_london_lab.py) line 288; [ict_scalper_london.py](../../../originals/gann_bot_500/research/ict_scalper_london.py) line 105). In effect: a flat 25 points per round trip. No commission or slippage is recorded in the lines read.

## Tuning and selection
- Search: 5 TP variants, "the ENTIRE search space" (spec.md line 58). The locked detection parameters (sweep_min 50, disp_mult 1.75, TP fixed_1500) came from an earlier IS optimisation of the full model over sweep_min {50, 100, 150, 200} x disp_mult {1.25, 1.5, 1.75, 2.0} x TP {1000, 1500, 2000, opposing pool} = 64 configs. London-only was chosen after it outperformed in the same window (ict_scalper_london.py lines 6-13, 51-52).
- Configurations run (counted from the code/results): 5 variants + 1 reference = 6 in this experiment. Ledger count (registry/trial_ledger.csv n_variants): 6. They match for FR-L. The earlier 64-config optimisation and the session choice are not counted here.
- How the reported variant was chosen: no selection in FR-L. PASS needs, for one variant: OOS PF >= 1.20; OOS n >= 15; max drawdown <= 25% (1 lot on $10k); IS and OOS not inverted (spec.md lines 62-66).
- Preregistered: yes, [FR_PREREGISTRATION.md](../../../originals/gann_bot_500/research/fleet_review/FR_PREREGISTRATION.md) (commit a87b81e per the registry). Blind predictions: the assistant STILL FAILS; the author ATR TP RESCUES IT (spec.md lines 12-13).

## Results
From [FR_L_results.json](../../../originals/gann_bot_500/research/fleet_review/FR_L_results.json) (stored) and the audit reruns. Win rates are printed double-scaled in the logs (e.g. "515.5%" for 5.15%).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Reference fixed 1500, all | 679 | PF 0.587, win 5.2%, max DD 74.9% | FR_L_results.json |
| Reference IS / OOS | 472 / 207 | PF 0.67 / 0.36 | same |
| atr_1.0 | 692 (OOS 212) | PF 0.182, OOS 0.35; FAIL | same |
| atr_1.5 | 691 (OOS 211) | PF 0.315, OOS 0.49; FAIL | same |
| atr_2.0 | 689 (OOS 210) | PF 0.421, OOS 0.60; FAIL | same |
| pct_0.3 | 679 (OOS 207) | PF 0.694, OOS 0.65; FAIL | same |
| pct_0.5 | 679 (OOS 207) | PF 0.590, OOS 0.53; FAIL | same |
| Reference, true UTC rerun | 623 (OOS 183) | PF 0.497 | [true.frl.log](../../../audit/phaseC/logs_L1/true.frl.log) |
| All variants, true UTC | 622-642 | PF 0.192 to 0.690; all FAIL | same |
| Audit | | VERIFIED-WITH-CORRECTIONS; exact on the recorded clock | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 31 |

The reference IS n of 472 is derived as 679 - 207. Every variant fails the OOS PF and drawdown gates.

## Code and how to rerun
- Code: [london_tp_backtest.py](../../../originals/gann_bot_500/research/fleet_review/london_tp_backtest.py) (the FR-L harness), [ict_london_lab.py](../../../originals/gann_bot_500/research/ict_london_lab.py) (feed and session runner), [ict_scalper_london.py](../../../originals/gann_bot_500/research/ict_scalper_london.py) (locked detection engine).
- Audit rerun stage: `fr` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh); [audit/phaseC/run_frl.sh](../../../audit/phaseC/run_frl.sh), both clocks).
- Public data enough? yes. `histdata_xau` (public) in [data/manifest.csv](../../../data/manifest.csv). The lab imports MetaTrader5 but does not use the broker feed for this run (london_tp_backtest.py lines 5-6).

## Corrections from the release review
- README Rules: "6 TP variants". Wrong. The prereg pins 5 variants plus the fixed-1500 reference ([spec.md](../../../experiments/ict/FR-L/spec.md) line 58; FR_L_results.json keys).
- README Costs and Gates: "see prereg". The spread is in effect a flat 25 points per round trip on HistData; the four gates should be listed.
- README Caveats: "Early PF 2.90 at n=9 is the same line per memory; verify in Phase 3." Chat residue and not evidence. That early figure (n=9, INSUFFICIENT SAMPLE) is in no published file and is UNVERIFIED ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 31). It should not be quoted as a result.
- README Source: "ICT London kill-zone". It should say this is the author's own engine; the locked parameters came from an earlier 64-config IS optimisation, and the London-only session was picked after seeing it do best in the same window ([ict_scalper_london.py](../../../originals/gann_bot_500/research/ict_scalper_london.py) lines 6-13, 51-52). That prior search is not in the ledger count.
- README does not link the harness [london_tp_backtest.py](../../../originals/gann_bot_500/research/fleet_review/london_tp_backtest.py) or [ict_london_lab.py](../../../originals/gann_bot_500/research/ict_london_lab.py).
- The OOS split is by M1 bar count, not "last 30% of events" as a reader might assume.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Reference n=679 PF=0.587; all variants fail. Displayed WR double-scaled, corrected in the log. |
| Rerun, recorded clock | Reference n=679 PF 0.587 |
| Rerun, true UTC | n=623 PF 0.497 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Exact on the recorded clock. The PF 2.90 at n=9 is `UNVERIFIED` and `INSUFFICIENT SAMPLE`, is in no file found, and is not a result of this audit.

## Audit caveats
Log carries an explicit WR scale correction. Early PF 2.90 at n=9 is the same line per memory; verify in Phase 3.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
