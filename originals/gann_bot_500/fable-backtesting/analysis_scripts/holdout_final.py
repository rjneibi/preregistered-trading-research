"""FINAL EXAM: 2015-2021 virgin holdout for the tuned R3+S3 flip scalp."""
import json
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1
from tune_r3s3 import Sim, stats_row, OUT

# calibration: mean entry price of the 2021-2026 tuning events (no-Mon R3/S3)
tune_ev = [json.loads(l) for l in (OUT / "events.jsonl").read_text().splitlines()]
tune_ev = [e for e in tune_ev if {"R3", "S3"} & set(e["zone_sources"])
           and pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]
P0 = sum(e["h4_close"] for e in tune_ev) / len(tune_ev)
print(f"calibration price P0 (2021-26 mean entry) = {P0:.0f}")

hold = [json.loads(l) for l in
        (OUT / "events_2015_2021.jsonl").read_text().splitlines()]
hold.sort(key=lambda x: x["entry_ts"])
hold = [e for e in hold if {"R3", "S3"} & set(e["zone_sources"])]
mon = [e for e in hold if pd.Timestamp(e["entry_ts"]).strftime("%a") == "Mon"]
nomon = [e for e in hold if pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]
print(f"holdout R3/S3 events: {len(hold)}  no-Mon={len(nomon)} Mon={len(mon)}")

rfs.BT_START = pd.Timestamp("2015-06-19T00:00:00Z")
rfs.BT_END = pd.Timestamp("2021-06-18T23:59:00Z")
rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=45), rfs.BT_END)
sim = Sim(m1)

def run_scaled(events, tp8, sl12, ts=None, scaled=True):
    out = []
    for e in events:
        k = (e["h4_close"] / P0) if scaled else 1.0
        out.append(sim.run(e, entry="market", tp_usd=tp8 * k, sl_usd=sl12 * k,
                           time_stop_h=ts))
    return out

rows = []
rows.append(stats_row("TP8_SL12_ts24h price-scaled",
                      run_scaled(nomon, 8., 12., 24)))
rows.append(stats_row("TP8_SL12 price-scaled", run_scaled(nomon, 8., 12.)))
rows.append(stats_row("TP10_SL10_ts24h price-scaled",
                      run_scaled(nomon, 10., 10., 24)))
rows.append(stats_row("TP10_SL10 price-scaled", run_scaled(nomon, 10., 10.)))
rows.append(stats_row("TP8_SL12_ts24h raw-$ (unscaled)",
                      run_scaled(nomon, 8., 12., 24, scaled=False)))
rows.append(stats_row("MONDAYS-ONLY TP8_SL12_ts24h scaled",
                      run_scaled(mon, 8., 12., 24)))
print("\n=== VIRGIN HOLDOUT 2015-2021 (no-Monday R3/S3 unless noted) ===")
print(pd.DataFrame(rows).to_string(index=False))

# year-by-year for the headline candidate
res = run_scaled(nomon, 8., 12., 24)
d = pd.DataFrame([{"year": e["entry_ts"][:4], "pnl": r["pnl"]}
                  for e, r in zip(nomon, res) if r["pnl"] is not None])
print("\nheadline candidate per year (net $ at 1 lot):")
print((d.groupby("year").pnl.agg(["count", "sum"]) / [1, 100 / 100]
       ).round(0).rename(columns={"sum": "net_pts"}))
d["usd"] = d.pnl
print("wr by year:")
print(d.assign(win=d.pnl > 0).groupby("year").win.mean().round(3))
