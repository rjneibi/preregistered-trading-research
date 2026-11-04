"""Cost model: measured tick-spread matrix + commission + Islamic admin fee.

Adapted from fable-backtesting/cost_engine.py::CostModel (the matrix BUILDER
stays in fable-backtesting — goldbot reads cost_matrix.json read-only).

Units: $1 price move = 100 points = $100 per 1.0 lot, so 1 point = $1/lot.

Regimes:
  flat        — legacy 20 pts/round-trip (13 spread + 7 commission), the
                assumption every historical PF figure was produced under;
                kept ONLY for parity. No admin fee.
  optimistic  — half median spread per side, zero slippage.
  realistic   — median spread + slippage per side.
  worst       — p95 spread + slippage per side.
Non-flat regimes add commission per round trip and the [ESTIMATE] Islamic
admin fee per rollover night held.

The current matrix is THIN (a 1-day 2026 sample + one 2015 file): cells with
n<50 fall back to the overall stats, so 'realistic' is effectively the
overall median everywhere. Rerun fable-backtesting/cost_engine.py after the
full tick download and every number here tightens automatically.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .config import Cfg, resolve_path

ET = ZoneInfo("America/New_York")
REGIMES = ("flat", "optimistic", "realistic", "worst")


def _news_windows_utc(days_json: Path) -> list[tuple[datetime, datetime]]:
    """(start,end) naive-UTC windows: +/-15min around 08:30 ET and 14:00 ET
    on each calendar news day (cost_engine.py convention)."""
    days = json.loads(days_json.read_text())["days"]
    win = []
    for d in days:
        for hh, mm in ((8, 30), (14, 0)):
            et = datetime.fromisoformat(d).replace(hour=hh, minute=mm, tzinfo=ET)
            c = et.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            win.append((c - timedelta(minutes=15), c + timedelta(minutes=15)))
    return win


class CostModel:
    def __init__(self, cfg: Cfg) -> None:
        costs = cfg.costs
        self.slip = {"optimistic": float(costs.slippage_pts.optimistic),
                     "realistic": float(costs.slippage_pts.realistic),
                     "worst": float(costs.slippage_pts.worst)}
        self.commission_pts_rt = float(costs.commission_pts_rt.value)
        self.flat_rt_pts = float(costs.legacy_flat_rt_pts.value)
        self.admin_fee_usd_night = float(
            costs.islamic_admin_fee_usd_per_lot_night.value)

        mpath = resolve_path(cfg, costs.matrix_path)
        if mpath.exists():
            d = json.loads(mpath.read_text())
            self.matrix = d["matrix"]
            self.news = d.get("news")
            self.overall = d["overall"]
            self.matrix_source = str(mpath)
        else:                                   # config-median fallback
            med = float(costs.spread_median_usd.value)
            self.matrix = {}
            self.news = None
            self.overall = {"n": 0, "med": med, "p75": med, "p95": med}
            self.matrix_source = f"FALLBACK config median ${med:.2f} (no matrix at {mpath})"

        npath = resolve_path(cfg, costs.get("news_calendar_json", ""))
        self.windows = (_news_windows_utc(npath)
                        if str(npath).endswith(".json") and npath.exists() else [])

    # -- spread ------------------------------------------------------------
    def _cell(self, ts: pd.Timestamp) -> dict:
        c = self.matrix.get(str(ts.hour), {}).get(str(ts.dayofweek))
        return c if (c and c["n"] >= 50) else self.overall

    def spread_usd(self, ts: pd.Timestamp, regime: str = "realistic") -> float:
        naive = ts.tz_localize(None) if ts.tzinfo else ts
        in_news = bool(self.news) and any(
            a <= naive <= b for a, b in self.windows
            if abs((a - naive).days) < 1)
        cell = self.news if in_news else self._cell(ts)
        key = {"optimistic": "med", "realistic": "med", "worst": "p95"}[regime]
        s = cell[key]
        return s / 2 if regime == "optimistic" else s

    def charge_pts(self, ts: pd.Timestamp, regime: str = "realistic") -> float:
        """Per-SIDE cost in points: half the spread + slippage."""
        return (self.spread_usd(ts, regime) / 2) * 100 + self.slip[regime]

    # -- round trip ---------------------------------------------------------
    def round_trip_pts(self, entry_ts: pd.Timestamp, exit_ts: pd.Timestamp,
                       regime: str = "realistic") -> float:
        if regime == "flat":
            return self.flat_rt_pts        # commission already inside the 20
        return (self.charge_pts(entry_ts, regime)
                + self.charge_pts(exit_ts, regime)
                + self.commission_pts_rt)

    def round_trip_usd(self, entry_ts: pd.Timestamp, exit_ts: pd.Timestamp,
                       regime: str = "realistic", nights: int = 0) -> float:
        """Round-trip cost in $ per 1.0 lot (1 pt = $1/lot), plus the
        [ESTIMATE] admin fee per rollover night (non-flat regimes only)."""
        usd = self.round_trip_pts(entry_ts, exit_ts, regime)
        if regime != "flat":
            usd += self.admin_fee_usd_night * nights
        return usd

    # -- honesty printout ---------------------------------------------------
    def breakeven_move_usd(self, regime: str = "realistic") -> float:
        """Typical breakeven move in $/oz (overall stats, no news window)."""
        if regime == "flat":
            return self.flat_rt_pts / 100.0
        key = "p95" if regime == "worst" else "med"
        s = self.overall[key]
        if regime == "optimistic":
            s = s / 2
        per_side = (s / 2) * 100 + self.slip[regime]
        return (2 * per_side + self.commission_pts_rt) / 100.0

    def describe(self) -> str:
        lines = [f"cost matrix: {self.matrix_source} "
                 f"(overall med=${self.overall['med']:.2f}, "
                 f"p95=${self.overall['p95']:.2f}, n={self.overall['n']:,})"]
        for r in REGIMES:
            lines.append(f"  {r:>10}: breakeven move ~ "
                         f"${self.breakeven_move_usd(r):.2f}/oz per round trip")
        lines.append(f"  admin fee [ESTIMATE]: "
                     f"${self.admin_fee_usd_night:.2f}/lot/night "
                     f"(pending broker T&Cs)")
        return "\n".join(lines)
