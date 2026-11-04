"""Public Binance klines (no key): BTCUSDT / ETHUSDT 1d and 1h from 2017-08 -> data/{SYM}_{TF}.npz (UTC)."""
import json, subprocess, time, sys
import numpy as np
def get(url):
    p = subprocess.run(["curl.exe", "-s", "--max-time", "30", url], capture_output=True, timeout=40)
    return json.loads(p.stdout)
for sym in ("BTCUSDT", "ETHUSDT"):
    for iv, step in (("1d", 86400_000), ("1h", 3600_000)):
        rows, start = [], 1502928000000          # 2017-08-17
        while True:
            k = get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval={iv}&startTime={start}&limit=1000")
            if not isinstance(k, list):
                print("error", k, flush=True); sys.exit(1)
            if not k: break
            rows += k
            start = k[-1][0] + step
            if len(k) < 1000: break
            time.sleep(0.25)
        a = np.array([[r[0] // 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])] for r in rows])
        np.savez(f"data/{sym}_{iv}.npz", t=a[:, 0].astype(np.int64), o=a[:, 1], h=a[:, 2], l=a[:, 3], c=a[:, 4], v=a[:, 5],
                 sp=np.zeros(len(a)))
        print(sym, iv, len(a), time.strftime('%Y-%m-%d', time.gmtime(a[0, 0])), "->", time.strftime('%Y-%m-%d', time.gmtime(a[-1, 0])), "last", a[-1, 4], flush=True)
