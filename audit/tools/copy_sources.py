"""First sandbox layer for a clean run. Copies code from the original folders, never writes there. Downloaded audit inputs come from the working audit's _copy/data, since the feeds change."""
import os
import shutil
import sys

SRC = sys.argv[1]
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(HERE, "_copy")
os.makedirs(os.path.join(C, "data"), exist_ok=True)
R = "@GANN_ROOT@/research"
IG = shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", ".pytest_cache", "node_modules")
shutil.copytree(R + "/goldbot", C + "/goldbot", ignore=IG)
os.makedirs(C + "/flip")
for f in ("flip_bot.py", "news_calendar.py", "portfolio_risk.py", "test_flip_bot_state.py"):
    p = "@GANN_ROOT@/fable-backtesting/" + f
    if os.path.exists(p):
        shutil.copy(p, C + "/flip")
shutil.copytree("@GANN_ROOT@/fable-backtesting/calendar", C + "/flip/calendar")
# Its OOS guard stops a rerun if the stored FULL grids are present. The sandbox rebuilds them.
shutil.copytree(R + "/crt_fvg", C + "/crt_fvg", ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", ".pytest_cache", "node_modules", "grid_FULL_*.pkl"))
shutil.copytree("@LBO_ROOT@", C + "/lbo", ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "node_modules", "tools", "raw", ".git"))
shutil.copytree(R + "/tvsearch", C + "/tvsearch", ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "results", "reports"))
os.makedirs(C + "/tvsearch/results", exist_ok=True)
shutil.copytree(HERE + "/tools/stubs", C + "/stubs")
os.makedirs(C + "/labelsizing")
for f in os.listdir(R + "/labelsizing_core"):
    if f.endswith((".py", ".md")):
        shutil.copy(R + "/labelsizing_core/" + f, C + "/labelsizing")
print("sources copied")
