"""Sandboxes for the zone-flip family (XAU-FLIP-RAW, FINAL_v3, FINAL_v4), one per clock. Rules untouched. MetaTrader5 and matplotlib are empty stubs."""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = os.path.abspath(os.path.join(HERE, "..", "_copy")).replace(os.sep, "/")
G = "@GANN_ROOT@"
IGN = shutil.ignore_patterns("__pycache__", "*.pyc", "*.png", "trades_*.jsonl", "calendar")
for clock, data in (("recorded", G + "/research/data/xauusd_m1_histdata.csv"), ("true", COPY + "/data/xauusd_m1_trueutc.csv")):
    root = f"{COPY}/sb_fable_{clock}"
    assert not os.path.exists(root), root
    os.makedirs(root + "/research/data")
    for f in ("levels.py", "signals.py", "structure.py", "logsetup.py", "config.py"):
        shutil.copy(f"{G}/{f}", root)
    shutil.copytree(G + "/research/dr_backtest", root + "/research/dr_backtest", ignore=IGN)
    shutil.copytree(G + "/research/flip_scalp", root + "/research/flip_scalp", ignore=IGN)
    shutil.copytree(G + "/research/flip_scalp/calendar", root + "/research/flip_scalp/calendar")
    for f in os.listdir(G + "/fable-backtesting/analysis_scripts"):
        if f.endswith(".py"):
            s = open(f"{G}/fable-backtesting/analysis_scripts/{f}", encoding="utf-8", errors="surrogateescape").read()
            s = s.replace(r'Path(r"@GANN_ROOT@")', f'Path(r"{root}")')
            open(f"{root}/research/flip_scalp/{f}", "w", encoding="utf-8", errors="surrogateescape").write(s)
    shutil.copy(data, root + "/research/data/xauusd_m1_histdata.csv")
    os.makedirs(root + "/matplotlib")
    open(root + "/matplotlib/__init__.py", "w").write("def use(*a, **k):\n    pass\n")
    open(root + "/matplotlib/pyplot.py", "w").write("def __getattr__(n):\n    return lambda *a, **k: None\n")
    open(root + "/MetaTrader5.py", "w").write("# Stub. The audit never reaches a terminal.\nTIMEFRAME_H4 = 0\nTIMEFRAME_M5 = 0\n")
    print(clock, "ok")
