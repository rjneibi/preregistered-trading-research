"""Data-quality report: gaps, duplicates, bad ticks, missing days, DST, spreads at the open."""
import datetime as dt

import numpy as np
import pandas as pd

from . import sessions as S


def dst_switch_dates(year, tz):
    """Dates on which tz changes UTC offset."""
    out = []
    d = dt.date(year, 1, 1)
    prev = None
    while d.year == year:
        off = dt.datetime(d.year, d.month, d.day, 12, tzinfo=tz).utcoffset()
        if prev is not None and off != prev:
            out.append(d)
        prev = off
        d += dt.timedelta(days=1)
    return out


def report(name, m, qc):
    t = m["t"]
    ts = pd.to_datetime(t * 60, unit="s", utc=True)
    lon = ts.tz_convert(S.LON)
    df = pd.DataFrame({"d": lon.date, "mod": lon.hour * 60 + lon.minute, "sp": m["sp"],
                       "dow": lon.dayofweek})
    # London morning window 07:00-12:00 local: the part of the day this study trades
    core = df[(df["mod"] >= 420) & (df["mod"] < 720) & (df.dow < 5)]
    per_day = core.groupby("d").size()
    all_wd = pd.bdate_range(lon[0].date(), lon[-1].date()).date
    per_day = per_day.reindex(all_wd, fill_value=0)
    missing = per_day[per_day == 0]
    thin = per_day[(per_day > 0) & (per_day < 0.8 * 300)]
    qc["weekdays_in_range"] = len(all_wd)
    qc["weekdays_no_morning_data"] = len(missing)
    qc["weekdays_thin_morning_data(<80%)"] = len(thin)
    qc["missing_days_sample"] = ", ".join(str(x) for x in list(missing.index)[:25])
    md = pd.Series(list(missing.index))
    qc["missing_days_on_dec24_25_26_31_jan1"] = int(sum((x.month == 12 and x.day in (24, 25, 26, 31)) or
                                                        (x.month == 1 and x.day == 1) for x in md))
    # largest intraday gaps inside the London morning
    dt_ = np.diff(t)
    same_morning = (df["mod"].values[1:] >= 420) & (df["mod"].values[1:] < 720) & (df.dow.values[1:] < 5) \
        & (df.d.values[1:] == df.d.values[:-1])
    gaps = dt_[same_morning]
    qc["morning_gaps_>5min"] = int((gaps > 5).sum())
    qc["morning_gaps_>30min"] = int((gaps > 30).sum())
    # DST: is there a bar within 5 minutes of the London open on the days around each switch?
    bad_dst = []
    years = range(lon[0].year, lon[-1].year + 1)
    for y in years:
        for tz in (S.LON, S.NY):
            for sd in dst_switch_dates(y, tz):
                for off in range(-3, 4):
                    d = sd + dt.timedelta(days=off)
                    if d.weekday() >= 5 or d < lon[0].date() or d > lon[-1].date():
                        continue
                    o = S.emin(d, 8, 0, S.LON)
                    i = np.searchsorted(t, o)
                    if i >= len(t) or t[i] > o + 5:
                        bad_dst.append(str(d))
    qc["dst_window_days_missing_open_bar"] = len(set(bad_dst))
    # spread profile around the London open (local minutes), median over all days
    prof = df[df.dow < 5].groupby("mod").sp.median()
    qc["spread_med_0700_0759"] = float(prof.loc[420:479].median())
    qc["spread_med_0800_0804"] = float(prof.loc[480:484].median())
    qc["spread_med_0805_0829"] = float(prof.loc[485:509].median())
    qc["spread_med_1000_1200"] = float(prof.loc[600:719].median())
    qc["spread_med_overnight_0000_0600"] = float(prof.loc[0:359].median())
    # opening spread by year (08:00-08:04 London)
    op = df[(df["mod"] >= 480) & (df["mod"] < 485) & (df.dow < 5)]
    yr = pd.to_datetime(pd.Series(op.d.values)).dt.year.values
    qc["open_spread_by_year"] = pd.Series(op.sp.values).groupby(yr).median().round(5).to_dict()
    return qc
