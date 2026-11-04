"""Gap analysis: how the Asian box actually behaves after the London open, plus trade-level
weak spots (news days, holidays, outliers, instruments)."""
import numpy as np
import pandas as pd

from . import variant_a as A
from .common import Ctx, split_of


def box_behaviour(name, box="utc0007", tf=5, window=120, reentry_bars=(3, 6, 12)):
    """Per-day: did a tf bar close above / below the box within `window` minutes of the
    open, which came first, and did price close back inside within N bars (false break)."""
    ctx = Ctx(name)
    m, b = ctx.m, ctx.bars(tf)
    dates = A.trading_dates(m, ctx.tz)
    days = A.build_days(m, dates, box, 120, ctx.daily)
    rows = []
    for d, r in days[days.ok].iterrows():
        js = np.searchsorted(b["t"], r.open_t)
        je = np.searchsorted(b["t"], r.open_t + window - tf, side="right")
        jx = np.searchsorted(b["t"], r.exit_t)
        C = b["c"]
        up = np.flatnonzero(C[js:je] > r.box_hi)
        dn = np.flatnonzero(C[js:je] < r.box_lo)
        first = None
        if up.size and (not dn.size or up[0] < dn[0]):
            first, j0 = "up", js + up[0]
        elif dn.size:
            first, j0 = "down", js + dn[0]
        row = dict(date=d, broke_up=bool(up.size), broke_down=bool(dn.size), first=first or "none",
                   width_pct=r.width_pct, open_outside=bool(r.open_px > r.box_hi or r.open_px < r.box_lo))
        if first:
            after = C[j0 + 1:jx]
            inside = (after <= r.box_hi) & (after >= r.box_lo)
            back = np.flatnonzero(inside)
            for n in reentry_bars:
                row[f"reentry_{n}"] = bool(back.size and back[0] < n)
            row["reentry_by_exit"] = bool(back.size)
            # close-to-close continuation from break bar to the 16:30 exit, in box widths
            w = r.box_hi - r.box_lo
            sgn = 1 if first == "up" else -1
            row["cont_to_exit_w"] = sgn * (C[jx - 1] - C[j0]) / w if jx - 1 > j0 and w > 0 else np.nan
        rows.append(row)
    df = pd.DataFrame(rows)
    df["split"] = split_of(df.date)
    df["inst"] = name
    return df


def summarise_box(df):
    n = len(df)
    s = dict(days=n,
             no_break_pct=float((df["first"] == "none").mean()),
             both_sides_pct=float((df.broke_up & df.broke_down).mean()),
             open_outside_box_pct=float(df.open_outside.mean()))
    br = df[df["first"] != "none"]
    for c in [c for c in df.columns if c.startswith("reentry")]:
        s[f"{c}_pct"] = float(br[c].mean())
    s["median_continuation_w"] = float(br.cont_to_exit_w.median())
    s["mean_continuation_w"] = float(br.cont_to_exit_w.mean())
    return s


def trade_weak_spots(tr):
    """Trade-level gap table: news, holidays, outliers, Mondays/Fridays, instruments."""
    out = {}
    R = tr.R.values
    out["all"] = (len(R), R.mean())
    news = tr.events != ""
    for ev in ("NFP", "US_CPI", "ECB", "BOE"):
        msk = tr.events.str.contains(ev)
        if msk.any():
            out[f"on_{ev}"] = (int(msk.sum()), tr.R[msk].mean())
    out["any_news"] = (int(news.sum()), tr.R[news].mean() if news.any() else np.nan)
    out["no_news"] = (int((~news).sum()), tr.R[~news].mean())
    dts = pd.to_datetime(tr.date)
    hol = ((dts.dt.month == 12) & (dts.dt.day >= 20)) | ((dts.dt.month == 1) & (dts.dt.day <= 3))
    out["xmas_newyear"] = (int(hol.sum()), tr.R[hol].mean() if hol.any() else np.nan)
    srt = np.sort(R)[::-1]
    for q in (0.01, 0.05):
        k = max(1, int(round(q * len(R))))
        out[f"drop_top_{int(q * 100)}pct"] = (len(R) - k, srt[k:].mean())
    return pd.DataFrame(out, index=["n", "exp"]).T
