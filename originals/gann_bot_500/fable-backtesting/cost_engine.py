"""
STATUS: Stage-2 of DATA_PLAN (2026-07-03). Empirical cost engine from
Dukascopy ticks (download/*.csv: timestamp_ms_utc, askPrice, bidPrice).

Builds cost_matrix.json:
  matrix[hour][dow] = {n, med, p75, p95}   spread in PRICE DOLLARS
  news = same stats pooled over ±15min around 08:30 ET / 14:00 ET on
         news days (calendar/news_days.json)
CostModel.charge(ts, regime) -> per-side spread cost in POINTS (x100),
  regimes: optimistic (half median), realistic (median + 5pts slippage),
  worst (p95 + 10pts).
Run directly to (re)build the matrix from all downloaded tick files and
print sanity checks. Incremental: uses whatever year files exist.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
DL = HERE / "download"
OUT = HERE / "cost_matrix.json"
ET = ZoneInfo("America/New_York")


def news_windows_utc(days_json=HERE / "calendar" / "news_days.json"):
    """(start,end) UTC windows: ±15min around 08:30 ET and 14:00 ET on
    each calendar news day."""
    days = json.loads(days_json.read_text())["days"]
    win = []
    for d in days:
        for hh, mm in ((8, 30), (14, 0)):
            et = datetime.fromisoformat(d).replace(hour=hh, minute=mm,
                                                   tzinfo=ET)
            c = et.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
            win.append((c - timedelta(minutes=15), c + timedelta(minutes=15)))
    return win


def build_matrix(symbol="xauusd", sample_every=25):
    """Sample every Nth tick (spread stats don't need every tick)."""
    files = sorted(DL.glob(f"{symbol}-tick-*.csv"))
    if not files:
        raise SystemExit(f"no tick files for {symbol} in {DL}")
    frames = []
    for f in files:
        if f.stat().st_size < 1000:
            continue
        df = pd.read_csv(f, usecols=["timestamp", "askPrice", "bidPrice"])
        df = df.iloc[::sample_every]
        frames.append(df)
        print(f"  loaded {f.name}: {len(df):,} sampled ticks", flush=True)
    t = pd.concat(frames, ignore_index=True)
    t["spread"] = (t.askPrice - t.bidPrice).clip(lower=0)
    t = t[t.spread < 20]                      # drop corrupt quotes
    ts = pd.to_datetime(t.timestamp, unit="ms")
    t["hour"], t["dow"] = ts.dt.hour, ts.dt.dayofweek

    def stats(s):
        return {"n": int(len(s)), "med": round(float(s.median()), 3),
                "p75": round(float(s.quantile(.75)), 3),
                "p95": round(float(s.quantile(.95)), 3)}

    matrix = {}
    for (h, d), g in t.groupby(["hour", "dow"]):
        matrix.setdefault(str(h), {})[str(d)] = stats(g.spread)

    wins = news_windows_utc()
    tsn = ts.dt.tz_localize(None)
    mask = pd.Series(False, index=t.index)
    # vectorized-ish: check windows per unique date to keep it fast
    by_date = {}
    for a, b in wins:
        by_date.setdefault(a.date(), []).append((a, b))
    dates = tsn.dt.date
    for d, ws in by_date.items():
        idx = t.index[dates == d]
        if len(idx) == 0:
            continue
        sub = tsn.loc[idx]
        for a, b in ws:
            mask.loc[idx[(sub >= a) & (sub <= b)]] = True
    news = stats(t.spread[mask]) if mask.any() else None
    overall = stats(t.spread)

    out = {"symbol": symbol, "built": datetime.utcnow().isoformat(),
           "files": [f.name for f in files], "overall": overall,
           "news": news, "matrix": matrix}
    OUT.write_text(json.dumps(out, indent=1))
    return out


class CostModel:
    """charge(ts, regime) -> per-side cost in POINTS ($1 = 100 pts)."""
    SLIP = {"optimistic": 0.0, "realistic": 5.0, "worst": 10.0}

    def __init__(self, path=OUT):
        d = json.loads(Path(path).read_text())
        self.m = d["matrix"]
        self.news = d["news"]
        self.overall = d["overall"]
        self.windows = news_windows_utc()

    def _cell(self, ts: pd.Timestamp):
        c = self.m.get(str(ts.hour), {}).get(str(ts.dayofweek))
        return c if (c and c["n"] >= 50) else self.overall

    def spread_usd(self, ts: pd.Timestamp, regime="realistic") -> float:
        naive = ts.tz_localize(None) if ts.tzinfo else ts
        in_news = self.news and any(a <= naive <= b
                                    for a, b in self.windows
                                    if abs((a - naive).days) < 1)
        cell = self.news if in_news else self._cell(ts)
        key = {"optimistic": "med", "realistic": "med", "worst": "p95"}[regime]
        s = cell[key]
        return s / 2 if regime == "optimistic" else s

    def charge_pts(self, ts, regime="realistic") -> float:
        """Per-SIDE cost in points: half-spread paid at entry AND exit,
        modeled as full spread once per round trip / 2 per side + slippage."""
        return (self.spread_usd(ts, regime) / 2) * 100 + self.SLIP[regime]


if __name__ == "__main__":
    out = build_matrix()
    print(f"\noverall spread: {out['overall']}")
    if out["news"]:
        print(f"news-window spread: {out['news']}")
    m = out["matrix"]
    for h in ("1", "8", "14", "18"):
        cell = m.get(h, {}).get("2")          # Wednesdays
        if cell:
            print(f"  Wed {h.zfill(2)}:00 UTC: med={cell['med']} "
                  f"p95={cell['p95']} n={cell['n']}")
    flat = 0.20
    print(f"\nflat-20pt assumption = ${flat:.2f} round trip; "
          f"empirical median = ${out['overall']['med']:.2f}")
