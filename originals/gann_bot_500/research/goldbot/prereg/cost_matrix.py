"""Per-era, hour-conditional cost matrix from tick data — the rerun's cost basis.

What ticks can and cannot tell you (honesty scope):
  * CAN: the bid-ask SPREAD distribution by (year, UTC hour) — this captures
    session structure and most scheduled-news timing, fixing the flat-$0.72
    problem and the "today's spread applied to 2015" bias.
  * CANNOT: slippage. Slippage stays modeled as k_slip x bucket spread per side
    (k_slip = 0.5 pinned in PREREGISTRATION.md as an ASSUMPTION) until live fills
    measure it.

Input format: CSV or Parquet tick files with time/bid/ask columns. Column names,
timezone, and numeric-epoch unit are parameters — VERIFY against your
bi5_downloader.py output before trusting the matrix; Dukascopy decoders commonly
emit epoch-ms, but I cannot confirm yours does.

Quantiles are computed on a capped uniform subsample per bucket (default 100k) —
approximate by design; n and mean are exact. Buckets and fallbacks are reported so
no silent coverage gaps enter the verdict.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def _read_ticks(path: Path, time_col: str, bid_col: str, ask_col: str,
                data_tz: str, time_unit: str | None):
    if path.suffix.lower() == ".parquet":
        yield pd.read_parquet(path, columns=[time_col, bid_col, ask_col])
        return
    for chunk in pd.read_csv(path, usecols=[time_col, bid_col, ask_col],
                             chunksize=2_000_000):
        yield chunk


def build_matrix(files: list[str | Path], time_col: str = "time", bid_col: str = "bid",
                 ask_col: str = "ask", data_tz: str = "UTC",
                 time_unit: str | None = "ms", bucket_cap: int = 100_000,
                 seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    buckets: dict[tuple[int, int], dict] = {}

    def _add(year: int, hour: int, spreads: np.ndarray) -> None:
        b = buckets.setdefault((year, hour), {"n": 0, "sum": 0.0,
                                              "samp": np.empty(0)})
        b["n"] += spreads.size
        b["sum"] += float(spreads.sum())
        pool = np.concatenate([b["samp"], spreads])
        if pool.size > bucket_cap:
            pool = rng.choice(pool, bucket_cap, replace=False)
        b["samp"] = pool

    for f in map(Path, files):
        for chunk in _read_ticks(f, time_col, bid_col, ask_col, data_tz, time_unit):
            t = chunk[time_col]
            if pd.api.types.is_numeric_dtype(t):
                ts = pd.to_datetime(t, unit=time_unit or "ms", utc=True)
            else:
                ts = pd.to_datetime(t)
                ts = ts.dt.tz_localize(data_tz) if ts.dt.tz is None else ts
                ts = ts.dt.tz_convert("UTC")
            spread = (chunk[ask_col] - chunk[bid_col]).to_numpy(float)
            ok = np.isfinite(spread) & (spread > 0)
            ts, spread = ts[ok], spread[ok]
            df = pd.DataFrame({"y": ts.dt.year.to_numpy(),
                               "h": ts.dt.hour.to_numpy(), "s": spread})
            for (y, h), grp in df.groupby(["y", "h"]):
                _add(int(y), int(h), grp["s"].to_numpy())

    out: dict = {"meta": {"bucket_cap": bucket_cap,
                          "note": "quantiles approximate (capped subsample); n/mean exact"},
                 "years": {}, "fallback": {}}
    year_pools: dict[int, list[np.ndarray]] = {}
    for (y, h), b in sorted(buckets.items()):
        s = b["samp"]
        out["years"].setdefault(str(y), {})[str(h)] = {
            "n": b["n"], "mean": b["sum"] / b["n"],
            "median": float(np.median(s)), "p75": float(np.percentile(s, 75)),
            "p90": float(np.percentile(s, 90))}
        year_pools.setdefault(y, []).append(s)
    for y, pools in year_pools.items():
        pool = np.concatenate(pools)
        if pool.size > bucket_cap:
            pool = rng.choice(pool, bucket_cap, replace=False)
        out["fallback"][str(y)] = {"median": float(np.median(pool)),
                                   "p90": float(np.percentile(pool, 90))}
    allpool = np.concatenate([b["samp"] for b in buckets.values()]) if buckets else np.array([0.0])
    out["fallback"]["_global"] = {"median": float(np.median(allpool)),
                                  "p90": float(np.percentile(allpool, 90))}
    return out


class CostMatrix:
    """Lookup + trade costing. Fallback chain (each use is warned once and
    counted): (year,hour) -> year -> global. Flat-model equivalence: with a
    constant spread s, trade cost per oz = s + 2*k_slip*s, matching the old
    CostModel with slippage_usd = k_slip*s."""

    def __init__(self, matrix: dict, stat: str = "median", k_slip: float = 0.5,
                 commission_per_lot_rt: float = 7.0, contract_oz: int = 100):
        self.m, self.stat, self.k = matrix, stat, k_slip
        self.commission, self.oz = commission_per_lot_rt, contract_oz
        self.fallback_hits: dict[str, int] = {}

    @classmethod
    def load(cls, path: str | Path, **kw) -> "CostMatrix":
        return cls(json.loads(Path(path).read_text()), **kw)

    def spread_usd(self, ts: pd.Timestamp) -> float:
        ts = ts.tz_convert("UTC")
        y, h = str(ts.year), str(ts.hour)
        yr = self.m["years"].get(y)
        if yr and h in yr:
            return float(yr[h][self.stat])
        if y in self.m["fallback"]:
            self.fallback_hits[y] = self.fallback_hits.get(y, 0) + 1
            return float(self.m["fallback"][y][self.stat if self.stat in self.m["fallback"][y] else "median"])
        self.fallback_hits["_global"] = self.fallback_hits.get("_global", 0) + 1
        return float(self.m["fallback"]["_global"][self.stat if self.stat in self.m["fallback"]["_global"] else "median"])

    def trade_cost_usd(self, entry_ts: pd.Timestamp, exit_ts: pd.Timestamp,
                       lots: float = 1.0) -> float:
        s_in, s_out = self.spread_usd(entry_ts), self.spread_usd(exit_ts)
        per_oz = (s_in + s_out) / 2.0 + self.k * (s_in + s_out)
        return lots * self.oz * per_oz + lots * self.commission

    def coverage_report(self) -> str:
        yrs = self.m["years"]
        lines = [f"{y}: {len(hs)}/24 hours, min n = {min(v['n'] for v in hs.values())}"
                 for y, hs in sorted(yrs.items())]
        lines.append(f"fallback hits so far: {self.fallback_hits or 'none'}")
        return "\n".join(lines)


def save_matrix(matrix: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(matrix, indent=1))
