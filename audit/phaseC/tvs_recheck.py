"""TVS-1. phase2.py seeds its grid from hash((asset, tf)), which is salted per process, so the stored search cannot be replayed. This re-evaluates the stored top 20 and a seeded 1,000-row sample of the stored configs, cell by cell, and compares metrics."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "_copy", "tvsearch", "src"))
sys.path.insert(0, SRC)
os.chdir(SRC)
import common
import phase2 as P

O = "@GANN_ROOT@/research/tvsearch/results/"
run = pd.read_csv(O + "all_runs.csv.gz")
top = pd.read_csv(O + "phase2_top20.csv")
pick = pd.concat([run.merge(top[["asset", "tf", "cfg"]], on=["asset", "tf", "cfg"]), run.sample(1000, random_state=7)]).drop_duplicates(["asset", "tf", "cfg"])
keys = ("is_n", "is_net", "oos_n", "oos_net", "oos_pf", "oos_sharpe", "is_sharpe")
rep, bad = dict(checked=0, exact=0, by_cell={}), []
for (a, tf), g in pick.groupby(["asset", "tf"]):
    D = common.dataset(a, tf, "long")
    C = {}
    split, edges = P.windows(D)
    ok = 0
    for _, x in g.iterrows():
        r = P.evaluate(json.loads(x.cfg), D, C, split, edges)
        rep["checked"] += 1
        same = r is not None and all((pd.isna(x[k]) and (r[k] is None or (isinstance(r[k], float) and not np.isfinite(r[k])))) or (x[k] == r[k]) or abs(float(x[k]) - float(r[k])) <= 1e-6 * max(1.0, abs(float(x[k]))) for k in keys if k in r)
        ok += bool(same)
        if not same and len(bad) < 5:
            bad.append(dict(cell=[a, tf], stored={k: x[k] for k in keys}, rerun=None if r is None else {k: r.get(k) for k in keys}))
    rep["exact"] += ok
    rep["by_cell"][f"{a} {tf}"] = [ok, len(g)]
    print(a, tf, ok, len(g), flush=True)
rep["mismatch_examples"] = bad
rep["stored_pass"] = 0
rep["stored_trials"] = len(run)
rerun = pd.read_csv(os.path.join(SRC, "..", "results", "phase2_top20.csv"))
rep["rerun_trials"] = len(pd.read_csv(os.path.join(SRC, "..", "results", "all_runs.csv.gz")))
rep["rerun_best_dsr"] = float(rerun.dsr.max())
rep["stored_best_dsr"] = float(top.dsr.max())
json.dump(rep, open(os.path.join(HERE, "tvs_recheck.json"), "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in rep.items() if k != "by_cell"}, default=str)[:900])
