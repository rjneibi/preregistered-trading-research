"""Two sandboxes of the goldbot package, one per clock. Only the config m1_path differs. Runners, rules and costs are untouched."""
import os
import re
import shutil

import numpy as np
import pandas as pd

from clockfix import shifted

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.join(HERE, "..", "_copy")
RAW = "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"
TRUE = os.path.abspath(os.path.join(COPY, "data", "xauusd_m1_trueutc.csv"))

os.makedirs(os.path.dirname(TRUE), exist_ok=True)
if not os.path.exists(TRUE):
    df = pd.read_csv(RAW)
    assert df.time.dtype.kind in "iu" and df.time.iloc[0] > 10**9, "time column must be epoch seconds"
    df["time"] = df.time.values - shifted(df.time.values).astype(np.int64) * 3600
    df = df.sort_values("time", kind="stable").drop_duplicates("time")
    df.to_csv(TRUE, index=False)
    print("true csv", len(df), df.time.iloc[0], df.time.iloc[-1])

for name, path in (("recorded", RAW), ("true", TRUE.replace(os.sep, "/"))):
    root = os.path.join(COPY, "sb_" + name, "research", "goldbot")
    if os.path.exists(root):
        shutil.rmtree(os.path.join(COPY, "sb_" + name))
    shutil.copytree(os.path.join(COPY, "goldbot"), root, ignore=shutil.ignore_patterns("__pycache__"))
    cal = os.path.join(COPY, "sb_" + name, "fable-backtesting", "calendar")
    shutil.copytree(os.path.join(COPY, "flip", "calendar"), cal)
    c = os.path.join(root, "config.yaml")
    s = open(c, encoding="utf-8").read()
    s2 = re.sub(r"m1_path:\s*\S+", "m1_path: " + path, s, count=1)
    assert s2 != s
    open(c, "w", encoding="utf-8").write(s2)
    print(name, "ok")
