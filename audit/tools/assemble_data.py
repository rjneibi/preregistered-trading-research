"""Copies the data files listed in data/manifest.csv from DATA_DIR into the clean clone and checks each SHA-256. Writes tools/data_check.json. Usage: assemble_data.py <clone> <DATA_DIR> <full|public>"""
import collections
import csv
import hashlib
import json
import os
import shutil
import sys

root, data, tier = sys.argv[1:4]
rows = list(csv.DictReader(open(os.path.join(root, "data", "manifest.csv"), encoding="utf-8")))
res = collections.defaultdict(collections.Counter)
bad, need = [], []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


for r in rows:
    if tier == "public" and r["access"] != "public":
        continue
    src = os.path.join(data, r["rel"])
    if not os.path.exists(src):
        res[r["group"]]["missing"] += 1
        if tier == "full" or r["access"] == "public":
            need.append(r["rel"])
        continue
    ok = sha(src) == r["sha256"]
    res[r["group"]]["same" if ok else "differs"] += 1
    if not ok:
        bad.append(r["rel"])
    if r["place"] == "copy":
        t = {"gann_bot_500": "originals/gann_bot_500", "london-breakout": "originals/london-breakout", "audit": "audit/_copy/data"}[r["rel"].split("/")[0]]
        t = os.path.join(root, t, r["rel"].split("/", 1)[1])
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copyfile(src, t)
json.dump(dict(groups={k: dict(v) for k, v in res.items()}, differs=bad, missing_required=need), open(os.path.join(root, "audit", "tools", "data_check.json"), "w", encoding="utf-8"), indent=1)
for k, v in sorted(res.items()):
    print(k, dict(v))
if need:
    print(len(need), "required files missing, first:", need[:5])
if bad:
    print(len(bad), "files differ from the audit's copy. Output hashes may not match. First:", bad[:5])
