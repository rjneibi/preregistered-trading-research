"""E1 per prereg/E1-PAIRS.md. One config per variant, gates per slice in order, holdout opened only after validation passes."""
import glob
import json
import os
import sys
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import coint
from statsmodels.tsa.vector_ar.vecm import coint_johansen

HERE = os.path.dirname(os.path.abspath(__file__))
GB = os.path.join(HERE, "..", "_copy", "goldbot")
sys.path[:0] = [HERE, GB]
import lib
from goldbot.ou_estimator import fit_ou

warnings.filterwarnings("ignore")
LBO = "@LBO_ROOT@/data/m1"
XM = "@GANN_ROOT@/research/cross_market/data"
DK = os.path.join(HERE, "..", "_copy", "data", "dk_xag")
PUB = os.path.join(HERE, "..", "_copy", "data", "public")
Q_V, R_V = 1e-5, 1e-3


def gold_m1():
    z = np.load(f"{LBO}/XAUUSD.npz")
    t = z["t"].astype(np.int64)
    t = t * 60 if int(t[0]) < 10**8 else t
    d = pd.DataFrame({"o": z["o"], "c": z["c"], "sp": z["sp"]}, index=pd.to_datetime(t, unit="s", utc=True))
    return d[~d.index.duplicated()].sort_index()


def silver_m1():
    fr = {}
    for s in ("bid", "ask"):
        a = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(DK, f"xagusd-{s}-*.csv")))])
        a.index = pd.to_datetime(a.timestamp, unit="ms", utc=True)
        fr[s] = a[~a.index.duplicated()].sort_index()
    x = fr["bid"].join(fr["ask"], lsuffix="_b", rsuffix="_a", how="inner")
    return pd.DataFrame({"o": (x.open_b + x.open_a) / 2, "c": (x.close_b + x.close_a) / 2, "sp": x.close_a - x.close_b}, index=x.index)


def to_h1(m):
    g = m.resample("1h")
    return pd.DataFrame(dict(o=g.o.first(), c=g.c.last(), sp=g.sp.median())).dropna()


def frame_xau_xag():
    a, b = to_h1(gold_m1()), to_h1(silver_m1())
    d = a.join(b, how="inner", lsuffix="_a", rsuffix="_b").dropna()
    return d.rename(columns=dict(o_a="a_o", c_a="a_c", sp_a="a_sp", o_b="b_o", c_b="b_c", sp_b="b_sp"))


def frame_crypto():
    fr = {}
    for s in ("BTCUSDT", "ETHUSDT"):
        z = np.load(f"{XM}/{s}_1h.npz")
        d = pd.DataFrame(dict(o=z["o"], c=z["c"]), index=pd.to_datetime(z["t"], unit="s", utc=True))
        fr[s] = d[~d.index.duplicated()].sort_index()
    d = fr["BTCUSDT"].join(fr["ETHUSDT"], how="inner", lsuffix="_a", rsuffix="_b").dropna()
    d = d.rename(columns=dict(o_a="a_o", c_a="a_c", o_b="b_o", c_b="b_c"))
    d["a_sp"], d["b_sp"] = 0.0, 0.0
    return d


def frame_gdx():
    r = json.load(open(os.path.join(PUB, "GDX_yahoo.json")))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    adj = np.array(r["indicators"]["adjclose"][0]["adjclose"], float) / np.array(q["close"], float)
    days = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert("America/New_York").normalize()
    g = pd.DataFrame({"a_o": np.array(q["open"], float) * adj, "a_c": np.array(q["close"], float) * adj, "raw": q["close"]}, index=days).dropna()
    m = gold_m1()
    idx = m.index.tz_convert("America/New_York")
    op, cl, sp = [], [], []
    keep = []
    for d in g.index:
        i = idx.searchsorted(d + pd.Timedelta(hours=9, minutes=30))
        j = idx.searchsorted(d + pd.Timedelta(hours=16), side="right") - 1
        if i >= len(idx) or j < 0 or idx[i] - (d + pd.Timedelta(hours=9, minutes=30)) > pd.Timedelta(minutes=15) or (d + pd.Timedelta(hours=16)) - idx[j] > pd.Timedelta(minutes=15):
            continue
        keep.append(d)
        op.append(m.o.iat[i])
        cl.append(m.c.iat[j])
        sp.append(m.sp.iat[j])
    g = g.loc[keep]
    g["b_o"], g["b_c"], g["b_sp"] = op, cl, sp
    g["a_sp"] = 0.0
    g.index = g.index.tz_convert("UTC")
    return g


def costs_for(pair, x, wa, wb, nights, days, a_sp0, a_sp1, b_sp0, b_sp1, a0, b0, side_a):
    """Round-trip cost as a fraction of gross notional. side_a is +1 when A is long."""
    def metal(px, s0, s1, oz):
        return (s0 + s1) / 2 / px + 0.5 * (s0 + s1) / px + 7.0 / (oz * px) + nights * 5.0 / (oz * px)

    if pair == "XAU/XAG":
        return wa * metal(a0, a_sp0, a_sp1, 100) + wb * metal(b0, b_sp0, b_sp1, 5000)
    if pair == "BTC/ETH":
        return wa * 0.001 + wb * 0.001 + (wb if side_a > 0 else wa) * 0.15 * days / 365
    return wa * 0.02 / a0 + wb * metal(b0, b_sp0, b_sp1, 100)


def kalman(la, lb, alpha, beta0):
    b, P = beta0, 1.0
    bs, es = np.empty(len(la)), np.empty(len(la))
    for i in range(len(la)):
        P += Q_V
        y = la[i] - alpha
        e = y - b * lb[i]
        S = lb[i] ** 2 * P + R_V
        K = P * lb[i] / S
        bs[i], es[i] = b, e
        b += K * e
        P *= 1 - K * lb[i]
    return bs, es, b, P


def run(pair, d, variant, form_days, bar_h, cap_h, top=np.inf):
    t = d.index
    la, lb = np.log(d.a_c.values), np.log(d.b_c.values)
    ao, bo, asp, bsp = d.a_o.values, d.b_o.values, d.a_sp.values, d.b_sp.values
    per = t.tz_localize(None).to_period("M")
    starts = np.flatnonzero(np.r_[True, per[1:] != per[:-1]])
    months, trades = [], []
    pos = None
    for k, s0 in enumerate(starts):
        s1 = starts[k + 1] if k + 1 < len(starts) else len(t)
        f0 = (np.searchsorted(t, t[s0] - pd.Timedelta(days=form_days)) if bar_h < 24 else s0 - form_days)
        if f0 < 0 or s0 - f0 < (400 if bar_h < 24 else 200) or t[f0] > t[s0] - pd.Timedelta(days=(form_days - 3) if bar_h < 24 else 300):
            continue
        fa, fb = la[f0:s0], lb[f0:s0]
        beta, alpha = np.polyfit(fb, fa, 1)
        res = fa - alpha - beta * fb
        eg = float(coint(fa, fb)[1])
        jo = coint_johansen(np.c_[fa, fb], 0, 1)
        jp = bool(jo.lr1[0] > jo.cvt[0, 1])
        ou = fit_ou(res, dt=float(bar_h), min_obs=100)
        both = (eg < 0.05) and jp
        months.append(dict(month=str(per[s0]), eg=eg < 0.05, jo=jp, both=both, valid=ou.valid, hl_h=ou.half_life if ou.valid else None))
        filt = both if variant != "V3" else True
        allow = filt and ou.valid
        hl = ou.half_life if ou.valid else None
        if variant == "V2":
            _, ef, bf, Pf = kalman(fa, fb, alpha, beta)
            sd = float(ef[20:].std())
            bs, es, _, _ = kalman(la[s0:s1], lb[s0:s1], alpha, bf)
            z = es / sd
        else:
            mu, sd = float(res.mean()), float(res.std())
            bs = np.full(s1 - s0, beta)
            z = (la[s0:s1] - alpha - beta * lb[s0:s1] - mu) / sd
        if pos is not None and variant != "V3" and not both and s0 + 1 < len(t):
            pos["force"] = True
        for i in range(s0, s1 - 1 if s1 == len(t) else s1):
            zi = z[i - s0]
            if pos is not None:
                hrs = (t[i] - pos["t0"]).total_seconds() / 3600
                if pos.get("force"):
                    why = "breakdown"
                elif pos["s"] * zi <= 0 and variant == "V2":
                    why = "cross"
                elif variant != "V2" and pos["s"] * ((la[i] - pos["alpha"] - pos["beta"] * lb[i] - pos["mu"]) / pos["sd"]) <= 0:
                    why = "cross"
                elif abs(zi if variant == "V2" else (la[i] - pos["alpha"] - pos["beta"] * lb[i] - pos["mu"]) / pos["sd"]) >= 4:
                    why = "stop"
                elif hrs >= pos["limit"]:
                    why = "time"
                else:
                    why = None
                if why and i + 1 < len(t):
                    j = i + 1
                    b_ = pos["beta"]
                    wa, wb = 1 / (1 + abs(b_)), abs(b_) / (1 + abs(b_))
                    a_ret = ao[j] / ao[pos["i"]] - 1
                    b_ret = bo[j] / bo[pos["i"]] - 1
                    sa = -pos["s"]
                    gross = sa * (wa * a_ret - np.sign(b_) * wb * b_ret)
                    days = (t[j] - t[pos["i"]]).total_seconds() / 86400
                    nights = int(days + 0.5)
                    c = costs_for(pair, None, wa, wb, nights, days, asp[pos["i"]], asp[j], bsp[pos["i"]], bsp[j], ao[pos["i"]], bo[pos["i"]], sa)
                    trades.append(dict(t0=t[pos["i"]], t1=t[j], gross=gross, cost=c, why=why, bars=j - pos["i"], coint_month=pos["both"], beta=b_))
                    pos = None
                    continue
            if pos is None and allow and 2 <= abs(zi) < top and i + 1 < len(t) and i + 1 < s1:
                pos = dict(i=i + 1, t0=t[i + 1], s=float(np.sign(zi)), beta=float(bs[i - s0]), alpha=alpha, mu=(res.mean() if variant != "V2" else 0.0), sd=sd, limit=min(3 * hl, cap_h), both=both)
    return pd.DataFrame(trades), pd.DataFrame(months)


def spread_ret(d):
    return np.diff(np.log(d.a_c.values)) - np.diff(np.log(d.b_c.values))


def slice_eval(t, d, a, b):
    x = t[(t.t0 >= a) & (t.t0 < b)] if len(t) else t
    if not len(x):
        return dict(n=0, status="INSUFFICIENT SAMPLE", passed=False, pf=None)
    dd = d[(d.index >= a) & (d.index < b)]
    p = lib.twin_p(float(x.gross.mean()), spread_ret(dd) / 2, x.bars.values, len(x))
    g = lib.gates((x.gross - x.cost).values, (x.gross - 2 * x.cost).values, p)
    g["pf_1_5x"] = round(lib.pf((x.gross - 1.5 * x.cost).values), 3)
    g["pf_gross"] = round(lib.pf(x.gross.values), 3)
    g["why"] = x.why.value_counts().to_dict()
    return g


def main():
    specs = (("XAU/XAG", frame_xau_xag, 90, 1, 240), ("BTC/ETH", frame_crypto, 90, 1, 240), ("Gold/GDX", frame_gdx, 252, 24, 1440))
    rep = {}
    for pair, fn, fd, bh, cap in specs:
        try:
            d = fn()
        except Exception as e:
            rep[pair] = dict(status=f"skipped: {e}")
            continue
        d = d[d.index >= "2015-01-01"] if pair != "BTC/ETH" else d
        t0, t1 = d.index[0], d.index[-1]
        c1, c2 = lib.cuts(t0, t1)
        r = dict(bars=len(d), first=str(t0), last=str(t1), dev_end=str(c1), val_end=str(c2))
        for v, top in (("V1", np.inf), ("V2", np.inf), ("V3", np.inf), ("V1_band", 4.0), ("V2_band", 4.0), ("V3_band", 4.0)):
            t, m = run(pair, d, v[:2], fd, bh, cap, top)
            if v == "V1":
                r["cointegration"] = dict(months=len(m), eg=round(float(m.eg.mean()), 3), johansen=round(float(m.jo.mean()), 3), both=round(float(m.both.mean()), 3), valid_ou=round(float(m.valid.mean()), 3),
                                          hl_h_p10_50_90=[round(float(x), 1) for x in np.nanpercentile(m.hl_h.astype(float), [10, 50, 90])])
                by_y = m.assign(y=m.month.str[:4]).groupby("y").both.mean().round(2).to_dict()
                r["cointegration"]["both_by_year"] = by_y
            s = dict()
            s["dev"] = slice_eval(t, d, t0, c1)
            if s["dev"]["passed"]:
                s["validation"] = slice_eval(t, d, c1, c2)
                if s["validation"]["passed"]:
                    s["holdout"] = slice_eval(t, d, c2, t1 + pd.Timedelta(seconds=1))
                    hx = t[t.t0 >= c2]
                    s["holdout"]["dsr_ledger"] = lib.dsr((hx.gross - hx.cost).values, lib.LEDGER_N)
                    s["holdout"]["dsr_family"] = lib.dsr((hx.gross - hx.cost).values, 9)
                else:
                    s["holdout"] = "not evaluated"
            else:
                s["validation"] = s["holdout"] = "not evaluated"
            if v[:2] == "V3" and len(t):
                dv = t[t.t0 < c1]
                for lab, q in (("in_cointegrated_months", dv[dv.coint_month]), ("outside", dv[~dv.coint_month])):
                    s[lab + "_dev"] = dict(n=len(q), pf=round(lib.pf((q.gross - q.cost).values), 3), pf_gross=round(lib.pf(q.gross.values), 3))
            last = c1 if s["validation"] == "not evaluated" else (c2 if s["holdout"] == "not evaluated" else t1 + pd.Timedelta(seconds=1))
            if len(t):
                t[t.t0 < last].to_csv(os.path.join(HERE, f"e1_trades_{pair.replace('/', '-')}_{v}.csv"), index=False)
            r[v] = s
            print(pair, v, json.dumps(s, default=str)[:400], flush=True)
        rep[pair] = r
    json.dump(rep, open(os.path.join(HERE, "e1_result.json"), "w"), indent=1, default=str)


main()
