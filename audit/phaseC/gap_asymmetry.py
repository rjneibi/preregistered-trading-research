"""B3: does giving targets the same gap treatment as stops change LBO-1 or CRT-FVG-1?

Stored trades, same entries, same exits, frozen selection. Only change: a target that the bar opens through fills at that open.
That is the favourable side the engines left out. A count of affected trades and the new stats per cell are written out.
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LBO = "@LBO_ROOT@"
CRT = "@GANN_ROOT@/research/crt_fvg/results"


def stat(r):
    r = np.asarray(r, float)
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), avg=round(float(r.mean()), 4), pf=round(float(w / l), 3) if l else None, t=round(float(r.mean() / r.std(ddof=1) * np.sqrt(len(r))), 2) if len(r) > 1 else None)


def m1(p):
    z = np.load(p)
    return {k: z[k] for k in z.files}


rep = {}
# LBO
fr = json.load(open(LBO + "/strategy/frozen_config.json")) if os.path.exists(LBO + "/strategy/frozen_config.json") else None
print("frozen", {k: fr[k] for k in list(fr)[:8]} if fr else None)
rr = None
for key in ("rr", "RR", "reward_risk"):
    if fr and key in fr:
        rr = float(fr[key])
if rr is None and fr:
    for v in fr.values():
        if isinstance(v, dict) and "rr" in v:
            rr = float(v["rr"])
t = pd.read_csv(LBO + "/results/oos_final_trades_k1.csv")
print("rr", rr, "reasons", t.why.value_counts().to_dict())
out = t.R.values.copy()
hits = 0
for inst, g in t.groupby("inst"):
    m = m1(f"{LBO}/data/m1/{inst}.npz")
    sp = m.get("sp", m.get("spread"))
    o = m.get("o", m.get("open"))
    for ix, x in g[g.why == 1].iterrows():
        j = int(x.exit_i)
        d = int(x.dir)
        tgt = d * x.planned + rr * x.risk
        op = d * o[j] - sp[j] / 2
        if op > tgt:
            out[t.index.get_loc(ix)] += (op - tgt) / x.risk
            hits += 1
rep["LBO-1 OOS frozen"] = dict(rr=rr, target_exits=int((t.why == 1).sum()), opened_through=hits, before=stat(t.R), after=stat(out))
print(rep["LBO-1 OOS frozen"])

# CRT
t = pd.read_csv(CRT + "/trades.csv")
print("crt periods", t.period.value_counts().to_dict(), t.why.value_counts().to_dict())
new = t.R.values.copy()
hits = 0
Z = {}
for sym, g in t[t.why == "target"].groupby("sym"):
    m = m1(f"{LBO}/data/m1/{sym}.npz")
    tt = m["t"].astype(np.int64) if "t" in m else m["time"].astype(np.int64)
    if tt[0] > 10**8:
        tt = tt // 60
    o, sp = m["o"], m["sp"]
    ex = pd.to_datetime(g.exit_utc).values.astype("datetime64[m]").astype(np.int64)
    # exit stamp is the bar close, t[j] + 1 minute
    for ix, e, d, tg, en, stp in zip(g.index, ex, g.dir, g.target, g.entry, g.stop):
        j = int(np.searchsorted(tt, e - 1))
        if j >= len(tt) or tt[j] != e - 1:
            j = int(np.searchsorted(tt, e))
            if j >= len(tt) or tt[j] != e:
                continue
        op = o[j] - d * sp[j] / 2
        if d * (op - tg) > 0:
            new[t.index.get_loc(ix)] += d * (op - tg) / (d * (en - stp))
            hits += 1
t["R2"] = new
rep["CRT-FVG-1 hits"] = dict(target_exits=int((t.why == "target").sum()), opened_through=hits)
cells = []
for (tf, tp), g in t[t.period == "OOS"].groupby(["tf", "tp"]):
    cells.append(dict(tf=int(tf), tp=str(tp), before=stat(g.R), after=stat(g.R2)))
rep["CRT-FVG-1 OOS cells"] = cells
print(rep["CRT-FVG-1 hits"])
for c in cells:
    print(c)
json.dump(rep, open(os.path.join(HERE, "gap_asymmetry.json"), "w"), indent=1)
