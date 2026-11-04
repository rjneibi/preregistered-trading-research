"""Third goldbot sandbox: recorded clock with the partial-coverage cost matrix from commit 977fff5, and a true-clock guard patch."""
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy"))
RAW = "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"
m = open("@GANN_ROOT@/research/goldbot/results/cost_matrix_977fff5.json", "rb").read()
open(os.path.join(COPY, "cost_matrix_partial.json"), "wb").write(m)
root = os.path.join(COPY, "sb_partial", "research", "goldbot")
assert not os.path.exists(os.path.dirname(os.path.dirname(root))), "sb_partial already exists"
shutil.copytree(os.path.join(COPY, "goldbot"), root, ignore=shutil.ignore_patterns("__pycache__"))
shutil.copytree(os.path.join(COPY, "flip", "calendar"), os.path.join(COPY, "sb_partial", "fable-backtesting", "calendar"))
open(os.path.join(root, "results", "cost_matrix.json"), "wb").write(m)
c = os.path.join(root, "config.yaml")
s = open(c, encoding="utf-8").read()
open(c, "w", encoding="utf-8").write(re.sub(r"m1_path:\s*\S+", "m1_path: " + RAW, s, count=1))
h = os.path.join(COPY, "sb_true", "research", "goldbot", "prereg", "hm_runner.py")
s = open(h, encoding="utf-8").read()
open(h, "w", encoding="utf-8").write(s.replace('assert len(trades) == 472, f"trade-set drift: {len(trades)} != 472"', 'assert len(trades) == 481, f"trade-set drift: {len(trades)} != 481"'))
print("ok", len(m))
