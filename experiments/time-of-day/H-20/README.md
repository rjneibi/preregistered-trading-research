# H-20

**Audit verdict: UNVERIFIED.** Original verdict: NOT RUN. Dated 2026-08-23. A verdict grades the stored claim, not the strategy.

**Hypothesis:** 20:00 UTC cohort is an hour effect, not overnight carry.

Family: time-of-day. Market: XAUUSD. Timeframe: H1. Idea source: cycle 2 diagnostic. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Nothing was run. H-20 is a frozen preregistration. It asked whether the profit concentration in trades entered at the 20:00 hour stamp came from the hour itself or from holding overnight. It planned to re-simulate the same 472 entry events under three exit policies and compare hours. It was withdrawn unrun under its own power rule. The audit later found that the "20:00 UTC" cohort was mislabelled by the data clock. Sources: [spec.md](../../../experiments/time-of-day/H-20/spec.md); [FUTURE_WORK.md](../../../FUTURE_WORK.md) lines 3-11.

## Instruments and data
- Instruments: XAUUSD ([spec.md](../../../experiments/time-of-day/H-20/spec.md) §4).
- Timeframe(s): entries come from the frozen goldbot "final" rule (conviction dual-arm H1+H4; [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 10). Exits were to be simulated on M1 bars (spec §4).
- Data source and file(s): HistData XAUUSD M1, `research/data/xauusd_m1_histdata.csv`, bid-only (spec §4 and §7 item 1). Manifest group `histdata_xau`, public ([data/manifest.csv](../../../data/manifest.csv)). Event set: the 472 trades of `results/verdict_trades.csv` ([verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv)).
- Period: M1 file 2010 to 2026-06-19 (spec §4); profiled range 2010-01-03 to 2026-06-19 ([data_profile.json](../../../audit/infrastructure/data_profile.json) key `histdata_xau_m1`).
- In-sample / out-of-sample: no train/test split. Two eras with the boundary pinned at 2021-06-19T00:00:00Z (spec G4).

## Rules
- Entry: unchanged frozen entry rule. The same 472 entry events in every arm (spec §4). Base rule parameters: R3/S3 pivots with UTC-midnight day boundary, H1-close hours 12-20 UTC, Monday skipped, dead-level check over the last 10 H4 closes, 24 h re-entry block ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 9-18).
- Exit (stop, target, time), by arm (spec §4):
  - A, as-is: server TP/SL, high-vol half-out, low-vol bail, 24 h stop. Regression reference only.
  - S, same-day: TP/SL active; otherwise flat at 20:45 UTC on the entry day.
  - N, next-day: TP/SL active; otherwise flat at 20:45 UTC on the next trading day.
  - Base exit values: TP 0.8 x ATR, SL 2.4 x ATR, 24 h time stop; bail: close half at -1.2 ATR in high vol, close all at -1.0 ATR after 8 h in low vol (config.yaml lines 21-34).
- Filters: rows by entry hour {12, 16, 20}; retry hours 13-15 and 17-19 pooled and never gated (spec §4).
- Position sizing: not stated in the spec. The primary metric is net per trade in ATR units, `net / (100 x atr)`, i.e. per 1 lot of 100 oz (spec §4). Not otherwise recorded in the published files.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Forced-flat time (arms S, N) | 20:45 UTC | spec §4 |
| Gated hours | 12, 16, 20 UTC | spec §4, G6 |
| ATR | H1, 14, Wilder with SMA seed | config.yaml lines 30-33 |
| TP / SL / time stop | 0.8 ATR / 2.4 ATR / 24 h | config.yaml lines 22-24 |
| Era boundary | 2021-06-19 | spec G4 |
| N_effective for DSR | 9 (entry hours 12-20) | spec G3 |
| Power floor G0 | n >= 100 at hour 20 and >= 200 at hour 16 in arm S | spec G0 |
| Kill thresholds | G1 Arm A within ±2% per hour; G2 D_hour <= 0, or D_night > 0 and D_hour < 0.5 D_night; G3 DSR < 0.95; G4 either era <= 0; G5 PF <= 1.00 | spec §5 |

## Costs
- Planned: p90 cost column, with swap at 2026 rates of -$70/lot/night long, +$29 short, x1.4 on triple Wednesday, per rollover crossing (spec §4, G6).
- The p90 column comes from the goldbot cost basis: a per-year x UTC-hour Dukascopy spread matrix, slippage k_slip = 0.5 x bucket spread per side (an assumption), commission $7 per lot round trip ([PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md) lines 25-27, 139; [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py) lines 1-9; [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 64-67).
- Nothing was applied, because nothing was run.

## Tuning and selection
- Search: none allowed. Arms, close time, hour grouping, N_eff, era boundary, cost column and swap are pinned; sensitivity sweeps are forbidden (spec G6).
- Configurations run (counted from the code/results): 0. Planned: 3 arms over hours {12, 16, 20} plus pooled retry hours. Ledger count ([trial_ledger.csv](../../../registry/trial_ledger.csv) row H-20, n_variants): 9, which is the pinned N_eff, not a count of runs.
- How the reported variant was chosen: not applicable. No variant was reported.
- Preregistered: yes, [H20_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/H20_PREREGISTRATION.md), frozen 2026-08-23. Its SHA-256 starts 5a2b501e, which matches the prefix the README gives. The blind predictions were sealed in a separate file. That file is withheld on purpose; only its SHA-256 is published ([DECISIONS.md](../../../DECISIONS.md) line 25).

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Motivating diagnostic, hour 20 (pre-freeze) | 110 | PF 1.539, +$8,746 at p90 (INSUFFICIENT SAMPLE to support a claim; the spec says so in §7 item 4) | spec §2 |
| Withdrawal reason (power) | - | minimum detectable effect 0.347 ATR at 80% power vs effect about 0.114 ATR | [FUTURE_WORK.md](../../../FUTURE_WORK.md) lines 5-7 |
| Audit: hour-20 cohort, recorded clock vs true UTC | 110 vs 98 | PF 1.793 vs 1.067 at p90 (both INSUFFICIENT SAMPLE) | [PHASE_B_REPORT.md](../../../audit/infrastructure/PHASE_B_REPORT.md) line 45 |
| Audit: Sidak p since 2023, recorded vs true UTC | not recorded | 0.110 vs 0.999 | FUTURE_WORK.md line 11 |

The diagnostic says PF 1.539 at hour 20, while the audit's recorded-clock rerun gives PF 1.793 for the same n=110. The published files do not explain the difference.

## Code and how to rerun
- Code: none. No H-20 runner is in [prereg/](../../../originals/gann_bot_500/research/goldbot/prereg/). The harness it names (`goldbot/triple_barrier.py`, `goldbot/events.py`) is in the goldbot package ([goldbot/](../../../originals/gann_bot_500/research/goldbot/goldbot/)).
- Audit rerun stage: none. The audit decided to leave it unrun ([audit/DECISIONS.md](../../../audit/DECISIONS.md) item 7).
- Public data enough? The M1 bars (`histdata_xau`) and the event file are public. A run would still be a new implementation, because no runner exists.

## Corrections from the release review
- README "Timeframe: H1". Incomplete. The entry rule uses H1 and H4 bars (config.yaml line 10), and the exits were to run on M1 (spec §4).
- README "Costs: per-year x UTC-hour Dukascopy spread matrix, k_slip 0.5 x spread per side (assumption), $7/lot RT". Incomplete. The spec gates on the p90 column of that matrix and adds swap at 2026 rates, -$70 long / +$29 short per lot-night, x1.4 on Wednesday (spec §4).
- README "Data: same 472 events". It does not name the M1 file or say it is bid-only. That flaw makes short-side stops under-detected (spec §7 item 1).
- README "Premise gone on true UTC" gives no figures and no source. The source is PHASE_B_REPORT.md line 45 and FUTURE_WORK.md line 11: on true UTC, n=98, PF 1.067, Sidak p 0.999.
- README "Variants counted in the ledger: 9". This is the pinned N_eff. No configuration was run.
- README "Provenance" cites only `DECISIONS.log (not published)`. FUTURE_WORK.md, PHASE_B_REPORT.md and the prereg in originals/ are published and hold the withdrawal and clock facts.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | Withdrawn unrun: MDE 0.347A vs effect ~0.114A. Sealed prediction never opened. |
| Rerun, recorded clock | not run |
| Rerun, true UTC | not run |

## Verdict
UNVERIFIED. Withdrawn. The audit did not open the sealed prediction. Premise gone on true UTC.

## Audit caveats
Correct disposition per power-first rule.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
