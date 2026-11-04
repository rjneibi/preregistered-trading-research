# GOLD-LIT-1

**Audit verdict: VERIFIED.** Original verdict: FAILED. Dated 2026-10-14. A verdict grades the stored claim, not the strategy.

**Hypothesis:** Published gold anomalies hold net of cost.

Family: literature replication. Market: XAUUSD. Timeframe: M1/D1. Idea source: Baur; intraday hat literature. Preregistration: [spec.md](spec.md).

> Written for the release from the published code, specs and logs. Each fact names its source file. Where the earlier page was wrong, the last section of the description says so.

## What was tested
Six published gold anomalies, tested in their published form. Two intraday legs of the "hat" pattern (buy in Asia hours, sell short in US hours), two seasonal windows (autumn, winter), and two long-horizon momentum rules (12 and 24 months). All six failed their pre-registered gates. The winter window came closest (Welch t = +1.85 against a required 2).

## Instruments and data
- Instruments: XAUUSD.
- Timeframe(s): M1 for H-A; monthly returns built from D1 closes for H-B and H-C ([gold_lit.py](../../../originals/gann_bot_500/research/gold_lit/gold_lit.py) `utc_m1`, `monthly`).
- Data source and file(s):
  - M1: `research/d_revival/m1.npz`, a splice of HistData M1 bid (to 2026-06-19) and a broker MT5 export (from 2026-06-26), stored in broker time ([data.py](../../../originals/gann_bot_500/research/d_revival/data.py) lines 1-2, 17-22). Converted to UTC with exit2's `to_utc` (minus 2 h, or 3 h in US daylight time) ([exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py) lines 29-34). Manifest group `broker_mt5`.
  - D1: `research/cross_market/data_edge/XAUUSD_D1.npz`, manifest group `broker_mt5` (MT5 demo export).
- Period: M1 2010-01 to 2026-10; monthly 2004-07 to 2026-10, 268 months (spec.md; audit/phaseC/logs_L1/recorded.gold_lit.gold_lit_py.log "monthly data").
- In-sample / out-of-sample: no fitting, so no train/test split. Intraday windows A 2010-17, B 2018-26, C 2023+ (C overlaps B). Monthly halves 2004-14 and 2015-26 (gold_lit.py `WIN`, `halves`; [spec.md](../../../experiments/literature-replication/GOLD-LIT-1/spec.md)).

## Rules
From spec.md and gold_lit.py.
- Entry:
  - H-A1 Asia long: every weekday buy at the first M1 open at or after 00:15 UTC (within 30 min).
  - H-A2 US short: every weekday sell at the first M1 open at or after 13:00 UTC.
  - H-B1 autumn: long gold only in September and November. H-B2 winter: long only in December, January and February.
  - H-C1 / H-C2: at month end, long next month if the trailing 12-month (C1) or 24-month (C2) return is > 0, else flat.
- Exit (stop, target, time): H-A1 exit at the last M1 close before 07:00 UTC; H-A2 buy back at the last close before 20:00 UTC (`leg`). H-B and H-C hold whole months. No stops or targets.
- Filters: weekdays only for H-A. Pre-declared robustness check: each H-A leg shifted +15 min (00:30 / 13:15 entry).
- Position sizing: H-A in $ per oz per trade; H-B and H-C in monthly returns, fully invested when long (gold_lit.py).

## Indicators and parameters
| Indicator or parameter | Value(s) used | Source |
|---|---|---|
| H-A1 times | buy 00:15 UTC, sell 07:00 UTC | spec.md; gold_lit.py `hat` |
| H-A2 times | sell 13:00 UTC, buy 20:00 UTC | same |
| Shift check | +15 min on entry | same |
| H-B months | B1 Sep+Nov; B2 Dec+Jan+Feb | gold_lit.py `seasonality` |
| H-C lookback | 12 and 24 months, decided at prior month end | gold_lit.py `momentum` |
| Financing (H-B, H-C, buy-and-hold) | 3% per year (0.25% per month) | gold_lit.py `fin = 0.03 / 12` |

## Costs
From gold_lit.py:
- H-A: $0.40/oz round trip; stress $0.80. No swap, since no rollover is crossed.
- H-B: financing 3%/yr on long months only; no transaction cost in the code.
- H-C: financing 3%/yr on held months plus 0.05% per switch. Buy-and-hold pays the same 3%.

## Tuning and selection
- Search: none. Six hypotheses fixed in advance; "No variant is added after the run" (spec.md).
- Configurations run (counted from the code/results): 6 hypotheses, plus 2 shifted H-A legs used only inside the H-A gates. Ledger count (registry/trial_ledger.csv, GOLD-LIT-1): 6. They match.
- How the reported variant was chosen: not applicable; all six are reported.
- Preregistered: yes ([PREREG.md](../../../originals/gann_bot_500/research/gold_lit/PREREG.md), frozen 2026-10-14 before any run; copied as spec.md). The author's own blind prediction was not recorded (spec.md last line). No code deviation found.

## Results
Gates (spec.md): H-A, each leg: net mean > 0 in A, B and C; full-sample net t >= 2; > 0 in B and C at stress cost; the +15 min shift also > 0 in A, B, C. H-B: in-window mean > other months in both halves, Welch t >= 2, net > 0. H-C: Sharpe >= buy-and-hold in both halves and a smaller full-sample max drawdown.

| Slice | Trades (n) | Result | Source file |
|---|---|---|---|
| H-A1 Asia long, all | 4,319 days | net t -0.14; A n=2,320 net -$0.088/oz; B n=2,257 -$0.050; C n=969 +$0.285 (stress -$0.115). FAIL | [recorded gold_lit log](../../../audit/phaseC/logs_L1/recorded.gold_lit.gold_lit_py.log) |
| H-A2 US short, all | 4,130 days | net t -0.57; A n=2,263 -$0.284; B n=2,117 +$0.018; C n=865 +$0.619. FAIL | same |
| H-B1 Sep+Nov | 47 in-window months (24 + 23) | 2004-14 +1.95% vs +0.63%; 2015-26 -1.00% vs +1.37%; Welch t -0.37. FAIL. INSUFFICIENT SAMPLE | same |
| H-B2 Dec-Feb | 69 in-window months (34 + 35) | +1.40% vs +0.69%; +2.41% vs +0.52%; Welch t +1.85 (needs 2). FAIL. INSUFFICIENT SAMPLE | same |
| H-C1 12m momentum | 267 months, invested 69% | Sharpe 0.57 vs 0.40 (2004-14); 0.41 vs 0.57 (2015-26); max DD 35% vs 49%. FAIL | same |
| H-C2 24m momentum | 267 months, invested 72% | Sharpe 0.44 vs 0.40; 0.46 vs 0.57; max DD 42% vs 49%. FAIL | same |
| Audit rerun, true clock | e.g. H-A2 4,128 days | all 6 still FAIL; intraday figures move (H-A1 net t -0.07; H-A2 net t -0.40) | audit/phaseC/logs_L1/true.gold_lit.gold_lit_py.log |

H-B and H-C count months, not trades; the 100-trade rule does not map onto them directly, so the seasonal rows are marked INSUFFICIENT SAMPLE on their month counts.

## Code and how to rerun
- Code: [gold_lit.py](../../../originals/gann_bot_500/research/gold_lit/gold_lit.py), data loader [data.py](../../../originals/gann_bot_500/research/d_revival/data.py), UTC conversion in [exit2.py](../../../originals/gann_bot_500/research/exit2/exit2.py). Audit queue [run_l1_queue.sh](../../../audit/phaseC/run_l1_queue.sh) (jobs `recorded gold_lit gold_lit.py` and `true gold_lit gold_lit.py`).
- Audit rerun stage: `l1_queue` (audit/tools/run_all.sh). A 2010-2012 exclusion run is `no1012_make`/`no1012_run`.
- Public data enough? No. Both inputs are manifest group `broker_mt5` (`d_revival/m1.npz`, `cross_market/data_edge/XAUUSD_D1.npz`).

## Corrections from the release review
- README "Data: 2004-2026" hides two different sources. Intraday tests use a HistData + broker MT5 splice, 2010-2026, converted to UTC in code; monthly tests use a broker MT5 D1 export, 2004-07 to 2026-10. Both are classed `broker_mt5`, not public (data.py; data/manifest.csv).
- README "Costs: $0.40; IC Raw post hoc" is partly wrong. $0.40/oz (stress $0.80) applies to the intraday legs only. Monthly tests use 3%/yr financing, plus 0.05% per switch for momentum. No "IC Raw" cost appears in gold_lit.py or its logs (gold_lit.py).
- README "Splits: halves" is incomplete. Intraday legs use windows A 2010-17, B 2018-26, C 2023+; only the monthly tests use halves (gold_lit.py `WIN`).
- README "Gates: see prereg" gives nothing on the page. The gates are listed above (spec.md).
- README results give no n. See the table: 4,319 and 4,130 trading days for H-A; 47 and 69 in-window months for H-B; 267 months for H-C.
- README "Rerun, true UTC: unchanged" is loose. Verdicts are unchanged, but the intraday numbers change (e.g. H-A1 net t -0.14 to -0.07) (true.gold_lit.gold_lit_py.log).
- README "Reruns exact" holds for the recorded clock only.
- Provenance lists `DECISIONS.log`, which is not in the repository, and does not link gold_lit.py.

## Registry and audit record

| Basis | Result |
|---|---|
| Stored | ALL 6 FAIL; winter t=+1.85 closest |
| Rerun, recorded clock | All 6 FAIL |
| Rerun, true UTC | unchanged |

## Verdict
VERIFIED. Reruns exact.

## Audit caveats
None recorded beyond the general limits in [FINDINGS.md](../../../FINDINGS.md).

## Provenance
Status of the number: found. Audit trail: [VERDICTS.md](../../../audit/VERDICTS.md).

- `originals/gann_bot_500/research/goldbot/results/DECISIONS.log` (withheld: it names excluded third parties and holds account details, see the root DECISIONS.md, item 21)
