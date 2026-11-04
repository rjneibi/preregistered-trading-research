"""Fills the path tokens in a clean clone, so the committed tree holds no absolute path. Runs only inside the clone. Usage: render_paths.py <clone>"""
import os
import sys

root = os.path.abspath(sys.argv[1]).replace(os.sep, "/")
data = os.path.abspath(os.environ["DATA_DIR"]).replace(os.sep, "/")
TOK = [
    ("@GANN_ROOT@/fable-backtesting/download", f"{data}/gann_bot_500/fable-backtesting/download"),
    ("@GANN_ROOT@", f"{root}/originals/gann_bot_500"),
    ("@LBO_ROOT@", f"{root}/originals/london-breakout"),
    ("@AUDIT@", f"{root}/audit"),
]
EXT = (".py", ".sh", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".json")
n = 0
for top in ("audit", "originals"):
    for d, sub, fs in os.walk(os.path.join(root, top)):
        sub[:] = [x for x in sub if not x.startswith(".venv") and x != "__pycache__"]
        for f in fs:
            if not f.endswith(EXT) or f in ("render_paths.py", "check_hashes.py"):
                continue
            p = os.path.join(d, f)
            s = open(p, encoding="utf-8", errors="surrogateescape", newline="").read()
            if "@" not in s:
                continue
            t = s
            for a, b in TOK:
                t = t.replace(a, b)
            if t != s:
                open(p, "w", encoding="utf-8", errors="surrogateescape", newline="").write(t)
                n += 1
print("rendered", n)
