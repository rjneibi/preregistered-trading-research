# LBO-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-30. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Asian-box and session-level breakouts have edge.

Family: breakout. Market: GER40, UK100 + 5 robustness. Timeframe: 1-15m. Idea source: social post, 'elitrade basic' PDF. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Two versions of the "London Breakout". Variant A trades a break of an overnight (Asian) price box at the London open. Variant B trades breaks of the previous session's levels in the Asia, London and New York sessions. Both ran on DAX (GER40) and FTSE (UK100) with Dukascopy 1-minute bid/ask data, with five more instruments as robustness checks ([originals/london-breakout/README.md](../../../originals/london-breakout/README.md) line 3). Selection rules and six pass gates were frozen before grid results were viewed ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 53-75).

## Instruments and data
- Instruments: GER40 (Dukascopy deuidxeur), UK100 (gbridxgbp) primary; US30, NAS100, EURUSD, GBPUSD, XAUUSD robustness ([config/research.yaml](../../../originals/london-breakout/config/research.yaml) lines 14-21).
- Timeframe(s): 1m bars; signal bars of 1, 5 or 15 minutes (Variant A grid `tf`); exits always simulated on 1m bars ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) line 34).
- Data source and file(s): Dukascopy M1 bid and ask with tick volume, downloaded with `dukascopy-node` 1.51.1 ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 16-18; [tools/download.py](../../../originals/london-breakout/tools/download.py), [tools/build_data.py](../../../originals/london-breakout/tools/build_data.py)). Signals use mid prices; fills at bid/ask.
- Period: config 2013-01-01 to 2026-10-30 exclusive ([config/research.yaml](../../../originals/london-breakout/config/research.yaml) lines 4-6). GER40 data starts 2013-09-30 ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) line 24). No overnight GER40/UK100 prices exist 2015-01 to about 2018-06, so about 860 of 2,691 IS+VAL weekdays have no Asian box and are excluded from Variant A (same file, lines 40-45).
- In-sample / out-of-sample: 60/20/20 by calendar time. IS to 2021-08-01; VAL to 2024-03-15; OOS 2024-03-15 to 2026-10-30, locked and run once ([config/research.yaml](../../../originals/london-breakout/config/research.yaml) lines 24-27; [RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 23-28).

## Rules
Frozen config (the reported variant), from [config/final_strategy.yaml](../../../originals/london-breakout/config/final_strategy.yaml):
- Entry: box = highest high / lowest low of 1m mid bars 23:00 (previous day) to 07:00 UTC, capped at 08:00 London, needing at least 50% bar coverage. Signal bars are complete 15m UTC buckets that open at or after 08:00 London and close within 30 minutes. Long if a whole signal bar is above the box high (low above box high); short mirror. The candle must point in the breakout direction with range at least ATR14 of the previous signal bars. First signal only. Market entry at the open of the next 1m bar.
- Exit (stop, target, time): stop at the box edge moved 25% of box width back inside the box (`in25`). No target. Forced exit 16:30 London. Same-bar stop and target counts as stop; gapped stops fill at the bar open ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 30-34).
- Filters: none (buffer 0, volume 0, no fresh-break, box or trend filter). Trading days: Mon-Fri London dates with a 1m bar within 5 minutes of 08:00 London.
- Position sizing: 0.5% of equity risk per trade (1% also tested); size = equity x risk / (|entry - stop| x value per point); max 1 trade per day. Results are in R units.
- Variant B (rejected at stage 1): previous-session 15m levels (session high/low, fractal swings, or pivots), break on 5m with a volume filter, ATR stop, RR 2-4, at most 2 trades, first 30 or 60 minutes, run on Asia, London and NY sessions ([src/lbo/report.py](../../../originals/london-breakout/src/lbo/report.py) line 377; [config/research.yaml](../../../originals/london-breakout/config/research.yaml) lines 65-73).
- An "author-literal" reference config of the source idea was also run (box 00:00-07:00 UTC, 5m, body at least 50%, close outside, 120 min, stop in25, RR 2) for reference only ([src/lbo/pipeline.py](../../../originals/london-breakout/src/lbo/pipeline.py) line 27).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| ATR | 14-bar rolling mean of true range on signal bars, previous bars only | [src/lbo/features.py](../../../originals/london-breakout/src/lbo/features.py) lines 9-27 |
| A: box | utc0007, utc2307, tokyo (09:00-15:00 JST), ny1904 (19:00-04:00 New York); frozen utc2307 | [config/research.yaml](../../../originals/london-breakout/config/research.yaml) line 37; [src/lbo/sessions.py](../../../originals/london-breakout/src/lbo/sessions.py) lines 28-46 |
| A: signal tf (min) | 1, 5, 15; frozen 15 | research.yaml line 38 |
| A: strong candle | none, body50, range1atr, close25; frozen range1atr | research.yaml line 39; [src/lbo/variant_a.py](../../../originals/london-breakout/src/lbo/variant_a.py) lines 57, 106-110 |
| A: breakout | close, whole, buffer (0.1 ATR); frozen whole | research.yaml lines 40, 44 |
| A: entry window (min) | 30, 60, 120; frozen 30 | research.yaml line 41 |
| A: stop | in25, mid, opp, candle, atr1, atr2; frozen in25 | research.yaml line 42 |
| A: RR | 1.0, 1.5, 2.0, 3.0, 4.0, none; frozen none | research.yaml line 43 |
| A: stop-order (OCO) grid | box 4 x window 3 x buffer {0, 0.1} x stop {in25, mid, opp, atr1, atr2} x RR 6 | research.yaml lines 45-50 |
| A: stage 2 / fixes | vol_k {0, 1, 1.5, 2}, stop_extra {atr0.5, atr3}, fresh {false, true}, max_trades {one, reversal}, box_filter {none, p20_80, no_narrow, no_wide, narrow, wide}; 26 fixes in all | research.yaml lines 51-56; RESEARCH_LOG.md lines 104-105 |
| B: sessions, levels | asia, london, ny; session_hl, fractal (n=2), pivot | research.yaml lines 59-60; [src/lbo/variant_b.py](../../../originals/london-breakout/src/lbo/variant_b.py) lines 10, 18 |
| B: window, vol_k, buffer, stop_atr, RR | {30, 60}; {0, 1, 1.5, 2}; {0, 0.1}; {0.5, 1, 1.5, 2, 3}; {2, 3, 4}; max 2 trades | research.yaml lines 61-66 |
| Min IS trades for selection | 150 per index | research.yaml line 32 |
| Seed | 20261030 | research.yaml line 2 |

## Costs
Spread from Dukascopy bid/ask per bar, taken as max(ask-bid at open, ask-bid at close); fills at bid/ask. Extra slippage per side: GER40 0.5, UK100 0.5, US30 1.0, NAS100 0.5, EURUSD 0.00002, GBPUSD 0.00003, XAUUSD 0.05 price units. Commission per round trip: indices 0; EURUSD/GBPUSD 0.00007; XAUUSD 0.07. Cost multipliers 0, 0.5, 1, 2 were reported; 1x is the headline ([config/research.yaml](../../../originals/london-breakout/config/research.yaml) lines 8-21, 29-31; [RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 18-21).

## Tuning and selection
- Search: Variant A stage-1 factorial, 4 x 3 x 4 x 3 x 3 x 6 x 6 = 15,552 market-entry configs plus 720 stop-order configs = 16,272 per index. Variant B 3 x 3 x 2 x 4 x 2 x 5 x 3 = 2,160 per index. B was also run on the 5 robustness instruments (10,800). Then 26 fixes and walk-forward selection over the full grid (24-month train, 6-month test) ([config/research.yaml](../../../originals/london-breakout/config/research.yaml); [results/stage1_A.json](../../../originals/london-breakout/results/stage1_A.json); [results/stage1_B.json](../../../originals/london-breakout/results/stage1_B.json)).
- Configurations run (counted from the code/results): 32,544 (A) + 4,320 (B) = 36,864 on the two indices; plus 10,800 B on robustness instruments, 26 fixes and 2 OOS runs = 47,692. RESEARCH_LOG gives "Total configurations evaluated: 59,778" ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) line 160), but its own listed parts sum to 47,692; the difference is not explained in the published files. Reruns of the selected rules on robustness instruments are not counted (same file, line 165). Ledger count (registry/trial_ledger.csv n_variants): 36,864, marked "exact". The ledger figure is the two-index stage-1 grid only, not the total searched.
- How the reported variant was chosen: frozen rule. Eligible = same config with at least 150 IS trades and IS expectancy above 0 at 1x costs on both indices (1,850 A configs; 0 B configs). Rank by plateau score (mean IS expectancy of the config and its one-step grid neighbours). Of the top 10, pick the best VAL expectancy with VAL above 0 on both indices. None qualified, so the best plateau config went forward labelled "FAILED validation" ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 55-61, 89-95). Selection used IS and VAL, not OOS. OOS was run once after the freeze.
- Preregistered: partly. The selection rule, gates G1-G6 and fix keep-rule were written in RESEARCH_LOG before results were viewed ("written while stage 1 was running", line 51). No separate hashed prereg file is published. The hypotheses H1-H15 are in [docs/research_summary.md](../../../originals/london-breakout/docs/research_summary.md). The author's own blind prediction was not collected (RESEARCH_LOG line 80).

## Results
All R values at 1x costs unless stated. Variant A frozen config.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| IS (pooled two indices) | 436 | +0.083R | [results/stage1_A.json](../../../originals/london-breakout/results/stage1_A.json) |
| VAL | 231 | -0.246R | same |
| IS+VAL | 667 | -0.031R; gross +0.051R; random-direction p 0.38 | [RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 112-117 |
| Walk-forward stitched A | 664 | -0.027R | [results/wfo.json](../../../originals/london-breakout/results/wfo.json) |
| Walk-forward stitched B | 594 | -0.268R | same |
| OOS, 0x costs | 204 | +0.055R, PF 1.11 | [results/oos_final.json](../../../originals/london-breakout/results/oos_final.json) |
| OOS, 1x costs | 204 | -0.0083R, t -0.09, PF 0.98, max DD 7.7% at 0.5% risk | same; [results/oos_final_trades_k1.csv](../../../originals/london-breakout/results/oos_final_trades_k1.csv) |
| OOS, 2x costs | 204 | -0.081R, PF 0.86 | same |
| OOS GER40, 1x | 98 | +0.129R, PF 1.26. INSUFFICIENT SAMPLE; not preregistered | same |
| OOS UK100, 1x | 106 | -0.136R, PF 0.76 | same |
| OOS author-literal reference, 1x | 1,121 | -0.108R, t -2.6, PF 0.85 | [results/oos_author_reference.json](../../../originals/london-breakout/results/oos_author_reference.json) |
| Multiple testing, A grid | 16,272 per index | Hansen SPA p 0.37, White RC p 0.996 (G4 fails) | [results/stage1_A.json](../../../originals/london-breakout/results/stage1_A.json) |
| Multiple testing, B grid | 2,160 per index | SPA p 0.975, White RC p 1.0 | [results/stage1_B.json](../../../originals/london-breakout/results/stage1_B.json) |

All six gates fail. 26 fixes tried; none met the keep-rule ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 123-127).

## Code and how to rerun
- Code: [run_all.py](../../../originals/london-breakout/run_all.py) (stages download, data, test, grids, analyze, deep, freeze, oos, docs, report); [src/lbo/](../../../originals/london-breakout/src/lbo) (engine, sessions, variant_a, variant_b, grid_a, grid_b, deep, pipeline); [strategy/signal.py](../../../originals/london-breakout/strategy/signal.py); [tests/](../../../originals/london-breakout/tests); configs [research.yaml](../../../originals/london-breakout/config/research.yaml) and [final_strategy.yaml](../../../originals/london-breakout/config/final_strategy.yaml). `oos` refuses a second run unless results/oos_*.json is deleted ([README.md](../../../originals/london-breakout/README.md) lines 33-34).
- Audit rerun stage: `lbo_crt` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh) line 40; [audit/phaseC/run_lbo_crt.sh](../../../audit/phaseC/run_lbo_crt.sh) runs grids, analyze, deep, freeze, oos in a sandbox copy). The rerun log reproduces OOS n=204, -0.0083R, PF 0.984 ([audit/phaseC/logs_L1/lbo_oos.log](../../../audit/phaseC/logs_L1/lbo_oos.log)).
- Public data enough? yes. Manifest group `dukascopy_m1` (public) in [data/manifest.csv](../../../data/manifest.csv); the download stage can also refetch it (about 3 GB).

## Corrections from the release review
- README Parameters: "36864+. Variants counted in the ledger: 36864." Misleading. 36,864 is only the stage-1 grid on the two indices. RESEARCH_LOG states 59,778 total configurations; its listed parts (A 32,544, B 4,320, B robustness 10,800, 26 fixes, 2 OOS runs) sum to 47,692 ([RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md) lines 160-165). The ledger row is marked "exact"; it is a minimum.
- README Preregistration points to RESEARCH_LOG. The gates were frozen in a log entry during stage 1, not in a separate hashed prereg. Say so.
- README Costs: "config/research.yaml" only. The actual costs are per-bar Dukascopy spread plus 0.5 points slip per side on GER40/UK100, no commission (see Costs above).
- README Results row "Rerun, true UTC: true UTC data" is not a result. No clock rerun was done; the data is Dukascopy on its measured clock ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 28; [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 139).
- README Source names a third-party branded PDF. Flagged for the author: the review asks whether this name should be public (review O-14). Not repeated here.
- [originals/london-breakout/README.md](../../../originals/london-breakout/README.md) line 10 says "See report.html". That file is not in the repo.
- The OOS PF 0.98 is quoted at 1x costs; at 0x it is 1.11 (n=204). The README does not say which cost level.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | OOS -0.008R n=204 |
| Rerun, recorded clock | OOS -0.0083R n=204 PF 0.98 |
| Rerun, true UTC | true UTC data |

## Verdict
VERIFIED. Second out-of-sample read happens in a sandbox only, DECISIONS 28. Frozen rule has no target exits.

## Audit caveats
Robustness-instrument grid count not yet added.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- [originals/london-breakout/README.md](../../../originals/london-breakout/README.md)
- [originals/london-breakout/RESEARCH_LOG.md](../../../originals/london-breakout/RESEARCH_LOG.md)
