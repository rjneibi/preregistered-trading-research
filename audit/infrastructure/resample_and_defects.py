"""Resampling check against native bars, and a compact per-dataset defect table."""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine"))
from nbe import closed_resample
import data_profile as dp

R = "@GANN_ROOT@/research"
rep = {}
for nm, mp, np_, sec, f in (("cross_market XAU M1 vs M5", R + "/cross_market/data/XAUUSD_M1.npz", R + "/cross_market/data/XAUUSD_M5.npz", 300, dp.npz),
                            ("cross_market XAU M1 vs H1", R + "/cross_market/data/XAUUSD_M1.npz", R + "/cross_market/data/XAUUSD_H1.npz", 3600, dp.npz),
                            ("ta_lab XAU M1 vs M15", R + "/ta_lab/data/XAU_M1.npy", R + "/ta_lab/data/XAU_M15.npy", 900, dp.npy),
                            ("ta_lab XAU M5 vs H1", R + "/ta_lab/data/XAU_M5.npy", R + "/ta_lab/data/XAU_H1.npy", 3600, dp.npy)):
    a, b = f(mp), f(np_)
    T, O, H, L, C = closed_resample(a["t"], a["o"], a["h"], a["l"], a["c"], sec)
    _, ia, ib = np.intersect1d(T, b["t"], return_indices=True)
    ia, ib = ia[1:], ib[1:]
    rep[nm] = dict(bars=len(ia), open_match=round(float(np.isclose(O[ia], b["o"][ib]).mean()), 4), high_match=round(float(np.isclose(H[ia], b["h"][ib]).mean()), 4),
                   low_match=round(float(np.isclose(L[ia], b["l"][ib]).mean()), 4), close_match=round(float(np.isclose(C[ia], b["c"][ib]).mean()), 4),
                   max_abs_close_diff=round(float(np.abs(C[ia] - b["c"][ib]).max()), 3))
    print(nm, rep[nm], flush=True)
p = json.load(open("data_profile.json"))
tab = {}
for k, v in p.items():
    if "per_year" not in v:
        continue
    t = {}
    for y, r in v["per_year"].items():
        for a, b in r.items():
            t[a] = t.get(a, 0) + b
    tab[k] = dict(first=v["first"], last=v["last"], **t, sha256_16=v["sha256"][:16])
    print(k, tab[k])
json.dump(dict(resample=rep, defects=tab), open("resample_and_defects.json", "w"), indent=1)
