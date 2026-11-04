"""Shared clock correction for the HistData XAUUSD file. Epoch seconds in, epoch seconds out.

Measured against Dukascopy on every trading day, 2013 to 2026 (`clock_map.py`): stamps run UTC+1 for part of the year and
UTC otherwise. Through 2018 the shift follows US switch dates. From 2019 it follows EU switch dates. No day breaks this rule.
Years before the Dukascopy overlap (2010-2012) are assumed to follow the US dates.
"""
from datetime import date, timedelta

import numpy as np

EU_FROM = 2019
E0 = date(1970, 1, 1)


def us_dst_bounds(y):
    """Epoch seconds of 00:00 + 2h on the second Sunday of March and first Sunday of November."""
    m = date(y, 3, 8)
    m += timedelta(days=(6 - m.weekday()) % 7)
    n = date(y, 11, 1)
    n += timedelta(days=(6 - n.weekday()) % 7)
    return (m - E0).days * 86400 + 7200, (n - E0).days * 86400 + 7200


def eu_bounds(y):
    """Epoch seconds of 00:00 + 1h on the last Sunday of March and of October."""
    a = date(y, 3, 31)
    a -= timedelta(days=(a.weekday() + 1) % 7)
    b = date(y, 10, 31)
    b -= timedelta(days=(b.weekday() + 1) % 7)
    return (a - E0).days * 86400 + 3600, (b - E0).days * 86400 + 3600


def shifted(stamp):
    """True where a HistData stamp runs UTC+1."""
    s = np.asarray(stamp, dtype=np.int64)
    y0 = str(np.datetime64(int(s.min()), "s"))[:4]
    y1 = str(np.datetime64(int(s.max()), "s"))[:4]
    out = np.zeros(len(s), bool)
    for y in range(int(y0), int(y1) + 1):
        a, b = eu_bounds(y) if y >= EU_FROM else us_dst_bounds(y)
        out |= (s >= a) & (s < b)
    return out


def true_utc(stamp):
    """Epoch seconds in true UTC for HistData stamps."""
    s = np.asarray(stamp, dtype=np.int64)
    return s - shifted(s).astype(np.int64) * 3600
