"""SC-1 USTEC ORB-30: independent numpy rewrite, twin test, statistics, 20 spot checks with a contact sheet.
The rewrite shares no code with scalp_lab.py. Also measures two fill assumptions in the original: entry at the range edge when the bar opened beyond it, and stop fills through a gap."""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.abspath(os.path.join(HERE, ".."))
src = open(HERE + "/spot_checks.py", encoding="utf-8").read().split("iso = lambda")[0]
sc = {"__file__": HERE + "/spot_checks.py"}
exec(compile(src, "spot_checks", "exec"), sc)
pa = sc["pa"]
z = np.load(A + "/_copy/rs_recorded/research/cross_market/data/USTEC_M1.npz")
ny = pd.to_datetime(z["t"], unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT").tz_convert("America/New_York").tz_localize(None)
keep = ~pd.isna(ny) & ~pd.Index(ny).duplicated()
ny = ny[keep]
o, h, l, c, sp = [z[k][keep].astype(float) for k in ("o", "h", "l", "c", "sp")]
mn = ny.hour.values * 60 + ny.minute.values
sess = (mn >= 570) & (mn < 960)
COST = 1.5 * float(np.median(sp[sess & (sp > 0)]))
day = ny.normalize().values
sess_idx = np.flatnonzero(sess)
cut = np.flatnonzero(np.diff(day[sess_idx]) > np.timedelta64(0)) + 1


def run(n=30, real_entry=False, gap_stop=False, cost=COST):
    out = []
    for ix in np.split(sess_idx, cut):
        m = mn[ix]
        if len(ix) < 300 or m[0] > 571 or m[-1] < 931:
            continue
        pre, post = ix[m < 570 + n], ix[m >= 570 + n]
        if not len(pre) or not len(post):
            continue
        hi, lo = h[pre].max(), l[pre].min()
        up, dn = h[post] > hi, l[post] < lo
        hit = np.flatnonzero(up | dn)
        if not len(hit) or (up[hit[0]] and dn[hit[0]]):
            continue
        b = post[hit[0]]
        s = 1 if up[hit[0]] else -1
        ent = hi if s > 0 else lo
        if real_entry:
            ent = max(ent, o[b]) if s > 0 else min(ent, o[b])
        stop = lo if s > 0 else hi
        rest = ix[ix > b]
        tch = (l[rest] <= stop) if s > 0 else (h[rest] >= stop)
        if tch.any():
            e = rest[tch.argmax()]
            ex, how = stop, 1
            if gap_stop:
                ex = min(stop, o[e]) if s > 0 else max(stop, o[e])
        elif len(rest):
            e, ex, how = rest[-1], c[rest[-1]], 0
        else:
            e, ex, how = b, ent, 0
        g = s * (ex - ent) / ent
        k = (cost * (1.5 if how else 1)) / ent
        out.append((ny[b], s, ent, stop, ex, how, g - k, b, e, o[b]))
    return out


r0 = run()
r = np.array([x[6] for x in r0])
pf = pa["pf"]
half = len(r) // 2
rep = dict(cost=round(COST, 3), n=len(r), pf=round(pf(r), 3), pf_h1=round(pf(r[:half]), 3), pf_h2=round(pf(r[half:]), 3), win=round(float((r > 0).mean()), 3), avg_bp=round(float(r.mean() * 1e4), 2))
rng = np.random.default_rng(20261031)
gr = r + np.array([(COST * (1.5 if x[5] else 1)) / x[2] for x in r0])
full, cnt = pf(r), 0
for _ in range(2000):
    fl = rng.choice([-1, 1], len(r))
    cnt += pf(gr * fl - (r - gr) * -1) >= full
rep["twin_flip_p"] = round((cnt + 1) / 2001, 4)
e = run(real_entry=True)
g = run(gap_stop=True)
b = run(real_entry=True, gap_stop=True)
rx = lambda t: np.array([x[6] for x in t])
rep["entry_beyond_edge_share"] = round(float(np.mean([(x[9] > x[2]) if x[1] > 0 else (x[9] < x[2]) for x in r0])), 3)
rep["fills"] = dict(real_entry=round(pf(rx(e)), 3), gap_stop=round(pf(rx(g)), 3), both=round(pf(rx(b)), 3), both_h1=round(pf(rx(b)[:half]), 3), both_h2=round(pf(rx(b)[half:]), 3), both_avg_bp=round(float(rx(b).mean() * 1e4), 2))
rep["cost_2x_pf"] = round(pf(rx(run(cost=2 * COST))), 3)
s_ = np.sort(r)
rep["pf_no_top5"] = round(pf(s_[:-5]), 3)
rep["boot_pf_ci"] = pa["block_boot"](r, pf)
rep["dsr"] = {str(k): pa["dsr"](r, k) for k in (18, 2000, 114500)}
rep["mintrl"] = pa["mintrl"](r)
yr = pd.Series(r, index=[x[0] for x in r0])
rep["by_year"] = {int(y): dict(n=int(len(v)), pf=round(pf(v.values), 2), sum_pct=round(float(v.sum() * 100), 1)) for y, v in yr.groupby(yr.index.year)}
rep["neighbours"] = {str(k): round(pf(rx(run(n=k))), 3) for k in (5, 15, 20, 25, 30, 35, 40, 45, 60)}
mo = sorted({str(x[0])[:7] for x in r0})
Mx = np.zeros((len(mo), 4))
for j, k in enumerate((5, 15, 30, 45)):
    for x in run(n=k):
        Mx[mo.index(str(x[0])[:7]), j] += x[6]
rep["pbo_4_windows"] = pa["cscv"](Mx)
gs = rng.choice(len(r0), 20, replace=False)
gs.sort()
cells, rows, ok = [], [], 0
for i in gs:
    t = r0[i]
    b_, e_ = t[7], t[8]
    d = np.flatnonzero((day == day[b_]) & sess)
    pre = d[mn[d] < 600]
    hi, lo = h[pre].max(), l[pre].min()
    chk = dict(first_bar_breaks=bool((h[b_] > hi) if t[1] > 0 else (l[b_] < lo)), none_earlier=bool(not ((h[d[(mn[d] >= 600) & (d < b_)]] > hi).any() or (l[d[(mn[d] >= 600) & (d < b_)]] < lo).any())), entry_is_edge=abs(t[2] - (hi if t[1] > 0 else lo)) < 1e-9, stop_is_other=abs(t[3] - (lo if t[1] > 0 else hi)) < 1e-9, flat_by_1600=bool(mn[e_] < 960))
    ok += all(chk.values())
    rows.append(dict(entry=str(t[0])[:16], side=t[1], entry_px=t[2], stop=t[3], exit=t[4], how="stop" if t[5] else "close", **chk))
    w = d[(d >= b_ - 45) & (d <= e_ + 15)]
    p = w - w[0]
    cells.append(sc["cell"](o[w], h[w], l[w], c[w], [(int(b_ - w[0]), sc["B"]), (int(e_ - w[0]), sc["P"])], [(hi, sc["O"]), (lo, sc["O"])]))
sc["sheet"].__globals__["HERE"] = HERE
sc["sheet"]("SC-1-ORB30", cells)
pd.DataFrame(rows).to_csv(HERE + "/SC-1-ORB30.csv", index=False)
rep["spot"] = f"{ok}/20"
print(json.dumps(rep, indent=0, default=float))
json.dump(rep, open(HERE + "/sc1_check.json", "w"), indent=1, default=float)
