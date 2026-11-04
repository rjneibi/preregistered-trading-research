"""Run one fully specified configuration and return an annotated trade list.

Used for the deep-dive analysis, the fixes in section 9, and the single OOS run.
"""
import numpy as np
import pandas as pd

from . import sessions as S
from . import variant_a as A
from . import variant_b as B
from .common import ROOT, Ctx, split_of

_CAL = None


def calendar():
    global _CAL
    if _CAL is None:
        df = pd.read_csv(ROOT / "data" / "calendar" / "high_impact_events.csv", parse_dates=["date"])
        df["date"] = df.date.dt.date
        _CAL = df
    return _CAL


def retest_signals(m, sig, days, window_end_min, edge="box"):
    """Replace each breakout signal by a limit order at the broken box edge, live from the
    signal until the end of the entry window. Unfilled signals are dropped."""
    rows = []
    t = m["t"]
    for s in sig.itertuples(index=False):
        d = days.iloc[int(s.day)]
        lvl = d.box_hi if s.dir > 0 else d.box_lo
        iw = np.searchsorted(t, window_end_min[int(s.day)])
        a = int(s.i_entry)
        if iw <= a:
            continue
        # long: buy limit at box_hi fills when ask low <= level (approx. mid low + spread/2)
        if s.dir > 0:
            hit = np.flatnonzero(m["l"][a:iw] + m["sp"][a:iw] / 2 <= lvl)
        else:
            hit = np.flatnonzero(m["h"][a:iw] - m["sp"][a:iw] / 2 >= lvl)
        if hit.size:
            r = s._asdict()
            r.update(i_entry=a + hit[0], planned=lvl, kind="limit")
            rows.append(r)
    return pd.DataFrame(rows, columns=sig.columns)


def run_a(name, sc: A.SigA, stop, rr, k=1.0, allow_oos=False, max_trades="one", manage=None,
          retest=False, ctx=None, days=None):
    ctx = ctx or Ctx(name, allow_oos=allow_oos)
    m = ctx.m
    if days is None:
        dates = A.trading_dates(m, ctx.tz)
        days = A.build_days(m, dates, sc.box, 120, ctx.daily)
    sig = A.signals(m, ctx.bars(sc.tf), ctx.vratio(sc.tf), days, sc)
    if retest and len(sig):
        wend = days.open_t.values.astype(float) + sc.window
        sig = retest_signals(m, sig, days, wend)
    tr = A.evaluate(m, days, sig, stop, [rr], k, ctx.slip, ctx.comm, max_trades=max_trades, manage=manage)
    return annotate(tr, days, m, rr, name, ctx), ctx, days


def run_b(name, sc: B.SigB, stop_atr, rr, k=1.0, allow_oos=False, ctx=None, sess=None):
    ctx = ctx or Ctx(name, allow_oos=allow_oos, tz=S.NY)
    m = ctx.m
    if sess is None:
        dates = B.trading_dates_ny(m)
        sess = B.build_sessions(m, ctx.bars(15), dates, sc.session, 60)
    sig = B.signals(m, ctx.bars(5), ctx.vratio(5), sess, sc)
    sv = sess.assign(box_hi=sess[f"{sc.level}_up"], box_lo=sess[f"{sc.level}_dn"])
    tr = A.evaluate(m, sv, sig, f"atr{stop_atr}", [rr], k, ctx.slip, ctx.comm, max_trades="two")
    return annotate(tr, sv, m, rr, name, ctx), ctx, sess


def annotate(tr, days, m, rr, name, ctx):
    if tr is None or len(tr) == 0:
        return pd.DataFrame(columns=["date", "R", "inst"])
    tr = tr.rename(columns={f"R_{float(rr)}": "R"})
    tr = tr[np.isfinite(tr.R)].copy()
    tr["inst"] = name
    tr["date"] = days.index.values[tr.day.values]
    tr["split"] = split_of(tr.date)
    tr["entry_min"] = m["t"][tr.i_entry.values]
    tr["exit_min"] = m["t"][np.clip(tr.exit_i.values, 0, len(m["t"]) - 1)]
    tr["i_exit_day"] = days.i_exit.values[tr.day.values]
    for col in ("width_pct", "rv_regime", "width"):
        if col in days:
            tr[col] = days[col].values[tr.day.values]
    tr["risk_pts"] = tr.risk / ctx.point
    dts = pd.to_datetime(tr.date)
    tr["year"] = dts.dt.year.values
    tr["dow"] = dts.dt.dayofweek.values
    tr["month"] = dts.dt.month.values
    cal = calendar()
    ev = cal.groupby("date").event.apply(lambda x: ",".join(sorted(set(x))))
    tr["events"] = tr.date.map(ev).fillna("")
    return tr.reset_index(drop=True)
