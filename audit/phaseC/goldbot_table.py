"""Side-by-side table for the goldbot family: original stored value, partial-matrix rerun where relevant, recorded clock, true UTC."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
O = "@GANN_ROOT@/research/goldbot/results"
COPY = os.path.join(HERE, "..", "_copy")
P, A, B = [os.path.join(COPY, f"sb_{x}", "research", "goldbot", "results") for x in ("partial", "recorded", "true")]


def L(d, f):
    p = os.path.join(d, f)
    return json.load(open(p)) if os.path.exists(p) else {}


def gates(x):
    return {k: v for k, v in x.get("gates", {}).items()} if isinstance(x.get("gates"), dict) else x.get("gates")


for f in ("HN_run.json", "HP_run.json", "HB_run_binding.json", "SZ_run.json", "HV_run.json", "HR_oos_run.json", "HCRT_run.json", "HSW_run.json", "HM_run.json", "HS_run.json"):
    print("=====", f)
    for nm, d in (("orig", O), ("partial", P), ("recorded", A), ("true", B)):
        x = L(d, f)
        if not x:
            print(" ", nm, "-")
            continue
        s = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in x.items() if not isinstance(v, (dict, list))}
        print(" ", nm, json.dumps(s)[:430])
        g = gates(x)
        print("    gates", json.dumps(g)[:430])
