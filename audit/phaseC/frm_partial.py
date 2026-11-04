"""FR-M on the cost matrix of its own date. The stored run predates the full-tick matrix (07-06 vs 07-07), so the partial matrix from commit 977fff5 reproduces it. Arg: clock."""
import json
import os
import runpy
import sys
from pathlib import Path

clock = sys.argv[1]
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "_copy" / f"sb_fable_{clock}"
os.chdir(ROOT)
g = runpy.run_path(str(ROOT / "research/fleet_review/micro_grid_backtest.py"), run_name="fr")
m = g["main"]
m.__globals__["MATRIX"] = HERE.parent / "_copy" / "cost_matrix_partial.json"
m.__globals__["OUT"] = HERE / f"frm_partial_{clock}.json"
m.__globals__["DECISIONS"] = HERE / "logs_L1" / f"frm_partial_{clock}.decisions"
sys.exit(m())
