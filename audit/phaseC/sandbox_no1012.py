"""Sandbox with the 2010-2012 bars removed from d_revival/m1.npz. Those years have no independent clock check. Everything else is unchanged, so these runs give the without-case for ASSUMED-CLOCK."""
import os
import shutil

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy")).replace(os.sep, "/")
src, dst = COPY + "/rs_recorded", COPY + "/rs_no1012"
assert not os.path.exists(dst)
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
n = 0
for r, _, fs in os.walk(dst):
    for f in fs:
        if f.endswith(".py"):
            p = os.path.join(r, f)
            t = open(p, encoding="utf-8", errors="surrogateescape").read()
            u = t.replace(src, dst)
            if u != t:
                open(p, "w", encoding="utf-8", errors="surrogateescape").write(u)
                n += 1
p = dst + "/research/d_revival/m1.npz"
z = np.load(p)
print(z.files, len(z[z.files[0]]))
t = z["t"]
print("t0", t[0], np.datetime64(int(t[0]), "s") if t[0] < 10**11 else t[0])
keep = t >= 1356998400
np.savez(p, **{k: z[k][keep] for k in z.files})
print("kept", int(keep.sum()), "of", len(t), "paths rewritten in", n)
