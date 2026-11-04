"""E7 per prereg/E7-INDICATORS.md. Part A gold 200-day, part B Bollinger + RSI on EURUSD and GBPUSD."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PC = os.path.join(HERE, "..", "phaseC")
GB = os.path.join(HERE, "..", "_copy", "goldbot")
sys.path[:0] = [HERE, PC, GB, os.path.join(GB, "prereg")]
import lib
from clockfix import shifted
from cost_matrix import CostMatrix
from goldbot.data import load_ohlc, resample_d1_utc

HIST = "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"
LBO = "@LBO_ROOT@/data/m1"
FEE_NIGHT_OZ = 0.05


def gold_d1():
    m1 = load_ohlc(HIST, data_tz="UTC")
    secs = m1.index.tz_localize(None).values.astype("datetime64[s]").astype(np.int64)
    out = m1.copy()
    out.index = m1.index - pd.to_timedelta(shifted(secs).astype(int), unit="h")
    out = out[~out.index.duplicated()].sort_index()
    d = resample_d1_utc(out)
    return d[d.index.dayofweek < 5]


def spells(d, cm):
    c, o = d.close.values, d.open.values
    s = pd.Series(c).rolling(200).mean().values
    on = c > s
    idx = d.index
    tr, i, n = [], 200, len(d)
    while i < n - 1:
        if on[i]:
            j = i
            while j < n - 2 and on[j]:
                j += 1
            a, b = i + 1, j + 1
            nights = int((idx[b] - idx[a]).days)
            gross = (o[b] - o[a]) / o[a]
            cost = cm.trade_cost_usd(idx[a], idx[b]) / 100 / o[a]
            fee = nights * FEE_NIGHT_OZ / o[a]
            tr.append(dict(t0=idx[a], t1=idx[b], gross=gross, cost=cost, fee=fee, hold=b - a))
            i = j + 1
        else:
            i += 1
    return pd.DataFrame(tr)


def daily_strategy(d, t, mult=1.0):
    ret = pd.Series(0.0, index=d.index)
    o = d.open
    roo = (o.shift(-1) / o - 1).fillna(0.0)
    for _, x in t.iterrows():
        m = (d.index >= x.t0) & (d.index < x.t1)
        ret[m] = roo[m]
        ret[x.t1] = ret.get(x.t1, 0.0) - mult * x.cost
        ret[m] = ret[m] - x.fee / max(m.sum(), 1)
    return ret


def sharpe(r):
    return float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0


def dd(r):
    e = (1 + r).cumprod()
    return float((e / e.cummax() - 1).min())


def bh(d):
    o = d.open
    return (o.shift(-1) / o - 1).fillna(0.0) - FEE_NIGHT_OZ * 1.4 / o


def slice_gold(d, t, a, b, ret_all, bh_all):
    x = t[(t.t0 >= a) & (t.t0 < b)]
    net1, net2 = (x.gross - x.cost - x.fee).values, (x.gross - 2 * x.cost - x.fee).values
    lr = np.diff(np.log(d.close[(d.index >= a) & (d.index < b)].values))
    p = lib.twin_p(float(np.mean(np.log1p(net1))) if len(net1) else 0.0, lr, x.hold.values, len(x)) if len(x) else 1.0
    g = lib.gates(net1, net2, p)
    m = (ret_all.index >= a) & (ret_all.index < b)
    g.update(sharpe=round(sharpe(ret_all[m]), 3), bh_sharpe=round(sharpe(bh_all[m]), 3), dd=round(dd(ret_all[m]), 3), bh_dd=round(dd(bh_all[m]), 3))
    g["sharpe_gate"] = g["sharpe"] >= g["bh_sharpe"]
    if g["status"] == "PASS" and not g["sharpe_gate"]:
        g.update(status="FAIL", passed=False)
    return g


def part_a():
    d = gold_d1()
    cm = CostMatrix.load(os.path.join(GB, "results", "cost_matrix.json"), stat="median", k_slip=0.5, commission_per_lot_rt=7.0)
    t = spells(d, cm)
    ret, b = daily_strategy(d, t), bh(d)
    rep = dict(label="CONTAMINATED in advance, GOLD-LIT-1 overlap", spells_total=len(t))
    for lab, s in (("with_2010_2012_ASSUMED_CLOCK", d.index[0]), ("without_2010_2012", pd.Timestamp("2013-01-01", tz="UTC"))):
        m = ret.index >= s
        x = t[t.t0 >= s]
        rep[lab] = dict(spells=len(x), pf=round(lib.pf((x.gross - x.cost - x.fee).values), 3), sharpe=round(sharpe(ret[m]), 3), bh_sharpe=round(sharpe(b[m]), 3), dd=round(dd(ret[m]), 3), bh_dd=round(dd(b[m]), 3))
    t0, t1 = pd.Timestamp("2013-01-01", tz="UTC"), d.index[-1]
    c1, c2 = lib.cuts(t0, t1)
    rep["slices"] = dict(dev_end=str(c1.date()), val_end=str(c2.date()))
    dev = slice_gold(d, t, t0, c1, ret, b)
    rep["dev"] = dev
    if dev["passed"]:
        rep["validation"] = slice_gold(d, t, c1, c2, ret, b)
        rep["holdout"] = slice_gold(d, t, c2, t1 + pd.Timedelta(days=1), ret, b) if rep["validation"]["passed"] else "not evaluated"
    else:
        rep["validation"] = rep["holdout"] = "not evaluated"
    return rep


def fx_h1(sym):
    z = np.load(f"{LBO}/{sym}.npz")
    t = z["t"].astype(np.int64)
    t = t * 60 if int(t[0]) < 10**8 else t
    d = pd.DataFrame({k: z[k].astype(float) for k in ("o", "h", "l", "c", "sp")}, index=pd.to_datetime(t, unit="s", utc=True))
    g = d.resample("1h")
    h = pd.DataFrame(dict(o=g.o.first(), h=g.h.max(), l=g.l.min(), c=g.c.last(), sp=g.sp.median())).dropna()
    return h


def bb_trades(h):
    c, o, hi, lo, sp = (h[k].values for k in ("c", "o", "h", "l", "sp"))
    cs = pd.Series(c)
    mid = cs.rolling(20).mean().values
    sd = cs.rolling(20).std(ddof=0).values
    dlt = cs.diff()
    up, dn = dlt.clip(lower=0), -dlt.clip(upper=0)
    rs = up.ewm(alpha=1 / 14, adjust=False).mean() / dn.ewm(alpha=1 / 14, adjust=False).mean()
    rsi = (100 - 100 / (1 + rs)).values
    tr = np.maximum.reduce([hi[1:] - lo[1:], np.abs(hi[1:] - c[:-1]), np.abs(lo[1:] - c[:-1])])
    atr = pd.Series(np.r_[np.nan, tr]).ewm(alpha=1 / 14, adjust=False).mean().values
    out, i, n = [], 40, len(c)
    while i < n - 2:
        s = 1 if (c[i] < mid[i] - 2 * sd[i] and rsi[i] < 30) else (-1 if (c[i] > mid[i] + 2 * sd[i] and rsi[i] > 70) else 0)
        if s == 0:
            i += 1
            continue
        k = i + 1
        px = o[k]
        stop = px - s * 2 * atr[i]
        ex, why = None, None
        for j in range(k, min(k + 48, n - 1)):
            if j > k and s * (o[j] - stop) <= 0:
                ex, why = o[j], "gap"
                break
            if (s == 1 and lo[j] <= stop) or (s == -1 and hi[j] >= stop):
                ex, why = stop, "stop"
                break
            if s * (c[j] - mid[j]) >= 0:
                ex, why = o[j + 1], "mid"
                j += 1
                break
        else:
            j = min(k + 48, n - 1)
            ex, why = o[j], "time"
        spr = sp[k] + sp[j]
        cost = spr + 0.5 * spr + 0.00007
        out.append(dict(t=h.index[k], s=s, gross=s * (ex - px), cost=cost, risk=2 * atr[i], hold=j - k, why=why))
        i = j + 1
    return pd.DataFrame(out)


def part_b(sym):
    h = fx_h1(sym)
    t = bb_trades(h)
    t0, t1 = h.index[0], h.index[-1]
    c1, c2 = lib.cuts(t0, t1)
    rep = dict(bars=len(h), first=str(t0.date()), last=str(t1.date()), dev_end=str(c1.date()), val_end=str(c2.date()))

    def sl(a, b):
        x = t[(t.t >= a) & (t.t < b)]
        net, net2 = (x.gross - x.cost).values, (x.gross - 2 * x.cost).values
        pr = h[(h.index >= a) & (h.index < b)]
        lr = np.diff(np.log(pr.c.values))
        p = lib.twin_p(float((net / pr.c.mean()).mean()) if len(x) else 0.0, lr, x.hold.values, len(x)) if len(x) else 1.0
        g = lib.gates(net, net2, p)
        g["pf_gross"] = round(lib.pf(x.gross.values), 3)
        g["pf_1_5x"] = round(lib.pf((x.gross - 1.5 * x.cost).values), 3)
        g["avg_r"] = round(float((net / x.risk.values).mean()), 4) if len(x) else None
        return g

    rep["dev"] = sl(t0, c1)
    if rep["dev"]["passed"]:
        rep["validation"] = sl(c1, c2)
        rep["holdout"] = sl(c2, t1 + pd.Timedelta(days=1)) if rep["validation"]["passed"] else "not evaluated"
    else:
        rep["validation"] = rep["holdout"] = "not evaluated"
    return rep


rep = dict(A_gold_200d=part_a(), B_EURUSD=part_b("EURUSD"), B_GBPUSD=part_b("GBPUSD"))
json.dump(rep, open(os.path.join(HERE, "e7_result.json"), "w"), indent=1, default=str)
print(json.dumps(rep, indent=1, default=str))
