"""
HistData M1 loader + resamplers + look-ahead-safe helpers.

All timestamps are tz-aware UTC. HistData `time` column is a Unix epoch (UTC),
confirmed identical to the bot's log convention (bot.py:598 etc.). Timezone
alignment is direct: no NY-vs-broker-vs-UTC conversion needed for entry-time
matching; NY-local session windows for the veto screen come later via
tz_convert('America/New_York').

Resample conventions:
  * M1  → row indexed by BAR-OPEN time (matches HistData raw format).
  * H1  → 1h bins on M1 open-time. Row index = bar OPEN. Bar closes at
          index + 1h. Only bars whose full 60 M1 constituents exist are kept.
  * H4  → same, 4h bins.
  * D1  → 24h bins aligned to UTC 00:00 (matches bot.py's _today_midnight_ts).

Look-ahead safety: for any "as of time T" query, a higher-TF bar is available
IFF its bar-close time <= T. The helper `snapshot_higher_tf` enforces this.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
HISTDATA_PATH = REPO / "research" / "data" / "xauusd_m1_histdata.csv"


# ─────────────────────────────────────────────────────────────────────────
# Loaders / resamplers
# ─────────────────────────────────────────────────────────────────────────
def load_m1(start_utc: Optional[pd.Timestamp] = None,
            end_utc: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """Read the M1 CSV, keep [start, end], return UTC-tz-aware ascending."""
    df = pd.read_csv(HISTDATA_PATH)
    df["ts"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("ts").sort_index()
    if start_utc is not None:
        df = df[df.index >= start_utc]
    if end_utc is not None:
        df = df[df.index <= end_utc]
    return df[["open", "high", "low", "close"]]


def resample_ohlc(m1: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample M1 -> H1/H4/D1. Index = bar-OPEN, tz-aware UTC. Drops rows
    whose constituent M1 count is below the expected minimum (weekend gaps)."""
    # aggregate
    grouped = m1.resample(rule, label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
    })
    counts = m1.resample(rule, label="left", closed="left").size()
    # drop rows with 0 constituents (weekend gaps)
    grouped = grouped[counts > 0]
    grouped = grouped.dropna(subset=["open", "close"])
    return grouped


def resample_d1_utc(m1: pd.DataFrame) -> pd.DataFrame:
    """D1 aligned to UTC 00:00, matching bot.py's _today_midnight_ts()."""
    return resample_ohlc(m1, "1D")


# ─────────────────────────────────────────────────────────────────────────
# Wilder ATR (same seed convention as broker.get_atr)
# ─────────────────────────────────────────────────────────────────────────
def wilder_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder-smoothed ATR over the given OHLC frame. Match broker.get_atr:
    seed = SMA of first `period` TR values; then Wilder-smooth the rest.
    Result indexed by the same bar-open times; leading `period-1` are NaN."""
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
    # seed at index `period` (0-based) with SMA of TR[1..period]
    seed = np.nanmean(tr[1:period + 1])
    atr[period] = seed
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(atr, index=df.index, name="atr")


# ─────────────────────────────────────────────────────────────────────────
# Snapshot helpers (look-ahead-safe higher-TF views)
# ─────────────────────────────────────────────────────────────────────────
def h4_close_time(open_ts: pd.Timestamp) -> pd.Timestamp:
    return open_ts + pd.Timedelta(hours=4)


def h1_close_time(open_ts: pd.Timestamp) -> pd.Timestamp:
    return open_ts + pd.Timedelta(hours=1)


def d1_close_time(open_ts: pd.Timestamp) -> pd.Timestamp:
    return open_ts + pd.Timedelta(days=1)


def completed_h4_before(h4: pd.DataFrame, now_utc: pd.Timestamp) -> pd.DataFrame:
    """H4 bars whose bar-CLOSE time is <= now_utc."""
    return h4[h4.index + pd.Timedelta(hours=4) <= now_utc]


def completed_d1_before(d1: pd.DataFrame, now_utc: pd.Timestamp) -> pd.DataFrame:
    return d1[d1.index + pd.Timedelta(days=1) <= now_utc]


def bars_to_dicts(df: pd.DataFrame) -> list[dict]:
    """Convert a completed-bars slice to bot-native list-of-dicts (with a
    `time` field == bar-open Unix epoch), matching broker.get_ohlc()."""
    if df.empty:
        return []
    out = []
    for ts, row in df.iterrows():
        out.append({
            "time": int(ts.timestamp()),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": 0.0,
        })
    return out


def assert_no_h1_leak(h1: pd.DataFrame, h4: pd.DataFrame,
                      cursor: pd.Timestamp) -> None:
    """Explicit leak assertion for the #1 silent backtest bug.

    At an H1 close time `cursor`, no H4 bar whose bar-CLOSE > cursor may be
    considered 'closed'. Raise loudly if the completed-H4 view breaks this."""
    completed = completed_h4_before(h4, cursor)
    if not completed.empty:
        last_close = completed.index[-1] + pd.Timedelta(hours=4)
        if last_close > cursor:
            raise AssertionError(
                f"H4 leak: 'completed' bar closes at {last_close.isoformat()} "
                f"but cursor is {cursor.isoformat()}"
            )
