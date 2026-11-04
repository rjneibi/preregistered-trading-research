"""EDGE-1 crypto: top coins 1d spot klines + perpetual funding-rate history (public Binance, no key)."""
import json, subprocess, time, os
import numpy as np
os.makedirs("data_edge", exist_ok=True)
def get(url):
    p = subprocess.run(["curl.exe", "-s", "--max-time", "30", url], capture_output=True, timeout=40)
    return json.loads(p.stdout)
COINS = "BTC ETH BNB XRP ADA SOL DOGE LTC LINK DOT AVAX TRX".split()
for c in COINS:
    sym = c + "USDT"; rows, start = [], 1502928000000
    while True:
        k = get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&startTime={start}&limit=1000")
        if not isinstance(k, list) or not k: break
        rows += k; start = k[-1][0] + 86400_000
        if len(k) < 1000: break
        time.sleep(0.25)
    a = np.array([[r[0] // 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[7])] for r in rows])
    np.savez(f"data_edge/C_{c}_D1.npz", t=a[:, 0].astype(np.int64), o=a[:, 1], h=a[:, 2], l=a[:, 3], c=a[:, 4], qv=a[:, 5], sp=np.zeros(len(a)))
    fr, start = [], 1567296000000   # 2019-09
    while True:
        k = get(f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={sym}&startTime={start}&limit=1000")
        if not isinstance(k, list) or not k: break
        fr += k; start = k[-1]["fundingTime"] + 1
        if len(k) < 1000: break
        time.sleep(0.3)
    if fr:
        np.savez(f"data_edge/F_{c}.npz", t=np.array([x["fundingTime"] // 1000 for x in fr], np.int64),
                 r=np.array([float(x["fundingRate"]) for x in fr]))
    print(c, len(a), time.strftime('%Y-%m-%d', time.gmtime(a[0, 0])), "funding", len(fr), flush=True)
