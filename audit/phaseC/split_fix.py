"""Finds stock splits in the daily ETF files, which were saved as raw prices, and builds a sandbox with split-adjusted copies. A split is an open-to-previous-close ratio above 1.45 or below 0.68 on a non-crypto file.
Reruns in rs_adj show which stored results depended on the jumps. The originals are read only."""
import glob
import json
import os
import shutil

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy")).replace(os.sep, "/")
R = "@GANN_ROOT@/research/cross_market"
SRC, DST = COPY + "/rs_recorded", COPY + "/rs_adj"
assert not os.path.exists(DST)
os.makedirs(DST + "/research")
for d in ("cross_market", "tune1"):
    shutil.copytree(f"{SRC}/research/{d}", f"{DST}/research/{d}", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
shutil.copytree(SRC + "/fable-backtesting", DST + "/fable-backtesting", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "download"))
n = 0
for r, _, fs in os.walk(DST):
    for f in fs:
        if f.endswith(".py"):
            p = os.path.join(r, f)
            t = open(p, encoding="utf-8", errors="surrogateescape").read()
            u = t.replace(SRC, DST).replace(r"@GANN_ROOT@/research/cross_market", DST + "/research/cross_market").replace("@GANN_ROOT@/research/cross_market", DST + "/research/cross_market")
            if u != t:
                open(p, "w", encoding="utf-8", errors="surrogateescape").write(u)
                n += 1
rep = {}
for sub in ("data", "data_edge"):
    dd = f"{DST}/research/cross_market/{sub}"
    os.makedirs(dd, exist_ok=True)
    for p in sorted(glob.glob(f"{R}/{sub}/*")):
        name = os.path.basename(p)
        out = os.path.join(dd, name)
        if not name.endswith("_D1.npz") or name.startswith("C_") or any(x in name for x in ("USDT", "BTC", "ETH", "BITX")):
            shutil.copy(p, out)
            continue
        z = dict(np.load(p))
        c, o = z["c"].astype(float).copy(), z["o"].astype(float).copy()
        h, l = z["h"].astype(float).copy(), z["l"].astype(float).copy()
        rat = o[1:] / c[:-1]
        ev = []
        for i in np.flatnonzero((rat > 1.45) | (rat < 0.68)):
            k = float(rat[i])
            ev.append([str(np.datetime64(int(z["t"][i + 1]), "s"))[:10], round(float(c[i]), 2), round(float(o[i + 1]), 2), round(k, 3)])
            for a in (c, o, h, l):
                a[: i + 1] *= k
        if ev:
            rep[name[:-7]] = ev
        z.update(c=c, o=o, h=h, l=l)
        np.savez(out, **z)
json.dump(rep, open(os.path.join(HERE, "split_events.json"), "w"), indent=0)
print(len(rep), "files with jumps;", sum(map(len, rep.values())), "events; py patched", n)
print(rep)
