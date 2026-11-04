"""FX-TRANSFER recompute from stored trades, DR screen at the 20-point cost, and the H1 and H2 drawdowns. Reads copies and originals, writes l2_more.json."""
import glob
import json
import os

import numpy as np
import pandas as pd

rep = {}
fx = {}
s = {}
for f in glob.glob("@GANN_ROOT@/research/fx_backtest/results/summary_[DR]_*.json"):
    d = json.load(open(f))
    s[d["profile"] + "_" + d["symbol"]] = d
for f in sorted(glob.glob("@GANN_ROOT@/research/fx_backtest/results/trades_[DR]_*.csv")):
    t = pd.read_csv(f)
    k = os.path.basename(f)[7:-4]
    r = t.r_multiple.dropna().values.astype(float)
    pf = r[r > 0].sum() / -r[r < 0].sum()
    oos = t[t.in_sample.astype(str).str.lower().isin(["false", "no", "0"])].r_multiple.dropna().values.astype(float)
    fx[k] = dict(n=len(r), pf=round(float(pf), 3), stored_n=s[k]["full"]["n"], stored_pf=round(s[k]["full"]["pf"], 3), oos_n=len(oos), oos_pf=round(float(oos[oos > 0].sum() / -oos[oos < 0].sum()), 3), stored_oos_pf=round(s[k]["oos"]["pf"], 3))
rep["fx"] = fx
print(json.dumps(fx, indent=0)[:1500])
for c in ("recorded", "true"):
    S = f"../_copy/sb_fable_{c}/research/dr_backtest/"
    for prof in "DR":
        e = [json.loads(x) for x in open(S + f"trades_{prof}.jsonl") if x.strip()]
        if not rep.get("keys"):
            rep["keys"] = list(e[0])
            print(e[0])
        rep[f"dr {c} {prof} n"] = len(e)
    h = json.load(open(f"../_copy/sb_{c}/research/goldbot/results/H1_rerun.json"))
    print(c, str({k: v for k, v in h.items() if "dd" in k.lower() or k == "full"})[:300])
json.dump(rep, open("l2_more.json", "w"), indent=1)
