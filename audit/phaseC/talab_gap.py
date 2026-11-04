"""TA-LAB sandbox gap2: a stop fills at the bar open only on a real gap between bars (B2). The first version, sandbox gap, also caught stops crossed
inside the previous bar after the ladder moved, so it overstated losses and is not used. The US-date variant was dropped once the clock check below showed B4 false.
Also measures the B4 clock error against Dukascopy, by day."""
import json
import os
import shutil
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy")).replace(os.sep, "/")
sys.path.insert(0, HERE)
SRC = COPY + "/rs_recorded/research/ta_lab"
STOP = """            adverse = l[j] if sgn == 1 else h[j] + sp[j]
"""
GAP = """            if j > k:
                op = o[j] if sgn == 1 else o[j] + sp[j]
                pc = c[j - 1] if sgn == 1 else c[j - 1] + sp[j - 1]
                # a real gap: last bar closed on the safe side of the stop and this bar opened through it
                if sgn * (op - lock) <= 0 and sgn * (pc - lock) > 0:
                    res, jx = sgn * (op - px), j
                    break
            adverse = l[j] if sgn == 1 else h[j] + sp[j]
"""
LOAD = """    summer = [(_last_sunday(y, 3), _last_sunday(y, 10)) for y in years]
"""
USD = """    from clockfix import us_dst_bounds
    summer = [us_dst_bounds(y) for y in years]
"""
for name, loadfix in (("gap2", False),):
    dst = f"{COPY}/rs_{name}/research/ta_lab"
    assert not os.path.exists(dst), dst + " exists"
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("__pycache__"))
    p = dst + "/lab.py"
    s = open(p, encoding="utf-8").read()
    assert STOP in s and LOAD in s
    s = s.replace(STOP, GAP).replace('o, h, l, sp, t = d["o"], d["h"], d["l"], d["spread"], d["t"]', 'o, h, l, c, sp, t = d["o"], d["h"], d["l"], d["c"], d["spread"], d["t"]')
    if loadfix:
        s = s.replace(LOAD, USD).replace('import numpy as np\n\nDATA', f'import numpy as np\n\nimport sys\nsys.path.insert(0, "{HERE.replace(os.sep, "/")}")\n\nDATA', 1)
    open(p, "w", encoding="utf-8").write(s)
    for f in os.listdir(dst):
        if f.endswith(".py"):
            q = dst + "/" + f
            t = open(q, encoding="utf-8", errors="surrogateescape").read()
            u = t.replace(f"{COPY}/rs_recorded/research/ta_lab", dst)
            if u != t:
                open(q, "w", encoding="utf-8", errors="surrogateescape").write(u)
    print(name, "ok")

sys.path.insert(0, SRC)
import lab

z = np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
k_ = "t" if "t" in z.files else "time"
rt = z[k_].astype(np.int64) * (60 if int(z[k_][0]) < 10**8 else 1)
rc = z["c" if "c" in z.files else "close"].astype(float)
m15 = lab.load("M15")
d15 = (rt // 900) * 900
# Dukascopy M15 close = last M1 close in each quarter
last = np.flatnonzero(np.diff(d15))
bt, bc = d15[last], rc[last]
res = []
for d in range(int(m15["t"][0] // 86400), int(min(m15["t"][-1], rt[-1]) // 86400) + 1):
    if (d + 4) % 7 == 6:
        continue
    i, j = np.searchsorted(m15["t"], [d * 86400, (d + 1) * 86400])
    if j - i < 40:
        continue
    t, c = m15["t"][i:j], m15["c"][i:j]
    best = None
    for L in (-2, -1, 0, 1, 2):
        k = np.searchsorted(bt, t - L * 3600)
        k[k >= len(bt)] = len(bt) - 1
        ok = bt[k] == t - L * 3600
        if ok.sum() < 30:
            continue
        cc = float(np.corrcoef(np.diff(c[ok]), np.diff(bc[k[ok]]))[0, 1])
        if best is None or cc > best[1]:
            best = (L, cc)
    if best:
        res.append((d, best[0], best[1]))
a = np.array(res)
segs, s = [], 0
for i in range(1, len(a) + 1):
    if i == len(a) or a[i, 1] != a[s, 1]:
        segs.append((str(np.datetime64(int(a[s, 0]) * 86400, "s"))[:10], str(np.datetime64(int(a[i - 1, 0]) * 86400, "s"))[:10], int(a[s, 1]), i - s))
        s = i
print("days", len(a), "not zero", int((a[:, 1] != 0).sum()), "low corr", int((a[:, 2] < 0.5).sum()))
print(segs)
json.dump(dict(days=len(a), not_zero=int((a[:, 1] != 0).sum()), segments=segs), open(os.path.join(HERE, "talab_clock.json"), "w"), indent=1)
