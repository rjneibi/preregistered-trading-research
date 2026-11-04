"""OHLC loader + resamplers + Wilder ATR (adapted from research/dr_backtest/data_prep.py).

All timestamps are tz-aware UTC internally. Input `time` column:
  * numeric  -> Unix epoch seconds, inherently UTC (data_tz ignored);
  * strings  -> parsed, localized to `data_tz`, converted to UTC. MT5 exports
    are usually broker server time — set data.data_tz accordingly or the
    day-cut (and therefore every pivot level) silently shifts.

Resample conventions (identical to dr_backtest — parity-critical):
  * row index = bar-OPEN time; bar closes at index + rule;
  * label="left", closed="left"; zero-constituent bins (weekend gaps) dropped;
  * D1 = 24h bins aligned to UTC 00:00.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


def load_ohlc(path: str | Path, data_tz: str = "UTC",
              start_utc: Optional[pd.Timestamp] = None,
              end_utc: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """Read CSV/Parquet with time,open,high,low,close[,volume]; return
    UTC-tz-aware ascending frame indexed by bar-open."""
    path = Path(path)
    if path.suffix.lower() in (".parquet", ".pq"):
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    assert "time" in df.columns, f"{path} has no 'time' column"

    t = df["time"]
    if pd.api.types.is_numeric_dtype(t):
        ts = pd.to_datetime(t, unit="s", utc=True)
    else:
        ts = pd.to_datetime(t)
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize(data_tz)
        ts = ts.dt.tz_convert("UTC")

    df = df.assign(ts=ts).set_index("ts").sort_index()
    if start_utc is not None:
        df = df[df.index >= start_utc]
    if end_utc is not None:
        df = df[df.index <= end_utc]
    cols = ["open", "high", "low", "close"]
    if "volume" in df.columns:
        cols.append("volume")
    return df[cols]


def resample_ohlc(m1: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample M1 -> H1/H4/D1. Index = bar-OPEN, tz-aware UTC. Drops
    zero-constituent bins (weekend gaps)."""
    grouped = m1.resample(rule, label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    })
    counts = m1.resample(rule, label="left", closed="left").size()
    grouped = grouped[counts > 0]
    grouped = grouped.dropna(subset=["open", "close"])
    return grouped


def resample_d1_utc(m1: pd.DataFrame) -> pd.DataFrame:
    """D1 aligned to UTC 00:00 (the VALIDATED pivot day boundary)."""
    return resample_ohlc(m1, "1D")


def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-smoothed ATR; seed = SMA of first `period` TR values, then
    Wilder-smooth. Same convention as the live broker.get_atr — parity-critical
    (an EMA-seeded ATR shifts every barrier by a few cents)."""
    high = df["high"].to_numpy(dtype=float)
    low = df["low"].to_numpy(dtype=float)
    close = df["close"].to_numpy(dtype=float)
    prev_close = np.concatenate(([np.nan], close[:-1]))
    tr = np.maximum.reduce([
        high - low,
        np.abs(high - prev_close),
        np.abs(low - prev_close),
    ])
    n = len(df)
    atr = np.full(n, np.nan, dtype=float)
    if n <= period:
        return pd.Series(atr, index=df.index, name="atr")
    seed = np.nanmean(tr[1:period + 1])
    atr[period] = seed
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(atr, index=df.index, name="atr")


def completed_before(df: pd.DataFrame, close_delta: pd.Timedelta,
                     now_utc: pd.Timestamp) -> pd.DataFrame:
    """Bars whose bar-CLOSE time (index + close_delta) is <= now_utc."""
    return df[df.index + close_delta <= now_utc]


def assert_no_leak(df: pd.DataFrame, close_delta: pd.Timedelta,
                   cursor: pd.Timestamp) -> None:
    """Explicit leak assertion for the #1 silent backtest bug: at decision
    time `cursor`, no bar closing after cursor may be considered 'closed'."""
    completed = completed_before(df, close_delta, cursor)
    if not completed.empty:
        last_close = completed.index[-1] + close_delta
        if last_close > cursor:
            raise AssertionError(
                f"leak: 'completed' bar closes at {last_close.isoformat()} "
                f"but cursor is {cursor.isoformat()}"
            )
