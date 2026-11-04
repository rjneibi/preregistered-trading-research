"""Monthly forward-test update. Paper only: reads public data, places nothing, and touches no broker or account.
Computes the frozen rules on public daily bars and appends trades closed since the freeze to FORWARD_LOG.csv. Rows are never rewritten.
Usage: python forward_update.py [--dry-run]. Rules live in strategies.json, which must not change after the freeze.
Needs curl, and dukascopy-node on PATH or in DUKA_CLI."""
import csv
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = json.load(open(os.path.join(HERE, "strategies.json"), encoding="utf-8"))
FREEZE = SPEC["freeze_date_utc"]
LOG = os.path.join(HERE, "FORWARD_LOG.csv")
CLI = os.environ.get("DUKA_CLI", "dukascopy-node")
HEAD = ["strategy", "market", "signal_day", "entry_day", "exit_day", "net_return", "run_utc"]


def duka(inst, start, end):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run([CLI, "-i", inst, "-from", start, "-to", end, "-t", "d1", "-p", "bid", "-f", "csv", "-dir", d, "-s"], check=True, capture_output=True)
        f = [x for x in os.listdir(d) if x.endswith(".csv")][0]
        a = np.genfromtxt(os.path.join(d, f), delimiter=",", skip_header=1)
    return dict(t=(a[:, 0] / 1000).astype(np.int64), o=a[:, 1], h=a[:, 2], l=a[:, 3], c=a[:, 4])


def binance(coin):
    start = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    rows = []
    while True:
        p = subprocess.run(["curl.exe" if os.name == "nt" else "curl", "-4", "-s", "--max-time", "40", f"https://api.binance.com/api/v3/klines?symbol={coin}USDT&interval=1d&startTime={start}&limit=1000"], capture_output=True)
        r = json.loads(p.stdout)
        rows += r
        if len(r) < 1000:
            break
        start = r[-1][0] + 1
    return dict(t=np.array([x[0] // 1000 for x in rows], np.int64), c=np.array([float(x[4]) for x in rows]))


def sma(x, n):
    return np.convolve(x, np.ones(n) / n, "full")[: len(x)] * (np.arange(1, len(x) + 1) >= n) + np.where(np.arange(1, len(x) + 1) >= n, 0, np.nan)


def rsi2(c):
    d = np.diff(c, prepend=c[0])
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    a, b = np.zeros(len(c)), np.zeros(len(c))
    for i in range(1, len(c)):
        a[i] = (a[i - 1] + up[i]) / 2
        b[i] = (b[i - 1] + dn[i]) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 - 100 / (1 + a / b)


def day(t):
    return datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d")


def dip(m, sp, fin):
    c, o, t = m["c"], m["o"], m["t"]
    r, s2, s5 = rsi2(c), sma(c, 200), sma(c, 5)
    out, i, n = [], 200, len(c)
    while i < n - 2:
        if r[i] < 10 and c[i] > s2[i]:
            j = i + 1
            while j < n - 2 and j - i < 10 and c[j] <= s5[j]:
                j += 1
            nights = int(t[j + 1] // 86400 - t[i + 1] // 86400)
            if j < n - 2 or c[j] > s5[j]:
                out.append((day(t[i]), day(t[i + 1]), day(t[j + 1]), o[j + 1] / o[i + 1] - 1 - sp / o[i + 1] - nights * fin))
            i = j + 1
        else:
            i += 1
    return out


def ibs(m, sp, fin):
    c, o, h, l, t = m["c"], m["o"], m["h"], m["l"], m["t"]
    with np.errstate(invalid="ignore", divide="ignore"):
        x = np.where(h > l, (c - l) / (h - l), np.nan)
    out, i, n = [], 252, len(c)
    while i < n - 2:
        if x[i] < 0.2:
            j = i + 1
            while j < n - 2 and j - i < 15 and not (x[j] > 0.8 or c[j] > h[j - 1]):
                j += 1
            nights = int(t[j + 1] // 86400 - t[i + 1] // 86400)
            if j < n - 2 or x[j] > 0.8 or c[j] > h[j - 1]:
                out.append((day(t[i]), day(t[i + 1]), day(t[j + 1]), o[j + 1] / o[i + 1] - 1 - sp / o[i + 1] - nights * fin))
            i = j + 1
        else:
            i += 1
    return out


def f6(coins, cost):
    d = {c: binance(c) for c in coins}
    days = sorted(set().union(*[set(v["t"].tolist()) for v in d.values()]))
    X = np.full((len(days), len(coins)), np.nan)
    ix = {t: i for i, t in enumerate(days)}
    for k, c in enumerate(coins):
        for t, p in zip(d[c]["t"], d[c]["c"]):
            X[ix[int(t)], k] = p
    r = np.vstack([np.full(len(coins), np.nan), X[1:] / X[:-1] - 1])
    rows = []
    prev = np.zeros(len(coins))
    for i in range(60, len(days) - 1):
        vol = np.nanstd(r[i - 59: i + 1], axis=0, ddof=1)
        ma = np.nanmean(X[i - 49: i + 1], axis=0)
        w = np.minimum((X[i] > ma) * (0.02 / vol), 1.0) / np.isfinite(ma).sum()
        w = np.nan_to_num(w)
        ret = float(np.nansum(w * r[i + 1]) - np.abs(w - prev).sum() * cost)
        prev = w
        rows.append((day(days[i]), day(days[i + 1]), day(days[i + 1]), ret))
    return rows


def main():
    end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = (datetime.strptime(FREEZE, "%Y-%m-%d") - timedelta(days=800)).strftime("%Y-%m-%d")
    done = set()
    if os.path.exists(LOG):
        done = {(r["strategy"], r["market"], r["signal_day"]) for r in csv.DictReader(open(LOG, encoding="utf-8"))}
    new = []
    for s in SPEC["strategies"]:
        for mk in s["markets"]:
            if s["rule"] == "f6":
                continue
            m = duka(mk["dukascopy"], start, end)
            fn = dip if s["rule"] == "rsi2_dip" else ibs
            for a, b, c, x in fn(m, mk["spread_price"], s["financing_per_night"]):
                if a > FREEZE and (s["id"], mk["name"], a) not in done:
                    new.append([s["id"], mk["name"], a, b, c, round(x, 6), end])
        if s["rule"] == "f6":
            for a, b, c, x in f6(s["coins"], s["cost_per_turnover"]):
                if a > FREEZE and (s["id"], "basket", a) not in done:
                    new.append([s["id"], "basket", a, b, c, round(x, 6), end])
    print(len(new), "new rows")
    if "--dry-run" in sys.argv:
        return
    first = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if first:
            w.writerow(HEAD)
        w.writerows(new)


main()
