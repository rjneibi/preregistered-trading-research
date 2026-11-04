"""Edge cases for strategy/signal.py (synthetic bars, no data files needed)."""
import numpy as np
import pandas as pd
import pytest

from strategy.signal import Params, decide, finalize, on_bar, session_times

P = Params(box_rule="utc0007", signal_tf=5, stop_rule="opp", rr=2.0, window_min=60)


def make_day(date, open_utc_hour, moves, box=(99.0, 101.0), drop_box_frac=0.0, start_prev_day=True):
    """1m bars: quiet box 99-101 from the previous evening until the London open, then
    `moves` = list of (minute offset from open, close price) applied as step bars."""
    start = pd.Timestamp(date, tz="UTC") - pd.Timedelta(hours=4 if start_prev_day else 0)
    open_ts = pd.Timestamp(date, tz="UTC") + pd.Timedelta(hours=open_utc_hour)
    idx = pd.date_range(start, open_ts + pd.Timedelta(minutes=180), freq="1min", inclusive="left")
    px = np.full(len(idx), 100.0)
    df = pd.DataFrame({"open": px, "high": px + 0.2, "low": px - 0.2, "close": px, "volume": 1.0}, index=idx)
    inbox = (idx < open_ts)
    df.loc[inbox & (idx.minute == 30), "high"] = box[1]
    df.loc[inbox & (idx.minute == 45), "low"] = box[0]
    for off, c in moves:
        t = open_ts + pd.Timedelta(minutes=off)
        after = df.index >= t
        df.loc[after, ["open", "close"]] = c
        df.loc[after, "high"] = c + 0.1
        df.loc[after, "low"] = c - 0.1
    if drop_box_frac:
        b = df.index[(df.index >= pd.Timestamp(date, tz="UTC")) & (df.index < open_ts)]
        df = df.drop(b[: int(len(b) * drop_box_frac)])
    return df, open_ts


def test_dst_summer_open_is_0700_utc():
    df, o = make_day("2024-07-10", 7, [(2, 102.0)])
    assert session_times(pd.Timestamp("2024-07-10").date(), P)["open"] == o
    d = decide(df, o + pd.Timedelta(minutes=5), P)
    assert d.action == "ENTER" and d.direction == 1 and d.stop_abs == pytest.approx(99.0)


def test_dst_winter_same_utc_time_is_before_open():
    df, o = make_day("2024-01-10", 8, [(2, 102.0)])
    early = decide(df, pd.Timestamp("2024-01-10 07:05", tz="UTC"), P)
    assert early.action == "NONE" and "before" in early.reason
    assert decide(df, o + pd.Timedelta(minutes=5), P).action == "ENTER"


def test_dst_switch_monday():
    # UK clocks went forward on Sunday 2024-03-31: Monday opens at 07:00 UTC
    df, o = make_day("2024-04-01", 7, [(2, 98.0)])
    d = decide(df, o + pd.Timedelta(minutes=5), P)
    assert d.action == "ENTER" and d.direction == -1


def test_box_data_gap_blocks_trading():
    df, o = make_day("2024-07-10", 7, [(2, 102.0)], drop_box_frac=0.7)
    d = decide(df, o + pd.Timedelta(minutes=5), P)
    assert d.action == "NONE" and "insufficient box" in d.reason


def test_missing_open_bar_holiday():
    df, o = make_day("2024-07-10", 7, [(2, 102.0)])
    df = df[(df.index < o) | (df.index >= o + pd.Timedelta(minutes=30))]
    d = decide(df, o + pd.Timedelta(minutes=35), P)
    assert d.action == "NONE" and "open" in d.reason


def test_both_sides_break_first_only_and_stale():
    # up-break in the first 5m bar, down-break at +20 min
    df, o = make_day("2024-07-10", 7, [(2, 102.0), (20, 98.0)])
    assert decide(df, o + pd.Timedelta(minutes=5), P).direction == 1
    late = decide(df, o + pd.Timedelta(minutes=25), P)          # bot missed the first signal
    assert late.action == "NONE" and "stale" in late.reason
    taken = decide(df, o + pd.Timedelta(minutes=25), P, trades_taken_today=1)
    assert taken.action == "NONE" and "max trades" in taken.reason


def test_window_expiry():
    df, o = make_day("2024-07-10", 7, [(75, 102.0)])            # break after the 60-min window
    d = decide(df, o + pd.Timedelta(minutes=80), P)
    assert d.action == "NONE" and "window over" in d.reason


def test_finalize_and_same_bar_sl_tp_is_stop():
    df, o = make_day("2024-07-10", 7, [(2, 102.0)])
    d = decide(df, o + pd.Timedelta(minutes=5), P)
    pos = finalize(d, 102.0)                                     # risk 3 -> target 108
    assert pos["stop"] == 99.0 and pos["target"] == pytest.approx(108.0)
    why, px = on_bar(pos, dict(open=102, high=109, low=98.5, close=103, time=o + pd.Timedelta(minutes=10)))
    assert why == "STOP" and px == 99.0
    why, px = on_bar(pos, dict(open=98, high=98.5, low=97, close=97.5, time=o + pd.Timedelta(minutes=11)))
    assert why == "STOP" and px == 98                             # gap through stop: fill at open
    why, _ = on_bar(pos, dict(open=103, high=103, low=102, close=102,
                              time=pd.Timestamp("2024-07-10 15:30", tz="UTC")))
    assert why == "TIME"                                          # 16:30 London = 15:30 UTC in summer


def test_finalize_rejects_stop_on_wrong_side():
    df, o = make_day("2024-07-10", 7, [(2, 102.0)])
    d = decide(df, o + pd.Timedelta(minutes=5), P)
    assert finalize(d, 98.0) is None
