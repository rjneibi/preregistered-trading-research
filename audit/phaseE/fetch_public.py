"""Public data for E1 and E5, saved under _copy/data/public, not committed. Nothing is analysed here. Uses curl because Python TLS fails on this PC."""
import json
import os
import subprocess
import time

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_copy", "data", "public")
os.makedirs(OUT, exist_ok=True)
COINS = "BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX".split()
DEAD = "LUNA FTT UST SRM WAVES MITH BTS ANC".split()
RES = {}


def get(url, ua=None):
    a = ["curl.exe" if os.name == "nt" else "curl", "-4", "-s", "--max-time", "40", url]
    if ua:
        a[1:1] = ["-A", ua]
    for k in range(4):
        p = subprocess.run(a, capture_output=True)
        if p.returncode == 0 and p.stdout:
            try:
                return json.loads(p.stdout)
            except ValueError:
                pass
        time.sleep(3 + 5 * k)
    return None


def funding(c):
    p = os.path.join(OUT, f"funding_{c}.json")
    if os.path.exists(p):
        return
    rows, start = [], 1567296000000
    while True:
        r = get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={c}USDT&startTime={start}&limit=1000")
        if not isinstance(r, list) or not r:
            break
        rows += [[x["fundingTime"], float(x["fundingRate"])] for x in r]
        if len(r) < 1000:
            break
        start = r[-1]["fundingTime"] + 1
        time.sleep(0.4)
    json.dump(rows, open(p, "w"))
    RES[f"funding {c}"] = len(rows)


def klines(c):
    p = os.path.join(OUT, f"kl_{c}.json")
    if os.path.exists(p):
        return
    rows, start = [], 1500000000000
    while True:
        r = get(f"https://api.binance.com/api/v3/klines?symbol={c}USDT&interval=1d&startTime={start}&limit=1000")
        if not isinstance(r, list) or not r:
            break
        rows += [[x[0], float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[7])] for x in r]
        if len(r) < 1000:
            break
        start = r[-1][0] + 1
        time.sleep(0.3)
    json.dump(rows, open(p, "w"))
    RES[f"klines {c}"] = len(rows)


def gdx():
    p = os.path.join(OUT, "GDX_yahoo.json")
    if os.path.exists(p):
        return
    r = get("https://query1.finance.yahoo.com/v8/finance/chart/GDX?period1=1388534400&period2=1793491200&interval=1d&events=div,split", ua="Mozilla/5.0")
    json.dump(r, open(p, "w"))
    RES["gdx"] = 0 if not r else len(r["chart"]["result"][0]["timestamp"])


gdx()
for c in COINS:
    funding(c)
for c in DEAD:
    klines(c)
print(json.dumps(RES, indent=0))
