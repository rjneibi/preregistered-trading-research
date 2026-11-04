"""Derived series built only from information available at each bar's close."""
import numpy as np
import pandas as pd


def resample(m, tf):
    """Aggregate 1m bars into tf-minute bars aligned to the UTC clock.

    Returns dict: t (bar open, epoch min), o,h,l,c,v, atr (ATR14 incl. this bar),
    atr_prev (ATR14 up to the previous bar), i_first (first 1m index in the bar).
    """
    t = m["t"]
    if tf == 1:
        b = dict(t=t.copy(), o=m["o"], h=m["h"], l=m["l"], c=m["c"], v=m["v"],
                 i_first=np.arange(len(t)))
    else:
        bucket = (t // tf) * tf
        starts = np.flatnonzero(np.r_[True, bucket[1:] != bucket[:-1]])
        ends = np.r_[starts[1:], len(t)] - 1
        b = dict(t=bucket[starts], o=m["o"][starts], h=np.maximum.reduceat(m["h"], starts),
                 l=np.minimum.reduceat(m["l"], starts), c=m["c"][ends],
                 v=np.add.reduceat(m["v"], starts), i_first=starts)
    prev_c = np.r_[b["c"][0], b["c"][:-1]]
    tr = np.maximum.reduce([b["h"] - b["l"], np.abs(b["h"] - prev_c), np.abs(b["l"] - prev_c)])
    atr = pd.Series(tr).rolling(14, min_periods=14).mean().values
    b["atr"] = atr
    b["atr_prev"] = np.r_[np.nan, atr[:-1]]
    b["tf"] = tf
    return b


def local_slot(t, tz):
    """Local minute-of-day for epoch-minute array t."""
    ts = pd.to_datetime(t * 60, unit="s", utc=True).tz_convert(tz)
    return (ts.hour * 60 + ts.minute).values


def volume_ratio(b, tz, lookback=20):
    """Bar volume / median volume of the same local time-of-day bar on the previous
    `lookback` occurrences (today excluded). NaN until 10 prior observations exist."""
    slot = local_slot(b["t"], tz)
    s = pd.Series(b["v"])
    med = s.groupby(slot).transform(
        lambda x: x.shift(1).rolling(lookback, min_periods=10).median())
    with np.errstate(divide="ignore", invalid="ignore"):
        return (s / med).values


def daily_bars(m, tz):
    """Daily OHLC by local calendar date in tz (all hours). Index = datetime.date."""
    ts = pd.to_datetime(m["t"] * 60, unit="s", utc=True).tz_convert(tz)
    df = pd.DataFrame({"o": m["o"], "h": m["h"], "l": m["l"], "c": m["c"], "d": ts.date})
    g = df.groupby("d")
    d = pd.DataFrame({"o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last()})
    pc = d.c.shift(1)
    tr = np.maximum.reduce([d.h - d.l, (d.h - pc).abs(), (d.l - pc).abs()])
    d["atr14_prev"] = pd.Series(tr, index=d.index).rolling(14).mean().shift(1)
    d["ema20_prev"] = d.c.ewm(span=20, adjust=False).mean().shift(1)
    d["ema50_prev"] = d.c.ewm(span=50, adjust=False).mean().shift(1)
    d["prev_c"] = pc
    # realised-vol regime: 20d stdev of daily returns vs its trailing 1y median (prior days)
    r = np.log(d.c).diff()
    rv = r.rolling(20).std().shift(1)
    d["rv20_prev"] = rv
    d["rv_regime"] = (rv / rv.rolling(250, min_periods=120).median()).values
    return d
