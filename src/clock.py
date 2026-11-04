"""HistData XAUUSD clock correction. Epoch seconds in, epoch seconds out.

Stamps run UTC+1 for part of each year and UTC otherwise. Through 2018 the shift follows US switch dates, from 2019 EU switch
dates. Measured against Dukascopy on every trading day from 2013 to 2026. Years 2010 to 2012 have no overlap, so they are assumed
to follow US dates and are labelled ASSUMED-CLOCK. The audit's working copy is audit/phaseC/clockfix.py, and tests/test_clock.py
keeps the two equal.
"""
from datetime import date, timedelta

import numpy as np

EU_FROM = 2019
ASSUMED_CLOCK_YEARS = (2010, 2011, 2012)
E0 = date(1970, 1, 1)


def us_dst_bounds(y):
    """Epoch seconds of 02:00 on the second Sunday of March and the first Sunday of November."""
    m = date(y, 3, 8)
    m += timedelta(days=(6 - m.weekday()) % 7)
    n = date(y, 11, 1)
    n += timedelta(days=(6 - n.weekday()) % 7)
    return (m - E0).days * 86400 + 7200, (n - E0).days * 86400 + 7200


def eu_bounds(y):
    """Epoch seconds of 01:00 on the last Sunday of March and of October."""
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
