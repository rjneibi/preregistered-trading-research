"""FINAL_v3 = one-per-day + ATR exits (1.4/2.1) + equity-risk sizing."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import load_m1, resample_ohlc
from research.dr_backtest.metrics import basic_stats
from innovate_r3s3 import SimX, r3s3_level, stats
from regime_switch import load_events

seq = []
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
    seen, res = set(), []
    for e in ev:
        day = pd.Timestamp(e["entry_ts"]).date()
        if day in seen:
            continue
        seen.add(day)
        p = sim.run(e, tp=1.4 * e["atr_at_build"], sl=2.1 * e["atr_at_build"],
                    level=r3s3_level(e))
        res.append(p)
        seq.append({"ts": e["entry_ts"], "pnl": p,
                    "sl_d": 2.1 * e["atr_at_build"]})
    print(f"era {era}: ", stats("FINAL_v3", res))

seq.sort(key=lambda t: t["ts"])
pnl = np.array([t["pnl"] for t in seq])          # pts at 1 lot -> $ = pts
cum = pnl.cumsum()
mdd = float((np.maximum.accumulate(cum) - cum).max())
s = basic_stats(list(pnl))
print(f"\nPOOLED fixed 1 lot: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
      f"net=${pnl.sum():,.0f} maxDD=${mdd:,.0f}")

eq, peak, curve = 30000.0, 30000.0, []
for t in seq:
    frac = 0.01 if eq >= 0.95 * peak else 0.005
    lot = (eq * frac) / (t["sl_d"] * 100.0)
    eq += t["pnl"] * lot
    peak = max(peak, eq)
    curve.append(eq)
c = pd.Series(curve)
mdd_pct = float(((c.cummax() - c) / c.cummax()).max())
print(f"with equity-risk sizing (1%/0.5% governor, $30k start): "
      f"final=${c.iloc[-1]:,.0f} ({(c.iloc[-1] / 30000 - 1) * 100:.0f}% "
      f"over 11y)  maxDD={mdd_pct * 100:.1f}%")
