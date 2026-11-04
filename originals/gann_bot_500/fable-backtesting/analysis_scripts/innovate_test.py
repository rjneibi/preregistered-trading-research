"""Round-2 TEST validation + overshoot-filter variants."""
import json
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1, resample_ohlc
from innovate_r3s3 import SimX, r3s3_level, stats, OUT

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
h4 = resample_ohlc(m1, "4h")
sim = SimX(m1, h4)

ev = [json.loads(l) for l in (OUT / "events.jsonl").read_text().splitlines()]
ev.sort(key=lambda x: x["entry_ts"])
base = [e for e in ev if {"R3", "S3"} & set(e["zone_sources"])
        and pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]
cut = int(round(len(base) * 0.7))
train, test = base[:cut], base[cut:]

def overshoot(e):
    return abs(e["h4_close"] - r3s3_level(e)) / max(e["atr_at_build"], 1e-9)

CAND = {
    "FINAL_v1 (ref)": (dict(), None),
    "pyramid +4": (dict(pyramid_at=4.), None),
    "pyramid +4 trail8/5": (dict(tp=None, trail_arm=8., trail_dist=5.,
                                 pyramid_at=4.), None),
    "trail arm4/dist4": (dict(tp=None, trail_arm=4., trail_dist=4.), None),
    "re-entry after SL": (dict(reenter=True), None),
    "FINAL_v1 + overshoot<1.5": (dict(), 1.5),
    "pyramid+4 + overshoot<1.5": (dict(pyramid_at=4.), 1.5),
}
for split, evs in [("TRAIN", train), ("TEST", test)]:
    rows = []
    for name, (kw, ov_max) in CAND.items():
        sel = [e for e in evs if ov_max is None or overshoot(e) <= ov_max]
        pnls = [sim.run(e, level=r3s3_level(e), **kw) for e in sel]
        rows.append(stats(name, pnls))
    print(f"=== {split} (n={len(evs)}) ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print()
