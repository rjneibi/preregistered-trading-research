"""
STATUS: Stage-2 GO/NO-GO harness (2026-07-03). Re-runs the v5.1 H1 arm with
time-varying costs from cost_matrix.json instead of flat 20pts.

Cost model (per round trip, POINTS):
  cost(ts) = broker_anchor * rel(ts) + 2*slip[regime]
  rel(ts)  = cell_med(ts) / overall_med   (Dukascopy DYNAMICS only)
  broker_anchor = 26 pts (13pt observed live spread paid ~both sides)
  slip: optimistic 0 / realistic 5 / worst 10 pts per side; worst uses p95.
Regression mode (--flat) charges constant 20 to reproduce round-8 numbers.
GO/NO-GO: REALISTIC regime PF >= 1.2 new era and >= 1.0 old era.
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
from research.dr_backtest.metrics import basic_stats
from bail_exit_v5 import Sim5, scan_entries
import bail_exit_v5

BROKER_ANCHOR = 26.0          # pts round-trip at median conditions
SLIP = {"optimistic": 0.0, "realistic": 10.0, "worst": 20.0}  # round-trip


class TimeCosts:
    def __init__(self, path=REPO / "fable-backtesting" / "cost_matrix.json"):
        d = json.loads(Path(path).read_text())
        self.m, self.overall = d["matrix"], d["overall"]
        self.news = d["news"]
        from cost_engine import news_windows_utc
        self.windows = news_windows_utc()

    def cost_pts(self, ts: pd.Timestamp, regime: str) -> float:
        naive = ts.tz_localize(None) if ts.tzinfo else ts
        in_news = self.news and any(
            a <= naive <= b for a, b in self.windows
            if abs((a.date() - naive.date()).days) < 1)
        cell = self.news if in_news else \
            self.m.get(str(ts.hour), {}).get(str(ts.dayofweek), self.overall)
        if cell is None or cell["n"] < 50:
            cell = self.overall
        key = "p95" if regime == "worst" else "med"
        rel = cell[key] / self.overall["med"]
        return BROKER_ANCHOR * rel + SLIP[regime]


def main(flat=False):
    tc = None if flat else TimeCosts()
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
        regimes = ["flat20"] if flat else ["optimistic", "realistic", "worst"]
        for regime in regimes:
            pnls = []
            for e in entries:
                kw = (dict(half_x=1.2) if e["hivol"]
                      else dict(bail_t=8, bail_x=1.0))
                # Sim5 charges bail_exit_v5.COST once per trade; patch it
                bail_exit_v5.COST = (20.0 if flat else
                                     tc.cost_pts(pd.Timestamp(e["ts"]),
                                                 regime))
                p = sim.run(e, **kw)
                if p is not None:
                    pnls.append(p)
            bail_exit_v5.COST = 20.0
            s = basic_stats(pnls)
            cum = pd.Series(pnls).cumsum()
            mdd = (cum.cummax() - cum).max()
            print(f"{era:>4} {regime:>11}: n={s['n']} wr={s['win_rate']} "
                  f"pf={s['pf']} net=${sum(pnls):,.0f} maxDD=${mdd:,.0f}",
                  flush=True)
        if era == "new" and not flat:
            e26 = [e for e in entries if e["ts"] >= "2026-01-01"]
            for regime in ("realistic", "worst"):
                pnls = []
                for e in e26:
                    kw = (dict(half_x=1.2) if e["hivol"]
                          else dict(bail_t=8, bail_x=1.0))
                    bail_exit_v5.COST = tc.cost_pts(pd.Timestamp(e["ts"]),
                                                    regime)
                    p = sim.run(e, **kw)
                    if p is not None:
                        pnls.append(p)
                bail_exit_v5.COST = 20.0
                s = basic_stats(pnls)
                print(f"2026H1 {regime:>11}: n={s['n']} wr={s['win_rate']} "
                      f"pf={s['pf']} net=${sum(pnls):,.0f}", flush=True)


if __name__ == "__main__":
    main(flat="--flat" in sys.argv)
