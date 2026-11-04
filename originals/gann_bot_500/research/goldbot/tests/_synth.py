"""Hand-built synthetic fixtures for the goldbot self-checks."""

from __future__ import annotations

import numpy as np
import pandas as pd


def mk_bars(start: str, bars: list[tuple[float, float, float, float]],
            freq: str = "1min") -> pd.DataFrame:
    """OHLC frame from (o,h,l,c) tuples, indexed at `freq` from `start` (UTC).
    Every bar is validated h >= max(o,c) and l <= min(o,c)."""
    idx = pd.date_range(start, periods=len(bars), freq=freq, tz="UTC")
    df = pd.DataFrame(bars, columns=["open", "high", "low", "close"], index=idx)
    bad = (df["high"] < df[["open", "close"]].max(axis=1)) | \
          (df["low"] > df[["open", "close"]].min(axis=1))
    assert not bad.any(), f"incoherent fixture bars at {list(df.index[bad])}"
    return df


def mk_event(ts: str, side: int, atr: float, hivol: bool) -> pd.DataFrame:
    return pd.DataFrame([{
        "event_ts": pd.Timestamp(ts), "side": side, "atr": atr,
        "hivol": hivol, "arms": "test", "day_open": pd.Timestamp(ts).normalize(),
        "level": np.nan,
    }])


def flat_bars(n: int, px: float = 100.0) -> list[tuple[float, float, float, float]]:
    return [(px, px + 0.1, px - 0.1, px)] * n
