"""Session clock: every time is computed from local wall-clock rules via zoneinfo, then
expressed as epoch minutes UTC. No hard-coded UTC offsets anywhere.
"""
import datetime as dt
from zoneinfo import ZoneInfo

LON = ZoneInfo("Europe/London")
NY = ZoneInfo("America/New_York")
TKY = ZoneInfo("Asia/Tokyo")
UTC = dt.timezone.utc


def emin(date, hh, mm, tz):
    """Epoch minutes (UTC) of local wall time date hh:mm in tz."""
    local = dt.datetime(date.year, date.month, date.day, hh, mm, tzinfo=tz)
    return int(local.astimezone(UTC).timestamp() // 60)


def prev_weekday(d):
    d = d - dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


# ---------- Variant A: Asian box before the London open ----------

BOX_RULES = ("utc0007", "utc2307", "tokyo", "ny1904")


def variant_a_times(d, box_rule, window_min, exit_hhmm=(16, 30)):
    """Times for London trading date d (a weekday).

    Returns dict of epoch minutes: box_start, box_end, open, win_end, exit.
    The box always ends no later than the London open (the author's 19:00-04:00 NY
    window runs past the London open, so it is truncated there - see docs/gaps.md).
    """
    lon_open = emin(d, 8, 0, LON)
    prev = d - dt.timedelta(days=1)
    if box_rule == "utc0007":
        b0, b1 = emin(d, 0, 0, UTC), emin(d, 7, 0, UTC)
    elif box_rule == "utc2307":
        b0, b1 = emin(prev, 23, 0, UTC), emin(d, 7, 0, UTC)
    elif box_rule == "tokyo":          # Tokyo cash session 09:00-15:00 JST (Japan has no DST)
        b0, b1 = emin(d, 9, 0, TKY), emin(d, 15, 0, TKY)
    elif box_rule == "ny1904":         # author's PDF Asia session, New York time
        b0, b1 = emin(prev, 19, 0, NY), emin(d, 4, 0, NY)
    else:
        raise ValueError(box_rule)
    b1 = min(b1, lon_open)
    return dict(box_start=b0, box_end=b1, open=lon_open, win_end=lon_open + window_min,
                exit=emin(d, exit_hhmm[0], exit_hhmm[1], LON))


# ---------- Variant B: three sessions in New York time ----------

SESSIONS = ("asia", "london", "ny")


def variant_b_times(d, session, window_min):
    """Times for the given session on trading date d (weekday), New York clock.

    Asia 19:00 (previous calendar day) - 04:00, London 03:00-12:00, NY 09:30-16:00.
    Levels come from the previous session, cut off 5 minutes before this open, because
    Asia is still open at the London open and London is still open at the NY open.
    """
    if session == "asia":
        prev = d - dt.timedelta(days=1)
        o, e = emin(prev, 19, 0, NY), emin(d, 4, 0, NY)
        pd_ = prev_weekday(d)
        p0, p1 = emin(pd_, 9, 30, NY), emin(pd_, 16, 0, NY)
    elif session == "london":
        o, e = emin(d, 3, 0, NY), emin(d, 12, 0, NY)
        prev = d - dt.timedelta(days=1)
        p0, p1 = emin(prev, 19, 0, NY), emin(d, 4, 0, NY)
    elif session == "ny":
        o, e = emin(d, 9, 30, NY), emin(d, 16, 0, NY)
        p0, p1 = emin(d, 3, 0, NY), emin(d, 12, 0, NY)
    else:
        raise ValueError(session)
    p1 = min(p1, o - 5)
    return dict(prev_start=p0, prev_end=p1, open=o, win_end=o + window_min, exit=e)
