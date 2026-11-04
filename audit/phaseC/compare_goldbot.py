"""Original outputs vs recorded-clock rerun vs true-UTC rerun, for the goldbot runners. Numbers only."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
O = "@GANN_ROOT@/research/goldbot/results"
A = os.path.join(HERE, "..", "_copy", "sb_recorded", "research", "goldbot", "results")
B = os.path.join(HERE, "..", "_copy", "sb_true", "research", "goldbot", "results")
FILES = ["H1_rerun.json", "H2_050.json", "H2_plateau.json", "H2_mechanism.json", "HN_run.json", "HP_run.json", "HB_run_binding.json", "SZ_run.json", "HV_run.json", "HR_is_manifest.json", "HR_oos_run.json", "HCRT_run.json", "HSW_run.json", "HM_run.json", "HS_run.json"]


def flat(x, p=""):
    out = {}
    if isinstance(x, dict):
        for k, v in x.items():
            out.update(flat(v, f"{p}.{k}" if p else str(k)))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            out.update(flat(v, f"{p}[{i}]"))
    else:
        out[p] = x
    return out


def load(d, f):
    p = os.path.join(d, f)
    return flat(json.load(open(p))) if os.path.exists(p) else None


rep = {}
for f in FILES:
    o, a, b = load(O, f), load(A, f), load(B, f)
    if o is None or a is None:
        rep[f] = dict(status="missing", orig=o is not None, rerun=a is not None, true=b is not None)
        print(f, rep[f])
        continue
    keys = sorted(set(o) | set(a))
    diff = []
    same = 0
    for k in keys:
        x, y = o.get(k), a.get(k)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            ok = (x == y) or (x != 0 and abs(y / x - 1) < 0.005) or (abs(x - y) < 1e-9)
        else:
            ok = x == y
        if ok:
            same += 1
        else:
            diff.append((k, x, y))
    rep[f] = dict(keys=len(keys), same=same, n_diff=len(diff), diff=diff[:40], true={k: (o.get(k), a.get(k), (b or {}).get(k)) for k in keys if b is not None and isinstance(a.get(k), (int, float, bool)) and a.get(k) != b.get(k)})
    print(f, "keys", len(keys), "same", same, "diff", len(diff), diff[:6])
json.dump(rep, open(os.path.join(HERE, "goldbot_compare.json"), "w"), indent=1, default=str)
vo = pd.read_csv(O + "/verdict_trades.csv")
va = pd.read_csv(A + "/verdict_trades.csv")
print("verdict_trades", len(vo), len(va), "gross same", bool(len(vo) == len(va) and np.allclose(vo.gross_usd, va.gross_usd)), "net sum", round(vo.net_med.sum(), 2), round(va.net_med.sum(), 2))
