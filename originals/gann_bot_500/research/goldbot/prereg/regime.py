"""H2 volatility-regime filter — self-contained, strictly causal.

Implements exactly the PREREGISTRATION.md definition:
  score(D) = percentile rank (fraction strictly below) of relATR on day D
             among the 252 strictly prior completed days,
  where relATR = ATR(14, daily)/close on daily bars cut at close_hour in tz
             (default UTC-00:00 to match the strategy's pivot day-cut),
  and a signal during day D uses score(D-1) -- the last COMPLETED day --
             because day D's ATR is unknowable intraday.

Self-contained on purpose: imports nothing from the goldbot package so it drops
into a diverged tree. If your repo's day-cut ever changes, change it HERE AND in
the pivots simultaneously; the percentile is convention-dependent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo


def _trading_day(index_utc: pd.DatetimeIndex, tz: str = "UTC", close_hour: int = 0) -> pd.Index:
    local = index_utc.tz_convert(ZoneInfo(tz))
    shifted = local + pd.Timedelta(hours=(24 - close_hour) % 24)
    return shifted.tz_localize(None).normalize()


def daily_rel_atr(df: pd.DataFrame, tz: str = "UTC", close_hour: int = 0,
                  atr_window: int = 14) -> pd.Series:
    """Relative ATR (ATR/close) on completed daily bars, indexed by trading day."""
    tday = _trading_day(df.index, tz, close_hour)
    g = df.groupby(tday)
    d = pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last()})
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(),
                    (d["low"] - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_window).mean()
    return (atr / d["close"]).rename("rel_atr")


def trailing_pct_rank(s: pd.Series, window: int = 252) -> pd.Series:
    """Percentile of s[i] among the `window` STRICTLY PRIOR values (fraction
    strictly below). NaN until a full prior window exists. O(n*window) loop is
    fine at daily granularity (~2,800 rows for 11 years)."""
    v = s.to_numpy(float)
    out = np.full(v.size, np.nan)
    for i in range(window, v.size):
        prior = v[i - window:i]
        if np.isnan(v[i]) or np.isnan(prior).any():
            continue
        out[i] = float(np.mean(prior < v[i]))
    return pd.Series(out, index=s.index, name="vol_pct")


def event_regime_mask(df: pd.DataFrame, events: np.ndarray, threshold: float = 0.50,
                      tz: str = "UTC", close_hour: int = 0, atr_window: int = 14,
                      pct_window: int = 252) -> np.ndarray:
    """Boolean mask over `events` (bar positions in df): True = trade allowed.

    Uses the PREVIOUS completed day's percentile (shift(1)). NaN (warmup) maps to
    False -- conservative: no trading before the filter has a full history.
    """
    rel = daily_rel_atr(df, tz, close_hour, atr_window)
    usable = trailing_pct_rank(rel, pct_window).shift(1)   # day D uses score(D-1)
    tday_all = _trading_day(df.index, tz, close_hour)
    ev_days = pd.Index(tday_all[np.asarray(events, int)])
    vals = usable.reindex(ev_days).to_numpy(float)
    return np.where(np.isnan(vals), False, vals >= threshold)


def mechanism_control(trade_net_usd: np.ndarray, in_mask: np.ndarray,
                      min_n_in: int = 40) -> dict:
    """Old-era conditional test from PREREGISTRATION.md: pass trades from ONE era.
    Returns PFs of filtered-in vs filtered-out and the verdict fields; caller
    checks (pf_in - pf_out) >= 0.15 with n_in >= min_n_in."""
    def _pf(x: np.ndarray) -> float:
        w, l = x[x > 0].sum(), x[x <= 0].sum()
        return float(w / abs(l)) if l != 0 else float("inf")
    inside, outside = trade_net_usd[in_mask], trade_net_usd[~in_mask]
    return {"n_in": int(in_mask.sum()), "n_out": int((~in_mask).sum()),
            "pf_in": _pf(inside) if len(inside) else float("nan"),
            "pf_out": _pf(outside) if len(outside) else float("nan"),
            "sufficient": bool(in_mask.sum() >= min_n_in)}
