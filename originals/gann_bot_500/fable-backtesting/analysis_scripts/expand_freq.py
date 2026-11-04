"""Round 5: trade-frequency expansion. Add R2/S2 flips to FINAL_v3
(session+noMon+ATR exits), day-cap variants. Both eras + 2025 slice."""
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1, resample_ohlc
from research.dr_backtest.metrics import basic_stats
from innovate_r3s3 import SimX, stats
import json

def load_events(fname):
    p = REPO / "research" / "flip_scalp" / fname
    ev = [json.loads(l) for l in p.read_text().splitlines()]
    ev.sort(key=lambda x: x["entry_ts"])
    return [e for e in ev
            if pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]

def lvl(e, srcs):
    for s, l in zip(e["zone_sources"], e["zone_levels"]):
        if s in srcs:
            return l
    return e["zone_levels"][0]

all_rows = {}
y2025 = {}
for era in ("old", "new"):
    if era == "new":
        start, end, fname = (pd.Timestamp("2021-06-19T00:00:00Z"),
                             pd.Timestamp("2026-06-19T17:57:00Z"),
                             "events.jsonl")
    else:
        start, end, fname = (pd.Timestamp("2015-06-19T00:00:00Z"),
                             pd.Timestamp("2021-06-18T23:59:00Z"),
                             "events_2015_2021.jsonl")
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    m1 = load_m1(start - pd.Timedelta(days=60), end)
    sim = SimX(m1, resample_ohlc(m1, "4h"))
    ev = [e for e in load_events(fname)
          if pd.Timestamp(e["entry_ts"]).hour in (12, 16, 20)]

    VARIANTS = {
        "v3 ref (R3/S3, 1/day)": ({"R3", "S3"}, 1),
        "+R2/S2, 1/day": ({"R2", "S2", "R3", "S3"}, 1),
        "+R2/S2, 2/day": ({"R2", "S2", "R3", "S3"}, 2),
        "+R2/S2, no cap": ({"R2", "S2", "R3", "S3"}, 99),
    }
    rows = []
    for name, (srcs, cap) in VARIANTS.items():
        day_n = {}
        res, res25 = [], []
        for e in ev:
            if not (srcs & set(e["zone_sources"])):
                continue
            d = pd.Timestamp(e["entry_ts"]).date()
            if day_n.get(d, 0) >= cap:
                continue
            day_n[d] = day_n.get(d, 0) + 1
            p = sim.run(e, tp=1.4 * e["atr_at_build"],
                        sl=2.1 * e["atr_at_build"], level=lvl(e, srcs))
            res.append(p)
            if e["entry_ts"].startswith("2025"):
                res25.append(p)
        rows.append(stats(f"{name}", res))
        if era == "new":
            s25 = basic_stats([x for x in res25 if x is not None])
            y2025[name] = (s25["n"], s25["win_rate"], s25["pf"],
                           round(sum(x for x in res25 if x is not None), 0))
    print(f"\n=== era {era} ===")
    print(pd.DataFrame(rows).to_string(index=False))

print("\n=== 2025 slice (n, wr, pf, net$@1lot) ===")
for k, v in y2025.items():
    print(f"{k:>24}: n={v[0]} wr={v[1]} pf={v[2]} net=${v[3]:,.0f}")
