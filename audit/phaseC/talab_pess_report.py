"""Compares every printed TA-LAB result line across gap2, pessA and pessB. Lines with `net` and `PF` are the rows; each row keeps its label."""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
L = os.path.join(HERE, "logs_talab")
ROW = re.compile(r"^(.*?)\bn\s+(\d+)\s+net\s+([+-][\d.]+)R\s+avg\s+([+-][\d.]+)R\s+PF\s+([\d.]+)")
rep, summary = {}, {}
for f in sorted(glob.glob(os.path.join(L, "gap2.round*.log"))):
    key = os.path.basename(f)[5:-4]
    rows = {}
    for v in ("gap2", "pessA", "pessB"):
        out, seen = {}, {}
        for x in open(os.path.join(L, f"{v}.{key}.log"), encoding="utf-8", errors="ignore"):
            m = ROW.match(x.strip())
            if m:
                lab = m.group(1).strip()
                seen[lab] = seen.get(lab, 0) + 1
                out[f"{lab}#{seen[lab]}"] = (int(m.group(2)), float(m.group(3)), float(m.group(5)))
        rows[v] = out
    tab, pos_before, pos_after = [], 0, 0
    for k, a in rows["gap2"].items():
        pa, pb = rows["pessA"].get(k), rows["pessB"].get(k)
        if not pa or not pb:
            continue
        worst = min(pa[1], pb[1])
        tab.append(dict(label=k, n=a[0], stock_net=a[1], stock_pf=a[2], pessA_net=pa[1], pessA_pf=pa[2], pessB_net=pb[1], pessB_pf=pb[2], worst_net=worst))
        pos_before += a[1] > 0
        pos_after += worst > 0
    rep[key] = tab
    if tab:
        summary[key] = dict(rows=len(tab), stock_positive=pos_before, worst_positive=pos_after, sum_stock=round(sum(t["stock_net"] for t in tab), 1), sum_worst=round(sum(t["worst_net"] for t in tab), 1),
                            newly_positive=[t["label"] for t in tab if t["worst_net"] > 0 and t["stock_net"] <= 0])
json.dump(dict(summary=summary, rows=rep), open(os.path.join(HERE, "talab_pess.json"), "w"), indent=1)
print(json.dumps(summary, indent=1))
for t in rep.get("round12_py", []):
    print(t)
