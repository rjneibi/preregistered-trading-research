# Data quality report

Source: Dukascopy 1-minute bid and ask candles with tick volume, downloaded with
`dukascopy-node` 1.51.1 (`tools/download.py`). Built by `tools/build_data.py`; generated file.

**Processing:**
- Bid and ask are joined per minute.
- Mid = (bid+ask)/2, used for signals.
- Spread = max(ask-bid at open, ask-bid at close), used for fills.
- Duplicate timestamps are dropped.
- Bars with high<low or a negative spread are dropped (none found).
- Flat zero-volume padding bars are dropped (none found).
- Bad-tick wicks are clipped to the body/neighbour envelope: more than 25 robust sigmas beyond the body and both neighbouring closes, with price back where it was one bar later.

| | GER40 | UK100 | GBPUSD | XAUUSD | US30 | NAS100 | EURUSD |
|---|---|---|---|---|---|---|---|
| first bar (UTC) | 2013-09-30 15:13 | 2013-01-01 03:51 | 2013-01-01 22:03 | 2013-01-01 23:00 | 2013-09-30 13:34 | 2013-01-01 05:44 | 2013-01-01 22:00 |
| last bar (UTC) | 2026-10-29 23:58 | 2026-10-29 23:59 | 2026-10-29 23:58 | 2026-10-29 23:58 | 2026-10-29 23:58 | 2026-10-29 23:59 | 2026-10-29 23:58 |
| clean 1m bars | 3928660 | 4033558 | 5154959 | 4893929 | 4024668 | 4144617 | 5145155 |
| duplicate timestamps (bid/ask) | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 |
| bid/ask rows without partner | 5 | 628 | 1 | 2 | 3 | 2 | 1 |
| bad-tick wicks clipped | 3 | 359 | 8 | 5 | 1 | 6 | 7 |
| weekdays in range | 3414 | 3608 | 3608 | 3608 | 3414 | 3608 | 3608 |
| weekdays with no 07:00-12:00 London data | 54 | 127 | 12 | 40 | 60 | 161 | 16 |
| ...of which Dec 24/25/26/31, Jan 1 | 30 | 25 | 12 | 24 | 23 | 24 | 11 |
| weekdays with thin morning data (<80%) | 41 | 69 | 9 | 0 | 28 | 48 | 10 |
| intraday gaps >5 min (07:00-12:00 London) | 268 | 399 | 12 | 7 | 62 | 125 | 5 |
| intraday gaps >30 min (07:00-12:00 London) | 21 | 73 | 1 | 0 | 22 | 22 | 0 |
| DST-window days without a bar at 08:00 London | 6 | 15 | 0 | 3 | 6 | 16 | 0 |
| median spread 00:00-06:00 London | 3.857 | 3.241 | 0.00011 | 0.35 | 5.438 | 3.394 | 4e-05 |
| median spread 07:00-07:59 London | 2.535 | 2.004 | 9e-05 | 0.34 | 4.4997 | 3.072 | 3e-05 |
| median spread 08:00-08:04 London (the open) | 1.422 | 1.028 | 9e-05 | 0.337 | 3.932 | 3.072 | 3e-05 |
| median spread 08:05-08:29 London | 1.413 | 1.023 | 9e-05 | 0.334 | 3.8945 | 3.072 | 3e-05 |
| median spread 10:00-12:00 London | 1.412 | 1.016 | 9e-05 | 0.327 | 3.9105 | 3.072 | 3e-05 |

## Findings

1. **Overnight gap on the index CFDs, 2015-01 to about 2018-06.** Dukascopy GER40 and UK100 have essentially no prices between about 20:00 and 06:00 UTC in those years. No Asian box can be built for those days, so Variant A excludes them: the box needs at least 50% minute coverage.
   - About 860 of the 2,691 IS+VAL weekdays are lost.
   - Variant B's London and NY sessions are unaffected. Its Asia session is empty in those years.
   - US30 and NAS100 show the same pattern.
2. **Missing weekdays are exchange holidays.** Examples: Good Friday, Easter Monday, Christmas, New Year, 1 May (Xetra), Whit Monday, German Unity Day (3 Oct).
   - The DST-window days without an open bar are Easter holidays that fall next to the March switch.
   - No DST misalignment was found. The session clock is tested in `tests/test_sessions_robustness.py` and `tests/test_signal.py`.
3. **Spread at the open.** On Dukascopy the index spread is widest overnight and in the hour before the cash open (GER40 ≈ 2.5 points at 07:00-07:59 London). It is already back to its daytime level in the first minutes after 08:00 London (GER40 ≈ 1.4, UK100 ≈ 1.0).
   - Retail brokers often widen for seconds around the open. One-minute data cannot show that, so it is covered by the slippage allowance:

| | GER40 | UK100 | US30 | NAS100 | EURUSD | GBPUSD | XAUUSD |
|---|---|---|---|---|---|---|---|
| slippage per side (price units) | 0.5 | 0.5 | 1.0 | 0.5 | 2e-05 | 3e-05 | 0.05 |
| commission per round trip (price units) | 0.0 | 0.0 | 0.0 | 0.0 | 7e-05 | 7e-05 | 0.07 |

   - Everything is also run at 0.5x and 2x costs.
4. **GER40 spread regime change.** The median opening spread was about 1.0 point in 2013-2019 and about 1.45 points from 2020 on. Part of the deterioration after 2020 in every config is this cost increase.
