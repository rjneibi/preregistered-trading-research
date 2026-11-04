# Data manifest

No raw market data is committed. [manifest.csv](manifest.csv) lists every input file with its size and the SHA-256 of the copy the audit used. `scripts/download_data.py` fetches what can be fetched and compares each file with these hashes.

| Group | Source | Range | Time zone | Files | MB | Access and licence |
|---|---|---|---|---:|---:|---|
| histdata_xau | HistData.com XAUUSD M1 ASCII | 2010 to 2026-06 | Stored stamps as given. See the clock note below | 1 | 263 | Free to download. Their terms bar redistribution, so it is not committed |
| dukascopy_ticks | Dukascopy ticks, bid and ask | XAU 2015 to 2026, XAG 2015 to 2022 | UTC | 231 | 20,912 | Free to download, not redistributed |
| dukascopy_m1 | Dukascopy M1 candles | 2013 to 2026-10 | UTC | 7 | 542 | Free to download, not redistributed |
| dukascopy_xag | Dukascopy XAGUSD M1 | 2015 to 2026-10 | UTC | 26 | 665 | Free to download, not redistributed |
| binance | Binance klines | 2017-08 to 2026-10 | UTC | 6 | 10 | Public endpoint |
| public_api | Binance funding and klines, Yahoo GDX | To 2026-10 | UTC | 21 | 3 | Public endpoints. Fetching later gives a longer file, so hashes differ |
| calendar_series | FRED VIXCLS and DTWEXBGS | To 2026-07-01 and 2026-06-26 | Dates | 4 | 1 | US public data. Fetched files, cut at those dates, matched the audit's on every byte |
| yahoo_intraday | Yahoo Finance SPY, QQQ intraday and daily | 60 days to 2 years before the fetch | UTC | 8 | 3 | Dated. The source no longer serves these dates |
| flip_events | flip_scalp signal lists | 2015 to 2026 | UTC | 2 | 1 | Left by an earlier run whose writer is not in the snapshot. Not published, not fetchable |
| demo_journal | Demo bot trade journal | 2026 | UTC | 1 | 0 | Holds demo balances, so it is not published. Not fetchable here |
| broker_mt5 | MetaTrader 5 demo terminal exports | Varies by symbol | Broker server time | 225 | 837 | Needs a terminal and login. Broker data may not be redistributed. Not fetchable here |

## Timezone handling

- HistData documents its ASCII files as EST without daylight saving. The audit found that this file does not behave that way, see [audit/findings/CLOCK_BUG.md](../audit/findings/CLOCK_BUG.md). The audit's file adds 5 hours and stores the result as epoch seconds. Those stamps still run UTC+1 for part of each year. [src/clock.py](../src/clock.py) corrects that, and its tests are in [tests/test_clock.py](../tests/test_clock.py).
- Years 2010 to 2012 of that file are ASSUMED-CLOCK.
- Broker exports use broker server time, which changes with daylight saving.

Two tick files the audit used have gaps: XAU September 2018 lacks 174 trading hours and XAG April 2016 lacks 386. See DECISIONS.md, item 19.

A fresh fetch of HistData 2020 matched the audit's file on all 354,291 rows. Other groups may differ if a source revises history. `download_data.py` reports any difference.
