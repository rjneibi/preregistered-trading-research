"""Point sys.path and runpy lines in the sandboxes at sandbox code, so no import can run or write inside an original folder. Data reads stay as they are."""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy")).replace(os.sep, "/")
ROOT = "@GANN_ROOT@"
for clock in ("recorded", "true"):
    base = f"{COPY}/rs_{clock}"
    n = 0
    for p in glob.glob(base + "/research/**/*.py", recursive=True):
        s = open(p, encoding="utf-8", errors="surrogateescape").read()
        lines = s.split("\n")
        for i, x in enumerate(lines):
            if "sys.path" in x or "run_path" in x:
                y = re.sub(r'r?"' + re.escape(ROOT) + r'/fable-backtesting"', f'"{base}/fable-backtesting"', x)
                y = re.sub(r'r?"' + re.escape(ROOT) + r'/research/([^"]*)"', lambda m: f'"{base}/research/{m.group(1).replace(chr(92), "/")}"', y)
                lines[i] = y
        t = "\n".join(lines)
        if t != s:
            open(p, "w", encoding="utf-8", errors="surrogateescape").write(t)
            n += 1
    print(clock, "patched", n)
