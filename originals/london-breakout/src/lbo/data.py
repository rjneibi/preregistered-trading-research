"""Build clean UTC 1-minute mid/spread arrays from Dukascopy bid+ask CSVs, plus a QC report.

Stored per instrument as data/m1/<NAME>.npz with:
  t      int64  bar open time, epoch minutes UTC
  o,h,l,c float64 mid prices ((bid+ask)/2 per field)
  sp     float64 spread = max(ask-bid at open, ask-bid at close)  (conservative)
  v      float64 tick volume (bid side, Dukascopy units; only relative values matter)
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
M1 = ROOT / "data" / "m1"


def _read_side(sym, side):
    files = sorted((RAW / sym).glob(f"{sym}-{side}-*.csv"))
    if not files:
        raise FileNotFoundError(f"no {side} files for {sym} in {RAW / sym}")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    return df


def build(name, sym, start, end):
    b = _read_side(sym, "bid")
    a = _read_side(sym, "ask")
    qc = {"instrument": name, "symbol": sym, "raw_bid_rows": len(b), "raw_ask_rows": len(a)}
    qc["dup_bid"] = int(b.timestamp.duplicated().sum())
    qc["dup_ask"] = int(a.timestamp.duplicated().sum())
    b = b.drop_duplicates("timestamp")
    a = a.drop_duplicates("timestamp")
    m = b.merge(a, on="timestamp", suffixes=("_b", "_a"), how="inner")
    qc["unmatched_bid_ask"] = len(b) + len(a) - 2 * len(m)
    m = m.sort_values("timestamp")
    t = (m.timestamp.values // 60000).astype(np.int64)
    lo = pd.Timestamp(start, tz="UTC").value // 60_000_000_000
    hi = pd.Timestamp(end, tz="UTC").value // 60_000_000_000
    keep = (t >= lo) & (t < hi)
    m, t = m[keep], t[keep]

    o = (m.open_b.values + m.open_a.values) / 2
    h = (m.high_b.values + m.high_a.values) / 2
    l = (m.low_b.values + m.low_a.values) / 2
    c = (m.close_b.values + m.close_a.values) / 2
    sp = np.maximum(m.open_a.values - m.open_b.values, m.close_a.values - m.close_b.values)
    v = m.volume_b.values.astype(float)

    # --- integrity checks ---
    bad_hl = (h < l) | (h < np.maximum(o, c) - 1e-9) | (l > np.minimum(o, c) + 1e-9)
    qc["bad_hilo_rows"] = int(bad_hl.sum())
    neg_sp = sp < 0
    qc["negative_spread_rows"] = int(neg_sp.sum())
    # Dukascopy pads silent minutes with flat zero-volume bars; they carry no information.
    flat0 = (v <= 0) & (o == h) & (h == l) & (l == c)
    qc["flat_zero_volume_rows_dropped"] = int(flat0.sum())
    # bad ticks: a wick that sticks out > 25 robust sigmas beyond the bar body and both
    # neighbouring closes, while price is back where it was one bar later.
    ret = np.diff(np.log(c), prepend=np.log(c[0]))
    mad = pd.Series(np.abs(ret)).rolling(1440, min_periods=60).median().bfill().values
    scale = np.maximum(mad * 1.4826, 1e-6)
    prev_c = np.roll(c, 1)
    next_c = np.roll(c, -1)
    env_hi = np.maximum.reduce([o, c, prev_c, next_c])
    env_lo = np.minimum.reduce([o, c, prev_c, next_c])
    spikes = ((np.log(h / env_hi) > 25 * scale) | (np.log(env_lo / l) > 25 * scale)) \
        & (np.abs(np.log(next_c / prev_c)) < 3 * scale)
    spikes[[0, -1]] = False
    qc["bad_tick_bars_clipped"] = int(spikes.sum())
    # clip spike wicks to the body/neighbour envelope instead of deleting the bar
    h = np.where(spikes, env_hi, h)
    l = np.where(spikes, env_lo, l)

    keep = ~(bad_hl | neg_sp | flat0)
    arr = dict(t=t[keep], o=o[keep], h=h[keep], l=l[keep], c=c[keep], sp=sp[keep], v=v[keep])
    qc["clean_rows"] = int(keep.sum())
    qc["first_bar_utc"] = str(pd.Timestamp(arr["t"][0] * 60, unit="s", tz="UTC"))
    qc["last_bar_utc"] = str(pd.Timestamp(arr["t"][-1] * 60, unit="s", tz="UTC"))
    M1.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(M1 / f"{name}.npz", **arr)
    return arr, qc


def load(name):
    z = np.load(M1 / f"{name}.npz")
    return {k: z[k] for k in z.files}
