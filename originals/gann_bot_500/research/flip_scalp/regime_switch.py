"""
STATUS: RESEARCH-ONLY (2026-07-02). Round 3a — regime-gated aggression.

Hypothesis: pyramid (+$4 add-on) is leverage on trend continuation; it should
be enabled ONLY when the market is trending. If a trend measure computed from
PAST daily bars predicts when pyramiding pays, the gated version should beat
FINAL_v1 in BOTH eras — that cross-era demand is the test.

Pre-registered regime rules (conventional thresholds, NOT tuned on our data):
  * ADX: D1 Wilder ADX(14) > 25  -> trending
  * ER : Kaufman efficiency ratio over 20 D1 closes > 0.30 -> trending
Regime value at entry = last fully-completed D1 bar before the entry's day.

Variants (both eras, no-Monday R3/S3, FINAL_v1 exits TP$8/SL$12/ts24h,
price-scaled in the 2015-21 era, P0=2531):
  ref FINAL_v1 | always-pyramid | pyramid iff ADX>25 | pyramid iff ER>0.30
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs                                   # noqa: E402
from research.dr_backtest.data_prep import (                   # noqa: E402
    load_m1, resample_ohlc, resample_d1_utc,
)
from research.dr_backtest.metrics import basic_stats            # noqa: E402
from innovate_r3s3 import SimX, r3s3_level, stats, OUT          # noqa: E402

P0 = 2531.0
ADX_TH = 25.0
ER_TH = 0.30


def wilder_adx_d1(d1: pd.DataFrame, period: int = 14) -> pd.Series:
    h = d1["high"].to_numpy(float)
    l = d1["low"].to_numpy(float)
    c = d1["close"].to_numpy(float)
    n = len(d1)
    tr = np.zeros(n)
    pdm = np.zeros(n)
    ndm = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0
        ndm[i] = dn if (dn > up and dn > 0) else 0.0
    atr = np.full(n, np.nan)
    spdm = np.full(n, np.nan)
    sndm = np.full(n, np.nan)
    if n <= period * 2:
        return pd.Series(np.full(n, np.nan), index=d1.index)
    atr[period] = tr[1:period + 1].mean()
    spdm[period] = pdm[1:period + 1].mean()
    sndm[period] = ndm[1:period + 1].mean()
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        spdm[i] = (spdm[i - 1] * (period - 1) + pdm[i]) / period
        sndm[i] = (sndm[i - 1] * (period - 1) + ndm[i]) / period
    dx = np.full(n, np.nan)
    for i in range(period, n):
        dip = 100 * spdm[i] / atr[i] if atr[i] > 0 else 0
        din = 100 * sndm[i] / atr[i] if atr[i] > 0 else 0
        dx[i] = 100 * abs(dip - din) / (dip + din) if (dip + din) > 0 else 0
    adx = np.full(n, np.nan)
    adx[period * 2] = np.nanmean(dx[period + 1:period * 2 + 1])
    for i in range(period * 2 + 1, n):
        adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
    return pd.Series(adx, index=d1.index)


def efficiency_ratio(d1: pd.DataFrame, lookback: int = 20) -> pd.Series:
    c = d1["close"]
    change = (c - c.shift(lookback)).abs()
    vol = c.diff().abs().rolling(lookback).sum()
    return change / vol


def regime_at(series: pd.Series, entry_ts: pd.Timestamp) -> float:
    """Value from the last D1 bar fully completed before entry's day."""
    day = entry_ts.floor("D")
    sub = series[series.index < day]
    return float(sub.iloc[-1]) if len(sub) else np.nan


def load_events(fname):
    ev = [json.loads(l) for l in (OUT / fname).read_text().splitlines()]
    ev.sort(key=lambda x: x["entry_ts"])
    return [e for e in ev if {"R3", "S3"} & set(e["zone_sources"])
            and pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]


def run_era(era: str):
    if era == "new":
        start, end, fname, scale = (pd.Timestamp("2021-06-19T00:00:00Z"),
                                    pd.Timestamp("2026-06-19T17:57:00Z"),
                                    "events.jsonl", False)
    else:
        start, end, fname, scale = (pd.Timestamp("2015-06-19T00:00:00Z"),
                                    pd.Timestamp("2021-06-18T23:59:00Z"),
                                    "events_2015_2021.jsonl", True)
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    m1 = load_m1(start - pd.Timedelta(days=60), end)
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    sim = SimX(m1, h4)
    adx = wilder_adx_d1(d1)
    er = efficiency_ratio(d1)
    ev = load_events(fname)

    res = {k: [] for k in ["ref", "pyr_always", "pyr_adx", "pyr_er"]}
    n_on_adx = n_on_er = 0
    for e in ev:
        ts = pd.Timestamp(e["entry_ts"])
        k = (e["h4_close"] / P0) if scale else 1.0
        base_kw = dict(tp=8. * k, sl=12. * k, level=r3s3_level(e))
        a = regime_at(adx, ts)
        r_ = regime_at(er, ts)
        on_adx = np.isfinite(a) and a > ADX_TH
        on_er = np.isfinite(r_) and r_ > ER_TH
        n_on_adx += on_adx
        n_on_er += on_er
        res["ref"].append(sim.run(e, **base_kw))
        res["pyr_always"].append(sim.run(e, pyramid_at=4. * k, **base_kw))
        res["pyr_adx"].append(sim.run(e, pyramid_at=4. * k, **base_kw)
                              if on_adx else sim.run(e, **base_kw))
        res["pyr_er"].append(sim.run(e, pyramid_at=4. * k, **base_kw)
                             if on_er else sim.run(e, **base_kw))
    print(f"\n=== era {era}: n={len(ev)}  pyramid-on rate: "
          f"ADX {n_on_adx / len(ev):.0%}, ER {n_on_er / len(ev):.0%} ===")
    rows = [stats(k, v) for k, v in res.items()]
    print(pd.DataFrame(rows).to_string(index=False))

    if era == "new":            # also show train/test split
        cut = int(round(len(ev) * 0.7))
        for lbl, sl_ in [("train", slice(None, cut)), ("test", slice(cut, None))]:
            rows = [stats(f"{k} [{lbl}]", v[sl_]) for k, v in res.items()]
            print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    run_era("new")
    run_era("old")
