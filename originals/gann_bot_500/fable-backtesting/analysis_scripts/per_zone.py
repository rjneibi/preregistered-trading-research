"""Per-zone-source accuracy of the flip signal (which zones are trustworthy?).

Each deduped trade lists the zone sources that flipped on that H4 close; the
bar's outcome is attributed to every source in it. Two scores per source:
  * SCALP  — TP $10 / SL $10 outcome (symmetric race: does the flip direction
             win the next $10?)
  * NOSL   — TP $10, no stop, 30-day horizon (does it EVER print $10 first?)
Events are cached to research/flip_scalp/events.jsonl to skip the slow scan.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from research.dr_backtest.metrics import basic_stats

EV_CACHE = REPO / "research" / "flip_scalp" / "events.jsonl"

rfs.apply_config()
m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS), rfs.BT_END)

if EV_CACHE.exists():
    events = [json.loads(l) for l in EV_CACHE.read_text().splitlines()]
    print(f"[cache] {len(events)} events loaded", flush=True)
else:
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    events = rfs.collect_flip_events(m1, h1, h4, d1, atr_h1)
    with open(EV_CACHE, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

sim = rfs.M1Sim(m1)
ev = sorted(events, key=lambda x: x["entry_ts"])

scalp, nosl = [], []
for e in ev:
    ts = pd.Timestamp(e["entry_ts"])
    scalp.append({**e, **sim.run(ts, e["direction"], 1000.0, 1000.0)})
    nosl.append({**e, **sim.run(ts, e["direction"], 1000.0, None,
                                horizon_hours=720)})

by_src_scalp = defaultdict(list)
by_src_nosl = defaultdict(list)
by_src_dir = defaultdict(lambda: defaultdict(list))
for t_s, t_n in zip(scalp, nosl):
    for src in t_s["zone_sources"]:
        if t_s["pnl_points"] is not None:
            by_src_scalp[src].append(t_s["pnl_points"])
            by_src_dir[src][t_s["direction"]].append(t_s["pnl_points"])
        if t_n["pnl_points"] is not None:
            by_src_nosl[src].append(t_n["pnl_points"])

rows = []
for src in sorted(by_src_scalp, key=lambda s: -len(by_src_scalp[s])):
    s = basic_stats(by_src_scalp[src])
    n_ = basic_stats(by_src_nosl[src])
    b = basic_stats(by_src_dir[src].get("BUY", []))
    sl = basic_stats(by_src_dir[src].get("SELL", []))
    rows.append({
        "source": src, "n": s["n"],
        "scalp_wr": s["win_rate"], "scalp_pf": s["pf"],
        "scalp_exp": s["expectancy"],
        "nosl_wr": n_["win_rate"], "nosl_exp": n_["expectancy"],
        "buy_n": b["n"], "buy_pf": b["pf"],
        "sell_n": sl["n"], "sell_pf": sl["pf"],
    })
df = pd.DataFrame(rows)
print("\n=== per-zone-source flip accuracy (TP$10; pnl pts incl. costs) ===")
print(df.to_string(index=False))
df.to_csv(REPO / "research" / "flip_scalp" / "per_zone_accuracy.csv",
          index=False)
print("\nwrote research/flip_scalp/per_zone_accuracy.csv")
