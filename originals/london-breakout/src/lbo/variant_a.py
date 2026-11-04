"""Variant A: Asian box, first strong close outside it after the London open."""
import datetime as dt
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import sessions as S
from .engine import simulate, simulate_managed

MIN_BOX_COVERAGE = 0.5      # fraction of box minutes that must have a bar


def trading_dates(m, tz):
    ts = pd.to_datetime(m["t"] * 60, unit="s", utc=True).tz_convert(tz)
    ds = sorted({d for d in ts.date if d.weekday() < 5})
    return ds


def build_days(m, dates, box_rule, window_max, daily):
    """Per-date schedule and box. One row per date that has usable data."""
    t = m["t"]
    rows = []
    for d in dates:
        T = S.variant_a_times(d, box_rule, window_max)
        i0, i1 = np.searchsorted(t, [T["box_start"], T["box_end"]])
        io, ie = np.searchsorted(t, [T["open"], T["exit"]])
        n_exp = T["box_end"] - T["box_start"]
        cover = (i1 - i0) / n_exp if n_exp > 0 else 0
        if cover < MIN_BOX_COVERAGE or io >= len(t) or t[io] >= T["open"] + 5 or ie <= io:
            rows.append(dict(date=d, ok=False, cover=cover))
            continue
        hi, lo = m["h"][i0:i1].max(), m["l"][i0:i1].min()
        rows.append(dict(date=d, ok=True, cover=cover, box_hi=hi, box_lo=lo,
                         open_t=T["open"], exit_t=T["exit"], i_open=io, i_exit=ie,
                         open_px=m["o"][io]))
    df = pd.DataFrame(rows).set_index("date")
    daily = daily.reindex(df.index)
    for col in ("atr14_prev", "ema20_prev", "ema50_prev", "prev_c", "rv_regime"):
        df[col] = daily[col].values
    df["width"] = df.box_hi - df.box_lo
    df["width_atr"] = df.width / df.atr14_prev
    # box-size percentile vs the trailing 250 usable days (prior days only)
    w = df.width_atr.where(df.ok)
    df["width_pct"] = w.rolling(250, min_periods=60).apply(
        lambda x: (x[:-1] < x[-1]).mean() if np.isfinite(x[-1]) else np.nan, raw=True)
    return df


@dataclass(frozen=True)
class SigA:
    box: str = "utc0007"
    tf: int = 5
    order: str = "market"         # market | stop
    breakout: str = "close"       # close | whole | buffer
    buffer_atr: float = 0.0       # used by breakout=buffer and order=stop
    strong: str = "none"          # none | body50 | range1atr | close25
    vol_k: float = 0.0            # 0 = ignore volume
    window: int = 120             # minutes after the open in which a signal may occur
    fresh: bool = False           # require the previous bar to close inside the box
    box_filter: str = "none"      # none | p20_80 | no_narrow | no_wide | narrow | wide
    trend: str = "none"           # none | ema20 | ema50 | prevclose


def box_filter_mask(days, how):
    p = days.width_pct.values
    if how == "none":
        return np.ones(len(days), bool)
    with np.errstate(invalid="ignore"):
        return {"p20_80": (p >= .2) & (p <= .8), "no_narrow": p >= .2, "no_wide": p <= .8,
                "narrow": p < .5, "wide": p >= .5}[how]


def signals(m, bars, vratio, days, cfg: SigA):
    """All qualifying entries per day, in time order.

    Returns DataFrame: day (row in days), dir, i_entry (1m index), planned (mid price),
    sig_h, sig_l (signal bar extremes), atr (signal-tf ATR at signal), kind.
    """
    ok = days.ok.values & box_filter_mask(days, cfg.box_filter)
    dpos = np.flatnonzero(ok)
    if cfg.order == "stop":
        return _stop_signals(m, bars, days, dpos, cfg)
    tf = bars["tf"]
    bt = bars["t"]
    open_t = days.open_t.values[dpos].astype(np.int64)
    js = np.searchsorted(bt, open_t)
    je = np.searchsorted(bt, open_t + cfg.window - tf, side="right")
    cnt = np.maximum(je - js, 0)
    idx = np.concatenate([np.arange(a, b) for a, b in zip(js, je)]) if cnt.sum() else np.array([], int)
    drow = np.repeat(dpos, cnt)
    if idx.size == 0:
        return pd.DataFrame(columns=["day", "dir", "i_entry", "planned", "sig_h", "sig_l", "atr", "kind"])
    O, H, L, C = bars["o"][idx], bars["h"][idx], bars["l"][idx], bars["c"][idx]
    A = bars["atr"][idx]
    Ap = bars["atr_prev"][idx]
    pc = bars["c"][np.maximum(idx - 1, 0)]
    bh, bl = days.box_hi.values[drow], days.box_lo.values[drow]
    buf = cfg.buffer_atr * A if cfg.breakout == "buffer" else 0.0
    if cfg.breakout == "whole":
        up, dn = L > bh, H < bl
    else:
        up, dn = C > bh + buf, C < bl - buf
    rng = H - L
    with np.errstate(invalid="ignore", divide="ignore"):
        if cfg.strong == "body50":
            su, sd = (C > O) & (C - O >= 0.5 * rng), (C < O) & (O - C >= 0.5 * rng)
        elif cfg.strong == "range1atr":
            su, sd = (C > O) & (rng >= Ap), (C < O) & (rng >= Ap)
        elif cfg.strong == "close25":
            su, sd = (C > O) & (C >= H - 0.25 * rng), (C < O) & (C <= L + 0.25 * rng)
        else:
            su = sd = np.ones(len(idx), bool)
        if cfg.vol_k > 0:
            vr = vratio[idx]
            vok = vr >= cfg.vol_k
        else:
            vok = np.ones(len(idx), bool)
    if cfg.fresh:
        up &= pc <= bh
        dn &= pc >= bl
    tr_up, tr_dn = _trend_masks(days, drow, cfg.trend, bh, bl)
    long_ok = up & su & vok & tr_up
    short_ok = dn & sd & vok & tr_dn
    q = long_ok | short_ok
    sel = np.flatnonzero(q)
    i_entry = np.searchsorted(m["t"], bt[idx[sel]] + tf)
    out = pd.DataFrame(dict(day=drow[sel], dir=np.where(long_ok[sel], 1, -1), i_entry=i_entry,
                            sig_h=H[sel], sig_l=L[sel], atr=A[sel], kind="market"))
    out = out[out.i_entry < days.i_exit.values[out.day.values]]
    out["planned"] = m["o"][out.i_entry.values]
    return out.reset_index(drop=True)


def _trend_masks(days, drow, how, bh, bl):
    n = len(drow)
    if how == "none":
        return np.ones(n, bool), np.ones(n, bool)
    op = days.open_px.values[drow]
    ref = {"ema20": days.ema20_prev, "ema50": days.ema50_prev, "prevclose": days.prev_c}[how].values[drow]
    if how == "prevclose":      # previous day's close relative to the box
        mid = (bh + bl) / 2
        return ref > mid, ref < mid
    return op > ref, op < ref


def _stop_signals(m, bars, days, dpos, cfg):
    """OCO stop orders at box edges (+buffer) live from the open for `window` minutes."""
    t = m["t"]
    rows = []
    atr_open = bars["atr_prev"][np.clip(np.searchsorted(bars["t"], days.open_t.values[dpos]), 0, len(bars["t"]) - 1)]
    for k, d in enumerate(dpos):
        io = int(days.i_open.values[d])
        iw = np.searchsorted(t, days.open_t.values[d] + cfg.window)
        if iw <= io:
            continue
        buf = cfg.buffer_atr * atr_open[k] if np.isfinite(atr_open[k]) else 0.0
        up_lvl, dn_lvl = days.box_hi.values[d] + buf, days.box_lo.values[d] - buf
        hu = np.flatnonzero(m["h"][io:iw] >= up_lvl)
        hd = np.flatnonzero(m["l"][io:iw] <= dn_lvl)
        cands = []
        if hu.size:
            cands.append((io + hu[0], 1, up_lvl))
        if hd.size:
            cands.append((io + hd[0], -1, dn_lvl))
        cands.sort(key=lambda x: (x[0], abs(m["o"][x[0]] - x[2])))
        for i, di, lvl in cands:
            rows.append(dict(day=d, dir=di, i_entry=i, planned=lvl, sig_h=m["h"][i], sig_l=m["l"][i],
                             atr=atr_open[k], kind="stop"))
    return pd.DataFrame(rows, columns=["day", "dir", "i_entry", "planned", "sig_h", "sig_l", "atr", "kind"])


STOPS = ("in25", "mid", "opp", "candle", "atr0.5", "atr1", "atr2", "atr3")


def evaluate(m, days, sig, stop_rule, rrs, k, slip, comm, max_trades="one",
             manage=None):
    """Turn signals into trades. Returns DataFrame (one row per trade) with R per rr column.

    max_trades: 'one' first signal per day | 'reversal' one more trade in the opposite
    direction after the first has closed | 'two' up to two sequential trades.
    manage: dict for simulate_managed (single rr) or None for the vectorised bracket.
    """
    rrs = list(rrs)
    out = []
    if sig is None or len(sig) == 0:
        return pd.DataFrame()
    bh_all, bl_all = days.box_hi.values, days.box_lo.values
    i_exit_all = days.i_exit.values
    for d, g in sig.groupby("day", sort=True):
        taken, last_exit, first_dir = 0, -1, 0
        for s in g.itertuples(index=False):
            if s.i_entry <= last_exit:
                continue
            if taken == 1 and max_trades == "one":
                break
            if taken == 1 and max_trades == "reversal" and s.dir == first_dir:
                continue
            if taken == 2:
                break
            stop = _stop(bh_all[d], bl_all[d], s, stop_rule)
            if not np.isfinite(stop) or (s.planned - stop) * s.dir <= 0:
                continue
            ie = int(i_exit_all[d])
            if manage is None:
                R, ei, why = simulate(m, int(s.i_entry), ie, int(s.dir), s.planned, stop, rrs,
                                      k, slip, comm, kind=s.kind)
            else:
                r1, e1, w1 = simulate_managed(m, int(s.i_entry), ie, int(s.dir), s.planned, stop,
                                              rrs[0], k, slip, comm, kind=s.kind, atr=s.atr, **manage)
                R, ei, why = np.array([r1]), np.array([e1]), np.array([w1])
            # for sequencing use the exit of the first rr column
            row = dict(day=d, dir=int(s.dir), i_entry=int(s.i_entry), planned=s.planned, stop=stop,
                       risk=abs(s.planned - stop), exit_i=int(ei[0]), why=int(why[0]))
            for rr, r in zip(rrs, R):
                row[f"R_{rr}"] = r
            out.append(row)
            taken += 1
            first_dir = first_dir or int(s.dir)
            last_exit = int(ei[0])
    return pd.DataFrame(out)


def _stop(bh, bl, s, rule):
    w = bh - bl
    di, p = s.dir, s.planned
    if rule == "in25":
        return bh - 0.25 * w if di > 0 else bl + 0.25 * w
    if rule == "mid":
        return (bh + bl) / 2
    if rule == "opp":
        return bl if di > 0 else bh
    if rule == "candle":
        return s.sig_l if di > 0 else s.sig_h
    if rule.startswith("atr"):
        a = s.atr
        return p - di * float(rule[3:]) * a if np.isfinite(a) else np.nan
    raise ValueError(rule)
