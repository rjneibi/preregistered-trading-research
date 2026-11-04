"""E4 per prereg/E4-NEWS.md. measure reads the ticks once and saves windows. rerun applies them to true-UTC trades. Usage: e4_news.py <measure|rerun>."""
import glob
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.join(HERE, "..", "phaseC")
GB = os.path.join(HERE, "..", "_copy", "goldbot")
sys.path[:0] = [HERE, os.path.join(GB, "prereg")]
import lib
from cost_matrix import CostMatrix

SRC = open(os.path.join(HERE, "..", "_copy", "rs_recorded", "fable-backtesting", "build_calendar.py"), encoding="utf-8").read()
NY = ZoneInfo("America/New_York")
WIN = ((-30, -5), (-5, 0), (0, 1), (1, 5), (5, 30), (30, 60))
TICKS = sorted(glob.glob("@GANN_ROOT@/fable-backtesting/download/xauusd-bi5-*.csv"))


def events():
    """Dates as listed in build_calendar.py. CPI exists only for 2015 and 2025-26. The file's 2015 list comes from a parse of the BLS page, read here the same way."""
    fomc = re.findall(r"\d{4}-\d{2}-\d{2}", SRC[SRC.index('FOMC = """'):SRC.index('CPI_KNOWN')])
    cpi = re.findall(r"\d{4}-\d{2}-\d{2}", SRC[SRC.index('CPI_KNOWN = """'):SRC.index("def first_friday")])
    html = open(os.path.join(HERE, "..", "_copy", "rs_recorded", "fable-backtesting", "calendar", "bls_2015.htm"), errors="ignore").read()
    months = "January February March April May June July August September October November December".split()
    pat = re.compile(rf"({'|'.join(months)})\s+(\d{{1,2}}),\s+(2015)")
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
        t = re.sub(r"<[^>]+>", " ", row)
        m = pat.search(t)
        if m and "Consumer Price Index" in t and "Chained" not in t:
            cpi.append(date(2015, months.index(m.group(1)) + 1, int(m.group(2))).isoformat())
    nfp = []
    for y in range(2015, 2027):
        for m in range(1, 13):
            if (y, m) <= (2026, 7):
                d = date(y, m, 1)
                while d.weekday() != 4:
                    d += timedelta(days=1)
                nfp.append(d.isoformat())

    def utc(ds, h, mi):
        return int(datetime.fromisoformat(ds).replace(hour=h, minute=mi, tzinfo=NY).timestamp())

    ev = [(utc(d, 14, 0), "FOMC") for d in sorted(set(fomc))] + [(utc(d, 8, 30), "NFP") for d in nfp] + [(utc(d, 8, 30), "CPI") for d in sorted(set(cpi))]
    return sorted(ev)


def measure():
    ev = events()
    et = np.array([e[0] for e in ev]) * 1000
    ty = [e[1] for e in ev]
    days = {e[0] // 86400 for e in ev}
    pools, base = {}, {}
    for f in TICKS:
        d = pd.read_csv(f, usecols=["timestamp", "askPrice", "bidPrice"])
        ts = d.timestamp.values
        s = (d.askPrice - d.bidPrice).values
        ok = np.isfinite(s) & (s > 0)
        ts, s = ts[ok], s[ok]
        for k, e in enumerate(et):
            lo, hi = np.searchsorted(ts, [e - 1800000, e + 3600000])
            if hi <= lo:
                continue
            off = (ts[lo:hi] - e) / 60000.0
            y = str(pd.Timestamp(int(e), unit="ms").year)
            for a, b in WIN:
                m = (off >= a) & (off < b)
                if m.any():
                    pools.setdefault((ty[k], y, f"{a}..{b}"), []).append(s[lo:hi][m].astype(np.float32))
        keep = ~np.isin(ts // 86400000, list(days))
        tk, sk = ts[keep][::20], s[keep][::20]
        hr = (tk // 3600000) % 24
        y0 = pd.to_datetime(tk[0], unit="ms").year
        for h in range(24):
            base.setdefault((str(y0), h), []).append(sk[hr == h].astype(np.float32))
        print(os.path.basename(f), flush=True)
    win = {}
    for k, v in pools.items():
        a = np.concatenate(v)
        win["|".join(k)] = dict(n=len(a), median=float(np.median(a)), p90=float(np.percentile(a, 90)), events=len(v))
    bs = {f"{k[0]}|{k[1]}": float(np.median(np.concatenate(v))) if sum(map(len, v)) else None for k, v in base.items()}
    json.dump(dict(windows=win, base=bs, events=len(ev), by_type={t: ty.count(t) for t in sorted(set(ty))}), open(os.path.join(HERE, "e4_spreads.json"), "w"), indent=0)


def in_win(tsec, et, ety):
    k = np.searchsorted(et, tsec)
    for j in (k - 1, k):
        if 0 <= j < len(et):
            off = (tsec - et[j]) / 60.0
            for a, b in WIN:
                if a <= off < b:
                    return ety[j], f"{a}..{b}"
    return None


def rerun():
    S = json.load(open(os.path.join(HERE, "e4_spreads.json")))
    W = S["windows"]
    ev = events()
    et = np.array([e[0] for e in ev])
    ety = [e[1] for e in ev]
    cm = CostMatrix.load(os.path.join(GB, "results", "cost_matrix.json"), stat="median", k_slip=0.5, commission_per_lot_rt=7.0)

    def ev_sp(ts):
        t = int(ts.timestamp())
        w = in_win(t, et, ety)
        if not w:
            return None
        y = min(ts.year, 2026)
        q = W.get(f"{w[0]}|{y}|{w[1]}") or W.get(f"{w[0]}|{y - 1}|{w[1]}")
        return q["p90"] if q else None

    def near(ts):
        t = int(ts.timestamp())
        k = np.searchsorted(et, t)
        return any(0 <= j < len(et) and abs(t - et[j]) <= 1800 for j in (k - 1, k))

    rep = {}
    h = pd.read_csv(os.path.join(PC, "h1_true_utc_trades.csv"), parse_dates=["entry_ts", "exit_ts"])
    rows = []
    for _, x in h.iterrows():
        a, b = x.entry_ts, x.exit_ts
        sa, sb = cm.spread_usd(a), cm.spread_usd(b)
        ea, eb = ev_sp(a), ev_sp(b)
        ca, cb = ea if ea else sa, eb if eb else sb
        rows.append(dict(c=100 * ((ca + cb) / 2 + 0.5 * (ca + cb)) + 7, hit=bool(ea or eb), near=near(a)))
    z = pd.DataFrame(rows)
    net = (h.gross_usd - z.c).values
    rep["H1"] = dict(n=len(h), matrix_pf=round(lib.pf(h.net_med.values), 3), event_aware_pf=round(lib.pf(net), 3), trades_touching_window=int(z.hit.sum()), extra_cost_usd=round(float((z.c - h.cost_med).sum())),
                     blackout_n=int((~z.near).sum()), blackout_pf_matrix=round(lib.pf(h.net_med.values[~z.near.values]), 3), blackout_pf_event=round(lib.pf(net[~z.near.values]), 3), pf_2x_event=round(lib.pf((h.gross_usd - 2 * z.c).values), 3))
    for nm in ("v3", "v4"):
        t = pd.read_csv(os.path.join(PC, f"fable_{nm}_true.csv"), parse_dates=["ts"])
        gross = t.pnl.values + 20.0
        base, ev_c, hit, nr = [], [], [], []
        for ts in t.ts:
            s, e = cm.spread_usd(ts), ev_sp(ts)
            base.append(cm.trade_cost_usd(ts, ts))
            si = e if e else s
            ev_c.append(100 * ((si + s) / 2 + 0.5 * (si + s)) + 7)
            hit.append(e is not None)
            nr.append(near(ts))
        base, ev_c, hit, nr = np.array(base), np.array(ev_c), np.array(hit), np.array(nr)
        net = gross - ev_c
        rep[nm] = dict(n=len(t), flat_cost_pf=round(lib.pf(t.pnl.values), 3), matrix_pf=round(lib.pf(gross - base), 3), event_aware_pf=round(lib.pf(net), 3), trades_in_window=int(hit.sum()), extra_cost_usd=round(float((ev_c - base).sum())),
                       blackout_n=int((~nr).sum()), blackout_pf_matrix=round(lib.pf((gross - base)[~nr]), 3), blackout_pf_event=round(lib.pf(net[~nr]), 3), pf_2x_event=round(lib.pf(gross - 2 * ev_c), 3),
                       note="Frozen basis: matrix cost, event spread at entry. The harness saves no exit time, so the exit uses the entry-hour matrix spread")
    agg = {}
    for typ in ("NFP", "CPI", "FOMC"):
        for a, b in WIN:
            w = f"{a}..{b}"
            ks = [v for k, v in W.items() if k.startswith(typ + "|") and k.endswith("|" + w)]
            if ks:
                agg[f"{typ} {w}"] = dict(events=sum(v["events"] for v in ks), median_of_year_medians=round(float(np.median([v["median"] for v in ks])), 3), median_of_year_p90=round(float(np.median([v["p90"] for v in ks])), 3))
    rep["spread_by_window"] = agg
    # Ratio to the same UTC hours on non-event days of the same year, as the prereg asks
    hrs = dict(NFP=("12", "13"), CPI=("12", "13"), FOMC=("18", "19"))
    ratio = {}
    for k, v in W.items():
        typ, y, w = k.split("|")
        b = [S["base"].get(f"{y}|{h}") for h in hrs[typ]]
        b = [x for x in b if x]
        if b:
            ratio.setdefault(f"{typ} {w}", []).append(v["median"] / float(np.mean(b)))
    rep["median_ratio_to_non_event_same_hours"] = {k: round(float(np.median(v)), 2) for k, v in ratio.items()}
    rep["prediction_3x_to_6x"] = "Scored against the first-minute ratios above"
    hb = [v for k, v in S["base"].items() if v and k.split("|")[1] in ("12", "13", "18", "19")]
    rep["non_event_median_spread_us_hours"] = round(float(np.median(hb)), 3)
    rep["events"] = S["by_type"]
    json.dump(rep, open(os.path.join(HERE, "e4_result.json"), "w"), indent=1)
    print(json.dumps(rep, indent=1))


if sys.argv[1] == "measure":
    measure()
else:
    rerun()
