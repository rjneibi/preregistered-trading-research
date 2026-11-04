# SZ

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: FAILED. Dated 2026-07-06. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Regime tilt repairs the sizing inversion.

Family: sizing. Market: XAUUSD. Timeframe: H1+H4. Idea source: own. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Risking a constant 1% of equity per trade (lots proportional to 1/ATR) turned the goldbot "final" breakout from a 1-lot PF above 1 to a sized PF below 1 in the HR in-sample run. SZ tested whether a regime tilt fixes this: risk 1.0% in high-volatility trades and 0.5% in low-volatility trades. Two secondary policies (an ATR cap and square-root sizing) were also run. All four policies walk the same 472 trades in time order from $10,000.

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): base trades from the H1 + H4 strategy; no new bars are built ([sz_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/sz_runner.py) lines 92-93).
- Data source and file(s): [results/verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv) (per-trade 1-lot net, ATR and hivol flag), produced by [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) from HistData M1 ([config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml) line 7).
- Period: 2015-06-19 to the end of the M1 file (run_verdict.py lines 41-43).
- In-sample / out-of-sample: none; the full window is the test set because no policy parameter is fitted ([spec.md](../../../experiments/sizing/SZ/spec.md) lines 36-41). Evaluation by era: old 2015-06-19 to 2021-06-18 (n=267), new from 2021-06-19 (n=205) ([SZ_run.json](../../../originals/gann_bot_500/research/goldbot/results/SZ_run.json)). CAP and A0 were calibrated on pre-cutoff (HR IS) trades only (spec.md lines 26-31).

## Rules
- Entry: the base goldbot "final" trades, unchanged (R3/S3 = PP +/- (H - L) of the prior day; H1 close beyond a live level with H1 and H4 arms agreeing; 12-20 UTC; skip Monday; dead-level check over 10 H4 closes; 24 h block) ([events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py) `generate_events_final`).
- Exit (stop, target, time): TP 0.8 x ATR, SL 2.4 x ATR, 24 h, bail overlay (config.yaml lines 20-35).
- Filters: none added.
- Position sizing: lots = floor((equity x risk fraction) / (stop distance x $100 per lot), 0.01); skip the trade if below 0.01 lot ([modules/sizing.py](../../../originals/gann_bot_500/research/goldbot/modules/sizing.py) lines 105-129). Trade P&L = 1-lot net x lots; equity compounds in event order (sz_runner.py lines 63-74). Policies (sz_runner.py lines 44-54):
  - B0 baseline: stop 2.4 x ATR, risk 1%.
  - P (primary): stop 2.4 x ATR, risk 1% if hivol else 0.5%.
  - S1: stop 2.4 x min(ATR, 3.9344), risk 1%.
  - S2: stop 2.4 x sqrt(ATR x 2.8789), risk 1%.

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Start equity | $10,000 | sz_runner.py line 41 |
| Stop multiple for sizing | 2.4 x ATR | sz_runner.py line 40 |
| Risk fraction | 1% (B0, S1, S2); 1% hivol / 0.5% lovol (P) | sz_runner.py lines 46-53 |
| hivol flag | day-build H1 ATR(14) > its 2,160-bar (90-day) median | [events.py](../../../originals/gann_bot_500/research/goldbot/goldbot/events.py) `generate_events_final`; config.yaml line 34 |
| CAP (S1) | 3.9344 (IS trade-ATR p75) | sz_runner.py line 38; spec.md line 27 |
| A0 (S2) | 2.8789 (IS trade-ATR median) | sz_runner.py line 39; spec.md line 30 |
| Lot step / min / max | 0.01 / 0.01 / 100 | config.yaml lines 110-115 |

## Costs
Inherited from the base trades' `net_med` column: per-year x UTC-hour median spread, slippage 0.5 x spread per side, $7 per lot round trip ([run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py) lines 83-86; [cost_matrix.py](../../../originals/gann_bot_500/research/goldbot/prereg/cost_matrix.py) `trade_cost_usd`). Costs scale with lots because the 1-lot net is multiplied by lots. The stored SZ_run.json matches the audit rerun on the earlier partial cost matrix (commit 977fff5), not the full matrix ([logs_partial/sz_runner.log](../../../audit/phaseC/logs_partial/sz_runner.log); [run_goldbot_partial.sh](../../../audit/phaseC/run_goldbot_partial.sh) header).

## Tuning and selection
- Search: none. Four pinned policies.
- Configurations run (counted from the code/results): 4 policies (B0, P, S1, S2), of which 3 are tested against the baseline (sz_runner.py line 98). Ledger count (registry/trial_ledger.csv n_variants): 1. They differ: the ledger counts only P, although S1 and S2 were pre-registered secondaries with a displacement rule and were computed.
- How the reported variant was chosen: P was fixed a priori as the primary (the live bot's published tilt). S1 or S2 could displace P only if P passed and the secondary beat P's sized PF by 0.03 in both eras (spec.md lines 32-33; sz_runner.py lines 115-124). P failed, so no displacement was checked.
- Preregistered: yes. [spec.md](../../../experiments/sizing/SZ/spec.md), copied from [SZ_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/SZ_PREREGISTRATION.md), frozen 2026-07-06. Gates, in both eras: P sized PF >= B0 sized PF + 0.05; P sized PF >= 1-lot PF - 0.02; P net/maxDD >= B0 net/maxDD (spec.md lines 48-52). No deviation found.

## Results
Sized PF per era. Each era has 267 (old) or 205 (new) trades for every policy (SZ_run.json).

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored 1-lot reference | old 267 / new 205 | PF 0.950 / 1.418 | [SZ_run.json](../../../originals/gann_bot_500/research/goldbot/results/SZ_run.json) |
| Stored B0 1% flat | 267 / 205 | PF 0.936 / 1.289 | SZ_run.json |
| Stored P tilt | 267 / 205 | PF 0.928 / 1.316; net/maxDD -0.373 / 3.453 | SZ_run.json |
| Stored S1 cap | 267 / 205 | PF 0.951 / 1.394 | SZ_run.json |
| Stored S2 sqrt | 267 / 205 | PF 0.944 / 1.346 | SZ_run.json |
| Stored gates | - | gates 1 and 2 FAIL in both eras; gate 3 passes: FAIL | SZ_run.json |
| Audit rerun, partial matrix | 267 / 205 | identical to stored | [logs_partial/sz_runner.log](../../../audit/phaseC/logs_partial/sz_runner.log) |
| Audit rerun, full matrix, recorded clock: 1-lot / B0 / P | 267 / 205 | 1-lot 0.897 / 1.276; B0 0.883 / 1.096; P 0.879 / 1.153; FAIL | [logs_recorded/sz_runner.log](../../../audit/phaseC/logs_recorded/sz_runner.log) |
| Audit rerun, full matrix, true UTC: 1-lot / B0 / P | era n not printed | 1-lot 0.831 / 1.114; B0 0.757 / 1.036; P 0.806 / 1.161; FAIL | [logs_true/sz_runner.log](../../../audit/phaseC/logs_true/sz_runner.log) |

## Code and how to rerun
- Code: [sz_runner.py](../../../originals/gann_bot_500/research/goldbot/prereg/sz_runner.py), [modules/sizing.py](../../../originals/gann_bot_500/research/goldbot/modules/sizing.py), base trades from [run_verdict.py](../../../originals/gann_bot_500/research/goldbot/prereg/run_verdict.py), [config.yaml](../../../originals/gann_bot_500/research/goldbot/config.yaml).
- Audit rerun stage: `goldbot_both` and `goldbot_partial` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? Yes. Manifest group `histdata_xau`; cost matrices are committed.

## Corrections from the release review
- README "Variants counted in the ledger: 1" is wrong as a count of what ran. Four policies were computed and three were tested against the baseline (B0, P, S1, S2; sz_runner.py line 98; SZ_run.json `policies`).
- README results rows "Rerun, recorded clock: One lot old 0.897, new 1.276" and "Rerun, true UTC: old 0.831, new 1.114" are the 1-lot reference PFs, not the tilt policy. The rerun tilt (P) sized PFs are old 0.879 / new 1.153 (recorded) and old 0.806 / new 1.161 (true UTC) (logs_recorded/sz_runner.log; logs_true/sz_runner.log). The registry's corrected-result cell repeats the same 1-lot figures.
- README "Rules: Tilt on 1/ATR lots." omits the numbers: 1.0% risk when hivol, 0.5% when lovol, stop 2.4 x ATR, $10,000 start, 0.01-lot floor with skip (sz_runner.py lines 38-54).
- README stored result gives no n. Each era has n=267 (old) and n=205 (new) (SZ_run.json).
- README "Costs: per-year x UTC-hour Dukascopy spread matrix" is misleading for the stored figures: they come from the earlier partial matrix (logs_partial/sz_runner.log).

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | tilt old PF 0.928 vs 0.936 |
| Rerun, recorded clock | One lot old 0.897, new 1.276 |
| Rerun, true UTC | old 0.831, new 1.114 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Stored tilt figures reproduce on the partial matrix.

## Audit caveats
First genuinely blind freeze; both forecasters were wrong at high confidence, which reset the calibration ledger.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/SZ_run.json](../../../originals/gann_bot_500/research/goldbot/results/SZ_run.json)
