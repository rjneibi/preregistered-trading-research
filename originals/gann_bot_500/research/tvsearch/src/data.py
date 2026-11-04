"""Load, validate and resample bars. Every timeframe of a dataset is resampled from ONE base series.

Bar frame columns: t (bar open, epoch s, local clock of the venue), o h l c v, sp (spread $, cost paid on entry),
sess (int session id), mins (minutes since session open), dow (0=Mon), wk (week id), mon (month id).

XAU  broker XAUUSD from the VM. Bars are BID; ask = bid + spread (floor $0.22). Volume = tick volume (what
     TradingView's VWAP uses on CFD gold too). Clock = broker server time (UTC+2/+3, NY-close aligned), so the
     server day IS the trading session: session VWAP resets at 00:00 server = 17:00 New York.
SPY/QQQ  Yahoo regular-hours bars, clock = America/New_York, session 09:30-16:00, 1 share.
"""
import os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
LOG = []
SPREAD_FLOOR = 0.22


def log(msg):
    LOG.append(msg); print("  [data]", msg)


def _frame(t_local, o, h, l, c, v, sp, sess_start_min):
    df = pd.DataFrame({"t": np.asarray(t_local, np.int64), "o": o, "h": h, "l": l, "c": c, "v": np.asarray(v, float), "sp": sp})
    sh = df.t.values - sess_start_min * 60
    sess = sh // 86400
    df["sess"] = sess                                           # days since 1970-01-01 of the session
    df["mins"] = (sh - sess * 86400) // 60
    df["dow"] = (sess + 3) % 7                                  # 1970-01-01 was a Thursday -> 0 = Monday
    df["wk"] = (sess + 3) // 7                                  # Monday-anchored week
    day = pd.to_datetime(sess * 86400, unit="s")
    df["mon"] = (day.year * 12 + day.month).values
    return df


def validate(df, name, base_min):
    t = df.t.values
    dup = int((np.diff(t) == 0).sum()); back = int((np.diff(t) < 0).sum())
    bad = int(((df.h < df[["o", "c"]].max(1)) | (df.l > df[["o", "c"]].min(1))).sum())
    nan = int(df[["o", "h", "l", "c"]].isna().any(axis=1).sum())
    same = df.sess.values[1:] == df.sess.values[:-1]
    gaps = int(((np.diff(t) > base_min * 60 * 5) & same).sum())
    ret = np.abs(np.diff(np.log(df.c.values)))
    jumps = int((ret > 0.15).sum())
    log(f"{name}: {len(df)} bars {pd.to_datetime(t[0], unit='s')}..{pd.to_datetime(t[-1], unit='s')} | dup {dup} out-of-order {back} "
        f"bad-OHLC {bad} NaN {nan} | intra-session gaps >5 bars {gaps} | |bar return|>15% {jumps} (split check)")
    df = df.drop_duplicates("t").sort_values("t").reset_index(drop=True)
    return df


def load_xau(kind="m1"):
    Z = np.load(os.path.join(DATA, "xau_tv.npz"))
    R = Z[kind]
    df = _frame(R["time"], R["open"], R["high"], R["low"], R["close"], R["tick_volume"],
                np.maximum(R["spread"] * 0.01, SPREAD_FLOOR), 0)
    return validate(df, f"XAU {kind}", 1 if kind == "m1" else 5)


def load_us(tk, iv):
    d = pd.read_csv(os.path.join(DATA, f"{tk}_{iv}.csv"))
    step = {"1m": 60, "5m": 300, "1h": 3600, "1d": 86400}[iv]
    if iv != "1d":
        d = d[(d.time % 60 == 0)]                                   # drop the live, unfinished last bar
    loc = pd.to_datetime(d.time, unit="s", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    tl = (loc - pd.Timestamp(0)).dt.total_seconds().astype(np.int64)
    if iv == "1d":
        tl = tl - tl % 86400 + 9 * 3600 + 1800
    df = _frame(tl.values, d.open.values, d.high.values, d.low.values, d.close.values, d.volume.fillna(0).values,
                np.zeros(len(d)), 9 * 60 + 30)
    if iv != "1d":
        keep = (df.mins >= 0) & (df.mins < 390)
        if (~keep).sum():
            log(f"{tk} {iv}: dropped {(~keep).sum()} bars outside 09:30-16:00 ET")
        df = df[keep].reset_index(drop=True)
        if iv == "1h":                                                # Yahoo's last hourly bar is 15:30-16:00
            pass
    return validate(df, f"{tk} {iv}", step // 60)


def resample(df, tf):
    """tf in minutes, or 'D' for one bar per session. Bins anchored at the session open (TradingView style)."""
    if tf == "D":
        key = df.sess.values
    else:
        key = df.sess.values * 10_000 + (df.mins.values // tf)
    g = df.groupby(key, sort=True)
    out = pd.DataFrame({"t": g.t.first(), "o": g.o.first(), "h": g.h.max(), "l": g.l.min(), "c": g.c.last(),
                        "v": g.v.sum(), "sp": g.sp.mean(), "sess": g.sess.first(), "mins": g.mins.first(),
                        "dow": g.dow.first(), "wk": g.wk.first(), "mon": g.mon.first()}).reset_index(drop=True)
    return out


def trim_partial(df, full_min):
    """Drop an incomplete first/last session (fetch window started mid-day, or today is still trading)."""
    for sid in (df.sess.iloc[0], df.sess.iloc[-1]):
        m = df.sess == sid
        span = df.mins[m].max() - df.mins[m].min()
        if span < full_min * 0.9:
            log(f"trimmed partial session {pd.to_datetime(int(sid) * 86400, unit='s').date()} ({int(m.sum())} bars)")
            df = df[~m]
    return df.reset_index(drop=True)


def arrays(df, tf_min):
    """Plain numpy dict the engine and indicators use."""
    D = {k: df[k].values for k in ("t", "o", "h", "l", "c", "v", "sp", "sess", "mins", "dow", "wk", "mon")}
    N = len(df)
    last = np.r_[np.flatnonzero(D["sess"][1:] != D["sess"][:-1]), N - 1]
    first = np.r_[0, last[:-1] + 1]
    sid = np.cumsum(np.r_[1, D["sess"][1:] != D["sess"][:-1]]) - 1
    D["sess_last"] = last[sid]; D["sess_first"] = first[sid]; D["sid"] = sid
    D["tf"] = tf_min; D["N"] = N
    return D


def last_days(df, days):
    t_end = df.t.values[-1]
    return df[df.t >= t_end - days * 86400].reset_index(drop=True)
