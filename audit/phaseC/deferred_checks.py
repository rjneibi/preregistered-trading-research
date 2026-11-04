"""Phase B carry-overs: entry-delay (shift) test, spreads around rollover and news, cost matrix against measured spread at each H1 trade,
HistData gaps, swap exposure, and a cross-source check against Yahoo daily closes (files fetched beforehand, read as numbers only)."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "stats")]
import importlib.util

spec = importlib.util.spec_from_file_location("pa", os.path.join(HERE, "..", "stats", "pass_audit.py"))
src = open(spec.origin, encoding="utf-8").read().replace("\nmain()\n", "\n")
pa = {"__file__": spec.origin}
exec(compile(src, "pass_audit", "exec"), pa)
LBO = "@LBO_ROOT@/data/m1"
rep = {}


def z(sym):
    d = np.load(f"{LBO}/{sym}.npz")
    k = "t" if "t" in d.files else "time"
    t = d[k].astype(np.int64) * (60 if int(d[k][0]) < 10**8 else 1)
    return t, d["sp"].astype(float), d["c"].astype(float)


# 1 entry delay ---------------------------------------------------------------
us = pa["load"]("US500")


def delayed(fn, m, delay):
    """Replay a rule with entry and exit both moved `delay` bars later."""
    c, o, t = m["c"], m["o"], m["t"]
    n = len(c)
    out = []
    sp = m["sp"] if m["sp"] else 0.0002 * float(np.median(c))
    for x in fn(m):
        i = int(np.searchsorted(t, x[0]))
        j = i + x[4]
        a, b = i + 1 + delay, j + 1 + delay
        if b >= n:
            break
        r = o[b] / o[a] - 1 - sp / o[a] - int(t[b] // 86400 - t[a] // 86400) * pa["FIN"]
        out.append(r)
    return np.array(out)


rep["shift"] = {}
for nm, fn in (("XM-1-A1", pa["a1"]), ("SW-1", pa["ibs_rule"])):
    row = {}
    for dl in (0, 1, 2, 3):
        r = delayed(fn, us, dl)
        row[f"delay_{dl}"] = dict(n=len(r), pf=round(pa["pf"](r), 3), avg_pct=round(float(r.mean() * 100), 3))
    rep["shift"][nm] = row
print(rep["shift"], flush=True)

# 2 spreads -------------------------------------------------------------------
sys.path.insert(0, os.path.join(HERE, "..", "infrastructure"))
powell = open("@GANN_ROOT@/research/powell/powell_lab.py", encoding="utf-8").read()
import re
body = powell[powell.index('FOMC = """'):]
FOMC = sorted(set(re.findall(r"\d{4}-\d{2}-\d{2}", body[:body.index('"""', 12)])))
from clockfix import us_dst_bounds


def is_dst(sec):
    y = int(str(np.datetime64(int(sec), "s"))[:4])
    a, b = us_dst_bounds(y)
    return a <= sec < b


def first_fridays(y0, y1):
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d = pd.Timestamp(y, m, 1)
            d += pd.Timedelta(days=(4 - d.weekday()) % 7)
            out.append(int(d.timestamp()))
    return out


rep["spreads"] = {}
for sym in ("XAUUSD", "NAS100", "US30", "EURUSD"):
    t, sp, c = z(sym)
    pos = sp > 0
    hour = (t % 86400) // 3600
    base = float(np.median(sp[pos & (hour >= 13) & (hour < 16)]))
    # NY 17:00 rollover, the same hour in UTC moves with US daylight time
    days = t // 86400
    uq = np.unique(days)
    dst_d = np.array([is_dst(int(u) * 86400 + 43200) for u in uq])
    dst = dst_d[np.searchsorted(uq, days)]
    mod = t % 86400
    roll = ((dst & (mod >= 20 * 3600 + 55 * 60) & (mod < 21 * 3600 + 30 * 60)) | (~dst & (mod >= 21 * 3600 + 55 * 60) & (mod < 22 * 3600 + 30 * 60))) & pos
    e = lambda ts, a, b: np.searchsorted(t, [ts + a * 60, ts + b * 60])
    fo, nf = [], []
    for s in FOMC:
        lo = int(pd.Timestamp(s).timestamp())
        at = lo + (18 if is_dst(lo + 43200) else 19) * 3600
        i, j = e(at, -1, 3)
        if j > i:
            fo.append(np.median(sp[i:j]))
    y0, y1 = [int(str(np.datetime64(int(x), "s"))[:4]) for x in (t[0], t[-1])]
    for lo in first_fridays(y0, y1):
        at = lo + 12 * 3600 + (30 * 60 if is_dst(lo + 43200) else 90 * 60)
        i, j = e(at, -1, 3)
        if j > i:
            nf.append(np.median(sp[i:j]))
    rr = sp[roll]
    rep["spreads"][sym] = dict(us_afternoon_median=round(base, 5), rollover_bars=int(roll.sum()), rollover_median=round(float(np.median(rr)), 5) if len(rr) else None, rollover_x=round(float(np.median(rr) / base), 2) if len(rr) else None,
                               rollover_p90_x=round(float(np.quantile(rr, 0.9) / base), 2) if len(rr) else None, fomc_median_x=round(float(np.median(fo) / base), 2) if fo else None, fomc_n=len(fo),
                               first_friday_release_median_x=round(float(np.median(nf) / base), 2), first_friday_n=len(nf))
print(rep["spreads"], flush=True)

# 3 cost matrix vs measured spread at each H1 trade, true clock -----------------
tr = pd.read_csv(os.path.join(HERE, "h1_true_utc_trades.csv"))
t, sp, c = z("XAUUSD")
to_s = lambda col: pd.to_datetime(tr[col], utc=True).astype("int64").values // 10**9 if pd.to_datetime(tr[col], utc=True).dtype.unit == "ns" else pd.to_datetime(tr[col], utc=True).astype("int64").values // 10**6
ent, ex = to_s("entry_ts"), to_s("exit_ts")


def at(u):
    i = np.searchsorted(t, u)
    i = np.minimum(i, len(t) - 1)
    return sp[i]


meas = (at(ent) + at(ex)) * 100 + 7.0  # same form as CostMatrix.trade_cost_usd with k_slip 0.5, one lot
gross = tr.gross_usd.values
net = gross - meas
gain, loss = net[net > 0].sum(), -net[net < 0].sum()
rep["h1_costs"] = dict(n=len(tr), matrix_cost_mean=round(float(tr.cost_med.mean()), 2), measured_cost_mean=round(float(meas.mean()), 2), pf_matrix=round(pa["pf"](tr.net_med.values), 3), pf_measured=round(float(gain / loss), 3),
                       nights_mean=round(float(((ex - ent) / 86400).mean()), 2), lot_nights=round(float(((ex // 86400 - ent // 86400)).sum()), 0), net_matrix=round(float(tr.net_med.sum())), breakeven_swap_usd_per_lot_night=None)
ln = rep["h1_costs"]["lot_nights"]
rep["h1_costs"]["breakeven_swap_usd_per_lot_night"] = round(float(tr.net_med.sum() / ln), 2) if ln else None
print(rep["h1_costs"], flush=True)

# 4 HistData gaps -------------------------------------------------------------
sys.path.insert(0, os.path.join(HERE, "..", "infrastructure"))
h = pd.read_csv("@GANN_ROOT@/research/data/xauusd_m1_histdata.csv", usecols=["time"]).time.values
g = np.where(np.diff(h) > 6 * 3600)[0]
weekday_gap = [(str(np.datetime64(int(h[i]), "s")), round((h[i + 1] - h[i]) / 3600, 1)) for i in g if not ((h[i] // 86400 + 4) % 7 in (5, 6) or (h[i + 1] // 86400 + 4) % 7 in (0, 6))]
rep["hist_gaps"] = dict(all_gaps_over_6h=len(g), not_weekend=len(weekday_gap), longest=sorted(weekday_gap, key=lambda x: -x[1])[:8])
print(rep["hist_gaps"], flush=True)

# 5 cross source --------------------------------------------------------------
def yahoo(p):
    j = json.load(open(p))["chart"]["result"][0]
    return pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s").normalize(), dtype=float).dropna()


SC = sys.argv[1]
rep["cross"] = {}
for nm, f, ys, path in (("US500 D1 vs ^GSPC", "@GANN_ROOT@/research/cross_market/data/US500_D1.npz", "gspc.json", None), ("BTC D1 vs BTC-USD", "@GANN_ROOT@/research/cross_market/data_edge/C_BTC_D1.npz", "btc.json", None), ("ETH D1 vs ETH-USD", "@GANN_ROOT@/research/cross_market/data_edge/C_ETH_D1.npz", "eth.json", None)):
    d = np.load(f)
    a = pd.Series(d["c"].astype(float), index=pd.to_datetime(d["t"], unit="s").normalize())
    a = a[~a.index.duplicated(keep="last")]
    b = yahoo(os.path.join(SC, ys))
    x = pd.concat([a.pct_change(), b.pct_change()], axis=1, join="inner").dropna()
    x.columns = ["a", "b"]
    best = {lag: float(x.a.corr(x.b.shift(lag))) for lag in (-1, 0, 1)}
    k = max(best, key=best.get)
    y = pd.concat([a, b], axis=1, join="inner").dropna()
    y.columns = ["a", "b"]
    rep["cross"][nm] = dict(days=len(x), corr_by_lag={str(q): round(v, 4) for q, v in best.items()}, best_lag=k, median_abs_level_diff_pct=round(float(((y.a / y.b - 1).abs()).median() * 100), 3))
print(rep["cross"], flush=True)
json.dump(rep, open(os.path.join(HERE, "deferred_checks.json"), "w"), indent=1, default=str)
