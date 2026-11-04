"""Replay the live module (strategy/signal.py) bar by bar on real GER40/UK100 data and check
it produces the same first signal (time, direction, stop) as the research backtest.
This is the look-ahead guard: the live module only ever sees closed bars."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data" / "m1" / "GER40.npz").exists(),
                                reason="needs built data (python run_all.py --stage data)")


def _params_from_final():
    from strategy.signal import load_params
    return load_params(ROOT / "config" / "final_strategy.yaml")


@pytest.mark.parametrize("name", ["GER40", "UK100"])
def test_live_module_matches_backtest(name):
    from lbo import variant_a as A
    from lbo.common import Ctx
    from strategy.signal import decide

    p = _params_from_final()
    sc = A.SigA(box=p.box_rule, tf=p.signal_tf, breakout=p.breakout, buffer_atr=p.buffer_atr,
                strong=p.strong, vol_k=p.vol_k, window=p.window_min, fresh=p.fresh,
                box_filter=p.box_filter, trend=p.trend)
    ctx = Ctx(name)
    m = ctx.m
    dates = A.trading_dates(m, ctx.tz)
    days = A.build_days(m, dates, sc.box, 120, ctx.daily)
    sig = A.signals(m, ctx.bars(sc.tf), ctx.vratio(sc.tf), days, sc)
    first = sig.groupby("day").first()
    ts = pd.to_datetime(m["t"] * 60, unit="s", utc=True)
    df = pd.DataFrame({"open": m["o"], "high": m["h"], "low": m["l"], "close": m["c"], "volume": m["v"]}, index=ts)

    rng = np.random.default_rng(7)
    ok_days = np.flatnonzero(days.ok.values)
    sample = rng.choice(ok_days, size=min(250, len(ok_days)), replace=False)
    mismatches = []
    compared = 0
    for di in sample:
        r = days.iloc[di]
        o = pd.Timestamp(int(r.open_t) * 60, unit="s", tz="UTC")
        hist = df[(df.index >= o - pd.Timedelta(days=3)) & (df.index < o + pd.Timedelta(minutes=p.window_min + 60))]
        live = None
        for step in range(p.signal_tf, p.window_min + p.signal_tf, p.signal_tf):
            d = decide(hist, o + pd.Timedelta(minutes=step), p)
            if d.action == "ENTER":
                live = d
                break
        bt = first.loc[di] if di in first.index else None
        if bt is None and live is None:
            continue
        if (bt is None) != (live is None):
            mismatches.append((r.name, "presence", bt is not None, live is not None))
            continue
        compared += 1
        bt_entry = pd.Timestamp(int(m["t"][int(bt.i_entry)]) * 60, unit="s", tz="UTC")
        live_entry = live.signal_bar_utc + pd.Timedelta(minutes=p.signal_tf)
        if int(bt.dir) != live.direction or bt_entry != live_entry:
            mismatches.append((r.name, "signal", int(bt.dir), live.direction, bt_entry, live_entry))
    assert not mismatches, mismatches[:5]
    assert compared >= 40, f"only {compared} signal days compared"
    print(name, 'signal days compared:', compared)
