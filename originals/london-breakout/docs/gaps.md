# Gap analysis

Every weakness found, with the evidence and what was done about it.
"Selected config" means the stage-1 pick:
- 23:00-07:00 UTC box, 15m bars, range ≥ 1×ATR, whole candle outside, 30-min window;
- stop 25% inside the box, no target, exit at 16:30.

"Author baseline" means the literal reading of the social post:
- 00:00-07:00 UTC box, 5m bars, body ≥ 50%, close outside, 120-min window;
- stop 25% inside the box, RR 2.

Unless stated otherwise, numbers are IS+VAL at 1x costs. The source files are in `results/`.

## 1. Rules that are ambiguous or contradictory

| Issue | Variant | What was done |
|---|---|---|
| The author's Asia session is 19:00-04:00 New York. 04:00 NY is 08:00 UTC (summer) or 09:00 UTC (winter), but London opens at 07:00 or 08:00 UTC. **The "Asian box" therefore overlaps the London open by one hour, all year round.** | A (ny1904), B | Box truncated at 08:00 London. Tested as one of four box definitions. |
| Variant B: the "previous session" for London (03:00 NY) is Asia, which is still open until 04:00. For NY (09:30) it is London, still open until 12:00. | B | Levels are taken from the previous session up to 5 minutes before the open. Sessions are not treated as closed. |
| "Strong candle", "closes fully outside", "strong volume", "just inside the box", "strict RR" are all undefined. | A, B | Every reading was parameterised and swept (`config/research.yaml`). 32,544 + 4,320 configs on the two indices. |
| Fixed UTC box windows (00:00-07:00, 23:00-07:00) end exactly at the open in summer but one hour *before* it in winter. In winter, price is outside the box at the open on about 15-17% of days (`results/box_behaviour_summary.json`). | A | Kept as specified. The "fresh break" fix tests whether to require a cross. |
| Variant A says one trade per day. Variant B says two per session. A says the session ends about 10:00 but an open trade can run, without saying until when. | A, B | A: forced exit at 16:30 London (cash close). B: exit at session end. Both 1-trade and 2-trade/reversal modes were tested. |
| The two variants use different instruments, sessions, timeframes and stop logic. There is no single "strategy" to test. | A, B | Implemented and judged separately. Neither passes. |

## 2. False breakouts

After the first 5m close outside the box (00:00-07:00 UTC box, within 120 min of the open):

| | GER40 | UK100 |
|---|---|---|
| closes back inside the box within 3 bars (15 min) | 45% | 44% |
| ... within 6 bars (30 min) | 56% | 54% |
| ... within 12 bars (60 min) | 65% | 63% |
| ... at any point before 16:30 | 83% | 82% |
| median move from the break bar to 16:30, in box widths | -0.02 | +0.05 |

Breaks of the Asian box are not followed by continuation in any systematic way. A typical break is retraced before lunch. Breakouts on the 1m chart and stops at the breakout-candle extreme are the worst cells in the whole grid: mean IS expectancy is -0.79R for tf=1 and -2.0R for candle stops. These are mostly cost-dominated, because a 1m candle range is only a few spreads wide.

## 3. Days with no setup, and both-side breaks

| | GER40 | UK100 |
|---|---|---|
| no 5m close outside the box within 120 min | 13% | 11% |
| both sides broken within 120 min | 11% | 10% |
| price already outside the box at 08:00 London | 15% | 17% |

The selected config is selective (whole 15m bar outside, range ≥ ATR, first 30 min). It trades on only about 40% of usable days. The "allow reversal trade" mode never fired for it, because one signal per 30-min window is the most it produces. For the author baseline, both-side days are where the second trade would come from.

## 4. News and event days

Calendar: `data/calendar/high_impact_events.csv`
- NFP and US CPI from BLS archives;
- every ECB meeting from 2013 to 2026;
- BoE only from 2024. Historical BoE dates could not be obtained, so this is an open gap.
- FOMC is ignored: it is announced after the 16:30 forced exit.

| Selected config | n | exp (R) |
|---|---|---|
| all trades | 667 | -0.031 |
| NFP days | 23 | +0.068 |
| US CPI days | 34 | -0.355 |
| ECB days | 20 | -0.271 |
| any listed event | 73 | -0.189 |
| no listed event | 594 | -0.011 |

Event days are worse, and CPI and ECB days especially. But the samples are tiny, and **excluding them does not create an edge**:
- the "news filter" fix makes IS +0.035R better;
- it makes VAL 0.005R worse;
- VAL stays at -0.25R.

For the author baseline, event days and other days are both about -0.12R.

## 5. Holidays and half-days

Exchange holidays have no 1m bar at 08:00 London and are skipped automatically. The signal module returns NONE with reason "no bar at the London open".

The 20 Dec - 3 Jan period is clearly bad:
- selected config: -0.37R (n=25);
- author baseline: -0.40R (n=99).

This fits thin liquidity and early closes on 24 and 31 December. A live bot should not trade 20 Dec - 3 Jan. This was not added as a fix, because it would have been chosen after seeing the result. It is a recommendation for any future pre-registration.

## 6. Spread widening at the open

On Dukascopy the spread is widest *before* the open:
- GER40: about 2.5 points between 07:00 and 07:59 London;
- GER40: back to about 1.4 points from 08:00;
- UK100: about 2.0, then about 1.0.

Most retail CFD brokers widen for some seconds around 08:00:00. One-minute data cannot see that, so it is modelled as 0.5 points of slippage per side on top of the bar spread. Even so, the edge is not robust to cost:

| | gross | 0.5x | 1x | 2x | cost multiple at which expectancy = 0 |
|---|---|---|---|---|---|
| selected config | +0.051 | +0.012 | -0.031 | -0.095 | **0.64x** |
| author baseline | +0.019 | -0.049 | -0.121 | -0.256 | **0.14x** |

The author baseline would need costs at 14% of a realistic level. Even Dukascopy's raw spread alone, without any slippage, is too much for it.

The GER40 opening spread on Dukascopy also rose from about 1.0 to about 1.45 points in 2020 (`docs/data_quality.md`). This is one reason, but **not the main one**, for the post-2021 deterioration: the *gross* expectancy of the selected config also turned negative in 2021-2024 (IS gross +0.165R, VAL gross -0.164R).

## 7. Dependence on a few outlier trades

Selected config:
- dropping the best 1% of trades moves expectancy from -0.031 to -0.087R;
- dropping the best 5% moves it to -0.236R.

The in-sample "profits" came from a handful of trend days. The positive IS years (2014, 2019) carry the whole IS result. 2019 alone is +20.9R of the +36R IS total.

## 8. Decay

Selected config, R per trade regressed on year: **-0.038R/year, t = -2.45**.
- First half of the years: +0.13R.
- Second half: -0.16R.

By year:
- 2014-2020: all positive.
- 2021, 2022, 2023, 2024 (to March): all negative.
- OOS (Mar 2024 - Oct 2026): -0.008R.

The author baseline has been negative in every year except 2015 (n=67) and 2020 (COVID volatility).

## 9. Instruments and sessions where it clearly fails

- **Variant B, all 21 instrument × session cells:** no config is positive in both IS and VAL on UK100, NAS100 or XAUUSD.
  - At most 7% of configs on EURUSD London and 4% on GER40 NY are positive in both. That is the false-positive rate one expects from a few thousand configs.
  - The **Asia session** loses 0.7-3R per trade everywhere: overnight index spreads of 3-8 points against ATR stops of a few points.
- **Variant A, robustness instruments** (selected rules unchanged):
  - US30: +0.10R (n=169, the only net-positive one);
  - XAUUSD: +0.03R;
  - GBPUSD: -0.03R;
  - EURUSD: -0.17R;
  - NAS100: -0.22R.
  - The author baseline is negative on all five (-0.13 to -0.41R). Gross it is +0.01 to +0.07R.
- **UK100** is the weaker index in every split, OOS included (-0.14R vs GER40 +0.13R OOS).

## 10. Other weaknesses found

- **Weekday:** Wednesday is the best day for both configs (+0.25R selected, 0.00R author; every other day is negative). There is no economic reason for this. It was not used as a filter, because it would be a pure data-mined artefact.
- **Box size:** no monotone relationship. For the selected config: Q1 -0.08, Q2 +0.10, Q3 +0.04, Q4 -0.28, Q5 +0.01. The practitioner claim that narrow boxes break out better (H7) is not supported.
- **Volatility regime:** low -0.06, normal +0.03, high -0.07. The literature's "works in high volatility" (H8) is not supported here.
- **Data:** Dukascopy has no overnight index prices in 2015 to mid-2018. About a third of the IS sample could not be used for Variant A (`docs/data_quality.md`).
- **Retest entry** (limit order at the broken edge) almost never fills for the selected config: 15 fills in 667 opportunities. A whole 15m bar beyond the box rarely comes back within the 30-min window. For configs that do retest, the fill is adversely selected.

## 11. Fixes tried (section 9) and outcome

26 candidate fixes were tested on IS and VAL only, under the keep-rule frozen in `RESEARCH_LOG.md`. **None was kept.** Full table: `results/deep_pick/fixes.csv`. Highlights:

| Fix | IS Δ | VAL Δ | VAL after | Why rejected |
|---|---|---|---|---|
| break-even at +1R (author's "paid" feature) | +0.062 | +0.024 | -0.222 | VAL still negative |
| BE at 1R + partial 50% at 1R | +0.011 | +0.062 | -0.183 | VAL still negative |
| ATR trail 4× | +0.047 | +0.066 | -0.180 | VAL still negative |
| confirmation: other index broke the same way first | +0.017 | +0.224 | -0.022 | VAL still negative; keeps only 35% of trades |
| volume ≥ 1.5× median | +0.126 | +0.092 | -0.153 | 23% of trades kept, VAL negative |
| trend filter EMA20 | +0.057 | -0.026 | -0.272 | worse in VAL |
| news filter | +0.035 | -0.005 | -0.251 | worse in VAL |
| time exit 60/120/240 min | -0.12 to -0.03 | +0.07 to +0.12 | -0.13 to -0.18 | worse in IS |

The management features shift the win/loss mix by a few hundredths of R. They do not create expectancy. This matches what the user's earlier work (EXIT-2) found: when the entry has no edge, exits only reshape the distribution.
