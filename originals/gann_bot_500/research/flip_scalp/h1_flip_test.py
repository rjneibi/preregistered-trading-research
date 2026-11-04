"""Round 6: H1-close flip granularity. Flip = first H1 close beyond an
unflipped R3/S3 level (baseline: last-10 H4 closes before midnight), H1 close
hour 12-20 UTC, no Monday, 1 trade/day, TP 1.4xATR / SL 2.1xATR / ts24h."""
import sys
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from innovate_r3s3 import SimX, stats

for era in ("old", "new"):
    if era == "new":
        start, end = (pd.Timestamp("2021-06-19T00:00:00Z"),
                      pd.Timestamp("2026-06-19T17:57:00Z"))
    else:
        start, end = (pd.Timestamp("2015-06-19T00:00:00Z"),
                      pd.Timestamp("2021-06-18T23:59:00Z"))
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    m1 = load_m1(start - pd.Timedelta(days=60), end)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    sim = SimX(m1, h4)

    res, res25 = [], []
    for day_open in d1.index[(d1.index >= start) & (d1.index <= end)]:
        if day_open.strftime("%a") == "Mon":
            continue
        built = rfs.build_day_zones(day_open, d1, h4, atr_h1, h1.index)
        if built is None:
            continue
        zones, atr = built
        live = [z for z in zones if z["source"] in ("R3", "S3")
                and not z["baseline_flipped"]]
        if not live:
            continue
        day_h1 = h1[(h1.index >= day_open) &
                    (h1.index < day_open + pd.Timedelta(days=1))]
        for open_ts, row in day_h1.iterrows():
            cursor = open_ts + pd.Timedelta(hours=1)
            if not (12 <= cursor.hour <= 20) or cursor > end:
                continue
            close = float(row["close"])
            hit = None
            for z in live:
                if z["side_orig"] == "support" and close < z["level"]:
                    hit = ("SELL", z)
                elif z["side_orig"] == "resistance" and close > z["level"]:
                    hit = ("BUY", z)
                if hit:
                    break
            if hit:
                e = {"entry_ts": cursor.isoformat(), "direction": hit[0],
                     "h4_close": close, "atr_at_build": atr}
                p = sim.run(e, tp=1.4 * atr, sl=2.1 * atr,
                            level=hit[1]["level"])
                res.append(p)
                if cursor.year == 2025:
                    res25.append(p)
                break                       # 1 trade/day
    print(f"era {era}:", stats("H1-flip v3", res))
    if era == "new":
        print("2025 slice:", stats("H1-flip 2025", res25))
