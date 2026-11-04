"""IS/OOS check for the R3/S3-only flip subset (TP$10/SL$10)."""
import json
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1
from research.dr_backtest.metrics import basic_stats

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
sim = rfs.M1Sim(m1)
events = [json.loads(l) for l in
          (REPO / "research/flip_scalp/events.jsonl").read_text().splitlines()]

for label, srcs in [("R3+S3", {"R3", "S3"}), ("R3 only", {"R3"}),
                    ("S3 only", {"S3"}), ("R2+R3+S2+S3", {"R2", "R3", "S2", "S3"})]:
    sub = [e for e in sorted(events, key=lambda x: x["entry_ts"])
           if srcs & set(e["zone_sources"])]
    trades = []
    for e in sub:
        r = sim.run(pd.Timestamp(e["entry_ts"]), e["direction"], 1000.0, 1000.0)
        if r["pnl_points"] is not None:
            trades.append({"ts": e["entry_ts"], "pnl": r["pnl_points"]})
    cut = int(round(len(trades) * 0.7))
    for lbl, part in [("ALL", trades), ("IS", trades[:cut]),
                      ("OOS", trades[cut:])]:
        s = basic_stats([t["pnl"] for t in part])
        print(f"{label:>12} {lbl:>4}: n={s['n']:>4} wr={s['win_rate']} "
              f"pf={s['pf']} exp={s['expectancy']}")
    print()
