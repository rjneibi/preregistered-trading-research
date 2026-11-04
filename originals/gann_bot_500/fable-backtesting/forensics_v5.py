"""
STATUS: RESEARCH-ONLY (2026-07-03). Round 9 — trade forensics on FINAL_v5.
Per-trade pre-entry features vs outcome; a pattern counts only if it points
the same way in BOTH eras. Features: direction, zone, entry hour, weekday,
hivol, overshoot (|close-level|/ATR), day extension (|close-day_open|/ATR),
room to next opposing zone (in ATR), news day (FOMC/NFP/CPI calendar),
D1 ADX(14). Outcome: FINAL_v5 COMBO exit pnl.
"""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))
sys.path.insert(0, str(REPO / "fable-backtesting"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from regime_switch import wilder_adx_d1
from bail_exit_v5 import Sim5, COST  # noqa: F401  (Sim5 has the v5 exits)

NEWS = {pd.Timestamp(d).date() for d in json.loads(
    (REPO / "fable-backtesting" / "calendar" / "news_days.json")
    .read_text())["days"]}

rows = []
for era, (start, end) in {
        "old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                pd.Timestamp("2021-06-18T23:59:00Z")),
        "new": (pd.Timestamp("2021-06-19T00:00:00Z"),
                pd.Timestamp("2026-06-19T17:57:00Z"))}.items():
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    m1 = load_m1(start - pd.Timedelta(days=100), end)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    atr_med = atr_h1.rolling(24 * 90, min_periods=200).median()
    adx = wilder_adx_d1(d1)
    sim = Sim5(m1)

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
        hivol = bool(np.isfinite(med) and atr > med)
        a_sub = adx[adx.index < day_open]
        adx_v = float(a_sub.iloc[-1]) if len(a_sub) else np.nan
        live = [z for z in zones if z["source"] in ("R3", "S3")
                and not z["baseline_flipped"]]
        if not live:
            continue
        d_open_px = float(d1.loc[day_open, "open"])
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
                sign = 1 if hit[0] == "BUY" else -1
                ahead = [z["level"] for z in zones
                         if sign * (z["level"] - close) > 0]
                room = (min(abs(l - close) for l in ahead) / atr
                        if ahead else 99.0)
                e = {"ts": cursor.isoformat(), "dir": hit[0], "atr": atr,
                     "hivol": hivol}
                kw = (dict(half_x=1.2) if hivol
                      else dict(bail_t=8, bail_x=1.0))
                p = sim.run(e, **kw)
                if p is None:
                    break
                rows.append({
                    "era": era, "ts": e["ts"], "dir": hit[0],
                    "zone": hit[1]["source"], "hour": cursor.hour,
                    "dow": cursor.strftime("%a"), "hivol": hivol,
                    "overshoot": abs(close - hit[1]["level"]) / atr,
                    "day_ext": abs(close - d_open_px) / atr,
                    "room": room, "news": cursor.date() in NEWS,
                    "adx": adx_v, "pnl": p, "win": p > 0})
                break

df = pd.DataFrame(rows)
df.to_csv(REPO / "fable-backtesting" / "forensics_trades.csv", index=False)
print(f"total trades: {len(df)}\n")


def pf(x):
    w = x[x > 0].sum()
    l = -x[x <= 0].sum()
    return round(w / l, 2) if l > 0 else float("inf")


def split_report(col, cats=None):
    print(f"--- {col} ---")
    for era in ("old", "new"):
        d = df[df.era == era]
        if cats is None:      # continuous -> median split
            m = d[col].median()
            buckets = {f"<= {m:.2f}": d[d[col] <= m],
                       f"> {m:.2f}": d[d[col] > m]}
        else:
            buckets = {str(c): d[d[col] == c] for c in cats}
        line = f"  {era}: "
        for name, b in buckets.items():
            if len(b) == 0:
                continue
            line += (f"[{name}: n={len(b)} wr={b.win.mean():.2f} "
                     f"pf={pf(b.pnl)} net=${b.pnl.sum():,.0f}]  ")
        print(line)


split_report("dir", ["BUY", "SELL"])
split_report("zone", ["R3", "S3"])
split_report("hour", sorted(df.hour.unique()))
split_report("dow", ["Tue", "Wed", "Thu", "Fri"])
split_report("hivol", [True, False])
split_report("news", [True, False])
split_report("overshoot")
split_report("day_ext")
split_report("room")
split_report("adx")

print("\n--- 15 worst trades (both eras) ---")
cols = ["era", "ts", "dir", "zone", "hour", "overshoot", "day_ext",
        "room", "news", "pnl"]
print(df.nsmallest(15, "pnl")[cols].round(2).to_string(index=False))
