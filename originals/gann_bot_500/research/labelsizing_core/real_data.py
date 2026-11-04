"""Real XAUUSD H1 OHLC adapter — a drop-in replacement for synth_data.

READ-ONLY. This module loads real history from a local CSV/parquet path. It does
NOT import MetaTrader5 and never connects to a broker — the path is supplied by
the caller (a CLI arg in run_real.py). The returned DataFrame has the SAME schema
``generate_synthetic_ohlc`` produces (DatetimeIndex named ``time`` at H1 with
columns ``open, high, low, close, tick_volume``), so it slots straight into the
existing labeling/feature/CPCV pipeline.

Real feeds contain bad bars. We do NOT silently repair them: ``load`` reports how
many incoherent bars exist and where, then runs ``assert_ohlc_coherent`` which
raises loudly. The caller decides what to do with a dirty feed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from synth_data import assert_ohlc_coherent

_REQUIRED = ["open", "high", "low", "close"]


def _read_frame(path: Path) -> pd.DataFrame:
    """Read a CSV or parquet file into a raw DataFrame (no schema coercion yet)."""
    suffix = path.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    if suffix in (".csv", ".txt"):
        return pd.read_csv(path)
    raise ValueError(f"unsupported data file type {suffix!r}: {path}")


def _build_index(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Construct a tz-naive H1 DatetimeIndex from common time columns.

    Preference order: an ISO ``datetime`` column, then an epoch-seconds ``time``
    column, then an existing DatetimeIndex. Any tz info is dropped (tz-naive).
    """
    if "datetime" in df.columns:
        idx = pd.to_datetime(df["datetime"], utc=True, errors="coerce")
    elif "time" in df.columns:
        col = df["time"]
        if np.issubdtype(col.dtype, np.number):
            idx = pd.to_datetime(col, unit="s", utc=True, errors="coerce")
        else:
            idx = pd.to_datetime(col, utc=True, errors="coerce")
    elif isinstance(df.index, pd.DatetimeIndex):
        idx = pd.to_datetime(df.index, utc=True, errors="coerce")
    else:
        raise ValueError(
            "no usable time column: expected 'datetime', 'time', or a DatetimeIndex"
        )
    # Drop timezone -> tz-naive, as the synthetic frame is tz-naive.
    idx = pd.DatetimeIndex(idx).tz_localize(None)
    return idx


def load(path: str | Path, *, strict: bool = True) -> pd.DataFrame:
    """Load real XAUUSD H1 OHLC as a synth-compatible DataFrame.

    Parameters
    ----------
    path : local CSV/parquet file (read-only).
    strict : when True (default) an incoherent feed raises after the report. Set
        False only for diagnostics; the pipeline always runs strict.

    Returns
    -------
    DataFrame indexed by a tz-naive hourly DatetimeIndex named ``time`` with
    columns ``open, high, low, close, tick_volume``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"data file not found: {path}")

    raw = _read_frame(path)
    raw.columns = [str(c).strip().lower() for c in raw.columns]

    missing = [c for c in _REQUIRED if c not in raw.columns]
    if missing:
        raise ValueError(f"missing required OHLC columns {missing} in {path.name}")

    idx = _build_index(raw)
    out = pd.DataFrame(
        {
            "open": pd.to_numeric(raw["open"], errors="coerce"),
            "high": pd.to_numeric(raw["high"], errors="coerce"),
            "low": pd.to_numeric(raw["low"], errors="coerce"),
            "close": pd.to_numeric(raw["close"], errors="coerce"),
        }
    )
    if "tick_volume" in raw.columns:
        out["tick_volume"] = pd.to_numeric(raw["tick_volume"], errors="coerce")
    else:
        out["tick_volume"] = 0
    out.index = idx
    out.index.name = "time"

    # Drop rows with unparseable time or OHLC, report the loss.
    n0 = len(out)
    out = out[~out.index.isna()]
    out = out.dropna(subset=_REQUIRED)
    n_nan = n0 - len(out)
    if n_nan:
        print(f"[real_data] dropped {n_nan} rows with NaN time/OHLC")

    # Sort chronologically and de-duplicate timestamps (keep first), report.
    out = out.sort_index()
    dup = out.index.duplicated(keep="first")
    if dup.any():
        print(f"[real_data] dropped {int(dup.sum())} duplicate timestamps")
        out = out[~dup]

    out["tick_volume"] = out["tick_volume"].fillna(0).astype(np.int64)

    _report_and_assert_coherence(out, strict=strict)
    return out


def _report_and_assert_coherence(df: pd.DataFrame, *, strict: bool) -> None:
    """Report incoherent bars (count + first few timestamps), then assert.

    We never silently fix bad bars — the report makes the data-quality problem
    visible and ``assert_ohlc_coherent`` raises so a dirty feed cannot pass.
    """
    lo_bad = df["low"] > df[["open", "close"]].min(axis=1) + 1e-9
    hi_bad = df["high"] < df[["open", "close"]].max(axis=1) - 1e-9
    rng_bad = df["high"] < df["low"]
    bad = lo_bad | hi_bad | rng_bad
    n_bad = int(bad.sum())

    print(f"[real_data] coherence: {len(df)} bars, {n_bad} incoherent")
    if n_bad:
        where = df.index[bad][:10]
        print(f"[real_data] first incoherent timestamps: {list(map(str, where))}")
        print(
            f"[real_data]   low>min(o,c): {int(lo_bad.sum())}  "
            f"high<max(o,c): {int(hi_bad.sum())}  high<low: {int(rng_bad.sum())}"
        )

    if strict:
        # Raises AssertionError loudly if any bar violates ordering.
        assert_ohlc_coherent(df)


if __name__ == "__main__":  # quick manual diagnostic, not part of the pipeline
    import sys

    if len(sys.argv) != 2:
        print("usage: python real_data.py <path-to-h1-csv-or-parquet>")
        raise SystemExit(2)
    frame = load(sys.argv[1])
    print(frame.head())
    print(f"loaded {len(frame)} bars: {frame.index[0]} .. {frame.index[-1]}")
