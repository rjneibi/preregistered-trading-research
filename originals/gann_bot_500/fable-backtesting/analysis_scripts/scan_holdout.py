"""Scan 2015-2021 flip events (virgin holdout window) -> events_2015_2021.jsonl"""
import json
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)

rfs.BT_START = pd.Timestamp("2015-06-19T00:00:00Z")
rfs.BT_END = pd.Timestamp("2021-06-18T23:59:00Z")   # disjoint from 2021-06-19+
rfs.apply_config()

m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)
print(f"[data] M1 bars: {len(m1):,}", flush=True)
h1 = resample_ohlc(m1, "1h")
h4 = resample_ohlc(m1, "4h")
d1 = resample_d1_utc(m1)
atr_h1 = wilder_atr(h1, 14)

events = rfs.collect_flip_events(m1, h1, h4, d1, atr_h1)
out = REPO / "research" / "flip_scalp" / "events_2015_2021.jsonl"
with open(out, "w") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")
print(f"wrote {out}: {len(events)} events")
