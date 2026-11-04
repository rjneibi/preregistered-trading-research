# H-P

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Two-arm portfolio beats best single arm.

Family: portfolio. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
H-P asks whether a two-arm gold portfolio still has an edge once it is priced at measured per-year spread costs ([spec.md](../../../experiments/portfolio/H-P/spec.md)). Arm A is the conviction dual-arm H1/H4 breakout (the H1-verdict trades). Arm B is FINAL_v3, the H4-close R3/S3 breakout. The arms trade independently at 1 lot each, and a combined daily loss breaker applies. Nothing is tuned: both arms are frozen earlier specs, and only the costs are new.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s):
  - Arm A: H1 and H4 closes.
  - Arm B: H4 closes at 12/16/20 UTC.
  - ATR on H1, daily bars cut at UTC 00:00, exits on M1 ([hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py) lines 45-59).
- Data source and file(s): HistData M1 XAUUSD via `config.yaml` `m1_path: ../data/xauusd_m1_histdata.csv` ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7; [data/manifest.csv](../../../data/manifest.csv) line 428, group `histdata_xau`). Arm A trades are read from [verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv) (hp_runner.py lines 96-97). Costs come from the Dukascopy tick spread matrix [cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json) (hp_runner.py lines 92-95).
- Period: old era 2015-06-19 to 2021-06-18 23:59 UTC; new era 2021-06-19 to the end of the data. There is a 100-day warm-up (hp_runner.py lines 32-35).
- In-sample / out-of-sample: the two eras, each with its own gate (gate 2). Both eras had been used in earlier development of both arms ([PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md) ledger rows 14, 25, 34). Neither is a clean holdout.

## Rules
- Entry:
  - Arm A: the conviction dual-arm event set of the H1 verdict ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 9-15: `variant: final`, H1 closes 12-20 UTC inclusive, skip Monday, dead-check on the last 10 H4 closes, 24 h re-entry block, at least 50 H4 bars of history).
  - Arm B: `generate_events_base` H4-close R3/S3 breakouts, kept only at 12, 16 or 20 UTC, first event per day (hp_runner.py lines 55-57).
- Exit (stop, target, time):
  - Arm A: TP 0.8 × ATR, SL 2.4 × ATR, 24 h time stop. The bail rules are on. In the high-vol regime, half closes at the first M1 close ≤ -1.2 × ATR. In the low-vol regime, everything closes at an M1 close ≤ -1.0 × ATR after 8 h. Fills are `gap_open` (config.yaml lines 20-35).
  - Arm B: TP 1.4 × ATR, SL 2.1 × ATR, 24 h, no bail, `gap_open` (hp_runner.py lines 58-59).
- Filters: portfolio breaker. A NEW entry in either arm is skipped if the realized P&L of trades closed earlier that UTC day is ≤ -$1,500 (hp_runner.py lines 36, 73-87).
- Position sizing: 1.00 lot per trade in each arm, positions independent ([spec.md](../../../experiments/portfolio/H-P/spec.md), "Pinned specs").

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| R3 / S3 | PP ± 1.0 × prior UTC-day range, day cut utc00 | [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 17-18; [PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/PREREGISTRATION.md) |
| ATR | Wilder ATR(14) on H1, SMA seed | config.yaml lines 31-33; hp_runner.py line 54 |
| Vol regime (arm A bail) | ATR vs 2,160-bar (90 d) median, min 200 bars | config.yaml lines 34-35 |
| Arm A TP / SL / time | 0.8 / 2.4 × ATR / 24 h | config.yaml lines 22-25 |
| Arm A bail | hivol half at -1.2 × ATR; lovol all at -1.0 × ATR after 8 h | config.yaml lines 26-30 |
| Arm B TP / SL / time | 1.4 / 2.1 × ATR / 24 h | [hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py) line 58 |
| Arm B session | H4 closes at 12, 16, 20 UTC; 1 per day | hp_runner.py lines 56-57 |
| Dead-check | 10 H4 closes | config.yaml line 13 |
| Breaker | -$1,500 realized per UTC day | hp_runner.py line 36 |

## Costs
Per trade: lots × 100 oz × [(entry spread + exit spread)/2 + 0.5 × (entry spread + exit spread)] + $7 commission ([cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py) lines 124-128). Spreads come from a per-year × UTC-hour Dukascopy tick matrix. Gates 1-4 use the median and gate 5 uses p90. Slippage `k_slip = 0.5` is an assumption, as the prereg says ([hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py) lines 92-95). A flat 20-point column (`net_flat`) is reported for arm B only (line 69).

## Tuning and selection
- Search: none. Both arms are frozen, and the gates are fixed in the prereg.
- Configurations run (counted from the code/results): 1. Ledger count ([registry/trial_ledger.csv](../../../registry/trial_ledger.csv) line 74, n_variants): 1. They agree. The audit's partial-matrix reproduction is ledger row AUD-C-03 (line 146), counted at 0.
- How the reported variant was chosen: not applicable.
- Preregistered: yes. The page cites [HP_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/HP_PREREGISTRATION.md), frozen 2026-07-06, commit 56d89dd (private history, not verifiable). Gates: (1) PF ≥ 1.20, (2) each era PF ≥ 1.00, (3) net > best single arm, (4) monthly correlation between arms ≤ 0.60, (5) p90 PF ≥ 1.05. No deviation was found in the code.

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored, portfolio | 902 (2 blocked) | PF 1.373 (old 1.008 / new 1.641), p90 1.300, net $74,772, win 69.7%; monthly corr 0.821. Gate 4 fails, so FAIL | [HP_run.json](../../../originals/gann_bot_500/research/goldbot/results/HP_run.json); [HP_portfolio_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/HP_portfolio_trades.csv) |
| Stored, arm A / arm B alone | 472 / 432 | PF 1.236 / 1.459 | same |
| Audit, partial matrix (stored inputs) | 902 | PF 1.373; identical to stored | [logs_partial/hp_runner.log](../../../audit/phaseC/logs_partial/hp_runner.log) |
| Audit, recorded clock, full matrix | 902 | PF 1.279 (old 0.965 / new 1.504), p90 1.203, corr 0.82. Gates 2 and 4 fail | [logs_recorded/hp_runner.log](../../../audit/phaseC/logs_recorded/hp_runner.log); [goldbot_compare.json](../../../audit/phaseC/goldbot_compare.json) |
| Audit, recorded clock, arm A / arm B | 472 / 432 | PF 1.130 / 1.376 (arm B old 0.977) | same |
| Audit, true UTC, full matrix | 915 | PF 1.033 (old 0.841 / new 1.153), p90 0.972, net $7,984, corr 0.75. Gates 1, 2, 4 and 5 fail | [logs_true/hp_runner.log](../../../audit/phaseC/logs_true/hp_runner.log) |
| Audit, true UTC, arm A / arm B | 481 / 436 | PF 1.009 / 1.040 (arm B old 0.847) | same |

Verdict: original FAILED; audit VERIFIED-WITH-CORRECTIONS ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 33).

## Code and how to rerun
- Code: [hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py), [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py), the [goldbot package](../../../originals/gann_bot_500/research/goldbot/goldbot) (`events.generate_events_base`, `triple_barrier.run_exits`) and [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml). Arm A input: [verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv), written by the H1 verdict run.
- Audit rerun stage: `sb_goldbot`, then `goldbot_both` (recorded and true; [run_goldbot_both.sh](../../../audit/phaseC/run_goldbot_both.sh) runs run_verdict then hp_runner); `goldbot_partial` for the stored reproduction ([run_goldbot_partial.sh](../../../audit/phaseC/run_goldbot_partial.sh)); `c_compare_goldbot` for the comparison file.
- Public data enough? Yes. It needs the `histdata_xau` group ([data/manifest.csv](../../../data/manifest.csv) line 428). The cost matrix is published in `results/`, and its tick inputs are in the `dukascopy_ticks` group.

## Corrections from the release review
- "Caveats: Failed on correlation" is incomplete. It is true only of the stored run. On the recorded clock with the full matrix, gate 2 also fails (old era PF 0.965). On true UTC, gates 1, 2, 4 and 5 all fail (PF 1.033, old 0.841, p90 0.972) ([logs_true/hp_runner.log](../../../audit/phaseC/logs_true/hp_runner.log)).
- "Stored: PF 1.373, corr 0.82" gives no n. n = 902 portfolio trades (472 arm A + 432 arm B, 2 blocked) ([HP_run.json](../../../originals/gann_bot_500/research/goldbot/results/HP_run.json)).
- The rerun rows give no correlation. It is 0.82 on the recorded clock and 0.75 on true UTC. Both fail gate 4 ([goldbot_compare.json](../../../audit/phaseC/goldbot_compare.json)).
- "Rules: Arm A + arm B" defines nothing. The arm rules are in [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) lines 9-35 and [hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py) lines 45-59.
- Provenance cites `DECISIONS.log (not published)`, but the runner [hp_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/hp_runner.py) and all three audit logs are published.
- "Data: HistData M1 + Dukascopy tick cost matrix 2015-2026" does not say that the stored PF 1.373 used an earlier partial-coverage matrix (commit 977fff5, [cost_matrix_977fff5.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix_977fff5.json); [audit/phaseC/sandbox_partial.py](../../../audit/phaseC/sandbox_partial.py) line 1).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | PF 1.373, corr 0.82 |
| Rerun, recorded clock | n=902 PF 1.279, old 0.965 |
| Rerun, true UTC | n=915 PF 1.033, old 0.841 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Stored PF 1.373 reproduces on the partial matrix. On the full matrix gate 2 reads false.

## Audit caveats
Failed on correlation.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/HP_run.json](../../../originals/gann_bot_500/research/goldbot/results/HP_run.json)
