"""Phase B data integrity: coverage, hashes, per-year defects, clock audit, cross-source. Read-only on inputs."""
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
R = "@GANN_ROOT@/research"
UTC = timezone.utc


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def npy(p):
    a = np.load(p)
    return dict(t=a["time"].astype(np.int64), o=a["open"].astype(float), h=a["high"].astype(float), l=a["low"].astype(float), c=a["close"].astype(float))


def npz(p):
    z = np.load(p)
    k = set(z.files)
    tk = "t" if "t" in k else "time"
    m = {x: x for x in "ohlc"} if "o" in k else {x: {"o": "open", "h": "high", "l": "low", "c": "close"}[x] for x in "ohlc"}
    return dict(t=z[tk].astype(np.int64), **{x: z[m[x]].astype(float) for x in "ohlc"})


def csv_hist(p):
    a = np.genfromtxt(p, delimiter=",", skip_header=1)
    return dict(t=a[:, 0].astype(np.int64), o=a[:, 1], h=a[:, 2], l=a[:, 3], c=a[:, 4])


SETS = {"histdata_xau_m1": (R + "/data/xauusd_m1_histdata.csv", csv_hist, 60),
        "talab_xau_m1": (R + "/ta_lab/data/XAU_M1.npy", npy, 60), "talab_xau_m5": (R + "/ta_lab/data/XAU_M5.npy", npy, 300),
        "talab_xau_m15": (R + "/ta_lab/data/XAU_M15.npy", npy, 900), "talab_xau_h1": (R + "/ta_lab/data/XAU_H1.npy", npy, 3600),
        "talab_xag_m5": (R + "/ta_lab/data/XAG_M5.npy", npy, 300), "talab_xag_m15": (R + "/ta_lab/data/XAG_M15.npy", npy, 900),
        "drevival_m1": (R + "/d_revival/m1.npz", npz, 60), "lbo_xau_m1": ("@LBO_ROOT@/data/m1/XAUUSD.npz", npz, 60),
        "cm_xau_m1": (R + "/cross_market/data/XAUUSD_M1.npz", npz, 60), "cm_xau_d1": (R + "/cross_market/data/XAUUSD_D1.npz", npz, 86400),
        "cm_xag_h1": (R + "/cross_market/data/XAGUSD_H1.npz", npz, 3600), "cm_us500_m1": (R + "/cross_market/data/US500_M1.npz", npz, 60),
        "cm_us500_d1": (R + "/cross_market/data/US500_D1.npz", npz, 86400), "cm_ustec_m1": (R + "/cross_market/data/USTEC_M1.npz", npz, 60),
        "cm_btc_1d": (R + "/cross_market/data/BTCUSDT_1d.npz", npz, 86400), "tv_xau": (R + "/tvsearch/data/xau_tv.npz", None, 60)}


def yr(t):
    return (t.astype("datetime64[s]").astype("datetime64[Y]").astype(int) + 1970)


def profile(d, step):
    t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
    dt = np.diff(t)
    tr = np.maximum(h[1:] - l[1:], np.abs(h[1:] - c[:-1]))
    atr = np.convolve(tr, np.ones(1440 if step == 60 else 100) / (1440 if step == 60 else 100), "same") + 1e-9
    y = yr(t[1:])
    out = {}
    for u in np.unique(y):
        m = y == u
        out[int(u)] = dict(rows=int(m.sum()), dup_or_backward=int((dt[m] <= 0).sum()), gaps_gt_1h=int((dt[m] > 3600).sum()) if step < 3600 else int((dt[m] > 4 * 86400).sum()),
                           nonpos=int((l[1:][m] <= 0).sum()), bad_ohlc=int(((h[1:] < np.maximum(o[1:], c[1:]))[m] | (l[1:] > np.minimum(o[1:], c[1:]))[m]).sum()),
                           flat=int(((h[1:] == l[1:])[m]).sum()), outlier_20x=int((tr[m] > 20 * atr[m]).sum()))
    return out


def first_fridays(a=2015, b=2026):
    for y in range(a, b + 1):
        for m in range(1, 13):
            d = datetime(y, m, 1, tzinfo=UTC)
            d += timedelta(days=(4 - d.weekday()) % 7)
            yield d


def us_dst(d):
    y = d.year
    s = datetime(y, 3, 8, tzinfo=UTC)
    s += timedelta(days=(6 - s.weekday()) % 7)
    e = datetime(y, 11, 1, tzinfo=UTC)
    e += timedelta(days=(6 - e.weekday()) % 7)
    return s <= d < e


def nfp_clock(d, shift=0):
    """Hour-minute of the largest 1m range on first Fridays, split by US DST. True release 12:30 (DST) / 13:30 (std) UTC."""
    t = d["t"] + shift
    r = d["h"] - d["l"]
    res = {True: [], False: []}
    for f in first_fridays():
        a = int(f.timestamp()) + 9 * 3600
        i, j = np.searchsorted(t, [a, a + 8 * 3600])
        if j - i < 200:
            continue
        k = i + int(np.argmax(r[i:j]))
        res[us_dst(f)].append(int((t[k] % 86400) // 60))
    return {("dst" if k else "std"): {"n": len(v), "mode_min_utc": (int(np.bincount(v).argmax()) if v else None), "share_mode": round(float(np.mean(np.array(v) == np.bincount(v).argmax())), 2) if v else None} for k, v in res.items()}


def weekly_reopen(d):
    t = d["t"]
    g = np.where(np.diff(t) > 24 * 3600)[0] + 1
    y = yr(t[g])
    return {int(u): int(np.bincount(((t[g[y == u]] % 86400) // 3600).astype(int)).argmax()) for u in np.unique(y)}


def cross(a, b, year_month):
    """Best lag (minutes, a stamp minus b stamp) by matching close changes. b is the reference."""
    lo = int(datetime(year_month[0], year_month[1], 1, tzinfo=UTC).timestamp())
    hi = lo + 28 * 86400
    ia = (a["t"] >= lo - 7200) & (a["t"] < hi + 7200)
    ib = (b["t"] >= lo) & (b["t"] < hi)
    if ia.sum() < 1000 or ib.sum() < 1000:
        return None
    sa = dict(zip(a["t"][ia].tolist(), a["c"][ia]))
    best = None
    for lag in range(-180, 181, 60):
        x = [(sa.get(int(u) + lag * 60), v) for u, v in zip(b["t"][ib], b["c"][ib])]
        x = np.array([p for p in x if p[0] is not None])
        if len(x) < 500:
            continue
        cc = np.corrcoef(np.diff(x[:, 0]), np.diff(x[:, 1]))[0, 1]
        if best is None or cc > best[1]:
            best = (lag, float(cc), float(np.median(x[:, 0] - x[:, 1])), float(np.percentile(np.abs(x[:, 0] - x[:, 1]), 99)), len(x))
    return dict(lag_min=best[0], ret_corr=round(best[1], 3), med_diff=round(best[2], 3), p99_abs_diff=round(best[3], 3), n=best[4]) if best else None


def main():
    data = {}
    rep = {}
    for k, (p, f, step) in SETS.items():
        if f is None:
            z = np.load(p, allow_pickle=True)
            rep[k] = dict(path=p, sha256=sha(p), keys=list(z.files))
            continue
        d = f(p)
        data[k] = d
        rep[k] = dict(path=p, sha256=sha(p), rows=len(d["t"]), first=str(datetime.fromtimestamp(int(d["t"][0]), UTC))[:16], last=str(datetime.fromtimestamp(int(d["t"][-1]), UTC))[:16],
                      per_year=profile(d, step))
        if step == 60:
            rep[k]["nfp_clock"] = nfp_clock(d)
        if step <= 900:
            rep[k]["weekly_reopen_hour_mode"] = weekly_reopen(d)
        print(k, rep[k]["rows"], rep[k]["first"], rep[k]["last"], rep[k].get("nfp_clock"), flush=True)
    ref = data["lbo_xau_m1"]
    c = {}
    for k in ("histdata_xau_m1", "talab_xau_m1", "drevival_m1", "cm_xau_m1"):
        c[k] = {f"{y}-{m:02d}": cross(data[k], ref, (y, m)) for y, m in [(2016, 1), (2016, 7), (2020, 1), (2020, 7), (2024, 1), (2024, 7), (2025, 1), (2025, 7), (2026, 1), (2026, 8)]}
        print(k, c[k], flush=True)
    rep["cross_source_vs_dukascopy_lbo"] = c
    json.dump(rep, open(os.path.join(OUT, "data_profile.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
