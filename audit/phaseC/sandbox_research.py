"""Sandbox copies of the research folders. Code unchanged, data read in place or copied. Two clocks for the d_revival M1 file.

recorded: d_revival/m1.npz as stored.
true: the same bars with the HistData part moved to real broker time (UTC+2/+3 on US dates), which is what the file says it holds.
"""
import os
import shutil

import numpy as np

from clockfix import shifted, us_dst_bounds

HERE = os.path.dirname(os.path.abspath(__file__))
R = "@GANN_ROOT@/research"
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy"))
DIRS = ["cross_market", "ta_lab", "d_revival", "exit2", "gold_lit", "price_action", "pa_lab", "sweep_mtf", "tune1", "fleet_review", "powell", "dr_backtest", "vp_backtest", "market_context"]
IGN = shutil.ignore_patterns("__pycache__", "*.pyc", "trades_*.jsonl")


def broker_true(t):
    """HistData part: stored stamp - 2h = raw HistData stamp, which clockfix corrects to UTC; then the US-date broker offset."""
    raw = t - 7200
    utc = raw - shifted(raw).astype(np.int64) * 3600
    out = utc + 7200
    years = sorted(set(str(x)[:4] for x in utc[[0, -1]].astype("datetime64[s]")))
    for y in range(int(years[0]), int(years[-1]) + 1):
        a, b = us_dst_bounds(y)
        out[(utc >= a) & (utc < b)] += 3600
    return out


for clock in ("recorded", "true"):
    root = os.path.join(COPY, "rs_" + clock, "research")
    if os.path.exists(os.path.dirname(root)):
        shutil.rmtree(os.path.dirname(root))
    os.makedirs(root)
    for d in DIRS if clock == "recorded" else ["d_revival", "exit2", "gold_lit", "price_action", "sweep_mtf"]:
        ig = IGN if d != "cross_market" else shutil.ignore_patterns("__pycache__", "*.pyc", "data*")
        shutil.copytree(os.path.join(R, d), os.path.join(root, d), ignore=ig)
    print(clock, os.listdir(root))

p = os.path.join(COPY, "rs_true", "research", "d_revival", "m1.npz")
z = np.load(p)
d = {k: z[k] for k in z.files}
last_hist = 1781888220 + 7200
k = d["t"] <= last_hist
t = d["t"].copy()
t[k] = broker_true(t[k])
assert np.all(np.diff(t) > 0), "not sorted after the fix"
print("bars moved", int((t != d["t"]).sum()), "of", len(t))
d["t"] = t
np.savez(p, **d)
