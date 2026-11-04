"""
STATUS: RESEARCH-ONLY (2026-07-03). Round 8 — loss-compression engineering.
Problem (2026 H1): TP 0.8xATR / SL 2.4xATR gives 74-86% WR but each full SL
loss = 3 wins. Fix candidates (pre-registered, mechanism: a trade deep
underwater for hours is a failed break — exit before the full stop):

  BAIL(T,X): from T hours after entry, if the M1 close is worse than
             -X*ATR, exit at market. Hard SL/TP/ts24h unchanged.
  HALF(X):   when price first closes worse than -X*ATR, close half the
             position; remainder runs to SL/TP/timeout.

Variants: ref | bail(4h,1.0) | bail(8h,1.0) | bail(4h,1.4) | half(1.2).
Windows: 2015-21 era, 2021-26 era, 2026-H1 slice. Entries: FINAL_v4
(H1-close R3/S3 flip, 12-20 UTC, no Mon, 1/day). Costs 20 pts/trade.
"""
import json
import sys
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

OUT = REPO / "fable-backtesting"
COST = 20.0
HOR_H = 24


def scan_entries(start, end, m1, h1, h4, d1, atr_h1):
    atr_med = atr_h1.rolling(24 * 90, min_periods=200).median()
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
        hivol = bool(np.isfinite(med) and atr > med)
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
                entries.append({"ts": cursor.isoformat(), "dir": hit[0],
                                "atr": atr, "hivol": hivol})
                break
    return entries


class Sim5:
    def __init__(self, m1):
        self.t = m1.index.values
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)

    def run(self, e, bail_t=None, bail_x=None, half_x=None):
        sign = 1 if e["dir"] == "BUY" else -1
        atr = e["atr"]
        i0 = self.t.searchsorted(np.datetime64(pd.Timestamp(e["ts"])))
        if i0 >= len(self.t):
            return None
        fill = self.o[i0]
        tp = fill + sign * 0.8 * atr
        sl = fill - sign * 2.4 * atr
        bail_px = fill - sign * (bail_x or 0) * atr
        half_px = fill - sign * (half_x or 0) * atr
        i_bail = (self.t.searchsorted(self.t[i0] + np.timedelta64(bail_t, "h"))
                  if bail_t else None)
        i_end = min(self.t.searchsorted(
            self.t[i0] + np.timedelta64(HOR_H, "h")), len(self.t))
        i_end = max(i_end, i0 + 1)
        halved = False
        pnl_bank = 0.0     # realized from the half-close, in price units
        frac = 1.0
        for i in range(i0, i_end):
            hi, lo, cl = self.h[i], self.l[i], self.c[i]
            if (lo <= sl) if sign > 0 else (hi >= sl):
                return (pnl_bank + frac * sign * (sl - fill)) * 100 - COST
            if (hi >= tp) if sign > 0 else (lo <= tp):
                return (pnl_bank + frac * sign * (tp - fill)) * 100 - COST
            if half_x and not halved and \
                    ((cl <= half_px) if sign > 0 else (cl >= half_px)):
                pnl_bank += 0.5 * sign * (cl - fill)
                frac = 0.5
                halved = True
            if bail_t and i >= i_bail and \
                    ((cl <= bail_px) if sign > 0 else (cl >= bail_px)):
                return (pnl_bank + frac * sign * (cl - fill)) * 100 - COST
        cl = self.c[i_end - 1]
        return (pnl_bank + frac * sign * (cl - fill)) * 100 - COST


def report(tag, pnls):
    p = [x for x in pnls if x is not None]
    s = basic_stats(p)
    losses = [x for x in p if x <= 0]
    avg_loss = np.mean(losses) if losses else 0
    worst = min(p) if p else 0
    cum = pd.Series(p).cumsum()
    mdd = (cum.cummax() - cum).max() if len(p) else 0
    print(f"  {tag:>16}: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
          f"net=${sum(p):,.0f} avgLoss=${avg_loss:,.0f} "
          f"worst=${worst:,.0f} maxDD=${mdd:,.0f}")


def combo_kw(e):
    """Regime-conditional: high-vol -> half-out at -1.2xATR (tail
    compression); low-vol -> 8h bail at -1.0xATR (dither cleanup)."""
    return dict(half_x=1.2) if e["hivol"] else dict(bail_t=8, bail_x=1.0)


VARIANTS = {"ref (v4)": {}, "bail4h_1.0": dict(bail_t=4, bail_x=1.0),
            "bail8h_1.0": dict(bail_t=8, bail_x=1.0),
            "bail4h_1.4": dict(bail_t=4, bail_x=1.4),
            "half_1.2": dict(half_x=1.2), "COMBO_regime": None}

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
    sim = Sim5(m1)
    def run_v(evs, kw):
        if kw is None:
            return [sim.run(e, **combo_kw(e)) for e in evs]
        return [sim.run(e, **kw) for e in evs]

    print(f"\n=== era {era}: {len(entries)} entries "
          f"(hivol {sum(e['hivol'] for e in entries)}) ===")
    for name, kw in VARIANTS.items():
        report(name, run_v(entries, kw))
    if era == "new":
        e26 = [e for e in entries if e["ts"] >= "2026-01-01"]
        print(f"--- 2026 H1 slice ({len(e26)} entries) ---")
        for name, kw in VARIANTS.items():
            report(name, run_v(e26, kw))
