# Finding: the HistData gold file was read as UTC and it is not

Status: confirmed, 2026-10-31. Affects the zone-flip and goldbot families, July to August 2026.
No verdict changes direction, and no failed strategy passes. Several results that looked close to passing were clock effects.

## What is wrong

`research/data/xauusd_m1_histdata.csv` holds epoch stamps. The code treated them as true UTC. They run one hour ahead for most of the year:

| Period | Stamp minus true UTC | Switch dates |
|---|---|---|
| Through 2018 | +1h between the US switches, 0 otherwise | US |
| 2019 onward | +1h between the EU switches, 0 otherwise | EU |

So 62.1% of bars are off by one hour. Before 2019 the stamps equal New York local time plus 5 hours. From 2019 they equal
London time. A 2026-10-13 comment in `d_revival/data.py` had already noted the New York rule, but that note never reached
the older results. It also missed the 2019 change.

## How it was detected

| Check | Result | Evidence |
|---|---|---|
| NFP spike, first Fridays | Stamped 13:30 in both seasons. True time is 12:30 in US summer | `infrastructure/data_profile.json` |
| Close-change match against Dukascopy, sampled months | 60-minute lag every July, 0 every January | `infrastructure/clock_cross.json` |
| Daily map against Dukascopy, every trading day 2013-2026 | 3,474 days, 2 values, 28 clean segments | `phaseC/clock_map_all.json` |
| FOMC 14:00 ET statement, 91 dates | See below | `phaseC/clock_anchors.json` |
| Weekly reopen hour, by year and season | Corrected file matches Dukascopy each year from 2013 | same file |
| Daily maintenance break hour | Raw: stamp hour 22 all year. Corrected: 21 in summer, 22 in winter, same as Dukascopy | same file |

FOMC, largest first bar on the statement. Counts are events found at each stamp time:

| Series | US summer, 18:00 | US summer, 19:00 | Other | Winter, 19:00 | Other |
|---|---|---|---|---|---|
| HistData raw | 9 | 48 | 3 | 21 | 1 |
| HistData corrected | 47 | 1 | 5 | 21 | 1 |
| Dukascopy (reference) | 51 | 1 | 5 | 21 | 1 |

Twelve FOMC dates since 2019 fall in the weeks between the US and EU switches, where the raw stamp is already UTC. That is where the raw 18:00 events are expected.

## The first fix was wrong, and the extra anchor caught it

The Phase B fix applied US dates to every year. One more independent anchor was required before any rerun depended on it. Running
it showed the corrected file one hour off on 15 to 20 trading days a year from 2019. The daily map then gave the two-regime rule above.
The Phase B H1 figures (n=478, PF 1.012) came from that first fix and are replaced by the figures below.

The corrected file now shows zero lag on all 3,474 days, all 162 months and all 803 days around the US switches.
The lowest monthly correlation against Dukascopy is 0.916. Years 2010-2012 have no Dukascopy overlap, so the US rule there is an
assumption, supported only by the reopen and break hours. The review found three macro anchors in the US-to-EU gap weeks that also fit the US rule: NFP 2010-11-05, NFP 2012-11-02 and CPI 2012-03-16. Those years are labelled `ASSUMED-CLOCK` everywhere. `VERDICTS.md` shows every affected gold result with and without them, and no pass or fail line moves.

## What is affected

Files checked against Dukascopy day by day:

| Dataset | Finding | Effect |
|---|---|---|
| `data/xauusd_m1_histdata.csv` | Defect above | Goldbot, zone-flip, DR, FR families |
| `d_revival/m1.npz` | HistData + 2h, so it inherits the switch dates | Matches broker time from 2019, not before. Up to one hour off a New York clock on 15 to 20 trading days a year |
| `ta_lab/data/*.npy` through `lab.load()` | Clean on all 1,098 days | None. Phase B item B4 is withdrawn |
| `cross_market` M1 (`server = Athens local`) | Clean, converted correctly in `scalp_lab` | None |
| Dukascopy files (LBO, CRT, Powell ticks) | True UTC | None |

## Before and after

Same rules, parameters and costs. Only timestamps moved. Recorded-clock runs reproduce the stored files exactly.

| Result | Trades | Full PF | Old era | New era | p90 PF | Verdict |
|---|---|---|---|---|---|---|
| H1 recorded | 472 | 1.130 | 0.897 | 1.276 | 1.045 | FAILED |
| **H1 true UTC** | 481 | **1.009** | 0.831 | 1.114 | 0.933 | FAILED |
| H-B recorded | 432 | 1.376 | 0.977 | 1.705 | 1.309 | FAILED |
| **H-B true UTC** | 436 | **1.040** | 0.847 | 1.162 | 0.989 | FAILED |
| H-N news days, recorded | 66 | 1.443 | 1.130 | 1.656 | 1.342 | FAILED |
| **H-N true UTC** | 65 | **0.914** | 0.724 | 1.028 | 0.848 | FAILED |
| H-P portfolio, recorded | 902 | 1.279 | 0.965 | 1.504 | 1.203 | FAILED |
| **H-P true UTC** | 915 | **1.033** | 0.841 | 1.153 | 0.972 | FAILED |
| H-R routed OOS, recorded | 107 | 1.336 | | | 1.237 | FAILED |
| **H-R true UTC** | 105 | **1.075** | | | 0.994 | FAILED |
| H-M filtered, recorded | | 1.102 | 0.888 | 1.251 | 1.020 | FAILED |
| **H-M true UTC** | | **0.999** | 0.814 | 1.114 | 0.927 | FAILED |
| FINAL_v3 recorded, 20-point cost | 432 | 1.667 | 1.244 | 2.005 | | FAILED |
| **FINAL_v3 true UTC** | 436 | **1.254** | 1.066 | 1.371 | | FAILED |
| FINAL_v4 recorded, 20-point cost | 565 | 1.331 | 1.212 | 1.400 | | FAILED |
| **FINAL_v4 true UTC** | 577 | **1.145** | 1.053 | 1.196 | | FAILED |

The H-N new-era figure carried the claim that news days were the best trades. At a PF of 0.914 it is gone.

Other headline numbers:

| Claim | Recorded | True UTC |
|---|---|---|
| FINAL_v4, 2025 | n=51, 86.3% win, PF 2.90, +$21,768 | n=52, 76.9% win, PF 1.13, +$3,338 |
| FINAL_v3 pooled net, max drawdown | $70,596, $6,935 | $33,520, $14,959 |
| H1 max drawdown | $7,108 | $11,291 |
| H1 positive splits of 15 | 11 | 8 |
| Hour 20, p90 cost, all years | n=110, PF 1.793, +$11,700 | n=102, PF 1.081, +$1,948 |
| Hour 20, 2023 on, Sidak p | 0.110 | 0.999 |
| DOOR-3, winners that reach $20 adverse | 0 of 360, max $17.60 | 4 of 353, max $37.86 |
| H-S winner OOS PF | 0.200 | 0.197 |

The clock does not cut every number. HCRT moved up (PF 0.86 to 0.91), HSW moved up slightly (0.83 to 0.85), and the raw TP5/SL15 flip
grid cell moved up (1.06 to 1.15). They all still fail or are not strategies. Picking out only the falls would misreport the effect.

## Narratives retired

- **"20:00 UTC cash close."** Written for the hour-20 cohort in `DECISIONS.log` and in `H20_PREREGISTRATION.md`. The cohort was a mix of 19:00
  and 20:00 UTC trades, and the concentration falls from PF 1.79 to 1.08 once the clock is right. It does not survive on true UTC.
  The explanation is retired. The originals stay as written; `audit/CHANGES.md` records the change.
- **"News days are the best trades."** Does not survive: PF 0.91 on true UTC.
- **"86% win rate" for FINAL_v4 in 2025.** Replaced by 77% and PF 1.13.
- **"Zero winners ever reach $20."** True only on the wrong clock. Four of 353 do on true UTC, so the fixed-dollar stop argument from
  DOOR-3 rested on the mislabelled sample.

## Live flip_bot

`flip_bot.py` runs on true UTC, so the true-UTC column is the one that describes the rule it trades. For H1 that is PF 1.009 at matrix costs,
0.933 at p90, and 0.952 at spreads measured at each entry and exit. The recorded runs are valid tests of a rule anchored to New York
time, but that rule was never what the bot traded.

`flip_bot` has a hard guard that refuses non-demo accounts (`flip_bot.py:622-623`), so no real money is exposed through it.

## Reproducing this

`phaseC/clockfix.py` holds the rule. `clock_map_all.py` and `clock_anchors.py` rebuild the evidence. `sandbox_goldbot.py`,
`sandbox_fable.py` and `run_goldbot_both.sh` rerun the experiments on both clocks.
