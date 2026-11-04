# CYCLES-1-10

**Audit verdict: VERIFIED-WITH-CORRECTIONS.** Original verdict: INCONCLUSIVE. Dated 2026-08-25. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Which assumptions of the programme survive standard tests?

Family: diagnostics. Market: XAUUSD. Timeframe: H1+H4. Idea source: own.

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Ten rounds ("cycles") of standard diagnostics, from 2026-08-25, on one frozen trade ledger: the 472 trades of the H1 conviction dual-arm breakout rule (flip_bot v1.1 rules). The aim was to see which assumptions of the programme survive standard tests: a break in performance, whether the sample can resolve an edge at all, an hour-of-day effect, and cost sensitivity ([registry/experiments.yaml](../../../registry/experiments.yaml), CYCLES-1-10 and H1 entries). No strategy was tuned. The original cycle scripts were one-off shell work and are not in the repo; the audit recomputed the key statistics ([audit/phaseC/l2_recompute.py](../../../audit/phaseC/l2_recompute.py) line 1).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): H1 and H4 signals, M1 exits (H1 rule).
- Data source and file(s): the frozen ledger [verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv) (472 trades; columns include gross_usd, cost_med, cost_p90, net_p90, atr). It was built from HistData XAUUSD M1 plus a Dukascopy tick cost matrix ([registry/experiments.yaml](../../../registry/experiments.yaml) H1 entry, line 300; [cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json)). The audit recompute uses fresh H1 reruns on both clocks (`h1_recorded_clock_trades.csv`, `h1_true_utc_trades.csv`, written by [audit/phaseC/h1_clock.py](../../../audit/phaseC/h1_clock.py) lines 82-83; not shipped).
- Period: trades from 2015-07-02 to 2026-06-10 (counted from verdict_trades.csv). 267 trades in era "old", 205 in "new".
- In-sample / out-of-sample: none. Diagnostics of an already-opened ledger. Sub-windows used: from 2021-06-19 ("modern") and from 2023-01-01 ("recent") ([l2_recompute.py](../../../audit/phaseC/l2_recompute.py) line 59).

## Rules
- Entry: none new. The ledger is the H1 rule as frozen (prereg commit 35deedc) ([audit/phaseC/h1_clock.py](../../../audit/phaseC/h1_clock.py) line 1).
- Exit (stop, target, time): as H1. Not restated in the published CYCLES files.
- Filters: none added.
- Position sizing: as H1; results in USD per trade, also scaled per ATR (net_p90 / (ATR x 100)) ([l2_recompute.py](../../../audit/phaseC/l2_recompute.py) lines 46-49).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| Break test | Quandt-Andrews sup-F for one break in the mean, 15% trimming, on net, gross and cost per ATR | [l2_recompute.py](../../../audit/phaseC/l2_recompute.py) lines 26-39, 50-52 |
| PSR | probabilistic Sharpe vs SR0 = 0, on monthly sums of net per ATR | same, lines 42-45, 53-55 |
| Hour test | one-sample t-test of entry hour 20:00 UTC trades (net per ATR), Sidak correction k=3 | same, lines 56-65 |
| Minimum track record / power ("n=784 needed vs 41 trades/yr") | method and inputs Not recorded in the published files | [registry/experiments.yaml](../../../registry/experiments.yaml) only |
| Breakeven markup, slippage stress | Not recorded in the published files | README Rules only |
| Cost basis | p90 cost per trade from the cost matrix; the stored ledger includes swap | [H20_PREREGISTRATION.md](../../../originals/gann_bot_500/research/goldbot/prereg/H20_PREREGISTRATION.md) line 30 |

## Costs
The ledger carries median and p90 costs per trade from the per-year x UTC-hour Dukascopy spread matrix, k_slip 0.5 x spread per side, $7/lot round trip ([registry/experiments.yaml](../../../registry/experiments.yaml) H1 entry, line 308). The stored cycle figures include measured swap. The audit recompute uses net_p90 without swap ([audit/VERDICTS.md](../../../audit/VERDICTS.md) line 43).

## Tuning and selection
- Search: none. Diagnostics only.
- Configurations run (counted from the code/results): 0 new rules. Ledger count (registry/trial_ledger.csv n_variants): 0. The three sub-windows (full, modern, recent) and three series (net, gross, cost) are tests, not variants; the Sidak k=3 reflects this.
- How the reported variant was chosen: not applicable.
- Preregistered: no (diagnostics of a frozen ledger). Cycle 10 pre-registered the forward-test criteria used by FORWARD-FLIP-DEMO (per [registry/experiments.csv](../../../registry/experiments.csv)).

## Results
| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| Stored claim | 472 | No significant performance break; cost/ATR break at 2020-02-28; n=784 needed vs 41 trades/yr; hour 20 Sidak p 0.206; PSR 0.041 full sample | [registry/experiments.yaml](../../../registry/experiments.yaml) (original log not published) |
| Recompute, recorded clock: sup-F net/ATR | 472 | F 2.40 at 2018-12-19 (gross 1.65 at 2017-03-15) | [audit/phaseC/l2_recompute.json](../../../audit/phaseC/l2_recompute.json) |
| Recompute, recorded: sup-F cost/ATR | 472 | F 144.43 at 2020-02-28 (matches stored) | same |
| Recompute, recorded: PSR monthly full | 472 | 0.175 (stored 0.041) | same |
| Recompute, recorded: hour 20, from 2021-06-19 | 205 (hour 20: 42) | t 1.90, p 0.065, Sidak 0.182. INSUFFICIENT SAMPLE | same |
| Recompute, recorded: hour 20, from 2023-01-01 | 143 (hour 20: 32) | t 2.17, p 0.038, Sidak 0.110. INSUFFICIENT SAMPLE | same |
| Recompute, true UTC: sup-F net/ATR | 481 | F 3.65 at 2019-10-24 | same |
| Recompute, true UTC: hour 20, from 2021-06-19 | 214 (hour 20: 44) | p 0.642, Sidak 0.954 | same |
| Recompute, true UTC: hour 20, from 2023-01-01 | 151 (hour 20: 33) | p 0.903, Sidak 0.999 | same |
| Recompute, true UTC: PSR monthly full | 481 | 0.028 | same |
| H1 ledger itself, recorded clock, p90 | 472 | PF 1.045, net $4,201 | [audit/phaseC/h1_clock.json](../../../audit/phaseC/h1_clock.json) |
| Audit | | VERIFIED-WITH-CORRECTIONS; "Cash-close story retired" | [audit/VERDICTS.md](../../../audit/VERDICTS.md) line 43 |

On the true UTC clock the hour-20 effect disappears. The stored sup-F 3.36 and Sidak 0.385 / 0.206 include swap; the audit's recompute does not, so the stored values stand as stored (VERDICTS.md line 43).

## Code and how to rerun
- Code: original cycle scripts do not exist (shell work). Recompute: [audit/phaseC/l2_recompute.py](../../../audit/phaseC/l2_recompute.py), inputs from [audit/phaseC/h1_clock.py](../../../audit/phaseC/h1_clock.py).
- Audit rerun stage: `h1_clock` then `c_l2_recompute` ([audit/tools/run_all.sh](../../../audit/tools/run_all.sh)).
- Public data enough? yes for the recompute: `histdata_xau` (public) for the M1 data; the cost matrix is shipped as [cost_matrix.json](../../../originals/gann_bot_500/research/goldbot/results/cost_matrix.json) (built from `dukascopy_ticks`, public). The true-UTC file is built by the audit's clock fix. MinTRL, power, breakeven markup, slippage stress and broker-contact results cannot be rerun: no code is published.

## Corrections from the release review
- README Data: "472-trade frozen ledger". It does not say which rule. It is the H1 conviction dual-arm breakout ledger, [verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv), 2015-07-02 to 2026-06-10.
- README does not say the original cycle code does not exist. Only the audit recompute ([l2_recompute.py](../../../audit/phaseC/l2_recompute.py)) is published, and it covers sup-F, PSR and the hour test only. MinTRL, power, breakeven markup, slippage stress and "first broker contact" have no published code or output.
- README Results, stored "PSR 0.041 full sample". The audit recompute gives 0.175 (recorded clock, no swap) and 0.028 (true UTC) ([l2_recompute.json](../../../audit/phaseC/l2_recompute.json)). VERDICTS does not comment on PSR. The README should show this.
- README Results show recomputed values without n. The hour-20 subsets are 32-44 trades: INSUFFICIENT SAMPLE.
- README Provenance relies on DECISIONS.log, which is not published. The "n=784 needed vs 41 trades/yr" figure has no published source beyond the registry text. (472 trades over about 10.9 years is about 43 a year, counted from verdict_trades.csv.)

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | No significant performance break; cost/ATR break at 2020-02-28; n=784 needed vs 41 trades/yr; hour 20 Sidak p=0.206; PSR 0.041 full sample |
| Rerun, recorded clock | Net sup-F 2.40 at 2018-12-19; Sidak 0.182, 0.110 |
| Rerun, true UTC | Net 3.65 at 2019-10-24; Sidak 0.954, 0.999 |

## Verdict
VERIFIED-WITH-CORRECTIONS. Recomputed without swap, so 3.36 and 0.385, 0.206 stay as stored. Cost break exact at 144.43. Cash-close story retired.

## Audit caveats
Key finding of the programme: an edge is neither shown nor excluded, because the sample cannot resolve it. Cycle 5's precision argument killed in cycle 6; the v1.3 fix killed in cycle 7; all four door-3 predictions refuted in cycle 8.

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
- [originals/gann_bot_500/research/goldbot/results/verdict_trades.csv](../../../originals/gann_bot_500/research/goldbot/results/verdict_trades.csv)
