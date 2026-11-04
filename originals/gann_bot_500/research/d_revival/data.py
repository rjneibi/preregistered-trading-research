"""XAUUSD M1 (bid, BROKER time UTC+2/+3) 2010-01 .. 2026-10 for the Profile-D revival study.
histdata CSV (2010-01..2026-06-19) + ta_lab XAU_M1.npy (2026-06-26..). Cached as npz."""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "m1.npz")


def load():
    if os.path.exists(CACHE):
        z = np.load(CACHE)
        return {k: z[k] for k in z.files}
    import pandas as pd
    df = pd.read_csv(r"@GANN_ROOT@/research/data/xauusd_m1_histdata.csv")
    A = np.load(r"@GANN_ROOT@/research/ta_lab/data/XAU_M1.npy")
    # Clock check (2026-10-13): histdata stamps = NY local + 5h (true UTC in winter, UTC+1 in
    # summer) = broker time - 2h all year; ta_lab XAU_M1/M5 = broker time - 3h all year
    # (weekly reopen always 22:00). Store BROKER time (MetaQuotes: UTC+2 / UTC+3 on US DST).
    keep = A["time"].astype(np.int64) + 3600 > int(df.time.iloc[-1])
    d = dict(t=np.concatenate([df.time.values.astype(np.int64) + 7200,
                               A["time"][keep].astype(np.int64) + 3 * 3600]))
    for k in ("open", "high", "low", "close"):
        d[k[0]] = np.concatenate([df[k].values.astype(float), A[k][keep].astype(float)])
    np.savez(CACHE, **d)
    return d


if __name__ == "__main__":
    import datetime as dt
    d = load()
    t = d["t"]
    f = lambda x: dt.datetime.fromtimestamp(int(x), dt.timezone.utc)
    print(len(t), f(t[0]), f(t[-1]), "sorted", bool(np.all(np.diff(t) > 0)))
    # weekly open hour check (should be 22 UTC summer / 23 UTC winter)
    gaps = np.where(np.diff(t) > 36 * 3600)[0]
    for g in gaps[[0, 10, 30, 300, 500, -2]]:
        print("reopen", f(t[g + 1]))
