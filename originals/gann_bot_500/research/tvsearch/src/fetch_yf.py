"""Download SPY/QQQ bars from Yahoo's public chart API into data/ (CSV, UTC epoch seconds).

The yfinance package is not used: its curl_cffi dependency is a new native DLL that Windows Application Control
blocks on this machine. The chart endpoint gives the same bars. Yahoo limits: 1m = last ~30 days in <=8-day
requests, 5m = 60 days, 1h = 730 days, 1d = full history. Regular trading hours only (includePrePost=false).
1m is the primary source (every intraday timeframe is resampled from it); 1h and 1d feed the long-history check.
    python src/fetch_yf.py [TICKER ...]
"""
import json
import os
import sys
import time
import urllib.request

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{tk}?interval={iv}&period1={a}&period2={b}&includePrePost=false&events=div%2Csplit"


def chart(tk, iv, a, b):
    req = urllib.request.Request(URL.format(tk=tk, iv=iv, a=int(a), b=int(b)), headers={"User-Agent": "Mozilla/5.0"})
    for k in range(4):
        try:
            r = json.loads(urllib.request.urlopen(req, timeout=30).read())["chart"]["result"][0]
            break
        except Exception as e:
            print("retry", tk, iv, e)
            time.sleep(2 + 3 * k)
    else:
        raise RuntimeError(f"{tk} {iv} failed")
    q = r["indicators"]["quote"][0]
    df = pd.DataFrame({"time": r.get("timestamp", []), "open": q.get("open", []), "high": q.get("high", []),
                       "low": q.get("low", []), "close": q.get("close", []), "volume": q.get("volume", [])})
    return df.dropna(subset=["open", "high", "low", "close"])


def main(tickers=("SPY", "QQQ")):
    now = int(time.time())
    for tk in tickers:
        parts, a = [], now - 29 * 86400
        while a < now:
            parts.append(chart(tk, "1m", a, min(a + 7 * 86400, now)))
            a += 7 * 86400
        out = {"1m": pd.concat(parts), "5m": pd.concat([chart(tk, "5m", now - (k + 1) * 19 * 86400, now - k * 19 * 86400) for k in (2, 1, 0)]), "1h": chart(tk, "60m", now - 729 * 86400, now), "1d": chart(tk, "1d", now - 10 * 365 * 86400, now)}
        for iv, df in out.items():
            df = df.drop_duplicates("time").sort_values("time")
            df.to_csv(os.path.join(DATA, f"{tk}_{iv}.csv"), index=False)
            print(tk, iv, len(df), pd.to_datetime(df.time.iloc[0], unit="s"), "..", pd.to_datetime(df.time.iloc[-1], unit="s"))


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or ("SPY", "QQQ"))
