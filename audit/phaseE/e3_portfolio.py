"""E3, descriptive only. The trade_checks files hold only 20 sampled trades, so streams come from the same stats/pass_audit.py rule code that matched the originals exactly."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "..", "stats")
src = open(os.path.join(S, "pass_audit.py"), encoding="utf-8").read().replace("\nmain()\n", "\n")
pa = {"__file__": os.path.join(S, "pass_audit.py"), "__name__": "pa"}
exec(compile(src, "pass_audit", "exec"), pa)
SB = pa["SB"]
sys.path[:0] = [SB + "/cross_market", SB + "/tune1"]
import edge_lab
import tune_dip


def stream(tr, m, scale=1.0):
    t = m["t"]
    rows = {}
    for x in tr:
        i = int(np.searchsorted(t, x[0]))
        j = min(i + int(x[4]) + 1, len(t) - 1)
        d = pd.Timestamp(int(t[j]), unit="s").normalize()
        rows[d] = rows.get(d, 0.0) + float(x[3]) * scale
    return pd.Series(rows).sort_index()


us = pa["load"]("US500")
a = stream(pa["a1"](us), us)
b = stream(pa["ibs_rule"](us), us)
pool = []
for sym in tune_dip.HOLD_M:
    m = pa["load"](sym)
    sp = max(m["sp"], 0.0002 * float(np.median(m["c"])))
    pool.append(stream(pa["a1"](dict(m, sp=sp)), m, 1.0 / len(tune_dip.HOLD_M)))
c = pd.concat(pool, axis=1).sum(axis=1).sort_index()
f = edge_lab.f6()[0]
f.index = pd.to_datetime(f.index).tz_localize(None).normalize()
df = pd.concat({"XM-1-A1": a, "SW-1": b, "TUNE-1-DIP": c, "EDGE-1-F6": f}, axis=1)
df = df[df.index >= "2012-01-01"].sort_index()
idx = pd.date_range(df.index.min(), df.index.max(), freq="D")
df = df.reindex(idx).fillna(0.0)


def dd(r):
    eq = (1 + r).cumprod()
    return eq / eq.cummax() - 1


rep = dict(note="Descriptive only. No selection, no PASS. Weights use the full sample, so the combination is hindsight-scaled.", window=[str(idx[0].date()), str(idx[-1].date())], days=len(idx))
live = df[df.index >= f.index.min()]
rep["corr_daily_all"] = df.corr().round(3).to_dict()
rep["corr_daily_common_window"] = live.corr().round(3).to_dict()
rep["common_window_start"] = str(f.index.min().date())
ov = {}
for k in df:
    bad = df[k] <= df[k][df[k] < 0].quantile(0.1)
    ov[k] = {o: round(float((df.loc[bad, o] < 0).mean()), 3) for o in df if o != k}
rep["share_of_worst_decile_days_other_also_down"] = ov
dds = {k: dd(live[k]) for k in live}
ol = {}
for k in dds:
    deep = dds[k] <= dds[k].min() * 0.5
    ol[k] = {o: round(float((dds[o][deep] < -0.02).mean()), 3) for o in dds if o != k}
rep["share_of_deep_dd_days_other_also_in_dd_over_2pct"] = ol
vol = live.std()
w = (1 / vol) / (1 / vol).sum()
combo = (live * w).sum(axis=1)
rep["equal_risk_weights_full_sample"] = w.round(3).to_dict()


def stats(r):
    s = r[r != 0] if False else r
    return dict(sharpe_ann=round(float(s.mean() / s.std() * np.sqrt(365)), 2), max_dd=round(float(dd(s).min()), 3), total=round(float((1 + s).prod() - 1), 3))


rep["each_alone_common_window"] = {k: stats(live[k]) for k in live}
rep["equal_risk_combination"] = stats(combo)
json.dump(rep, open(os.path.join(HERE, "e3_result.json"), "w"), indent=1, default=str)
print(json.dumps(rep, indent=1, default=str))
