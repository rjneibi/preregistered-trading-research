"""Round 13: asymmetric scale-in. Enter HALF at the flip; add the second
half only when price moves +0.4xATR in favor. All v5 COMBO exits unchanged
(shared TP/SL/bail/half-out/24h, computed from the FIRST fill). Mechanism:
losers fail fast at half size; winners confirm and carry full size.
Cost: 10 pts per leg (20 total when both legs fill)."""
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
from bail_exit_v5 import scan_entries

HOR_H = 24


class Sim6:
    def __init__(self, m1):
        self.t = m1.index.values
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)

    def run(self, e, scale_in=None):
        sign = 1 if e["dir"] == "BUY" else -1
        atr = e["atr"]
        i0 = self.t.searchsorted(np.datetime64(pd.Timestamp(e["ts"])))
        if i0 >= len(self.t):
            return None
        fill = self.o[i0]
        tp = fill + sign * 0.8 * atr
        sl = fill - sign * 2.4 * atr
        hivol = e["hivol"]
        half_px = fill - sign * 1.2 * atr          # hivol de-risk
        bail_px = fill - sign * 1.0 * atr          # lovol 8h bail
        add_px = fill + sign * scale_in * atr if scale_in else None
        i_bail = self.t.searchsorted(self.t[i0] + np.timedelta64(8, "h"))
        i_end = max(min(self.t.searchsorted(
            self.t[i0] + np.timedelta64(HOR_H, "h")), len(self.t)), i0 + 1)

        legs = [(fill, 0.5 if scale_in else 1.0)]
        added = scale_in is None
        derisked = False
        bank = 0.0

        def net_at(px):
            g = sum(f * sign * (px - ep) for ep, f in legs)
            n_legs = len(legs)
            return (bank + g) * 100 - 10.0 * (n_legs if scale_in else 2)

        for i in range(i0, i_end):
            hi, lo, cl = self.h[i], self.l[i], self.c[i]
            if not added and ((hi >= add_px) if sign > 0 else (lo <= add_px)):
                legs.append((add_px, 0.5))
                added = True
            if (lo <= sl) if sign > 0 else (hi >= sl):
                return net_at(sl)
            if (hi >= tp) if sign > 0 else (lo <= tp):
                return net_at(tp)
            if hivol and not derisked and \
                    ((cl <= half_px) if sign > 0 else (cl >= half_px)):
                bank += sum(0.5 * f * sign * (cl - ep) for ep, f in legs)
                legs = [(ep, f * 0.5) for ep, f in legs]
                derisked = True
            if (not hivol) and i >= i_bail and \
                    ((cl <= bail_px) if sign > 0 else (cl >= bail_px)):
                return net_at(cl)
        return net_at(self.c[i_end - 1])


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
    entries = scan_entries(start, end, m1, h1, h4, d1, wilder_atr(h1, 14))
    sim = Sim6(m1)
    windows = [(era, entries)]
    if era == "new":
        windows.append(("2026H1", [e for e in entries
                                   if e["ts"] >= "2026-01-01"]))
    for tag, evs in windows:
        for name, si in [("baseline", None), ("scale-in 0.4", 0.4),
                         ("scale-in 0.25", 0.25)]:
            p = pd.Series([x for x in (sim.run(e, si) for e in evs)
                           if x is not None])
            gw, gl = p[p > 0].sum(), p[p <= 0].sum()
            pf = round(gw / -gl, 2) if gl < 0 else 99
            cum = p.cumsum()
            print(f"{tag:>7} {name:>14}: n={len(p)} wr={(p > 0).mean():.0%} "
                  f"pf={pf} gross+=${gw:,.0f} gross-=${gl:,.0f} "
                  f"NET=${p.sum():,.0f} maxDD=${(cum.cummax()-cum).max():,.0f}")
