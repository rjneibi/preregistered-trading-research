"""Validated R3/S3 breakout event generators (the goldbot spec's
`r3s3_fade_events` replacement — the validated edge is the BREAKOUT).

Two generators, one return contract:
  columns: event_ts (bar-CLOSE decision time, tz-aware UTC), side (+1 BUY /
  -1 SELL), atr (H1 Wilder-14 at the daily build), hivol (ATR > rolling
  90d median), arms, day_open, level.

`generate_events_final` — conviction dual-arm, ported line-for-line from
fable-backtesting/bot_spec_backtest.py:42-89 ("backtest flip_bot v1.1 EXACTLY
as coded"), including the tie-hour fix: an H1 close at 12/16/20 UTC is also
the UTC-H4 candle close, so it counts as BOTH arms simultaneously. Missing
that fix mislabels every tie conviction and degraded old-era PF 1.27 -> 1.10.

`generate_events_base` — the simpler H4-close ancestor (the PF 1.42 / OOS
1.26 variant when paired with fixed-$ exits), ported from
run_flip_scalp.py::collect_flip_events restricted to R3/S3 + skip-Monday.
"""

from __future__ import annotations

import pandas as pd

from .pivots import daily_pivots, dead_levels

_FAR_PAST = pd.Timestamp("2000-01-01T00:00:00Z")


def _day_guard(piv_row, n_h4: int, min_h4: int, atr: float) -> bool:
    """Common per-day admission: previous trading day exists (pivot row not
    NaN), enough completed H4 history (parity with the harness's
    SWING_LOOKBACK_H4=50 day guard), finite positive ATR."""
    if piv_row.isna().any():
        return False
    if n_h4 < min_h4:
        return False
    return bool(atr == atr and atr > 0)


def _atr_at_build(h1_index: pd.DatetimeIndex, atr_h1: pd.Series,
                  atr_med: pd.Series, day_open: pd.Timestamp):
    """ATR (and its regime median) of the last H1 bar fully closed before
    day_open — searchsorted convention identical to the harness."""
    pos = h1_index.searchsorted(day_open - pd.Timedelta(hours=1),
                                side="right") - 1
    if pos < 0:
        return float("nan"), float("nan")
    return float(atr_h1.iloc[pos]), float(atr_med.iloc[pos])


def generate_events_final(h1: pd.DataFrame, h4: pd.DataFrame,
                          d1: pd.DataFrame, atr_h1: pd.Series, cfg,
                          start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Conviction dual-arm: enter on the H1 close (12-20 UTC) where a
    direction's SECOND arm label appears; 1/direction/day; global 24h
    re-entry block (single-position proxy)."""
    scfg = cfg.strategy
    ecfg = cfg.exits.final.atr
    sess_lo, sess_hi = scfg.session_utc
    skip_wd = set(scfg.skip_weekday)
    atr_med = atr_h1.rolling(ecfg.regime_median_bars,
                             min_periods=ecfg.min_periods).median()
    piv = daily_pivots(d1)
    blocked_until = _FAR_PAST
    block = pd.Timedelta(hours=scfg.reentry_block_hours)
    rows = []

    for day_open in d1.index[(d1.index >= start) & (d1.index <= end)]:
        if day_open.weekday() in skip_wd:
            continue
        p = piv.loc[day_open]
        atr, med = _atr_at_build(h1.index, atr_h1, atr_med, day_open)
        r3, s3 = float(p["r3"]), float(p["s3"])
        r3_dead, s3_dead, n_h4 = dead_levels(h4, day_open, r3, s3,
                                             n=scfg.dead_check_h4_closes)
        if not _day_guard(p, n_h4, scfg.min_h4_history, atr):
            continue
        hivol = bool(med == med and atr > med)
        live = {}
        if not r3_dead:
            live["BUY"] = r3
        if not s3_dead:
            live["SELL"] = s3
        if not live:
            continue

        day_h1 = h1[(h1.index >= day_open) &
                    (h1.index < day_open + pd.Timedelta(days=1))]
        labels = {"BUY": set(), "SELL": set()}
        done = set()
        for open_ts, row in day_h1.iterrows():
            cursor = open_ts + pd.Timedelta(hours=1)
            if not (sess_lo <= cursor.hour <= sess_hi) or cursor > end:
                continue
            close = float(row["close"])
            for direc in ("BUY", "SELL"):
                lvl = live.get(direc)
                if lvl is None or direc in done:
                    continue
                hit = (close > lvl) if direc == "BUY" else (close < lvl)
                if not hit:
                    continue
                if cursor.hour % 4 == 0:        # an H4-hour close IS both arms
                    labels[direc].update(("h4", "h1"))
                else:
                    labels[direc].add("h1")
                if len(labels[direc]) == 2 and cursor >= blocked_until:
                    rows.append({
                        "event_ts": cursor,
                        "side": 1 if direc == "BUY" else -1,
                        "atr": atr, "hivol": hivol,
                        "arms": "h1+h4", "day_open": day_open, "level": lvl,
                    })
                    done.add(direc)
                    blocked_until = cursor + block
    return pd.DataFrame(rows)


def generate_events_base(h4: pd.DataFrame, d1: pd.DataFrame,
                         atr_h1: pd.Series, h1_index: pd.DatetimeIndex,
                         cfg, start: pd.Timestamp,
                         end: pd.Timestamp) -> pd.DataFrame:
    """Base ancestor: any H4 close beyond a live R3/S3 fires immediately
    (no session filter, no conviction, no re-entry block); a level flips at
    most once per day, so max one BUY + one SELL per day."""
    scfg = cfg.strategy
    ecfg = cfg.exits.final.atr        # ATR/regime conventions shared
    skip_wd = set(scfg.skip_weekday)
    atr_med = atr_h1.rolling(ecfg.regime_median_bars,
                             min_periods=ecfg.min_periods).median()
    piv = daily_pivots(d1)
    rows = []

    for day_open in d1.index[(d1.index >= start) & (d1.index <= end)]:
        if day_open.weekday() in skip_wd:
            continue
        p = piv.loc[day_open]
        atr, med = _atr_at_build(h1_index, atr_h1, atr_med, day_open)
        r3, s3 = float(p["r3"]), float(p["s3"])
        r3_dead, s3_dead, n_h4 = dead_levels(h4, day_open, r3, s3,
                                             n=scfg.dead_check_h4_closes)
        if not _day_guard(p, n_h4, scfg.min_h4_history, atr):
            continue
        hivol = bool(med == med and atr > med)
        live = {}
        if not r3_dead:
            live["BUY"] = r3
        if not s3_dead:
            live["SELL"] = s3
        if not live:
            continue

        day_h4 = h4[(h4.index >= day_open) &
                    (h4.index < day_open + pd.Timedelta(days=1))]
        for open_ts, row in day_h4.iterrows():
            cursor = open_ts + pd.Timedelta(hours=4)
            if cursor > end:
                break
            close = float(row["close"])
            for direc in ("BUY", "SELL"):
                lvl = live.get(direc)
                if lvl is None:
                    continue
                hit = (close > lvl) if direc == "BUY" else (close < lvl)
                if not hit:
                    continue
                rows.append({
                    "event_ts": cursor,
                    "side": 1 if direc == "BUY" else -1,
                    "atr": atr, "hivol": hivol,
                    "arms": "h4", "day_open": day_open, "level": lvl,
                })
                live.pop(direc)       # a zone flips once per day
            if not live:
                break
    return pd.DataFrame(rows)
