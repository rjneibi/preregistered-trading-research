"""London Breakout (Variant A, Asian box) - standalone signal module for a live bot.

Dependencies: numpy, pandas, PyYAML (only for load_params), Python >= 3.9 (zoneinfo).
No dependency on the research package.

Contract
--------
decide(bars_1m, now_utc, params, trades_taken_today=0, daily=None, box_ratio_history=None)
    bars_1m : DataFrame indexed by tz-aware UTC bar-OPEN timestamps (1-minute bars),
              columns open, high, low, close, volume. Mid prices are what the research
              used. Supply at least 30 calendar days if vol_k > 0, else 2 days.
    now_utc : tz-aware timestamp. Only bars whose close (open + 1 min) <= now are used.
    Returns a Decision. action == "ENTER" means: enter at market NOW (the next bar open),
    then call finalize(decision, fill_mid) to get the exact stop and target to place.

on_bar(position, bar) -> exit decision for an open position (stop first if both hit).

The module only ever reports a signal on the signal-timeframe bar that has *just* closed;
if the first qualifying bar of the day is older (bot was offline), it returns NONE/stale,
because entering late is not what was tested.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field, asdict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
TKY = ZoneInfo("Asia/Tokyo")
UTC = dt.timezone.utc


@dataclass(frozen=True)
class Params:
    box_rule: str = "utc0007"        # utc0007 | utc2307 | tokyo | ny1904
    signal_tf: int = 5               # minutes: 1 | 5 | 15
    breakout: str = "close"          # close | whole | buffer
    buffer_atr: float = 0.0          # breakout=buffer: close beyond edge + buffer_atr * ATR
    strong: str = "none"             # none | body50 | range1atr | close25
    vol_k: float = 0.0               # 0 = ignore volume
    window_min: int = 120            # signal bar must close within this many minutes of 08:00 London
    fresh: bool = False              # previous signal-tf bar must have closed inside the box
    stop_rule: str = "opp"           # in25 | mid | opp | candle | atr<k>
    rr: float = 2.0                  # inf = no target
    exit_local: tuple = (16, 30)     # forced flat, London time
    box_filter: str = "none"         # none | p20_80 | no_narrow | no_wide | narrow | wide
    trend: str = "none"              # none | ema20 | ema50 | prevclose
    max_trades_per_day: int = 1
    min_box_coverage: float = 0.5
    atr_len: int = 14
    vol_lookback_days: int = 20
    box_pct_lookback: int = 250


@dataclass
class Decision:
    action: str                      # NONE | ENTER
    reason: str
    direction: int = 0               # +1 long, -1 short
    signal_bar_utc: pd.Timestamp | None = None
    box_hi: float = np.nan
    box_lo: float = np.nan
    ref_price: float = np.nan        # signal bar close (indicative only)
    stop_abs: float = np.nan         # absolute stop for box/candle rules
    stop_dist: float = np.nan        # distance for ATR rules
    rr: float = np.nan
    exit_utc: pd.Timestamp | None = None
    info: dict = field(default_factory=dict)


def load_params(path):
    import yaml
    y = yaml.safe_load(open(path))
    s = y["signal"]
    return Params(box_rule=s["box_rule"], signal_tf=int(s["signal_tf_min"]), breakout=s["breakout"],
                  buffer_atr=float(s.get("buffer_atr", 0.0)), strong=s["strong_candle"],
                  vol_k=float(s.get("volume_k", 0.0)), window_min=int(s["entry_window_min"]),
                  fresh=bool(s.get("fresh_break", False)), stop_rule=y["exits"]["stop_rule"],
                  rr=float("inf") if str(y["exits"]["rr"]) == "none" else float(y["exits"]["rr"]), exit_local=tuple(y["exits"]["forced_exit_london"]),
                  box_filter=s.get("box_filter", "none"), trend=s.get("trend_filter", "none"),
                  max_trades_per_day=int(y["risk"]["max_trades_per_day"]))


# ---------------------------------------------------------------- session clock

def _utc(d, hh, mm, tz):
    return pd.Timestamp(dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)).tz_convert("UTC")


def session_times(d: dt.date, p: Params):
    """Box window, London open, entry-window end and forced exit for London date d (UTC)."""
    lon_open = _utc(d, 8, 0, LON)
    prev = d - dt.timedelta(days=1)
    b0, b1 = {
        "utc0007": (_utc(d, 0, 0, UTC), _utc(d, 7, 0, UTC)),
        "utc2307": (_utc(prev, 23, 0, UTC), _utc(d, 7, 0, UTC)),
        "tokyo": (_utc(d, 9, 0, TKY), _utc(d, 15, 0, TKY)),
        "ny1904": (_utc(prev, 19, 0, NY), _utc(d, 4, 0, NY)),
    }[p.box_rule]
    b1 = min(b1, lon_open)
    return dict(box_start=b0, box_end=b1, open=lon_open,
                win_end=lon_open + pd.Timedelta(minutes=p.window_min),
                exit=_utc(d, p.exit_local[0], p.exit_local[1], LON))


# ---------------------------------------------------------------- helpers

def _resample(closed: pd.DataFrame, tf: int, now):
    if tf == 1:
        b = closed.copy()
    else:
        b = closed.resample(f"{tf}min", origin="epoch", label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        b = b[b.index + pd.Timedelta(minutes=tf) <= now]          # complete buckets only
    pc = b.close.shift(1).fillna(b.close)
    tr = np.maximum.reduce([b.high - b.low, (b.high - pc).abs(), (b.low - pc).abs()])
    b["atr"] = pd.Series(tr, index=b.index).rolling(14, min_periods=14).mean()
    b["atr_prev"] = b.atr.shift(1)
    return b


def _vol_ratio(b: pd.DataFrame, lookback: int):
    loc = b.index.tz_convert(LON)
    slot = loc.hour * 60 + loc.minute
    med = b.volume.groupby(slot).transform(lambda x: x.shift(1).rolling(lookback, min_periods=10).median())
    return b.volume / med


def daily_from_bars(bars_1m: pd.DataFrame) -> pd.DataFrame:
    """London-date daily bars with the prior-day features the filters need."""
    loc = bars_1m.index.tz_convert(LON)
    g = bars_1m.groupby(loc.date)
    d = pd.DataFrame({"o": g.open.first(), "h": g.high.max(), "l": g.low.min(), "c": g.close.last()})
    pc = d.c.shift(1)
    tr = np.maximum.reduce([d.h - d.l, (d.h - pc).abs(), (d.l - pc).abs()])
    d["atr14_prev"] = pd.Series(tr, index=d.index).rolling(14).mean().shift(1)
    d["ema20_prev"] = d.c.ewm(span=20, adjust=False).mean().shift(1)
    d["ema50_prev"] = d.c.ewm(span=50, adjust=False).mean().shift(1)
    d["prev_c"] = pc
    return d


def _box_ok(p, ratio_today, history):
    if p.box_filter == "none":
        return True, np.nan
    h = np.asarray([x for x in (history or [])[-(p.box_pct_lookback - 1):] if np.isfinite(x)])
    if len(h) < 59 or not np.isfinite(ratio_today):
        return False, np.nan
    pct = float((h < ratio_today).mean())
    ok = {"p20_80": .2 <= pct <= .8, "no_narrow": pct >= .2, "no_wide": pct <= .8,
          "narrow": pct < .5, "wide": pct >= .5}[p.box_filter]
    return ok, pct


# ---------------------------------------------------------------- main entry point

def decide(bars_1m: pd.DataFrame, now_utc, p: Params, trades_taken_today: int = 0,
           daily: pd.DataFrame | None = None, box_ratio_history=None) -> Decision:
    now = pd.Timestamp(now_utc).tz_convert("UTC")
    d = now.tz_convert(LON).date()
    if d.weekday() >= 5:
        return Decision("NONE", "weekend")
    T = session_times(d, p)
    if trades_taken_today >= p.max_trades_per_day:
        return Decision("NONE", "max trades reached")
    if now < T["open"] + pd.Timedelta(minutes=p.signal_tf):
        return Decision("NONE", "before first signal bar closes")
    closed = bars_1m[bars_1m.index + pd.Timedelta(minutes=1) <= now]
    box = closed[(closed.index >= T["box_start"]) & (closed.index < T["box_end"])]
    n_exp = (T["box_end"] - T["box_start"]).total_seconds() / 60
    if n_exp <= 0 or len(box) / n_exp < p.min_box_coverage:
        return Decision("NONE", f"insufficient box data ({len(box)}/{int(n_exp)} bars)")
    bh, bl = float(box.high.max()), float(box.low.min())
    if not closed.index[closed.index >= T["open"]].size or \
            closed.index[closed.index >= T["open"]][0] >= T["open"] + pd.Timedelta(minutes=5):
        return Decision("NONE", "no bar at the London open (holiday or data gap)", box_hi=bh, box_lo=bl)

    if p.box_filter != "none" or p.trend != "none":
        if daily is None:
            daily = daily_from_bars(bars_1m)
        drow = daily.loc[d] if d in daily.index else None
        if drow is None:
            return Decision("NONE", "no daily features", box_hi=bh, box_lo=bl)
        ok, pct = _box_ok(p, (bh - bl) / drow.atr14_prev, box_ratio_history)
        if not ok:
            return Decision("NONE", f"box filter ({p.box_filter}) pct={pct:.2f}", box_hi=bh, box_lo=bl)

    b = _resample(closed, p.signal_tf, now)
    vr = _vol_ratio(b, p.vol_lookback_days) if p.vol_k > 0 else None
    tf = pd.Timedelta(minutes=p.signal_tf)
    win = b[(b.index >= T["open"]) & (b.index + tf <= T["win_end"])]
    if win.empty:
        return Decision("NONE", "no closed signal bar yet", box_hi=bh, box_lo=bl)
    prev_close = b.close.shift(1)
    first = None
    for ts, r in win.iterrows():
        di = _qualifies(r, prev_close.loc[ts], bh, bl, p, vr.loc[ts] if vr is not None else np.nan)
        if di and p.trend != "none":
            di = di if _trend_ok(di, drow, closed, T, bh, bl, p) else 0
        if di:
            first = (ts, r, di)
            break
    last_closed_bar = b.index[-1]
    if first is None:
        done = now >= T["win_end"]
        return Decision("NONE", "entry window over, no setup" if done else "no setup yet", box_hi=bh, box_lo=bl)
    ts, r, di = first
    if ts != last_closed_bar:
        return Decision("NONE", f"stale signal at {ts} (not the bar that just closed)", box_hi=bh, box_lo=bl)
    dec = Decision("ENTER", "breakout", direction=di, signal_bar_utc=ts, box_hi=bh, box_lo=bl,
                   ref_price=float(r.close), rr=p.rr, exit_utc=T["exit"],
                   info=dict(signal_high=float(r.high), signal_low=float(r.low), atr=float(r.atr)))
    rule = p.stop_rule
    w = bh - bl
    if rule == "in25":
        dec.stop_abs = bh - 0.25 * w if di > 0 else bl + 0.25 * w
    elif rule == "mid":
        dec.stop_abs = (bh + bl) / 2
    elif rule == "opp":
        dec.stop_abs = bl if di > 0 else bh
    elif rule == "candle":
        dec.stop_abs = float(r.low) if di > 0 else float(r.high)
    elif rule.startswith("atr"):
        dec.stop_dist = float(rule[3:]) * float(r.atr)
    else:
        raise ValueError(rule)
    return dec


def _qualifies(r, prev_close, bh, bl, p, vratio):
    """+1 / -1 if this closed signal bar is a valid breakout, else 0."""
    rng = r.high - r.low
    atr = r.atr
    buf = p.buffer_atr * atr if p.breakout == "buffer" else 0.0
    if p.breakout == "whole":
        up, dn = r.low > bh, r.high < bl
    else:
        up, dn = r.close > bh + buf, r.close < bl - buf
    if p.fresh:
        up = up and prev_close <= bh
        dn = dn and prev_close >= bl
    if p.strong == "body50":
        up = up and r.close > r.open and (r.close - r.open) >= 0.5 * rng
        dn = dn and r.close < r.open and (r.open - r.close) >= 0.5 * rng
    elif p.strong == "range1atr":
        up = up and r.close > r.open and rng >= r.atr_prev
        dn = dn and r.close < r.open and rng >= r.atr_prev
    elif p.strong == "close25":
        up = up and r.close > r.open and r.close >= r.high - 0.25 * rng
        dn = dn and r.close < r.open and r.close <= r.low + 0.25 * rng
    if p.vol_k > 0 and not (np.isfinite(vratio) and vratio >= p.vol_k):
        return 0
    return 1 if up else (-1 if dn else 0)


def _trend_ok(di, drow, closed, T, bh, bl, p):
    if p.trend == "prevclose":
        mid = (bh + bl) / 2
        return (drow.prev_c > mid) if di > 0 else (drow.prev_c < mid)
    op = float(closed[closed.index >= T["open"]].open.iloc[0])
    ref = drow.ema20_prev if p.trend == "ema20" else drow.ema50_prev
    return op > ref if di > 0 else op < ref


def finalize(dec: Decision, fill_mid: float):
    """Exact stop and target for the actual entry price (mid). The research measured R from
    the planned entry = next bar open, which is what fill_mid represents."""
    if dec.action != "ENTER":
        raise ValueError("not an entry")
    stop = dec.stop_abs if np.isfinite(dec.stop_abs) else fill_mid - dec.direction * dec.stop_dist
    risk = (fill_mid - stop) * dec.direction
    if risk <= 0:
        return None                                   # stop on the wrong side: skip the trade
    target = fill_mid + dec.direction * dec.rr * risk if np.isfinite(dec.rr) else np.nan
    return dict(direction=dec.direction, entry=fill_mid, stop=stop, target=target, risk=risk,
                exit_utc=dec.exit_utc)


def on_bar(position: dict, bar: dict, now_utc=None):
    """Exit check for one closed 1m bar (mid prices, as in the research).
    position: dict from finalize(). bar: dict open/high/low/close and 'time' (UTC open time).
    Returns ("STOP"|"TARGET"|"TIME"|None, price). Stop first if both are touched."""
    di = position["direction"]
    if bar.get("time") is not None and pd.Timestamp(bar["time"]) >= position["exit_utc"]:
        return "TIME", bar["open"]
    lo, hi = (bar["low"], bar["high"]) if di > 0 else (-bar["high"], -bar["low"])
    stop, tgt = di * position["stop"], di * position["target"] if np.isfinite(position["target"]) else np.inf
    if lo <= stop:
        o = di * bar["open"]
        return "STOP", di * min(stop, o)
    if hi >= tgt:
        return "TARGET", position["target"]
    return None, np.nan


def position_size(equity, risk_fraction, risk_price, value_per_point):
    """Units so that hitting the stop loses risk_fraction of equity."""
    return equity * risk_fraction / (risk_price * value_per_point)
