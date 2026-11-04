"""Copies the rest of the inputs into the sandboxes from the originals, read only. tools/sandbox_extra.txt lists them as sandbox|path. Run before sandbox_paths.py so paths get rewritten."""
import os
import shutil

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = "@GANN_ROOT@"
n = 0
for x in open(os.path.join(HERE, "tools", "sandbox_extra.txt"), encoding="utf-8"):
    x = x.strip()
    if not x:
        continue
    b, r = x.split("|")
    t = os.path.join(HERE, "_copy", b, r)
    if not os.path.exists(f"{G}/{r}"):
        continue
    os.makedirs(os.path.dirname(t), exist_ok=True)
    shutil.copy(f"{G}/{r}", t)
    n += 1
shutil.copy(os.path.join(HERE, "phaseC", "combo5.py"), os.path.join(HERE, "_copy", "rs_recorded", "research", "cross_market"))
print(n, "files copied")
