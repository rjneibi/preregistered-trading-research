"""Direct Dukascopy .bi5 downloader/decoder (replaces flaky dukascopy-node).
URL: datafeed.dukascopy.com/datafeed/{SYM}/{YYYY}/{MM-1:02d}/{DD:02d}/{HH}h_ticks.bi5
Row: >3I2f = ms-in-hour, ask_int, bid_int, askvol, bidvol; XAU/XAG divisor 1000.
Writes monthly CSVs (timestamp,askPrice,bidPrice) into download/, resumable.
Usage: py -3.11 bi5_downloader.py test | py -3.11 bi5_downloader.py run
"""
import lzma
import socket
import struct
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# datafeed.dukascopy.com blackholes IPv6 on this network (curl works via
# IPv4 fallback; python/node hang) — force IPv4 for all lookups here.
_orig_gai = socket.getaddrinfo
socket.getaddrinfo = (lambda host, port, family=0, *a, **k:
                      _orig_gai(host, port, socket.AF_INET, *a, **k))

DL = Path(__file__).parent / "download"
LOG = Path(__file__).parent / "ticks_download.log"
DIV = {"XAUUSD": 1000.0, "XAGUSD": 1000.0}
UA = {"User-Agent": "Mozilla/5.0 gannbot-research"}


def fetch_hour(sym, d: date, hour):
    """Transport via curl.exe — the only client that reliably reaches the
    datafeed on this network (python/node TLS stalls; curl works)."""
    import subprocess
    url = (f"https://datafeed.dukascopy.com/datafeed/{sym}/{d.year}/"
           f"{d.month - 1:02d}/{d.day:02d}/{hour:02d}h_ticks.bi5")
    try:
        p = subprocess.run(["curl.exe", "-s", "--max-time", "30", url],
                           capture_output=True, timeout=40)
        if p.returncode != 0:
            return None
        raw = p.stdout
    except Exception:
        return None
    if not raw:
        return []
    try:
        buf = lzma.decompress(raw)
    except lzma.LZMAError:
        return []
    base = int(datetime(d.year, d.month, d.day, hour,
                        tzinfo=timezone.utc).timestamp() * 1000)
    div = DIV[sym]
    return [(base + ms, a / div, b / div)
            for ms, a, b, _, _ in struct.iter_unpack(">3I2f", buf)]


PRICE_BAND = {"XAUUSD": (500.0, 20000.0), "XAGUSD": (5.0, 500.0)}
MEDIANS = Path(__file__).parent / "bi5_medians.json"


def validate_month(path: Path, sym: str) -> bool:
    """Data-integrity gate: quarantine (.suspect) months with implausible
    price scale, a >2x discontinuity vs the previous kept month, or a
    corrupt-spread fraction >5%. Returns True if the file is kept."""
    import json as _j
    prices, bad_spread, n = [], 0, 0
    with open(path) as f:
        next(f, None)
        for line in f:
            try:
                _, a, b = line.rstrip("\n").split(",")
                a, b = float(a), float(b)
            except ValueError:
                continue
            n += 1
            if n % 50 == 0:                   # sample every 50th tick
                prices.append(a)
            s = a - b
            if s <= 0 or s > 0.02 * a:
                bad_spread += 1
    if not prices or n == 0:
        reason = "empty"
    else:
        prices.sort()
        med = prices[len(prices) // 2]
        lo, hi = PRICE_BAND.get(sym, (0, 1e9))
        hist = _j.loads(MEDIANS.read_text()) if MEDIANS.exists() else {}
        prev = hist.get(sym)
        if not (lo <= med <= hi):
            reason = f"band med={med:.2f}"
        elif prev and not (0.5 <= med / prev <= 2.0):
            reason = f"discontinuity med={med:.2f} prev={prev:.2f}"
        elif bad_spread / n > 0.05:
            reason = f"bad_spread={bad_spread / n:.1%}"
        else:
            hist[sym] = med
            MEDIANS.write_text(_j.dumps(hist))
            return True
    path.rename(path.with_suffix(".suspect"))
    log(f"BI5-SUSPECT {path.name} ({reason})")
    return False


def month_days(y, m):
    d = date(y, m, 1)
    while d.month == m:
        yield d
        d += timedelta(days=1)


def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{msg} {datetime.now().isoformat(timespec='seconds')}\n")


def run():
    DL.mkdir(exist_ok=True)
    # cooldown gate: rate-limited IPs get HTTP 000; probe until feed answers
    log("WAITING for datafeed (rate-limit cooldown)")
    while True:
        if fetch_hour("XAUUSD", date(2020, 3, 2), 10):
            break
        time.sleep(600)
    log("DATAFEED REACHABLE — starting pull")
    for sym in ("XAUUSD", "XAGUSD"):
        for y in range(2015, 2027):
            for m in range(1, 13):
                if (y, m) > (2026, 6):
                    continue
                out = DL / f"{sym.lower()}-bi5-{y}-{m:02d}.csv"
                if out.exists() and out.stat().st_size > 10000:
                    continue
                rows_n, fails = 0, 0
                with open(out, "w") as f:
                    f.write("timestamp,askPrice,bidPrice\n")
                    for d in month_days(y, m):
                        if d > date(2026, 6, 19):
                            break
                        for h in range(24):
                            rows = fetch_hour(sym, d, h)
                            if rows is None:
                                fails += 1
                                time.sleep(2)
                                rows = fetch_hour(sym, d, h) or []
                            for ts, a, b in rows:
                                f.write(f"{ts},{a},{b}\n")
                            rows_n += len(rows)
                            time.sleep(0.05)
                if rows_n and validate_month(out, sym):
                    log(f"BI5 {sym} {y}-{m:02d} rows={rows_n} fails={fails}")
                elif not rows_n:
                    log(f"BI5 {sym} {y}-{m:02d} EMPTY fails={fails}")
    log("ALL COMPLETE")


def test():
    rows = fetch_hour("XAUUSD", date(2020, 3, 2), 10)
    print(f"ticks: {len(rows)}")
    for r in rows[:3]:
        print(datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc), r[1], r[2])


if __name__ == "__main__":
    (test if "test" in sys.argv else run)()
