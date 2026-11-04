"""HSW harness unit tests — synthetic fixtures ONLY (frozen prerequisite:
these must pass before hsw_runner touches real data).

Covers: penetration without reclaim; reclaim after the 60-min window;
both-sides void; depth threshold boundary; session boundary 06:59 vs 07:00;
anti-scalp floor and target-guard voiding; 1/day selection; mirror-arm entry
parity.

Run:  .venv/Scripts/python -m pytest prereg/test_hsw_pack.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from goldbot.data import resample_ohlc, wilder_atr  # noqa: E402
from hsw_runner import (_first_episode, find_events, entry_guard,  # noqa: E402
                        one_per_day, run_e2, build_days)


def mk_day(day: str, close: float = 2000.0, spread: float = 0.5,
           mods: dict | None = None) -> pd.DataFrame:
    """1440 M1 bars, flat at `close` with h/l = close +/- spread.
    mods: {minute_of_day: (o, h, l, c)} overrides."""
    idx = pd.date_range(f"{day} 00:00", periods=1440, freq="1min", tz="UTC")
    df = pd.DataFrame({"open": close, "high": close + spread,
                       "low": close - spread, "close": close}, index=idx)
    for m, (o, h, l, c) in (mods or {}).items():
        df.iloc[m] = [o, h, l, c]
    return df


def mk_m1(*days: pd.DataFrame) -> pd.DataFrame:
    return pd.concat(days)


# Day 1 establishes PDH=2010, PDL=1990 (single extreme bars at 10:00/14:00).
DAY1_MODS = {600: (2000, 2010, 1999.5, 2000), 840: (2000, 2000.5, 1990, 2000)}
# Lead-in days (D1-ATR warmup): identical wide-range days. Identical days
# never penetrate each other's extremes, and day 1's 1990/2010 moves stay
# inside the lead-in 1950/2050 range, so lead-in generates zero events.
LEAD_MODS = {600: (2000, 2050, 1999.5, 2000), 840: (2000, 2000.5, 1950, 2000)}


def base_fixture(day2_mods: dict) -> tuple[pd.DataFrame, pd.DataFrame,
                                           pd.Series]:
    lead = [mk_day(str(d.date()), mods=LEAD_MODS)
            for d in pd.date_range("2023-12-17", "2024-01-01")]
    m1 = mk_m1(*lead, mk_day("2024-01-02", mods=DAY1_MODS),
               mk_day("2024-01-03", mods=day2_mods))
    d1, _ = build_days(m1)
    atr_h1 = wilder_atr(resample_ohlc(m1, "1h"), 14)
    return m1, d1, atr_h1


def dip_bars(start_min: int, n_below: int, low: float,
             reclaim_close: float | None = 1992.0) -> dict:
    """n_below bars closing below PDL=1990 with the given low, then one
    reclaim bar (close back above) unless reclaim_close is None."""
    mods = {}
    for i in range(n_below):
        mods[start_min + i] = (1989.0, 1989.5, low, 1989.0)
    if reclaim_close is not None:
        mods[start_min + n_below] = (1989.0, reclaim_close + 0.5,
                                     1988.8, reclaim_close)
        for i in range(1, 6):   # hold near the reclaim px so the entry bar
            mods[start_min + n_below + i] = (reclaim_close,        # is honest
                                             reclaim_close + 0.5,
                                             reclaim_close - 0.5,
                                             reclaim_close)
    return mods


def test_first_episode_no_penetration():
    day = mk_day("2024-01-03")
    assert _first_episode(day, 1990.0, 1) is None


def test_first_episode_reclaim_and_extreme():
    day = mk_day("2024-01-03", mods=dip_bars(480, 5, 1985.0))  # 08:00
    ep = _first_episode(day, 1990.0, 1)
    assert ep["i_rec"] is not None
    assert ep["extreme"] == 1985.0
    assert ep["t_pen"].hour == 8 and ep["t_rec"].minute == 5


def test_no_reclaim_within_window_is_no_signal():
    # 70 bars below the level: reclaim bar arrives after the 60-min window
    day = mk_day("2024-01-03", mods=dip_bars(480, 70, 1985.0))
    ep = _first_episode(day, 1990.0, 1)
    assert ep["i_rec"] is None
    m1, d1, atr_h1 = base_fixture(dip_bars(480, 70, 1985.0))
    cand, _, diag = find_events(m1, d1, atr_h1)
    assert len(cand) == 0 and diag["no_reclaim"] == 1


def test_valid_long_candidate():
    m1, d1, atr_h1 = base_fixture(dip_bars(480, 5, 1985.0))
    cand, touch, diag = find_events(m1, d1, atr_h1)
    assert len(cand) == 1
    ev = cand.iloc[0]
    assert ev.side == 1 and ev.pdl == 1990.0 and ev.pdh == 2010.0
    assert ev.extreme == 1985.0 and abs(ev.depth - 5.0) < 1e-9
    assert ev.event_ts == pd.Timestamp("2024-01-03 08:06", tz="UTC")
    assert len(touch) == 1  # baseline fires on the same penetration
    assert touch.iloc[0].event_ts == pd.Timestamp("2024-01-03 08:01",
                                                  tz="UTC")


def test_both_sides_void():
    mods = {450: (2000, 2012, 1999.5, 2000)}       # 07:30 PDH spike
    mods.update(dip_bars(480, 5, 1985.0))          # 08:00 PDL sweep
    m1, d1, atr_h1 = base_fixture(mods)
    cand, _, diag = find_events(m1, d1, atr_h1)
    assert diag["both_sides_void"] == 1
    assert len(cand) == 1 and cand.iloc[0].side == -1   # the PDH short only


def test_session_boundary():
    # penetration start 06:59 -> excluded; 07:00 -> included
    m1a, d1a, atra = base_fixture(dip_bars(419, 5, 1985.0))   # 06:59
    ca, _, dga = find_events(m1a, d1a, atra)
    assert len(ca) == 0 and dga["asia_window"] == 1
    m1b, d1b, atrb = base_fixture(dip_bars(420, 5, 1985.0))   # 07:00
    cb, _, _ = find_events(m1b, d1b, atrb)
    assert len(cb) == 1


def test_depth_threshold_boundary():
    m1, d1, atr_h1 = base_fixture(dip_bars(480, 5, 1985.0))
    cand, _, _ = find_events(m1, d1, atr_h1)
    cand = entry_guard(m1, cand)
    a = float(cand.iloc[0].atr)
    exact_d = 5.0 / a
    assert len(cand[cand.depth >= exact_d * cand.atr]) == 1        # >= keeps
    assert len(cand[cand.depth >= (exact_d + 1e-6) * cand.atr]) == 0


def test_anti_scalp_guard_and_sl_floor():
    m1, d1, atr_h1 = base_fixture(dip_bars(480, 5, 1985.0))
    cand, _, _ = find_events(m1, d1, atr_h1)
    g = entry_guard(m1, cand)
    assert len(g) == 1
    ev = g.iloc[0]
    # tp_d = mid(2000) - entry, must clear 0.5*ATR
    assert ev.tp_d >= 0.5 * ev.atr
    # SL floor: raw distance entry-extreme vs 0.5*ATR floor
    assert ev.sl_d >= 0.5 * ev.atr
    assert ev.sl_d >= (ev.entry_px - ev.extreme) - 1e-9 or \
        ev.sl_d == 0.5 * ev.atr
    # now a sweep whose reclaim lands AT the prior-day mid -> tp_d ~ 0 -> void
    mods = dip_bars(480, 5, 1985.0, reclaim_close=1999.9)
    mods[486] = (2000.0, 2000.5, 1999.5, 2000.0)   # entry bar open at mid
    m1v, d1v, atrv = base_fixture(mods)
    cv, _, _ = find_events(m1v, d1v, atrv)
    assert len(cv) == 1
    assert len(entry_guard(m1v, cv)) == 0          # voided in ALL arms


def test_one_per_day_picks_earliest():
    df = pd.DataFrame({
        "event_ts": pd.to_datetime(["2024-01-03 09:00", "2024-01-03 14:00",
                                    "2024-01-04 10:00"], utc=True),
        "side": [1, -1, 1], "x": [1, 2, 3]})
    out = one_per_day(df)
    assert len(out) == 2 and list(out.x) == [1, 3]


def test_mirror_entry_parity():
    m1, d1, atr_h1 = base_fixture(dip_bars(480, 5, 1985.0))
    cand, _, _ = find_events(m1, d1, atr_h1)
    sig = entry_guard(m1, cand)
    fwd = run_e2(m1, sig)
    mir = run_e2(m1, sig.assign(side=-sig.side))
    assert list(fwd.entry_ts) == list(mir.entry_ts)
    assert list(fwd.entry_px) == list(mir.entry_px)
    assert (fwd.side.to_numpy() == -mir.side.to_numpy()).all()


if __name__ == "__main__":
    fns = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
