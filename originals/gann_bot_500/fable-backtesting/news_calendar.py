"""
news_calendar.py — live economic-calendar module for the flip-scalp bot.

Backtest-validated rule (fable-backtesting rounds 3b + 9): entries on
FOMC-statement / NFP / CPI days earn PF 1.4-2.3 in BOTH eras -> size 1.5x.
ONLY those three events count — do not broaden to all red news (untested).

Sources, in order:
  1. ForexFactory weekly XML (free, no key):
     https://nfs.faireconomy.media/ff_calendar_thisweek.xml
     Filter: currency=USD, impact=High, title matching FOMC/Non-Farm/CPI.
     Cached to calendar/ff_week_cache.json (refreshed if older than 12h).
  2. Fallback when feed unreachable: static FOMC schedule (Fed website,
     hardcoded 2026-2027) + first-Friday-of-month NFP rule + CPI schedule
     (BLS, hardcoded 2026). Accuracy note: NFP rule matched 9/12 exact
     dates in 2015; good enough for a 1-day sizing tilt.

API:
    news_weight(dt=None) -> 1.5 if dt (default: now UTC) is a validated
                            news day, else 1.0
    is_news_day(date)    -> bool
    week_events()        -> list of dicts for logging/telegram
"""
from __future__ import annotations

import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
CACHE = Path(__file__).parent / "calendar" / "ff_week_cache.json"
CACHE_TTL_H = 12
TITLE_RE = re.compile(
    r"(FOMC (Statement|Press)|Federal Funds Rate|Non-?Farm|CPI m/m|CPI y/y|"
    r"Core CPI)", re.I)

# ---- static fallback (update yearly; sources in module docstring) --------
FOMC_STATIC = {
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29",
    "2026-09-16", "2026-10-28", "2026-12-09",
    "2027-01-27", "2027-03-17", "2027-04-28", "2027-06-09", "2027-07-28",
    "2027-09-15", "2027-10-27", "2027-12-08",
}
CPI_STATIC = {
    "2026-01-13", "2026-02-11", "2026-03-11", "2026-04-10", "2026-05-12",
    "2026-06-10", "2026-07-14", "2026-08-12", "2026-09-11", "2026-10-14",
    "2026-11-10", "2026-12-10",
}


def _first_friday(y: int, m: int) -> date:
    d = date(y, m, 1)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def _fetch_feed() -> list[dict] | None:
    try:
        r = requests.get(FEED_URL, timeout=15,
                         headers={"User-Agent": "gannbot-calendar/1.0"})
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception:
        return None
    events = []
    for ev in root.iter("event"):
        g = {c.tag: (c.text or "").strip() for c in ev}
        if g.get("country") != "USD" or g.get("impact") != "High":
            continue
        if not TITLE_RE.search(g.get("title", "")):
            continue
        try:  # feed date format: MM-DD-YYYY
            d = datetime.strptime(g["date"], "%m-%d-%Y").date()
        except (KeyError, ValueError):
            continue
        events.append({"date": d.isoformat(), "title": g["title"],
                       "time": g.get("time", "")})
    return events


def _load_events() -> tuple[list[dict], str]:
    """Return (validated events this week, source_tag)."""
    if CACHE.exists():
        try:
            c = json.loads(CACHE.read_text())
            if time.time() - c["fetched"] < CACHE_TTL_H * 3600:
                return c["events"], "cache"
        except Exception:
            pass
    events = _fetch_feed()
    if events is not None:
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(
            {"fetched": time.time(), "events": events}))
        return events, "live"
    # stale cache beats static fallback
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text())["events"], "stale-cache"
        except Exception:
            pass
    return [], "fallback"


def is_news_day(d: date) -> bool:
    events, src = _load_events()
    if src != "fallback":
        # The feed covers the CURRENT calendar week (Sun-Sat). Inside that
        # window it is authoritative — it knows holiday-shifted dates the
        # static rules get wrong (e.g. NFP on Thu 2026-07-02, July-4th week).
        today = datetime.now(timezone.utc).date()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        if sunday <= d <= sunday + timedelta(days=6):
            return d.isoformat() in {e["date"] for e in events}
    return (d.isoformat() in FOMC_STATIC or d.isoformat() in CPI_STATIC
            or d == _first_friday(d.year, d.month))


def news_weight(dt: datetime | None = None) -> float:
    d = (dt or datetime.now(timezone.utc)).date()
    return 1.5 if is_news_day(d) else 1.0


def week_events() -> list[dict]:
    events, src = _load_events()
    return [{**e, "source": src} for e in events]


if __name__ == "__main__":
    print("feed events this week (validated types only):")
    evs = week_events()
    for e in evs:
        print(f"  {e['date']} {e['time']:>8}  {e['title']}  [{e['source']}]")
    if not evs:
        print("  (none from feed — fallback active)")
    today = datetime.now(timezone.utc).date()
    for i in range(7):
        d = today + timedelta(days=i)
        w = news_weight(datetime(d.year, d.month, d.day,
                                 tzinfo=timezone.utc))
        print(f"  {d} ({d.strftime('%a')}): weight={w}")
