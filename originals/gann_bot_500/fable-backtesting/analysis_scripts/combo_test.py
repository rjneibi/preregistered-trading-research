"""Combo round: stack the two surviving improvements (TP8/SL12 + time stop)."""
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1
from tune_r3s3 import Sim, load_events, stats_row, OUT

COMBOS = {
    "mkt_TP10_SL10 (baseline)": dict(entry="market", tp_usd=10., sl_usd=10.),
    "mkt_TP8_SL12": dict(entry="market", tp_usd=8., sl_usd=12.),
    "mkt_TP10_SL10_ts24h": dict(entry="market", tp_usd=10., sl_usd=10.,
                                time_stop_h=24),
    "mkt_TP8_SL12_ts24h": dict(entry="market", tp_usd=8., sl_usd=12.,
                               time_stop_h=24),
    "mkt_TP8_SL12_ts12h": dict(entry="market", tp_usd=8., sl_usd=12.,
                               time_stop_h=12),
}

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
sim = Sim(m1)
ev = load_events(OUT / "events.jsonl")
cut = int(round(len(ev) * 0.7))
for split, e_s in [("TRAIN", ev[:cut]), ("TEST", ev[cut:])]:
    rows = [stats_row(k, [sim.run(e, **kw) for e in e_s])
            for k, kw in COMBOS.items()]
    print(f"=== {split} ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print()
