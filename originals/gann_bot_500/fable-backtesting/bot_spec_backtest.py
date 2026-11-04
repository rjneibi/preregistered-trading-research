"""Round 17: backtest flip_bot v1.1 EXACTLY as coded.
Entry: per day/direction, arm labels from H1-UTC closes 12-20 (12/16/20 =
'h4' label, others 'h1'); enter at the close where the SECOND label appears
(sustained-break conviction). Baseline dead check (last-10 UTC-H4 closes),
no Mondays, 1/direction/day, no new entry within 24h of the last (single
position). Exits: Sim5 combo (TP 0.8xATR / SL 2.4xATR, hivol half-out,
lovol 8h bail, ts24h). Costs 20pts. Fixed 1 lot for comparability."""
import sys
from pathlib import Path
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))
sys.path.insert(0, str(REPO / "fable-backtesting"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from research.dr_backtest.metrics import basic_stats
from bail_exit_v5 import Sim5

H4H = {12, 16, 20}
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
    sim = Sim5(m1)
    blocked_until = pd.Timestamp("2000-01-01T00:00:00Z")

    for day_open in d1.index[(d1.index >= start) & (d1.index <= end)]:
        if day_open.strftime("%a") == "Mon":
            continue
        built = rfs.build_day_zones(day_open, d1, h4, atr_h1, h1.index)
        if built is None:
            continue
        zones, atr = built
        pos = h1.index.searchsorted(day_open - pd.Timedelta(hours=1),
                                    side="right") - 1
        med = float(atr_med.iloc[pos]) if pos >= 0 else float("nan")
        hivol = bool(med == med and atr > med)
        live = {z["source"]: z for z in zones
                if z["source"] in ("R3", "S3") and not z["baseline_flipped"]}
        if not live:
            continue
        day_h1 = h1[(h1.index >= day_open) &
                    (h1.index < day_open + pd.Timedelta(days=1))]
        labels = {"BUY": set(), "SELL": set()}
        done = set()
        for open_ts, row in day_h1.iterrows():
            cursor = open_ts + pd.Timedelta(hours=1)
            if not (12 <= cursor.hour <= 20) or cursor > end:
                continue
            close = float(row["close"])
            for direc, src in (("BUY", "R3"), ("SELL", "S3")):
                z = live.get(src)
                if z is None or direc in done:
                    continue
                hit = (close > z["level"]) if direc == "BUY" \
                    else (close < z["level"])
                if not hit:
                    continue
                if cursor.hour in H4H:      # an H4-hour close IS both arms
                    labels[direc].update(("h4", "h1"))
                else:
                    labels[direc].add("h1")
                if len(labels[direc]) == 2 and cursor >= blocked_until:
                    e = {"ts": cursor.isoformat(), "dir": direc,
                         "atr": atr, "hivol": hivol}
                    kw = (dict(half_x=1.2) if hivol
                          else dict(bail_t=8, bail_x=1.0))
                    p = sim.run(e, **kw)
                    if p is not None:
                        rows.append({"era": era, "ts": e["ts"],
                                     "dir": direc, "hivol": hivol,
                                     "pnl": round(p, 0)})
                    done.add(direc)
                    blocked_until = cursor + pd.Timedelta(hours=24)

df = pd.DataFrame(rows)
df.to_csv(REPO / "fable-backtesting" / "bot_spec_trades.csv", index=False)
df["year"] = df.ts.str[:4]

def pf(x):
    w = x[x > 0].sum(); l = -x[x <= 0].sum()
    return round(w / l, 2) if l > 0 else 99.0

print("window,trades,wins,losses,winrate,pf,net,maxDD")
for tag, d in ([("old-era", df[df.era == "old"]),
                ("new-era", df[df.era == "new"]),
                ("2026H1", df[df.ts >= "2026-01-01"])] +
               [(y, df[df.year == y]) for y in sorted(df.year.unique())]):
    if not len(d):
        continue
    p = d.pnl
    cum = p.cumsum()
    print(f"{tag},{len(d)},{(p > 0).sum()},{(p <= 0).sum()},"
          f"{(p > 0).mean():.1%},{pf(p)},{p.sum():,.0f},"
          f"{(cum.cummax() - cum).max():,.0f}")
