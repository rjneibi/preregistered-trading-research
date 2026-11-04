# CRT-FVG-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-30. A verdict grades the stored claim, not the strategy.

**Hypothesis:** CRT + HTF FVG stack has edge.

Family: ICT/SMC. Market: XAU, EURUSD, GBPUSD, NAS100. Timeframe: 4H/1H/15m/3-15m. Idea source: the author's brief. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
A stacked ICT-style entry: a higher-timeframe bias, two same-direction 15m "candle range theory" (CRT) sweeps, a 1H fair value gap (FVG) as the area of interest, and a CRT sweep on the entry timeframe whose extreme lies inside that FVG. It ran on four symbols with five target modes and three entry timeframes. Settings were tuned in-sample on a 108-config grid and the selected settings were tested once out-of-sample. Result: 0 of 15 pooled cells passed.

## Instruments and data
- Instruments: XAUUSD (primary), EURUSD, GBPUSD, NAS100 ([config.yaml](../../../originals/gann_bot_500/research/crt_fvg/config.yaml) `symbols`).
- Timeframe(s): M1 data. 3m, 5m, 15m, 1H and 4H bars are built from M1 in code, aligned to UTC midnight ([spec.md](../../../experiments/ict-smc/CRT-FVG-1/spec.md), "Data"). Bias TF 4H or 1H, setup TF 15m, FVG TF 1H, entry TF 5m (spec), 3m and 15m (variants) (config.yaml `rules`).
- Data source and file(s): Dukascopy M1 bid/ask, cached as mid OHLC plus per-bar spread, UTC: `london-breakout/data/m1/{XAUUSD,EURUSD,GBPUSD,NAS100}.npz` (data/manifest.csv group `dukascopy_m1`, public).
- Period: 2013-01-01 to 2026-10-30 exclusive (config.yaml `data.start`/`end`). Known gap: NAS100 has no overnight prices from 2015 to mid-2018 (spec.md, "Data").
- In-sample / out-of-sample: first 70% of calendar time per symbol is IS (to 2022-09-06), last 30% OOS, opened once after the selection was frozen ([REPORT.md](../../../originals/gann_bot_500/research/crt_fvg/REPORT.md) line 3; config.yaml `is_frac: 0.70`). Exact split timestamps per symbol are in [spans.json](../../../originals/gann_bot_500/research/crt_fvg/results/spans.json). Walk-forward: 6 months train / 2 months test, rolling (config.yaml `wfo_*`).

## Rules
All from spec.md "Rule interpretations" and config.yaml `rules`. Long case shown; short is the mirror.
- Entry:
  - Swing pivot: a bar strictly below the N bars on each side; usable from bar j+N+1.
  - CRT: the first bar trading below the most recent confirmed swing low is the sweep; a close back above must come within K bars counting the sweep bar. Decision time is the close of the confirming bar.
  - Bias: the last CRT on the bias TF known at decision time is bullish, and the confirming entry bar closes above the EMA50 of closed bias-TF bars.
  - Rule 1: the last 2 setup-TF (15m) CRTs known strictly before the decision are both in the bias direction, with the second sweep extreme higher. The streak never expires.
  - Rule 2: a 1H FVG in the bias direction, known before the entry sweep bar opens, and not invalidated (a 1H close beyond the far edge). No expiry.
  - Rule 3: the entry CRT's sweep extreme lies inside that FVG (newest FVG if several).
  - Fill: open of the next M1 bar after the confirming close.
- Exit (stop, target, time): stop at sweep extreme minus `sl_buffer` x ATR(14) on the entry TF. Targets 1R, 1.5R, 2R, 3R from the fill, or `liq` = the nearest unswept opposing 15m swing known at decision (no trade in that mode if none). Flat at the first M1 bar at or after Friday 20:45 UTC. Otherwise held overnight; swap not modelled. A stop that gaps fills at the open; stop wins when stop and target are hit in the same M1 bar (spec.md, "Costs and fills").
- Filters: entries only 07:00-20:00 UTC; skip if the next bar opens more than 60 minutes after the signal; skip Friday at or after 20:45; one open trade per symbol, signals during a trade dropped.
- Position sizing: 1% risk per trade on a $100,000 account (config.yaml `account`). Results are reported in R.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Swing pivot N (`swing_n`) | default 2; grid {2, 3, 5} | config.yaml `rules`, `validation.grid` |
| CRT close-back window K (`crt_k`) | default 1; grid {1, 2, 3} | config.yaml |
| Minimum FVG height (`fvg_min_atr`, x ATR14 on 1H) | default 0; grid {0, 0.25, 0.5} | config.yaml |
| Bias timeframe (`bias_tf`) | default 240 (4H); grid {240, 60} | config.yaml |
| Bias EMA | 50 | config.yaml `bias_ema` |
| Stop buffer (`sl_buffer_atr`, x ATR14 entry TF) | default 0.1; grid {0.1, 0.25} | config.yaml |
| ATR length | 14 | config.yaml `atr_n` |
| Setup TF / min streak / monotonic | 15m / 2 / true | config.yaml |
| FVG TF / invalidation | 60m / close-through | config.yaml |
| Entry TFs | 5, 3, 15 minutes | config.yaml `entry_tfs` |
| TP modes | 1.0, 1.5, 2.0, 3.0 R, liq (15m swing) | config.yaml `tp_modes`, `liq_tf` |
| Session / Friday exit / max entry gap | 07:00-20:00 UTC / 20:45 UTC / 60 min | config.yaml |
| Seed | 20261030 | config.yaml |

## Costs
From config.yaml `symbols` and `costs`, and spec.md "Costs and fills":
- XAUUSD: $0.25 spread plus $0.07/oz commission ($7/lot round trip).
- EURUSD: 0.00005 (0.5 pip) plus 0.00007 commission. GBPUSD: 0.00010 (1.0 pip) plus 0.00007. NAS100: 1.5 points, no commission.
- Slippage: 1 tick on entries and on stop exits; targets fill as limits with no slippage.
- Sensitivities: 0x (gross), 2x, and Dukascopy's measured per-bar spread (config.yaml `multipliers`, `spread_mode`).

## Tuning and selection
- Search: swing_n {2,3,5} x crt_k {1,2,3} x fvg_min_atr {0,0.25,0.5} x bias_tf {4H,1H} x sl_buffer {0.1,0.25} = 108 configs, each run for 3 entry TFs x 5 TP modes x 4 symbols (config.yaml `validation.grid`; spec.md "Validation").
- Configurations run (counted from the code/results): 6,480 IS backtests (REPORT.md line 3). Ledger count (registry/trial_ledger.csv, CRT-FVG-1): 6,480. They match.
- How the reported variant was chosen: one config per entry TF x TP mode, by pooled IS expectancy (avg R) over the 4 symbols, among configs with at least 30 IS trades per symbol (config.yaml `min_is_trades`; spec.md "Selection rule"). Selection used IS data only and is stored in [selection.json](../../../originals/gann_bot_500/research/crt_fvg/results/selection.json). The 15m cells had no eligible config, so they fall back to the untuned spec defaults (REPORT.md, note under the gate table; cells.csv `fallback=True`). Walk-forward re-selects pooled per window with at least 10 train trades.
- Preregistered: partly. [PREREG.md](../../../originals/gann_bot_500/research/crt_fvg/PREREG.md) was frozen 2026-10-30 before any P&L (copied as [spec.md](../../../experiments/ict-smc/CRT-FVG-1/spec.md)). Deviation: the author's blind prediction was not collected, so the run does not count toward the calibration ledger (PREREG.md "STATUS"). Before the freeze, signal-count and look-ahead checks were run on XAUUSD 2014-2016 with no P&L.

## Results
Gates per cell (spec.md "Gates"): G1 OOS net avg R > 0 with n >= 50; G2 OOS PF >= 1.15; G3 > 0 at 2x costs; G4 beats random direction, one-sided Holm p < 0.05 over 15 cells; G5 walk-forward avg R > 0; G6 XAUUSD own OOS avg R > 0.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| All 15 pooled cells, OOS | 48 to 133 per cell | 0 of 15 pass. OOS net avg R -0.07 to -0.64 | [cells.csv](../../../originals/gann_bot_500/research/crt_fvg/results/cells.csv) |
| 5m 2R (main cell), OOS | 99 | avg R -0.32, PF 0.61. INSUFFICIENT SAMPLE | cells.csv; REPORT.md |
| 3m 1R, OOS (largest cell) | 133 | avg R -0.40, PF 0.45 | cells.csv |
| 3m 2R, OOS | 104 | avg R -0.52, PF 0.43 | cells.csv |
| 3m liq, OOS | 100 | avg R -0.64, PF 0.39 | cells.csv |
| Other 11 cells, OOS | 48 to 99 each | all negative, PF 0.39 to 0.92. INSUFFICIENT SAMPLE | cells.csv |
| Best gross cell (5m liq), OOS 0x cost | 78 | +0.49R gross, -0.17R net; REPORT says it rests on one +23.6R trade. INSUFFICIENT SAMPLE | REPORT.md "Verdict" |
| Walk-forward, all cells | 74 to 412 per cell | -0.13R to -0.39R, all negative | cells.csv `wfo_n`, `wfo_avgR` |
| XAU-only positive cells (5m liq, 3m 3R) | 29 and 12 | +0.35R, +0.25R. INSUFFICIENT SAMPLE | REPORT.md |
| Untuned defaults, OOS | 48 to 184 per cell | all negative (-0.07 to -0.60R) | REPORT.md "Spec defaults" |
| All trades of selected configs, IS+OOS, 1x cost | 3,829 rows | stored ledger; audit rerun matched cells and trades exactly | [trades.csv](../../../originals/gann_bot_500/research/crt_fvg/results/trades.csv); audit/VERDICTS.md:76 |
| Audit gap-asymmetry check | 1,076 target exits, 17 opened through | cell avg R moves at most 0.0045R | [gap_asymmetry.json](../../../audit/phaseC/gap_asymmetry.json); VERDICTS.md:76 |

## Code and how to rerun
- Code: [run.py](../../../originals/gann_bot_500/research/crt_fvg/run.py) (`python run.py [grid|select|full|analyse|report]`), [rules.py](../../../originals/gann_bot_500/research/crt_fvg/crt_fvg/rules.py), [engine.py](../../../originals/gann_bot_500/research/crt_fvg/crt_fvg/engine.py), [pipeline.py](../../../originals/gann_bot_500/research/crt_fvg/crt_fvg/pipeline.py), [analyse.py](../../../originals/gann_bot_500/research/crt_fvg/crt_fvg/analyse.py), tests [test_rules.py](../../../originals/gann_bot_500/research/crt_fvg/tests/test_rules.py). Audit driver: [run_lbo_crt.sh](../../../audit/phaseC/run_lbo_crt.sh); gap check [gap_asymmetry.py](../../../audit/phaseC/gap_asymmetry.py).
- Audit rerun stage: `lbo_crt` (audit/tools/run_all.sh; CLEAN_RUN_stages.txt); gap check `c_gap_asymmetry`.
- Public data enough? Yes. Needs manifest group `dukascopy_m1` (public). `lbo_crt` is not in audit/tools/stages_broker.txt.

## Corrections from the release review
- README "Source: user brief" is chat residue. The source is the frozen plan PREREG.md (spec.md).
- README "Rules: 108-config IS grid, 15 pooled cells" describes the grid, not the rules. The rules are the swing/CRT/bias/streak/FVG stack listed above (spec.md).
- README "Costs: see config" is incomplete. Actual: XAU $0.25 + $0.07/oz, EURUSD 0.5 pip + $7/lot, GBPUSD 1.0 pip + $7/lot, NAS100 1.5 pt; 1 tick slippage on entries and stops (config.yaml).
- README gates "OOS>0, PF>=1.15, 2x cost, Holm, WFO" omit the n >= 50 condition in G1 and gate G6 (XAUUSD's own OOS avg R > 0) (spec.md "Gates").
- README row "Rerun, true UTC | true UTC data" is not a result. This study uses Dukascopy data on a measured UTC clock, so no separate true-UTC rerun applies (audit/VERDICTS.md:139).
- README results give no n. Per-cell OOS n is 48 to 133; 11 of 15 cells have fewer than 100 trades (cells.csv). The 3,829 trades are IS plus OOS for all selected configs, not OOS only (REPORT.md "Files").
- README does not say the 15m cells used untuned defaults because no config met the 30-IS-trades rule (REPORT.md).
- README does not say the author's blind prediction was not collected (PREREG.md "STATUS").
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link the runner run.py or the results folder.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | 0/15 PASS; OOS -0.07..-0.64R |
| Rerun, recorded clock | 0/15 PASS, cells and 3,829 trades exact |
| Rerun, true UTC | true UTC data |

## Verdict
VERIFIED. Gap asymmetry at most 0.0045R per cell.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/crt_fvg/REPORT.md](../../../originals/gann_bot_500/research/crt_fvg/REPORT.md)
