"""Phase 2 toxicity guards. Both DEFAULT OFF in config.

SpreadGate — rolling-median spread gate. The window/multiplier defaults are
placeholders: calibrate them on YOUR broker's tick spread distribution before
trusting them live (README broker checklist item 4).

NewsBlackout — blocks entries inside +/-N-minute windows around calendar
events from a weekly-exported UTC CSV. NOTE: for the validated R3/S3 flip
strategy this was tested and REJECTED — news days are the BEST trades
(new-era PF 2.40 on FOMC/NFP/CPI days); the live layer applies a 1.5x sizing
weight instead (fable-backtesting/news_calendar.py). The guard exists for
other strategies / Phase 2 experimentation, enabled: false by default.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class SpreadGate:
    def __init__(self, window_bars: int = 1440, mult: float = 2.0) -> None:
        assert window_bars > 1 and mult > 0
        self.window_bars = window_bars
        self.mult = mult

    def flags(self, spread: pd.Series) -> pd.Series:
        """True where the spread exceeds mult x rolling median (lagged one
        bar so the current observation cannot gate itself)."""
        med = spread.rolling(self.window_bars,
                             min_periods=max(2, self.window_bars // 4)
                             ).median().shift(1)
        return (spread > self.mult * med).fillna(False)

    def ok(self, current_spread: float, history: pd.Series) -> bool:
        med = history.tail(self.window_bars).median()
        if med != med:                       # not enough history: fail open
            return True
        return current_spread <= self.mult * med


class NewsBlackout:
    """UTC calendar CSV with columns ts_utc[,event]; blocks entries in
    [ts - pre_min, ts + post_min]."""

    def __init__(self, calendar_csv: str | Path,
                 pre_min: int = 15, post_min: int = 15) -> None:
        df = pd.read_csv(calendar_csv)
        assert "ts_utc" in df.columns, "calendar CSV needs a ts_utc column"
        ts = pd.to_datetime(df["ts_utc"])
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize("UTC")
        ts = ts.dt.tz_convert("UTC").dt.tz_localize(None)   # naive-UTC arrays
        self.starts = (ts - pd.Timedelta(minutes=pre_min)).to_numpy()
        self.ends = (ts + pd.Timedelta(minutes=post_min)).to_numpy()

    def blocked(self, ts: pd.Timestamp) -> bool:
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        v = ts.tz_convert("UTC").tz_localize(None).to_datetime64()
        return bool(((self.starts <= v) & (v <= self.ends)).any())
