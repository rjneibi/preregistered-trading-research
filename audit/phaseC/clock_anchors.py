"""Independent anchors for the clock fix, none of which use NFP.

A. FOMC statement, 14:00 ET: 18:00 UTC in US daylight time, 19:00 UTC otherwise.
B. Weekly reopen hour, by year and regime.
C. Daily maintenance break, by year and regime. Runs every day, so it also tests the fix at each switch.
D. Lag against Dukascopy, month by month, before and after the fix.
E. Lag against Dukascopy, day by day, around each US switch.
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "infrastructure")]
import data_profile as dp
from clockfix import eu_bounds, shifted, true_utc, us_dst_bounds

UTC = timezone.utc
SRC = open("@GANN_ROOT@/research/powell/powell_lab.py", encoding="utf-8").read()
body = SRC[SRC.index('FOMC = """'):]
body = body[:body.index('"""', 12)]
FOMC = sorted(set(re.findall(r"\d{4}-\d{2}-\d{2}", body)))


def load_ref():
    z = np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
    k = "t" if "t" in z.files else "time"
    d = dict(t=z[k].astype(np.int64) * (60 if int(z[k][0]) < 10**8 else 1))
    for x, n in zip("ohlc", ("open", "high", "low", "close")):
        d[x] = z[x if x in z.files else n].astype(float)
    return d


def is_dst_date(s):
    y, m, dd = map(int, s.split("-"))
    e = (date(y, m, dd) - date(1970, 1, 1)).days * 86400 + 12 * 3600
    a, b = us_dst_bounds(y)
    return bool(a <= e < b)


def fomc_minute(d):
    """Stamp minute of the largest one-minute range, 17:30 to 19:29 and 18:30 to 20:29 stamp clock merged."""
    t, r = d["t"], d["h"] - d["l"]
    out = {True: [], False: []}
    for s in FOMC:
        lo = int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())
        i, j = np.searchsorted(t, [lo + 17 * 3600, lo + 19 * 3600 + 15 * 60 + 3600])
        if j - i < 100:
            continue
        # the statement bar is the first big bar; the press conference comes 30 minutes later and can be larger
        w = r[i:j]
        base = np.median(w)
        big = np.where(w >= max(6 * base, 0.5 * w.max()))[0]
        if len(big) == 0:
            continue
        k = i + int(big[0])
        out[is_dst_date(s)].append(int((t[k] % 86400) // 60))
    res = {}
    for k, v in out.items():
        c = Counter(v)
        res["dst" if k else "std"] = dict(n=len(v), at_1800=sum(1 for x in v if 1080 <= x <= 1082), at_1900=sum(1 for x in v if 1140 <= x <= 1142), other=sum(1 for x in v if not (1080 <= x <= 1082 or 1140 <= x <= 1142)), top=[(f"{a // 60:02d}:{a % 60:02d}", b) for a, b in c.most_common(3)])
    return res


def reopen(d):
    t = d["t"]
    g = np.where(np.diff(t) > 24 * 3600)[0] + 1
    tt = t[g]
    # stamps of the first bar after a weekend. Regime read from the date, not the stamp hour.
    wd = ((tt // 86400) + 4) % 7
    keep = wd == 0  # Sunday
    tt = tt[keep]
    res = {}
    for y in sorted(set(dp.yr(tt).tolist())):
        for reg in (True, False):
            x = tt[(dp.yr(tt) == y) & (np.array([is_dst_date(str(np.datetime64(int(u), "s"))[:10]) for u in tt]) == reg)]
            if len(x):
                res[f"{y}-{'dst' if reg else 'std'}"] = Counter(((x % 86400) // 3600).astype(int).tolist()).most_common(2)
    return res


def break_hour(t):
    """Weekday hour with the fewest bars, by year and regime."""
    wd = ((t // 86400) + 4) % 7
    k = (wd >= 1) & (wd <= 4)  # Monday to Thursday, so no weekend edge
    tt = t[k]
    days = tt // 86400
    uniq, inv = np.unique(days, return_inverse=True)
    dst_day = np.array([is_dst_date(str(np.datetime64(int(u) * 86400, "s"))[:10]) for u in uniq])
    yrs = dp.yr(uniq * 86400)
    hr = ((tt % 86400) // 3600).astype(int)
    res = {}
    for y in np.unique(yrs):
        for reg in (True, False):
            sel = (yrs == y) & (dst_day == reg)
            if sel.sum() < 10:
                continue
            h = np.bincount(hr[sel[inv]], minlength=24)
            res[f"{int(y)}-{'dst' if reg else 'std'}"] = int(h.argmin())
    return res


def lag(a_t, a_c, b_t, b_c, lo, hi, lags=(-120, -60, 0, 60, 120)):
    ib = (b_t >= lo) & (b_t < hi)
    if ib.sum() < 300:
        return None
    bt, bc = b_t[ib], b_c[ib]
    best = None
    for L in lags:
        _, ia, ibb = np.intersect1d(a_t, bt + L * 60, return_indices=True)
        if len(ia) < 200:
            continue
        x, y = a_c[ia], bc[ibb]
        keep = np.diff(ia) == np.diff(ibb)
        if keep.sum() < 100:
            continue
        cc = float(np.corrcoef(np.diff(x)[keep], np.diff(y)[keep])[0, 1])
        if best is None or cc > best[1]:
            best = (L, cc)
    return best


def main():
    h = dp.csv_hist(dp.SETS["histdata_xau_m1"][0])
    r = load_ref()
    fx = dict(h)
    fx["t"] = true_utc(h["t"])
    o = np.argsort(fx["t"], kind="stable")
    u = np.concatenate(([True], np.diff(fx["t"][o]) > 0))
    for k in "tohlc":
        fx[k] = fx[k][o][u]
    print("FOMC dates", len(FOMC), FOMC[0], FOMC[-1], "backward after fix", int((np.diff(true_utc(h["t"])) < 0).sum()), "dupes dropped", int((~u).sum()))
    rep = dict(fomc_n=len(FOMC), hist_first=str(np.datetime64(int(h["t"][0]), "s")), hist_last=str(np.datetime64(int(h["t"][-1]), "s")), share_shifted=round(float(shifted(h["t"]).mean()), 4))
    rep["A_fomc"] = dict(histdata_raw=fomc_minute(h), histdata_fixed=fomc_minute(fx), dukascopy=fomc_minute(r))
    print(json.dumps(rep["A_fomc"], indent=0))
    rep["B_reopen"] = dict(histdata_raw=reopen(h), histdata_fixed=reopen(fx), dukascopy=reopen(r))
    print("B", json.dumps(rep["B_reopen"]))
    rep["C_break_hour"] = dict(histdata_raw=break_hour(h["t"]), histdata_fixed=break_hour(fx["t"]), dukascopy=break_hour(r["t"]))
    print("C", json.dumps(rep["C_break_hour"]))
    months = []
    y0 = max(int(dp.yr(h["t"][:1])[0]), int(dp.yr(r["t"][:1])[0]))
    for y in range(y0, 2027):
        for m in range(1, 13):
            lo = int(datetime(y, m, 1, tzinfo=UTC).timestamp())
            hi = int(datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=UTC).timestamp())
            a = lag(h["t"], h["c"], r["t"], r["c"], lo, hi)
            b = lag(fx["t"], fx["c"], r["t"], r["c"], lo, hi)
            if a and b:
                months.append((f"{y}-{m:02d}", a[0], round(a[1], 3), b[0], round(b[1], 3)))
    rep["D_monthly"] = months
    print("D months", len(months), "raw lags", Counter(x[1] for x in months), "fixed lags", Counter(x[3] for x in months), "min fixed corr", min(x[4] for x in months))
    print("D nonzero fixed", [x for x in months if x[3] != 0])
    bad = []
    n = 0
    for y in range(y0, 2027):
        for b0 in us_dst_bounds(y) + eu_bounds(y):
            for dd in range(-10, 11):
                lo = (b0 // 86400 + dd) * 86400
                if ((lo // 86400) + 4) % 7 == 6:
                    continue
                x = lag(fx["t"], fx["c"], r["t"], r["c"], lo, lo + 86400, lags=(-60, 0, 60))
                if x:
                    n += 1
                    if x[0] != 0:
                        bad.append((str(np.datetime64(lo, "s"))[:10], x[0], round(x[1], 3)))
    rep["E_switch_days"] = dict(days=n, not_zero=len(bad), list=bad[:60])
    print("E", n, len(bad), bad[:40])
    json.dump(rep, open(os.path.join(HERE, "clock_anchors.json"), "w"), indent=1, default=str)


main()
