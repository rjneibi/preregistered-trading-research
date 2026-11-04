"""Fetches the public datasets into DATA_DIR and compares each file with the SHA-256 the audit used.

Usage: python scripts/download_data.py [--dir data/raw] [--group NAME ...] [--years 2020 2021] [--list]
Groups come from data/manifest.csv. Files are written to DATA_DIR at their manifest path. Raw data stays out of git.

Three kinds of group exist:
  public  Fetched here. Needs curl, and Node 18+ for the Dukascopy groups.
  dated   The source no longer serves that history, so this script cannot fetch it.
  broker  MetaTrader 5 exports. They need a broker terminal and login, and may not be redistributed, so this script
          cannot fetch them and exits with code 3 if asked. See REPRODUCE.md for what that limits.

A public dataset can legitimately change after the audit date, for example when an exchange revises a series. A file that
differs is reported, not hidden, and output hashes may then differ too.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUKA = "dukascopy-node@1.51.1"
HIST_LAST = 1781888220  # Last bar in the file the audit used.
COINS_1D = ("BTCUSDT", "ETHUSDT")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def curl(*a):
    return subprocess.run(["curl", "-s", "--max-time", "120", *a], capture_output=True, check=False).stdout


def rows_from_histdata(zip_bytes):
    """Generic ASCII rows, EST without daylight saving. +5h gives the stamp the audit's file stores. The clock fix in src/clock.py comes later."""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    nm = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    for line in z.read(nm).decode("utf-8", "ignore").splitlines():
        p = line.split(";")
        if len(p) < 5:
            continue
        est = dt.datetime.strptime(p[0], "%Y%m%d %H%M%S")
        ep = int((est + dt.timedelta(hours=5)).replace(tzinfo=dt.timezone.utc).timestamp())
        yield ep, (round(float(p[1]), 3), round(float(p[2]), 3), round(float(p[3]), 3), round(float(p[4]), 3))


def histdata_part(year, month, jar):
    tail = f"xauusd/{year}" + (f"/{month}" if month else "")
    ref = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/" + tail
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
    page = curl("-A", ua, "-c", jar, ref).decode("utf-8", "replace")
    m = re.search(r'name="tk" id="tk" value="([0-9a-f]+)"', page)
    if not m:
        raise RuntimeError(f"no download token for {tail}")
    dm = f"{year}{int(month):02d}" if month else ""
    z = curl("-A", ua, "-b", jar, "-e", ref, "-d", f"tk={m.group(1)}&date={year}&datemonth={dm or year}&platform=ASCII&timeframe=M1&fxpair=XAUUSD", "https://www.histdata.com/get.php")
    if not z.startswith(b"PK"):
        raise RuntimeError(f"no zip for {tail}")
    return z


def g_histdata_xau(base, years):
    seen = {}
    with tempfile.TemporaryDirectory() as d:
        jar = os.path.join(d, "jar")
        for y in years or range(2010, 2027):
            for m in [None] if y < 2026 else range(1, 7):
                z = histdata_part(y, m, jar)
                seen.update(rows_from_histdata(z))
                print(" histdata", y, m or "", len(seen), flush=True)
                time.sleep(1)
    p = os.path.join(base, "gann_bot_500/research/data/xauusd_m1_histdata.csv")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close"])
        for ep in sorted(seen):
            if ep <= HIST_LAST:
                w.writerow([ep, *seen[ep]])


def npx():
    x = shutil.which("npx") or shutil.which("npx.cmd")
    if not x:
        sys.exit("Node 18+ with npx is needed for this group")
    return x


def duka_year(inst, side, year, out):
    """One instrument, side and year of M1 candles with volume."""
    if os.path.exists(out):
        return
    d1 = f"{year + 1}-01-01" if year < 2026 else "2026-10-30"
    with tempfile.TemporaryDirectory() as t:
        for _ in range(4):
            subprocess.run([npx(), "--yes", DUKA, "-i", inst, "-from", f"{year}-01-01", "-to", d1, "-t", "m1", "-p", side, "-v", "true", "-f", "csv", "-dir", t, "-bs", "10", "-bp", "400", "-r", "8", "-rp", "3000", "-s"],
                           capture_output=True, check=False)
            f = [x for x in os.listdir(t) if x.endswith(".csv")]
            if f:
                os.makedirs(os.path.dirname(out), exist_ok=True)
                shutil.move(os.path.join(t, f[0]), out)
                return
    raise RuntimeError(f"no data for {inst} {side} {year}")


def g_dukascopy_xag(base, years):
    for y in years or range(2015, 2027):
        for s in ("bid", "ask"):
            duka_year("xagusd", s, y, os.path.join(base, f"audit/dk_xag/xagusd-{s}-{y}.csv"))
            print(" xag", y, s, flush=True)


def g_dukascopy_m1(base, years):
    """Raw yearly files, then the project's own builder."""
    lb = os.path.join(base, "london-breakout")
    shutil.copytree(os.path.join(ROOT, "originals/london-breakout"), lb, dirs_exist_ok=True, ignore=shutil.ignore_patterns("results"))
    for inst in ("deuidxeur", "gbridxgbp", "usa30idxusd", "usatechidxusd", "eurusd", "gbpusd", "xauusd"):
        for y in years or range(2013, 2027):
            for s in ("bid", "ask"):
                duka_year(inst, s, y, os.path.join(lb, f"data/raw/{inst}/{inst}-{s}-{y}.csv"))
                print(" m1", inst, y, s, flush=True)
    subprocess.run([sys.executable, "tools/build_data.py"], cwd=lb, check=True)


def g_dukascopy_ticks(base, years):
    """The project's own downloader, run on a copy so its output lands in DATA_DIR. It takes days, and needs about 21 GB."""
    w = os.path.join(base, "gann_bot_500/fable-backtesting")
    os.makedirs(w, exist_ok=True)
    s = open(os.path.join(ROOT, "originals/gann_bot_500/fable-backtesting/bi5_downloader.py"), encoding="utf-8").read().replace('"curl.exe"', '"curl"')
    open(os.path.join(w, "bi5_downloader.py"), "w", encoding="utf-8").write(s)
    subprocess.run([sys.executable, "bi5_downloader.py", "run"], cwd=w, check=True)


def klines(host, sym, iv, start):
    rows = []
    step = {"1d": 86400_000, "1h": 3600_000}[iv]
    while True:
        k = json.loads(curl(f"https://{host}/api/v3/klines?symbol={sym}&interval={iv}&startTime={start}&limit=1000"))
        if not isinstance(k, list):
            raise RuntimeError(str(k)[:200])
        if not k:
            break
        rows += k
        start = k[-1][0] + step
        if len(k) < 1000:
            break
        time.sleep(0.25)
    return rows


def g_binance(base, years):
    import numpy as np
    d = os.path.join(base, "gann_bot_500/research/cross_market/data")
    os.makedirs(d, exist_ok=True)
    for sym in COINS_1D:
        for iv in ("1d", "1h"):
            r = klines("data-api.binance.vision", sym, iv, 1502928000000)
            a = np.array([[x[0] // 1000, float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[5])] for x in r])
            np.savez(os.path.join(d, f"{sym}_{iv}.npz"), t=a[:, 0].astype(np.int64), o=a[:, 1], h=a[:, 2], l=a[:, 3], c=a[:, 4], v=a[:, 5], sp=np.zeros(len(a)))
            print(" binance", sym, iv, len(a), flush=True)


def g_public_api(base, years):
    s = open(os.path.join(ROOT, "audit/phaseE/fetch_public.py"), encoding="utf-8").read()
    s = s.replace('os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_copy", "data", "public")', repr(os.path.join(base, "audit", "public")))
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(s)
    subprocess.run([sys.executable, f.name], check=True)
    os.remove(f.name)


def g_calendar_series(base, years):
    """FRED daily series, cut at the audit's last row, which reproduces the audit's files while FRED leaves those rows unchanged."""
    ends = {"vix.csv": ("VIXCLS", "2026-07-01"), "dollar.csv": ("DTWEXBGS", "2026-06-26")}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "manifest.csv"), encoding="utf-8")):
        if r["group"] != "calendar_series":
            continue
        sid, end = ends[os.path.basename(r["rel"])]
        b = curl(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}").replace(b"\r\n", b"\n").decode()
        keep = [x for x in b.strip().split("\n") if x.startswith("observation_date") or x[:10] <= end]
        if len(keep) < 100:
            raise SystemExit(f"FRED returned no usable rows for {sid}")
        p = os.path.join(base, r["rel"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as h:
            h.write("\n".join(keep) + "\n")
        print(" fred", sid, len(keep) - 1, flush=True)


FETCH = {"calendar_series": g_calendar_series, "histdata_xau": g_histdata_xau, "dukascopy_xag": g_dukascopy_xag, "dukascopy_m1": g_dukascopy_m1, "dukascopy_ticks": g_dukascopy_ticks, "binance": g_binance, "public_api": g_public_api}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.environ.get("DATA_DIR", os.path.join(ROOT, "data", "raw")))
    ap.add_argument("--group", nargs="*", default=[])
    ap.add_argument("--years", nargs="*", type=int)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "manifest.csv"), encoding="utf-8")))
    by = collections.defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)
    if a.list:
        for g, v in sorted(by.items()):
            print(f"{g:18s} {v[0]['access']:7s} {len(v):4d} files {sum(int(x['size']) for x in v) / 1e6:10.1f} MB  {'fetchable' if g in FETCH else 'not fetchable here'}")
        return
    want = a.group or sorted(FETCH)
    code = 0
    for g in want:
        if g not in FETCH:
            print(f"{g}: cannot be fetched by this script. {by[g][0]['source']}")
            code = 3
            continue
        print("group", g, flush=True)
        FETCH[g](a.dir, a.years)
    res = {}
    for g in want:
        c = collections.Counter()
        for r in by[g]:
            p = os.path.join(a.dir, r["rel"])
            c["missing" if not os.path.exists(p) else "same" if sha(p) == r["sha256"] else "differs"] += 1
        res[g] = dict(c)
    print(json.dumps(res, indent=1))
    sys.exit(code)


if __name__ == "__main__":
    main()
