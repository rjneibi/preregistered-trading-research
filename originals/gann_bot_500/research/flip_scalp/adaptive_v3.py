"""
STATUS: RESEARCH-ONLY (2026-07-02). Round 4 — drawdown reduction / adaptivity
on FINAL_v2 (R3/S3, no-Mon, 12/16/20 UTC, TP$8/SL$12/ts24h).

A. ONE-PER-DAY: take only the first qualifying flip each UTC day.
B. ATR-EXITS: TP=1.4x / SL=2.1x H1-ATR-at-build (same 1:1.5 geometry,
   self-adaptive to volatility; replaces manual price-rescaling).
C. EQUITY-RISK SIZING + DD GOVERNOR (post-process): start $30k, risk 1% of
   equity per trade (lot = risk$/(SL$*100)); if equity <95% of peak, risk
   0.5% until a new peak. Compare DD% vs fixed-lot.
D. STREAK THROTTLE (post-process): after 2 consecutive losses, half lot
   until the next win.
All rules pre-registered; evaluated on BOTH eras.
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

import run_flip_scalp as rfs                                    # noqa: E402
from research.dr_backtest.data_prep import load_m1, resample_ohlc  # noqa: E402
from research.dr_backtest.metrics import basic_stats             # noqa: E402
from innovate_r3s3 import SimX, r3s3_level, stats, OUT           # noqa: E402
from regime_switch import load_events, P0                        # noqa: E402


def run_eras():
    per_era = {}
    for era in ("old", "new"):
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
        ev = [e for e in load_events(fname)
              if pd.Timestamp(e["entry_ts"]).hour in (12, 16, 20)]

        rows, trades_base, trades_a = [], [], []
        seen_days = set()
        for e in ev:
            ts = pd.Timestamp(e["entry_ts"])
            k = (e["h4_close"] / P0) if scale else 1.0
            base = sim.run(e, tp=8. * k, sl=12. * k, level=r3s3_level(e))
            atrx = sim.run(e, tp=1.4 * e["atr_at_build"],
                           sl=2.1 * e["atr_at_build"], level=r3s3_level(e))
            trades_base.append({"ts": e["entry_ts"], "pnl": base,
                                "sl_d": 12. * k})
            day = ts.date()
            if day not in seen_days:
                seen_days.add(day)
                trades_a.append(base)
            rows.append(atrx)
        print(f"\n=== era {era} (n={len(ev)}) ===")
        print(pd.DataFrame([
            stats("FINAL_v2 (ref)", [t["pnl"] for t in trades_base]),
            stats("A: one-per-day", trades_a),
            stats("B: ATR exits 1.4/2.1", rows),
        ]).to_string(index=False))
        per_era[era] = trades_base
    return per_era


def sizing_sims(seq):
    """C and D on the pooled fixed-strategy sequence. pnl is per 1.00 lot."""
    # fixed lot baseline
    pnl = np.array([t["pnl"] for t in seq]) / 100.0 * 100.0   # $ at 1 lot
    cum = pnl.cumsum()
    mdd_fix = float((np.maximum.accumulate(cum) - cum).max())
    print(f"\nfixed 1 lot: net=${pnl.sum():,.0f}  maxDD=${mdd_fix:,.0f}  "
          f"(DD {100 * mdd_fix / 30000:.1f}% of $30k)")

    # C: equity-risk + governor
    eq, peak = 30000.0, 30000.0
    curve = []
    for t in seq:
        risk_frac = 0.01 if eq >= 0.95 * peak else 0.005
        lot = (eq * risk_frac) / (t["sl_d"] * 100.0)
        eq += (t["pnl"] / 100.0 * 100.0) * lot
        peak = max(peak, eq)
        curve.append(eq)
    c = pd.Series(curve)
    mdd_c = float(((c.cummax() - c) / c.cummax()).max())
    print(f"C: equity-risk 1%/0.5% governor: final=${c.iloc[-1]:,.0f} "
          f"(from $30k, {(c.iloc[-1] / 30000 - 1) * 100:.0f}%)  "
          f"maxDD={mdd_c * 100:.1f}%")

    # D: streak throttle at fixed base lot 1.0
    lot, streak, eqd = 1.0, 0, []
    e2 = 0.0
    for t in seq:
        use = 0.5 if streak >= 2 else 1.0
        e2 += (t["pnl"] / 100.0 * 100.0) * use
        streak = streak + 1 if t["pnl"] < 0 else 0
        eqd.append(e2)
    d = pd.Series(eqd)
    mdd_d = float((d.cummax() - d).max())
    print(f"D: streak-throttle: net=${d.iloc[-1]:,.0f}  maxDD=${mdd_d:,.0f}")


def main():
    per_era = run_eras()
    seq = sorted(per_era["old"] + per_era["new"], key=lambda t: t["ts"])
    sizing_sims(seq)


if __name__ == "__main__":
    main()
