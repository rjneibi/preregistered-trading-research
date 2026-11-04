"""Empirical HistData offset, day by day. Stamp minus true UTC, in hours.

Dukascopy overlap: best lag on M1 close changes. Before the overlap: stamp hour of the daily break against the US rule.
Output is a run-length table, which is the correction used by every later rerun.
"""
import json
import os
import sys
from collections import Counter
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "infrastructure")]
import data_profile as dp
from clockfix import us_dst_bounds


def load_ref():
    z = np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
    k = "t" if "t" in z.files else "time"
    return z[k].astype(np.int64) * (60 if int(z[k][0]) < 10**8 else 1), z["c" if "c" in z.files else "close"].astype(float)


def eu_bounds(y):
    a = date(y, 3, 31)
    a = (a.toordinal() - (a.weekday() + 1) % 7)
    b = date(y, 10, 31)
    b = (b.toordinal() - (b.weekday() + 1) % 7)
    e = date(1970, 1, 1).toordinal()
    return (a - e) * 86400 + 3600, (b - e) * 86400 + 3600


h = dp.csv_hist(dp.SETS["histdata_xau_m1"][0])
rt, rc = load_ref()
ht, hc = h["t"], h["c"]
first, last = ht[0] // 86400, ht[-1] // 86400
days = []
for d in range(int(max(first, rt[0] // 86400)), int(min(last, rt[-1] // 86400)) + 1):
    if (d + 4) % 7 >= 5:
        continue
    lo = d * 86400
    i, j = np.searchsorted(rt, [lo, lo + 86400])
    if j - i < 300:
        continue
    bt, bc = rt[i:j], rc[i:j]
    best = None
    for L in (-1, 0, 1, 2):
        k = np.searchsorted(ht, bt + L * 3600)
        k[k >= len(ht)] = len(ht) - 1
        ok = ht[k] == bt + L * 3600
        if ok.sum() < 200:
            continue
        x, y = hc[k[ok]], bc[ok]
        cont = np.diff(np.where(ok)[0]) == 1
        if cont.sum() < 100:
            continue
        cc = float(np.corrcoef(np.diff(x)[cont], np.diff(y)[cont])[0, 1])
        if best is None or cc > best[1]:
            best = (L, cc)
    if best:
        days.append((d, best[0], best[1]))
arr = np.array(days)
print("days", len(arr), Counter(arr[:, 1].astype(int).tolist()), "low corr days", int((arr[:, 2] < 0.5).sum()))
good = arr[arr[:, 2] >= 0.5]


def iso(d):
    return str(np.datetime64(int(d) * 86400, "s"))[:10]


segs = []
s = 0
for i in range(1, len(good) + 1):
    if i == len(good) or good[i, 1] != good[s, 1]:
        segs.append((iso(good[s, 0]), iso(good[i - 1, 0]), int(good[s, 1]), i - s))
        s = i
print("segments", len(segs))
for x in segs:
    print(x)
# compare each day with two candidate rules
us, eu = [], []
for d, L, c in good:
    t = int(d) * 86400 + 12 * 3600
    y = int(iso(d)[:4])
    a, b = us_dst_bounds(y)
    us.append(int(a <= t < b) == L)
    e, f = eu_bounds(y)
    eu.append(int(e <= t < f) == L)
us, eu = np.array(us), np.array(eu)
yrs = np.array([int(iso(d)[:4]) for d in good[:, 0]])
tab = {int(y): dict(days=int((yrs == y).sum()), us_rule_wrong=int((~us[yrs == y]).sum()), eu_rule_wrong=int((~eu[yrs == y]).sum())) for y in np.unique(yrs)}
for y, v in tab.items():
    print(y, v)
# daily break stamp hour in the years before the overlap
t = ht[ht < rt[0]]
dd = t // 86400
out = []
for d in np.unique(dd):
    if (d + 4) % 7 > 3:
        continue
    hr = np.bincount(((t[dd == d] % 86400) // 3600).astype(int), minlength=24)
    if hr[20:24].min() == 0 or hr[20:24].min() < 30:
        out.append((iso(d), 20 + int(hr[20:24].argmin())))
print("pre-overlap days", len(out), Counter(x[1] for x in out))
json.dump(dict(segments=segs, by_year=tab, low_corr_days=int((arr[:, 2] < 0.5).sum()), pre_overlap_break_hours=Counter(x[1] for x in out)), open(os.path.join(HERE, "clock_map.json"), "w"), indent=1)
