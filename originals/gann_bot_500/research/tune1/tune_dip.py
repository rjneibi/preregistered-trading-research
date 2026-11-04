"""TUNE-1 part 1 (PREREG.md): index dip grid on DEV only, then a one-shot sealed evaluation of frozen finalists.
  python tune_dip.py dev      -> results/dip_dev.csv (DEV data only; nothing after 2023-10-12 is used)
  python tune_dip.py final    -> results/dip_final.txt (reads results/dip_finalists.json; run ONCE)"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DIRS = [r"@GANN_ROOT@/research/cross_market/data", r"@GANN_ROOT@/research/cross_market/data_edge"]
DEV_END = pd.Timestamp("2023-10-12 23:59")
HALF = pd.Timestamp("2018-01-01")
DEV = ["US500", "US30", "US2000"]
HOLD_T = ["US500", "US30", "US2000", "USTEC"]
HOLD_M = ["DE40", "FRA40", "ESP35", "AUS200", "HK50", "EWG", "EWJ", "EWU", "EFA", "EEM", "FXI", "INDA",
          "SMH", "XLK", "XLV", "XLP", "XLE", "VNQ"]
FIN_L = 0.05 / 365
MIN_CELL = 20

ENTRIES = ([("rsi2", a) for a in (5, 10, 15, 20, 25, 30)] + [("ibs", b) for b in (0.1, 0.15, 0.2, 0.25, 0.3)]
           + [("rsi2ibs", (a, b)) for a in (10, 20, 30) for b in (0.2, 0.3, 0.5)]
           + [("down", n) for n in (2, 3, 4)] + [("low", k) for k in (3, 5, 7, 10)]
           + [("crsi", s) for s in (20, 35, 50)] + [("stretch", x) for x in (0.5, 1.0, 1.5)])
FILTERS = ["none", "s200", "s100", "s50", "s50>s200"]
EXITS = ["s5", "s3", "s10", "prevhigh", "ibs_ph", "rsi50", "rsi70", "upclose"]
HOLDS = [5, 10, 15]
LIVE = {"live_rsi2": (("rsi2", 10), "s200", "s5", 10), "live_ibs": (("ibs", 0.2), "none", "ibs_ph", 15)}


def load(sym):
    for d in DIRS:
        p = os.path.join(d, f"{sym}_D1.npz")
        if os.path.exists(p):
            z = np.load(p)
            df = pd.DataFrame({k: z[k] for k in ("o", "h", "l", "c", "sp")}, index=pd.to_datetime(z["t"], unit="s"))
            df = df[~df.index.duplicated()].sort_index()
            sp = 1.5 * float(np.median(z["sp"][z["sp"] > 0])) if (z["sp"] > 0).any() else 0.0
            return df, max(sp, 0.0002 * float(df["c"].median()))
    raise FileNotFoundError(sym)


def prep(sym):
    d, sp = load(sym)
    c, h, l = d["c"], d["h"], d["l"]
    df = c.diff()
    up, dn = df.clip(lower=0).ewm(alpha=.5).mean(), (-df).clip(lower=0).ewm(alpha=.5).mean()
    rsi2 = (100 - 100 / (1 + up / dn.replace(0, 1e-12))).values
    rng = (h - l).replace(0, np.nan)
    ibs = ((c - l) / rng).values
    sma = {n: c.rolling(n).mean().values for n in (3, 5, 10, 50, 100, 200)}
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(1)
    atr10 = tr.rolling(10).mean().values
    cv, hv = c.values, h.values
    dnrun = pd.Series((df < 0).astype(int)).groupby(((df < 0) != (df < 0).shift()).cumsum()).cumsum().values
    F = dict(rsi2=rsi2, ibs=ibs, c=cv, h=hv, sma=sma, atr10=atr10, dnrun=dnrun,
             low={k: c.rolling(k).min().values for k in (3, 5, 7, 10)}, crsi=rsi2 + np.r_[np.nan, rsi2[:-1]])
    return dict(d=d, sp=sp, F=F, o=d["o"].values, idx=d.index,
                days=np.r_[0, np.cumsum((d.index[1:] - d.index[:-1]).days)])


def entry_mask(F, e):
    k, p = e
    with np.errstate(invalid="ignore"):
        if k == "rsi2": m = F["rsi2"] < p
        elif k == "ibs": m = F["ibs"] < p
        elif k == "rsi2ibs": m = (F["rsi2"] < p[0]) & (F["ibs"] < p[1])
        elif k == "down": m = F["dnrun"] >= p
        elif k == "low": m = F["c"] <= F["low"][p]
        elif k == "crsi": m = F["crsi"] < p
        elif k == "stretch": m = F["c"] < F["sma"][5] - p * F["atr10"]
    return np.nan_to_num(m).astype(bool)


def filt_mask(F, f):
    c, s = F["c"], F["sma"]
    with np.errstate(invalid="ignore"):
        m = {"none": np.ones(len(c), bool), "s200": c > s[200], "s100": c > s[100], "s50": c > s[50],
             "s50>s200": s[50] > s[200]}[f]
    m = np.nan_to_num(m).astype(bool)
    m[:200] = False
    return m


def exit_mask(F, x):
    c, h, s = F["c"], F["h"], F["sma"]
    ph = np.r_[np.inf, h[:-1]]
    pc = np.r_[np.inf, c[:-1]]
    with np.errstate(invalid="ignore"):
        m = {"s5": c > s[5], "s3": c > s[3], "s10": c > s[10], "prevhigh": c > ph,
             "ibs_ph": (F["ibs"] > 0.8) | (c > ph), "rsi50": F["rsi2"] > 50, "rsi70": F["rsi2"] > 70,
             "upclose": c > pc}[x]
    return np.nan_to_num(m).astype(bool)


def next_true(m):
    """nt[j] = smallest k >= j with m[k], else len(m)."""
    n = len(m); nt = np.full(n + 1, n)
    for j in range(n - 1, -1, -1):
        nt[j] = j if m[j] else nt[j + 1]
    return nt


def run(P, sig, nt_exit, hold, lo=None, hi=None):
    """trades (signal date, net return, hold days). Signal at close i, in at open i+1, exit at open j+1."""
    o, idx, days, sp = P["o"], P["idx"], P["days"], P["sp"]
    n = len(o)
    cand = np.flatnonzero(sig)
    out, busy = [], -1
    for i in cand:
        if i <= busy or i >= n - 2:
            continue
        j = min(nt_exit[i + 1], i + hold, n - 2)
        if lo is not None and (idx[i] < lo or idx[j + 1] > hi):
            busy = j
            continue
        r = o[j + 1] / o[i + 1] - 1 - sp / o[i + 1] - (days[j + 1] - days[i + 1]) * FIN_L
        out.append((idx[i], r, j - i))
        busy = j
    return out


def pf(r):
    r = np.asarray(r)
    if len(r) == 0:
        return np.nan
    neg = -r[r < 0].sum()
    return r[r > 0].sum() / neg if neg > 0 else 99.0


def configs():
    return list(itertools.product(range(len(ENTRIES)), FILTERS, EXITS, HOLDS))


def dev():
    Ps = {s: prep(s) for s in DEV}
    cache = {}
    for s, P in Ps.items():
        F = P["F"]
        cache[s] = dict(E=[entry_mask(F, e) for e in ENTRIES], Fm={f: filt_mask(F, f) for f in FILTERS},
                        X={x: next_true(exit_mask(F, x)) for x in EXITS})
    rows = []
    for ei, f, x, hd in configs():
        cells, allr = [], []
        for s, P in Ps.items():
            C = cache[s]
            tr = run(P, C["E"][ei] & C["Fm"][f], C["X"][x], hd, P["idx"][0], DEV_END)
            r1 = [r for t, r, _ in tr if t < HALF]; r2 = [r for t, r, _ in tr if t >= HALF]
            cells += [(len(r1), pf(r1)), (len(r2), pf(r2))]
            allr += [r for _, r, _ in tr]
        ok = all(n >= MIN_CELL for n, _ in cells)
        rob = min(p for _, p in cells) if ok else np.nan
        allr = np.array(allr)
        rows.append(dict(entry=f"{ENTRIES[ei][0]}:{ENTRIES[ei][1]}", ei=ei, filt=f, exit=x, hold=hd, n=len(allr),
                         robust_pf=rob, pooled_pf=pf(allr), avg_bp=allr.mean() * 1e4 if len(allr) else np.nan,
                         min_n=min(n for n, _ in cells)))
    df = pd.DataFrame(rows)
    # neighbourhood plateau: neighbours = same family, adjacent parameter / any one other dimension changed
    df["key"] = list(zip(df.ei, df.filt, df.exit, df.hold))
    by = {k: v for k, v in zip(df.key, df.robust_pf)}
    fam = [e[0] for e in ENTRIES]
    neigh = []
    for ei, f, x, hd in df.key:
        nb = []
        for ej in (ei - 1, ei + 1):
            if 0 <= ej < len(ENTRIES) and fam[ej] == fam[ei]:
                nb.append(by[(ej, f, x, hd)])
        hi_ = HOLDS.index(hd)
        for hj in (hi_ - 1, hi_ + 1):
            if 0 <= hj < len(HOLDS):
                nb.append(by[(ei, f, x, HOLDS[hj])])
        nb += [by[(ei, g, x, hd)] for g in FILTERS if g != f]
        nb = [v for v in nb if not np.isnan(v)]
        neigh.append(np.median(nb) if nb else np.nan)
    df["plateau"] = neigh
    df = df.drop(columns="key").sort_values("robust_pf", ascending=False)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    df.to_csv(os.path.join(HERE, "results", "dip_dev.csv"), index=False)
    print(f"{len(df)} configs, {df.robust_pf.notna().sum()} with n>={MIN_CELL} in all 6 cells")
    for name, (e, f, x, hd) in LIVE.items():
        r = df[(df.entry == f"{e[0]}:{e[1]}") & (df.filt == f) & (df.exit == x) & (df.hold == hd)].iloc[0]
        print(f"  {name}: robust PF {r.robust_pf:.2f} pooled {r.pooled_pf:.2f} n{r.n} rank {list(df.index).index(r.name) + 1}")
    print(df.head(40).to_string(index=False, float_format=lambda v: f"{v:.2f}"))


def evaluate(spec, syms, lo, hi):
    """returns {sym: (returns array, hold lengths, pool idx)}"""
    (e, f, x, hd) = spec
    out = {}
    for s in syms:
        P = prep(s); F = P["F"]
        fm = filt_mask(F, f)
        tr = run(P, entry_mask(F, e) & fm, next_true(exit_mask(F, x)), hd, lo, hi)
        pool = np.flatnonzero(fm & (P["idx"] >= lo) & (P["idx"] <= hi))
        out[s] = (np.array([r for _, r, _ in tr]), np.array([h for *_, h in tr]), pool, P)
    return out


def twin_pooled(res, k=1000, seed=3):
    """random entries from each market's filter pool with the same hold lengths; p = P(twin pooled PF >= real)."""
    rng = np.random.default_rng(seed)
    real = pf(np.concatenate([v[0] for v in res.values()]))
    hits = 0
    for _ in range(k):
        rs = []
        for s, (r, lens, pool, P) in res.items():
            if len(lens) == 0:
                continue
            o, days, sp = P["o"], P["days"], P["sp"]
            pool_ = pool[pool + lens.max() + 2 < len(o)]
            e = rng.choice(pool_, len(lens)); L = rng.permutation(lens)
            rs.append(o[e + L + 1] / o[e + 1] - 1 - sp / o[e + 1] - (days[e + L + 1] - days[e + 1]) * FIN_L)
        hits += pf(np.concatenate(rs)) >= real
    return hits / k


def final():
    fin = json.load(open(os.path.join(HERE, "results", "dip_finalists.json")))
    specs = dict(LIVE)
    for k, (e, f, x, hd) in fin.items():
        specs[k] = ((e[0], tuple(e[1]) if isinstance(e[1], list) else e[1]), f, x, hd)
    lines = []
    P_ = lambda s: (print(s, flush=True), lines.append(s))
    T0, T1 = pd.Timestamp("2023-10-13"), pd.Timestamp("2026-12-31")
    M0 = pd.Timestamp("2000-01-01")
    res = {}
    for name, spec in specs.items():
        ht = evaluate(spec, HOLD_T, T0, T1); hm = evaluate(spec, HOLD_M, M0, T1)
        rt = np.concatenate([v[0] for v in ht.values()]); rm = np.concatenate([v[0] for v in hm.values()])
        per_m = {s: (len(v[0]), pf(v[0])) for s, v in hm.items()}
        pt, pm = twin_pooled(ht), twin_pooled(hm)
        res[name] = dict(t_pf=pf(rt), t_n=len(rt), m_pf=pf(rm), m_n=len(rm), share=np.mean([p > 1 for n, p in per_m.values() if n]),
                         pt=pt, pm=pm, per_t={s: (len(v[0]), pf(v[0])) for s, v in ht.items()}, per_m=per_m,
                         t_avg=rt.mean() * 1e4, m_avg=rm.mean() * 1e4)
        r = res[name]
        P_(f"{name:12s} {spec}\n   HOLD-T n{r['t_n']} PF {r['t_pf']:.2f} avg {r['t_avg']:+.1f}bp twin p {pt:.3f} | "
           + " ".join(f"{s} n{n} {p:.2f}" for s, (n, p) in r["per_t"].items())
           + f"\n   HOLD-M n{r['m_n']} PF {r['m_pf']:.2f} avg {r['m_avg']:+.1f}bp twin p {pm:.3f} PF>1 in {r['share']:.0%} | "
           + " ".join(f"{s} {p:.2f}" for s, (n, p) in r["per_m"].items()))
    bt = max(res["live_rsi2"]["t_pf"], res["live_ibs"]["t_pf"]); bm = max(res["live_rsi2"]["m_pf"], res["live_ibs"]["m_pf"])
    for name in fin:
        r = res[name]
        g1 = r["t_pf"] >= 1.30 and r["t_n"] >= 30 and r["t_pf"] > bt
        g2 = r["m_pf"] >= 1.15 and r["share"] >= 2 / 3 and r["m_pf"] > bm
        g3 = r["pt"] < 0.05 and r["pm"] < 0.05
        P_(f"VERDICT {name}: G1 {'Y' if g1 else 'n'} G2 {'Y' if g2 else 'n'} G3 {'Y' if g3 else 'n'} -> {'PASS' if g1 and g2 and g3 else 'FAIL'}"
           f"  (baseline best HOLD-T PF {bt:.2f}, HOLD-M PF {bm:.2f})")
    open(os.path.join(HERE, "results", "dip_final.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    {"dev": dev, "final": final}[sys.argv[1]]()
