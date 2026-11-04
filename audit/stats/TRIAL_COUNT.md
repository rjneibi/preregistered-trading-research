# How the trial count is built

Generated from `registry/trial_ledger.csv` by `stats/trial_count.py`. Current total: **179,000 variants** over 174 ledger rows.

## What counts as a trial

- One variant is one distinct rule, parameter set and market combination that produced a result, whether or not anyone looked at it closely.
- A grid counts every cell. An optimiser counts every configuration it evaluated. TVS-1's 64,521 configs are all counted.
- Audit reruns of the same rule count 0, because they add no new choice. The one exception is TVS-1's rerun, which drew 64,431 mostly new configs, and they count (DECISIONS 46). New audit experiments count their stated variants.
- Analyst-derived work stays in the count although it is not published or tested. Removing it would flatter the rest.
- Row counts with `count_basis` marked as a floor are lower bounds.
- Blank counts are read as 0. NQ-TRANSFER is the one case that matters, and it has no recorded count.

## Primary and secondary DSR

The primary DSR uses the ledger total, 179,000 now. Phase C used the floor at that time, 114,500, and those files keep it. The rise comes from TVS-1's fresh draw of 64,431 configs and Phase E's stated variants. It treats all work as one search, including unrelated markets.
That is harsh, and it is deliberate: this is one researcher selecting what to look at next from everything tried so far.
The secondary DSR uses the variants inside the programme that produced the result. It answers a narrower question, and passing it does not change a verdict.
Read the DSR as an order of magnitude. Two inputs pull opposite ways and neither is measured. Trial Sharpe variance uses the null value 1/T (DECISIONS 24), which understates the hurdle. N treats every variant as independent, which overstates it, since TVS-1 and its redraw sample one grid and LBO-1's cells are near-duplicates.
At 179,000 trials a DSR of 0.95 needs a t-statistic of about 6.2, so almost nothing can clear this gate. Failing it alone carries little information, which is why VERDICTS also shows N as dated at each result and the other weaknesses.

## Counts corrected by the second release review

A release review in November 2026 counted the configurations in the published code and results and found 18 rows where the ledger counts fewer than were run. The ledger is left as it was, and the counts sit beside it in `registry/ledger_corrections.csv`. With them the total is **190,234** rather than 179,000.
The deflated Sharpe in VERDICTS keeps the ledger count. A larger count only raises the hurdle, and the t-statistic it needs grows with the log of the count, so no verdict can change. Family counts for the fragile results become: XM-1-A1 17 to 17, SW-1 50 to 60, EDGE-1-F6 34 to 37, TUNE-1-DIP 3,960 to 3,960.

| Trial | Ledger | Counted | Basis |
|---|---:|---:|---|
| LBO-1 | 36,864 | 47,692 | sum of listed parts |
| SW-1 | 50 | 60 | exact |
| EDGE-1-F6 | 8 | 11 | exact |
| HPF | 7 | 12 | exact |
| HSW | 1 | 8 | exact |
| HCRT | 1 | 6 | exact |
| HV | 1 | 2 | exact |
| SZ | 1 | 4 | exact |
| TA-LAB-R1-R2 | 5 | 28 | exact |
| TA-LAB-R4-SWEEP | 4 | 72 | exact |
| TA-LAB-R5-R9 | 4 | 58 | exact |
| SWEEP-MTF-1 | 4 | 8 | exact |
| XAU-FLIP-RAW | 2 | 15 | exact |
| DR-EDGE-SCREEN | 8 | 20 | exact |
| SC-1 | 18 | 27 | exact |
| BOT-LAB-1 | 12 | 116 | approximate |
| GB-22 | 1 | 22 | approximate |
| FR-L | 6 | 70 | approximate |

## By family

| Family | Rows | Variants |
|---|---:|---:|
| indicator search | 1 | 64,521 |
| audit Phase D | 7 | 64,431 |
| breakout | 1 | 36,864 |
| ICT/SMC | 6 | 6,494 |
| mean-reversion | 2 | 3,972 |
| analyst/copy | 21 | 1,464 |
| ORB | 1 | 800 |
| price action | 4 | 58 |
| swing | 1 | 50 |
| pivot/breakout | 6 | 43 |
| goldbot pre-July ledger | 39 | 41 |
| audit Phase E | 15 | 38 |
| support/resistance | 3 | 30 |
| mixed | 3 | 21 |
| crypto | 1 | 20 |
| scalping/ORB | 1 | 18 |
| LLM agent | 1 | 17 |
| trend filter | 1 | 12 |
| scalping | 1 | 12 |
| transfer test | 3 | 10 |
| time-of-day | 1 | 9 |
| trend | 2 | 9 |
| event | 1 | 7 |
| ICT | 1 | 6 |
| exits | 1 | 6 |
| literature replication | 1 | 6 |
| grid | 1 | 5 |
| TA levels | 1 | 5 |
| volatility | 1 | 5 |
| ML | 2 | 4 |
| regime filter | 1 | 3 |
| volume | 1 | 2 |
| ML/meta-label | 1 | 2 |
| portfolio | 2 | 2 |
| risk geometry | 1 | 2 |
| audit rerun | 2 | 2 |
| arbitrage | 1 | 1 |
| trend/mean-reversion | 1 | 1 |
| pivot/mean-reversion | 1 | 1 |
| news sizing | 1 | 1 |
| routing overlay | 1 | 1 |
| sizing | 1 | 1 |
| regime | 1 | 1 |
| forward test | 1 | 1 |
| copy trading | 1 | 1 |
| goldbot ledger | 12 | 0 |
| regime/sizing | 1 | 0 |
| diagnostics | 2 | 0 |
| implementation audit | 1 | 0 |
| rotation | 1 | 0 |
| audit Phase C | 10 | 0 |

## Family counts used for the secondary DSR

| Result | Ledger rows counted | Family N |
|---|---|---:|
| XM-1-A1 | XM-1-A1, XM-1-OTHERS | 17 |
| SW-1 | SW-1 | 50 |
| EDGE-1-F6 | CR-1, EDGE-1-F1, EDGE-1-F3-F5-F7, EDGE-1-F6, EDGE-1-F9 | 34 |
| TUNE-1-DIP | TUNE-1-DIP | 3,960 |
