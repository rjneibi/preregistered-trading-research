"""
STATUS: RESEARCH-ONLY (2026-07-02). Round 3c — externally-sourced filter tests
from the user's "XAUUSD Alpha Blueprint" document. Pre-registered rules, both
eras, FINAL_v1 exits (TP$8/SL$12/ts24h, price-scaled old era):

  1. SESSION  — keep only London/NY H4 closes (12/16/20 UTC); blueprint says
                Asian-session breakouts fail.
  2. DOLLAR   — FRED DTWEXBGS (broad dollar). Weak dollar (< 50d SMA) ->
                suppress SELLs; strong -> suppress BUYs. (DXY inversion.)
  3. VIX      — FRED VIXCLS. Prior close > 25 -> BUYs only (risk-off bid).
  4. ROUND    — skip flips whose R3/S3 level is within $5 of a $100 multiple
                (blueprint: round numbers = manipulation zones).
All external series lagged: value used = last observation dated BEFORE the
entry's UTC date (FRED stamps are close-of-day).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs                                   # noqa: E402
from research.dr_backtest.data_prep import load_m1, resample_ohlc  # noqa: E402
from innovate_r3s3 import SimX, r3s3_level, stats, OUT          # noqa: E402
from regime_switch import load_events, P0                       # noqa: E402

CAL = OUT / "calendar"


def fred_series(fname):
    df = pd.read_csv(CAL / fname)
    df.columns = ["date", "val"]
    df["date"] = pd.to_datetime(df["date"])
    df["val"] = pd.to_numeric(df["val"], errors="coerce")
    return df.dropna().set_index("date")["val"]


def lagged(series, entry_ts):
    sub = series[series.index < pd.Timestamp(entry_ts).tz_localize(None)
                 .normalize()]
    return float(sub.iloc[-1]) if len(sub) else np.nan


def main():
    vix = fred_series("vix.csv")
    dxy = fred_series("dollar.csv")
    dxy_sma = dxy.rolling(50).mean()

    for era in ("new", "old"):
        if era == "new":
            start, end, fname, scale = (pd.Timestamp("2021-06-19T00:00:00Z"),
                                        pd.Timestamp("2026-06-19T17:57:00Z"),
                                        "events.jsonl", False)
        else:
            start, end, fname, scale = (pd.Timestamp("2015-06-19T00:00:00Z"),
                                        pd.Timestamp("2021-06-18T23:59:00Z"),
                                        "events_2015_2021.jsonl", True)
        rfs.BT_START, rfs.BT_END = start, end
        rfs.apply_config()
        m1 = load_m1(start - pd.Timedelta(days=60), end)
        h4 = resample_ohlc(m1, "4h")
        sim = SimX(m1, h4)
        ev = load_events(fname)

        def pnl_of(e):
            k = (e["h4_close"] / P0) if scale else 1.0
            return sim.run(e, tp=8. * k, sl=12. * k, level=r3s3_level(e))

        def keep_session(e):
            return pd.Timestamp(e["entry_ts"]).hour in (12, 16, 20)

        def keep_dollar(e):
            ts = e["entry_ts"]
            d, s = lagged(dxy, ts), lagged(dxy_sma, ts)
            if not (np.isfinite(d) and np.isfinite(s)):
                return True
            weak = d < s
            return (e["direction"] == "BUY") if weak else \
                   (e["direction"] == "SELL")

        def keep_vix(e):
            v = lagged(vix, e["entry_ts"])
            if not np.isfinite(v) or v <= 25:
                return True
            return e["direction"] == "BUY"

        def keep_round(e):
            lv = r3s3_level(e)
            return abs(lv - round(lv / 100.0) * 100.0) > 5.0

        FILTERS = {"baseline": lambda e: True, "session L/NY": keep_session,
                   "dollar-trend": keep_dollar, "vix-riskoff": keep_vix,
                   "round-number": keep_round}
        print(f"\n=== era {era}: n={len(ev)} ===")
        rows = []
        for name, f in FILTERS.items():
            sel = [e for e in ev if f(e)]
            rows.append({**stats(name, [pnl_of(e) for e in sel]),
                         "kept%": round(100 * len(sel) / len(ev))})
        print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
