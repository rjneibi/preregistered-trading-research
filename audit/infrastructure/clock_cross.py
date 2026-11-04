"""Cross-source clock check against Dukascopy (true UTC), plus last-date table for the fresh holdout."""
import json
import os
from datetime import datetime, timezone

import numpy as np

import data_profile as dp

UTC = timezone.utc
z = np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
print({k: (z[k].dtype.str, z[k].shape, z[k][:2].tolist()) for k in z.files})
tk = "t" if "t" in z.files else "time"
scale = 60 if int(z[tk][0]) < 10**8 else 1
ref = dict(t=z[tk].astype(np.int64) * scale)
for x, n in zip("ohlc", ("open", "high", "low", "close")):
    ref[x] = z[x if x in z.files else n].astype(float)
print("lbo", datetime.fromtimestamp(int(ref["t"][0]), UTC), datetime.fromtimestamp(int(ref["t"][-1]), UTC), dp.nfp_clock(ref))
rep = {"lbo_nfp": dp.nfp_clock(ref)}
sets = {"histdata": dp.csv_hist(dp.SETS["histdata_xau_m1"][0]), "talab_m1_raw": dp.npy(dp.SETS["talab_xau_m1"][0]), "drevival": dp.npz(dp.SETS["drevival_m1"][0]), "cm_m1": dp.npz(dp.SETS["cm_xau_m1"][0])}
for k, d in sets.items():
    rep[k] = {f"{y}-{m:02d}": dp.cross(d, ref, (y, m)) for y, m in [(2016, 1), (2016, 7), (2020, 1), (2020, 7), (2024, 1), (2024, 7), (2025, 1), (2025, 7), (2026, 1), (2026, 3), (2026, 8)]}
    print(k, {a: (b["lag_min"], b["ret_corr"], b["med_diff"]) for a, b in rep[k].items() if b}, flush=True)
tv = np.load(dp.SETS["tv_xau"][0], allow_pickle=True)
print("tv", {k: tv[k].shape for k in tv.files})
for k in tv.files:
    if "t" in k.lower() and tv[k].dtype.kind in "iuf" and tv[k].ndim == 1 and len(tv[k]) > 10:
        print(k, datetime.fromtimestamp(int(tv[k][0]), UTC), datetime.fromtimestamp(int(tv[k][-1]), UTC))
json.dump(rep, open("clock_cross.json", "w"), indent=1, default=str)
