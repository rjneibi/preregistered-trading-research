"""Stamp minus true UTC, by day, for every gold M1 file against Dukascopy. Run-length segments."""
import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "infrastructure")]
import data_profile as dp
from clockfix import true_utc

z = np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
k_ = "t" if "t" in z.files else "time"
rt = z[k_].astype(np.int64) * (60 if int(z[k_][0]) < 10**8 else 1)
rc = z["c" if "c" in z.files else "close"].astype(float)


def iso(d):
    return str(np.datetime64(int(d) * 86400, "s"))[:10]


def mp(ht, hc):
    o = np.argsort(ht, kind="stable")
    ht, hc = ht[o], hc[o]
    res = []
    for d in range(int(max(ht[0], rt[0]) // 86400), int(min(ht[-1], rt[-1]) // 86400) + 1):
        if (d + 4) % 7 == 6:
            continue
        i, j = np.searchsorted(rt, [d * 86400, (d + 1) * 86400])
        if j - i < 300:
            continue
        bt, bc = rt[i:j], rc[i:j]
        best = None
        for L in (-1, 0, 1, 2, 3, 4):
            k = np.searchsorted(ht, bt + L * 3600)
            k[k >= len(ht)] = len(ht) - 1
            ok = ht[k] == bt + L * 3600
            if ok.sum() < 200:
                continue
            x, y = hc[k[ok]], bc[ok]
            c = np.diff(np.where(ok)[0]) == 1
            if c.sum() < 100:
                continue
            cc = float(np.corrcoef(np.diff(x)[c], np.diff(y)[c])[0, 1])
            if best is None or cc > best[1]:
                best = (L, cc)
        if best:
            res.append((d, best[0], best[1]))
    a = np.array(res)
    g = a[a[:, 2] >= 0.5]
    segs, s = [], 0
    for i in range(1, len(g) + 1):
        if i == len(g) or g[i, 1] != g[s, 1]:
            segs.append((iso(g[s, 0]), iso(g[i - 1, 0]), int(g[s, 1]), i - s))
            s = i
    return dict(days=len(a), low_corr=int((a[:, 2] < 0.5).sum()), lags=Counter(a[:, 1].astype(int).tolist()), n_segments=len(segs), segments=segs)


h = dp.csv_hist(dp.SETS["histdata_xau_m1"][0])
rep = {"histdata_raw": mp(h["t"], h["c"]), "histdata_fixed": mp(true_utc(h["t"]), h["c"])}
for nm, key, f in (("talab_m1", "talab_xau_m1", dp.npy), ("drevival_m1", "drevival_m1", dp.npz), ("cross_market_m1", "cm_xau_m1", dp.npz)):
    d = f(dp.SETS[key][0])
    rep[nm] = mp(d["t"], d["c"])
for k, v in rep.items():
    print(k, v["days"], "lowcorr", v["low_corr"], v["lags"], "segments", v["n_segments"], v["segments"][:3], v["segments"][-3:], flush=True)
json.dump(rep, open(os.path.join(HERE, "clock_map_all.json"), "w"), indent=1, default=str)
