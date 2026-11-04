"""Composite (pyramid + re-entry + overshoot) on train/test, then ONE virgin
holdout shot for FINAL_v2. Holdout uses price-scaled $ (P0=2531)."""
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

P0 = 2531.0

def overshoot(e):
    return abs(e["h4_close"] - r3s3_level(e)) / max(e["atr_at_build"], 1e-9)

def load(era):
    f = "events.jsonl" if era == "new" else "events_2015_2021.jsonl"
    ev = [json.loads(l) for l in (OUT / f).read_text().splitlines()]
    ev.sort(key=lambda x: x["entry_ts"])
    return [e for e in ev if {"R3", "S3"} & set(e["zone_sources"])
            and pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]

COMBOS = {
    "FINAL_v1 (ref)": (dict(), None),
    "pyr4 + reentry": (dict(pyramid_at=4., reenter=True), None),
    "pyr4 + reentry + ov<1.5": (dict(pyramid_at=4., reenter=True), 1.5),
    "pyr4 + ov<1.5": (dict(pyramid_at=4.), 1.5),
}

# ---- 2021-26 train/test --------------------------------------------------
rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
h4 = resample_ohlc(m1, "4h")
sim = SimX(m1, h4)
base = load("new")
cut = int(round(len(base) * 0.7))
for split, evs in [("TRAIN", base[:cut]), ("TEST", base[cut:])]:
    rows = []
    for name, (kw, ov) in COMBOS.items():
        sel = [e for e in evs if ov is None or overshoot(e) <= ov]
        rows.append(stats(name, [sim.run(e, level=r3s3_level(e), **kw)
                                 for e in sel]))
    print(f"=== {split} ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print()

# ---- virgin holdout, ONE shot: winner + ref ------------------------------
del sim, m1, h4
rfs.BT_START = pd.Timestamp("2015-06-19T00:00:00Z")
rfs.BT_END = pd.Timestamp("2021-06-18T23:59:00Z")
m1o = load_m1(rfs.BT_START - pd.Timedelta(days=45), rfs.BT_END)
h4o = resample_ohlc(m1o, "4h")
simo = SimX(m1o, h4o)
hold = load("old")
print(f"=== VIRGIN HOLDOUT 2015-21 (n={len(hold)}, price-scaled) ===")
rows = []
for name, (kw, ov) in COMBOS.items():
    sel = [e for e in hold if ov is None or overshoot(e) <= ov]
    pnls = []
    for e in sel:
        k = e["h4_close"] / P0
        kw2 = dict(kw)
        kw2["tp"] = 8.0 * k
        kw2["sl"] = 12.0 * k
        if "pyramid_at" in kw2:
            kw2["pyramid_at"] = 4.0 * k
        pnls.append(simo.run(e, level=r3s3_level(e), **kw2))
    rows.append(stats(name, pnls))
print(pd.DataFrame(rows).to_string(index=False))
