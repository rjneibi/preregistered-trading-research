import glob
import json
import os
import re

import numpy as np
import pandas as pd

A = "../_copy/sb_%s/research/goldbot/results/"
for c in ("recorded", "true"):
    h = json.load(open(A % c + "H2_050.json"))
    print(c, "H2", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items() if not isinstance(v, (dict, list))}, str(h.get("median", h.get("table", "")))[:300])
    hs = json.load(open(A % c + "HS_run.json"))
    print(c, "HS", hs.get("winner"), {k: v for k, v in hs.items() if "oos" in k.lower() or "gates" in k}, str(hs.get("winner_stats", ""))[:300])
    hv = json.load(open(A % c + "HV_run.json"))
    print(c, "HV", str(hv)[:420])
    sz = json.load(open(A % c + "SZ_run.json"))
    print(c, "SZ", sz["onelot_pf"])
    hp = json.load(open(A % c + "HP_run.json"))
    print(c, "HP", {k: {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()} for k, v in hp.items() if isinstance(v, dict) and k.startswith("port")} or str(hp)[:360])
for c in ("recorded", "true"):
    p = f"../_copy/sb_fable_{c}/research/flip_scalp/grid_summary.json"
    g = json.load(open(p))
    print(c, "flip", list(g)[:5] if isinstance(g, dict) else type(g))
    tx = open(f"logs_L1/{c}.run_flip_scalp.log", encoding="utf-8", errors="ignore").read().splitlines()
    print("\n".join(x[:120] for x in tx if "headline" in x.lower() or "all" in x.lower())[:500])
    r = open(f"../_copy/sb_fable_{c}/research/flip_scalp/flip_scalp_report.md", encoding="utf-8", errors="ignore").read()
    print("\n".join(x[:130] for x in r.splitlines() if x.startswith("|"))[:900])
auc = [float(x) for x in re.findall(r"OOS AUC ([0-9.]+)", open("logs_L1/recorded.d_revival.ml_lab_py.log", errors="ignore").read())]
print("ML AUC mean", round(np.mean(auc), 3), len(auc), re.findall(r"shuffled.*AUC.*|mean.*AUC.*", open("logs_L1/recorded.d_revival.ml_lab_py.log", errors="ignore").read())[:3])
print(open("logs_L1/recorded.d_revival.diag_py.log", errors="ignore").read()[:600])
for f in sorted(glob.glob("@GANN_ROOT@/research/fx_backtest/results/trades_[DR]_*.csv"))[:6]:
    t = pd.read_csv(f)
    c = [x for x in t.columns if "pnl" in x.lower()]
    r = t[c[0]].values.astype(float)
    print(os.path.basename(f), c[:3], len(r), round(r[r > 0].sum() / -r[r < 0].sum(), 3))
