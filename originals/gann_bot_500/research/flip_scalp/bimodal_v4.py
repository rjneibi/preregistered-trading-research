"""
STATUS: RESEARCH-ONLY (2026-07-02). Round 7 — bimodal high-WR engineering.
Objectives (user): max win rate, minimal losers, more trades/month.
Entries: H1-close flips of R3/S3 (frequency arm), session 12-20 UTC,
no Monday, 1 trade/day. Geometries (TPxATR, SLxATR): high-WR candidates
(1.0,1.5) (1.0,2.5) (0.8,2.4) vs ref (1.4,2.1); all with 24h time stop.
Vol regime: ATR-at-build vs trailing 90-day median (high/low).
Tuning on NEW era per user; OLD era = validation.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from research.dr_backtest.metrics import basic_stats
from innovate_r3s3 import SimX

GEOS = {"ref_1.4/2.1": (1.4, 2.1), "hw_1.0/1.5": (1.0, 1.5),
        "hw_1.0/2.5": (1.0, 2.5), "hw_0.8/2.4": (0.8, 2.4)}

def stats_line(tag, pnls):
    p = [x for x in pnls if x is not None]
    if not p:
        return f"{tag}: n=0"
    s = basic_stats(p)
    return (f"{tag}: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
            f"net=${sum(p):,.0f}")

for era in ("new", "old"):
    if era == "new":
        start, end = (pd.Timestamp("2021-06-19T00:00:00Z"),
                      pd.Timestamp("2026-06-19T17:57:00Z"))
    else:
        start, end = (pd.Timestamp("2015-06-19T00:00:00Z"),
                      pd.Timestamp("2021-06-18T23:59:00Z"))
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    m1 = load_m1(start - pd.Timedelta(days=100), end)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    atr_med = atr_h1.rolling(24 * 90, min_periods=200).median()
    sim = SimX(m1, h4)

    # scan H1 flips once
    entries = []
    for day_open in d1.index[(d1.index >= start) & (d1.index <= end)]:
        if day_open.strftime("%a") == "Mon":
            continue
        built = rfs.build_day_zones(day_open, d1, h4, atr_h1, h1.index)
        if built is None:
            continue
        zones, atr = built
        pos = h1.index.searchsorted(day_open - pd.Timedelta(hours=1),
                                    side="right") - 1
        med = float(atr_med.iloc[pos]) if pos >= 0 else np.nan
        hivol = np.isfinite(med) and atr > med
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
                entries.append({"entry_ts": cursor.isoformat(),
                                "direction": hit[0], "h4_close": close,
                                "atr_at_build": atr, "level": hit[1]["level"],
                                "hivol": hivol})
                break
    n_hi = sum(1 for e in entries if e["hivol"])
    print(f"\n=== era {era}: {len(entries)} H1-flip entries "
          f"(hivol {n_hi}, lovol {len(entries) - n_hi}) ===")

    results = {}
    for gname, (tpm, slm) in GEOS.items():
        pnls = [(e, sim.run(e, tp=tpm * e["atr_at_build"],
                            sl=slm * e["atr_at_build"], level=e["level"]))
                for e in entries]
        results[gname] = pnls
        for regime in ("ALL", "HIVOL", "LOVOL"):
            sel = [p for e, p in pnls
                   if regime == "ALL" or (e["hivol"] == (regime == "HIVOL"))]
            print(" ", stats_line(f"{gname} {regime}", sel))
        if era == "new":
            p25 = [p for e, p in pnls if e["entry_ts"].startswith("2025")]
            print(" ", stats_line(f"{gname} 2025", p25))
