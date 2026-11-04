"""TUNE-1 part 2 (PREREG.md): USTEC opening-range breakout grid on DEV, then one sealed evaluation.
  python tune_orb.py dev    -> results/orb_dev.csv   (USTEC up to 2025-10-12 only)
  python tune_orb.py final  -> results/orb_final.txt (reads results/orb_finalists.json; run ONCE)"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"@GANN_ROOT@/research/cross_market")
from scalp_lab import load_index  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEV_END = pd.Timestamp("2025-10-12")
RANGES = [5, 15, 30, 45, 60]
LAST = [660, 720, 810, 930, 960]          # last entry minute (NY); 960 = any time until the close
STOPS = ["other", "mid"]
TGTS = [0, 1, 2, 3]                       # 0 = hold to 16:00
SIDES = ["both", "long"]
MINR = [0.0015, 0.003]
LIVE = (30, 960, "other", 0, "both", 0.0015)


def sessions(sym, lo=None, hi=None):
    df, cost = load_index(sym)
    m = (df.index.hour * 60 + df.index.minute).values
    df = df[(m >= 570) & (m < 960)]
    out = []
    for d, g in df.groupby(df.index.normalize()):
        if lo is not None and not (lo <= d <= hi):
            continue
        mm = (g.index.hour * 60 + g.index.minute).values
        if len(g) < 300 or mm[0] > 571 or not (mm >= 931).any():
            continue
        out.append((d, mm, g["o"].values, g["h"].values, g["l"].values, g["c"].values))
    return out, cost


def day_trade(S, cfg, cost):
    """net return (fraction) of the day's trade or None."""
    d, m, o, h, l, c = S
    N, last, stop_k, tg, side_k, minr = cfg
    rs = m < 570 + N
    rh, rl = h[rs].max(), l[rs].min()
    if (rh - rl) / rh < minr:
        return None
    for i in np.flatnonzero((m >= 570 + N) & (m < last)):
        up, dn = h[i] > rh, l[i] < rl
        if up and dn:
            return None
        if not (up or dn):
            continue
        side = 1 if up else -1
        if side < 0 and side_k == "long":
            return None
        ent = max(rh, o[i]) if side > 0 else min(rl, o[i])
        st = (rl if side > 0 else rh) if stop_k == "other" else (rh + rl) / 2
        risk = side * (ent - st)
        if risk <= 0:
            return None
        tgt = ent + side * tg * risk if tg else None
        hs = (l[i + 1:] <= st) if side > 0 else (h[i + 1:] >= st)
        ht = ((h[i + 1:] >= tgt) if side > 0 else (l[i + 1:] <= tgt)) if tg else np.zeros(len(hs), bool)
        qs = np.argmax(hs) if hs.any() else 10 ** 9
        qt = np.argmax(ht) if ht.any() else 10 ** 9
        if qs == qt == 10 ** 9:
            ex, extra = c[-1], 0
        elif qs <= qt:
            ex, extra = st, 0.5 * cost
        else:
            ex, extra = tgt, 0
        g = side * (ex - ent) / ent
        return g - (cost + extra) / ent, g, (cost + extra) / ent
    return None


def pf(r):
    r = np.asarray(r)
    if len(r) == 0:
        return np.nan
    neg = -r[r < 0].sum()
    return r[r > 0].sum() / neg if neg > 0 else 99.0


def grid():
    return list(itertools.product(RANGES, LAST, STOPS, TGTS, SIDES, MINR))


def dev():
    S, cost = sessions("USTEC", pd.Timestamp("2000-01-01"), DEV_END)
    rows = []
    for cfg in grid():
        r = [x[0] for x in (day_trade(s, cfg, cost) for s in S) if x is not None]
        h = len(r) // 2
        a, b = r[:h], r[h:]
        ok = len(a) >= 100 and len(b) >= 100
        rows.append(dict(cfg=cfg, n=len(r), robust_pf=min(pf(a), pf(b)) if ok else np.nan, pf=pf(r),
                         avg_bp=np.mean(r) * 1e4 if r else np.nan))
    df = pd.DataFrame(rows)
    by = dict(zip(df.cfg, df.robust_pf))
    dims = [RANGES, LAST, STOPS, TGTS, SIDES, MINR]
    plat = []
    for cfg in df.cfg:
        nb = []
        for k, vals in enumerate(dims):
            i = vals.index(cfg[k])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    c2 = list(cfg); c2[k] = vals[j]; nb.append(by[tuple(c2)])
        nb = [v for v in nb if not np.isnan(v)]
        plat.append(np.median(nb) if nb else np.nan)
    df["plateau"] = plat
    df = df.sort_values("robust_pf", ascending=False)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    df.to_csv(os.path.join(HERE, "results", "orb_dev.csv"), index=False)
    lv = df[df.cfg == LIVE].iloc[0]
    print(f"{len(df)} configs; live ORB-30 dev robust PF {lv.robust_pf:.2f} PF {lv.pf:.2f} n{lv.n} rank {list(df.cfg).index(LIVE) + 1}")
    print(df.head(25).to_string(index=False))
    print("plateau >= 1.2:"); print(df[df.plateau >= 1.2].head(10).to_string(index=False))
    print("plateau >= 1.0:"); print(df[df.plateau >= 1.0].head(10).to_string(index=False))


def final():
    fin = {k: tuple(v) for k, v in json.load(open(os.path.join(HERE, "results", "orb_finalists.json"))).items()}
    specs = {"live_orb30": LIVE, **fin}
    rng = np.random.default_rng(9)
    T, ct = sessions("USTEC", DEV_END + pd.Timedelta(days=1), pd.Timestamp("2030-01-01"))
    M = {s: sessions(s) for s in ("US500", "US30")}
    lines, res = [], {}
    P_ = lambda s: (print(s, flush=True), lines.append(s))
    for name, cfg in specs.items():
        tt = [x for x in (day_trade(s, cfg, ct) for s in T) if x is not None]
        rt = np.array([x[0] for x in tt]); g = np.array([x[1] for x in tt]); cc = np.array([x[2] for x in tt])
        p = float(((rng.choice([-1, 1], (2000, len(g))) * g - cc).mean(1) >= rt.mean()).mean())
        rm = {s: np.array([x[0] for x in (day_trade(d, cfg, c) for d in S) if x is not None]) for s, (S, c) in M.items()}
        allm = np.concatenate(list(rm.values()))
        res[name] = dict(t=pf(rt), tn=len(rt), m=pf(allm), p=p)
        P_(f"{name:14s} {cfg} | HOLD-T n{len(rt)} PF {pf(rt):.2f} avg {rt.mean() * 1e4:+.2f}bp twin p {p:.3f} | HOLD-M "
           + " ".join(f"{s} n{len(r)} PF {pf(r):.2f}" for s, r in rm.items()) + f" pooled {pf(allm):.2f}")
    b = res["live_orb30"]
    for name in fin:
        r = res[name]
        ok = r["t"] >= 1.2 and r["t"] > b["t"] and r["tn"] >= 100 and r["m"] >= 1.1 and r["m"] > b["m"] and r["p"] < 0.05
        P_(f"VERDICT {name}: {'PASS' if ok else 'FAIL'} (live HOLD-T PF {b['t']:.2f}, HOLD-M {b['m']:.2f})")
    open(os.path.join(HERE, "results", "orb_final.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    {"dev": dev, "final": final}[sys.argv[1]]()
