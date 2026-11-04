"""Spot checks: 20 seeded random trades per headline or PASS result, drawn as a contact sheet, with a table of the rule values at entry and exit.
Plus the second-engine replay of FINAL_v3 and FINAL_v4 on the audit engine. No plotting library is available, so PNGs are written directly."""
import json
import os
import struct
import sys
import zlib

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.abspath(os.path.join(HERE, ".."))
sys.path[:0] = [A + "/engine", A + "/phaseC", A + "/_copy/rs_recorded/research/cross_market"]
from nbe import simulate

src = open(A + "/stats/pass_audit.py", encoding="utf-8").read().replace("\nmain()\n", "\n")
pa = {"__file__": A + "/stats/pass_audit.py"}
exec(compile(src, "pass_audit", "exec"), pa)
rng = np.random.default_rng(20261031)
W, H, COLS, ROWS = 300, 180, 4, 5
G, R_, B, O, P, K = (40, 150, 70), (200, 60, 50), (40, 90, 200), (235, 130, 20), (130, 60, 170), (60, 60, 60)


def png(path, a):
    h, w, _ = a.shape
    raw = b"".join(b"\0" + a[y].tobytes() for y in range(h))
    ch = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw, 6)) + ch(b"IEND", b""))


def line(a, x0, y0, x1, y1, col):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    xs = np.linspace(x0, x1, n).astype(int)
    ys = np.linspace(y0, y1, n).astype(int)
    ok = (xs >= 0) & (xs < a.shape[1]) & (ys >= 0) & (ys < a.shape[0])
    a[ys[ok], xs[ok]] = col


def cell(o, h, l, c, marks, hlines=(), curves=()):
    """marks: (bar index, colour). hlines: (price, colour). curves: (array, colour)."""
    a = np.full((H, W, 3), 255, np.uint8)
    n = len(o)
    lo = min(l.min(), *[p for p, _ in hlines]) if hlines else l.min()
    hi = max(h.max(), *[p for p, _ in hlines]) if hlines else h.max()
    pad = (hi - lo) * 0.05 + 1e-9
    lo, hi = lo - pad, hi + pad
    Y = lambda p: (H - 6) - (p - lo) / (hi - lo) * (H - 12)
    bw = (W - 10) / n
    X = lambda i: 5 + (i + 0.5) * bw
    for i, cl in marks:
        line(a, X(i), 2, X(i), H - 3, cl)
    for p, cl in hlines:
        line(a, 2, Y(p), W - 3, Y(p), cl)
    for v, cl in curves:
        for i in range(1, n):
            if np.isfinite(v[i]) and np.isfinite(v[i - 1]) and lo <= v[i] <= hi and lo <= v[i - 1] <= hi:
                line(a, X(i - 1), Y(v[i - 1]), X(i), Y(v[i]), cl)
    for i in range(n):
        col = G if c[i] >= o[i] else R_
        line(a, X(i), Y(h[i]), X(i), Y(l[i]), K)
        a[int(min(Y(o[i]), Y(c[i]))): int(max(Y(o[i]), Y(c[i]))) + 1, int(X(i) - max(bw * 0.3, 0)): int(X(i) + max(bw * 0.3, 1))] = col
    a[0, :] = a[-1, :] = (170, 170, 170)
    a[:, 0] = a[:, -1] = (170, 170, 170)
    return a


def sheet(name, cells):
    s = np.full((H * ROWS, W * COLS, 3), 255, np.uint8)
    for k, c in enumerate(cells[:COLS * ROWS]):
        s[(k // COLS) * H: (k // COLS) * H + H, (k % COLS) * W: (k % COLS) * W + W] = c
    png(os.path.join(HERE, name + ".png"), s)


def pick(n, k=20):
    return np.sort(rng.choice(n, min(k, n), replace=False))


iso = lambda s: str(np.datetime64(int(s), "s"))[:16]


def dip(name, m, trades, rows_fn, sma_n=(5, 200)):
    """Daily-rule sheet. Blue = entry bar, orange = exit bar. Purple = SMA200 or none, grey curve = SMA5."""
    t, o, h, l, c = m["t"], m["o"], m["h"], m["l"], m["c"]
    cells, rows = [], []
    for x in [trades[i] for i in pick(len(trades))]:
        i = int(np.searchsorted(t, x[0]))
        j = i + x[4]
        a, b = max(i - 15, 0), min(j + 6, len(t))
        marks = [(i + 1 - a, B), (j + 1 - a, O)]
        cells.append(cell(o[a:b], h[a:b], l[a:b], c[a:b], marks, curves=[(pa["sma"](c, n)[a:b], P if n == 200 else (120, 120, 120)) for n in sma_n]))
        rows.append(rows_fn(i, j, x))
    sheet(name, cells)
    pd.DataFrame(rows).to_csv(os.path.join(HERE, name + ".csv"), index=False)
    return rows


us = pa["load"]("US500")
rsi, s5, s200 = pa["rsi2"](us["c"]), pa["sma"](us["c"], 5), pa["sma"](us["c"], 200)
ibs = (us["c"] - us["l"]) / np.where(us["h"] > us["l"], us["h"] - us["l"], np.nan)
OK = {}


def a1row(m, r, s5_, s200_):
    def f(i, j, x):
        c = m["c"]
        ok = bool(r[i] < 10 and c[i] > s200_[i] and (c[j] > s5_[j] or j - i >= 10) and all(c[q] <= s5_[q] for q in range(i + 1, j)))
        return dict(signal=iso(m["t"][i]), rsi2=round(r[i], 1), close=c[i], sma200=round(s200_[i], 1), exit_day=iso(m["t"][j]), exit_close=c[j], sma5_exit=round(s5_[j], 1), hold=j - i, ret_pct=round(x[3] * 100, 3), rule_holds=ok)
    return f


r = dip("XM-1-A1", us, pa["a1"](us), a1row(us, rsi, s5, s200))
OK["XM-1-A1"] = [sum(x["rule_holds"] for x in r), len(r)]


def ibsrow(i, j, x):
    c, h = us["c"], us["h"]
    ok = bool(ibs[i] < 0.2 and (ibs[j] > 0.8 or c[j] > h[j - 1] or j - i >= 15))
    return dict(signal=iso(us["t"][i]), ibs=round(ibs[i], 3), exit_day=iso(us["t"][j]), exit_ibs=round(ibs[j], 3), exit_close=c[j], prev_high=h[j - 1], hold=j - i, ret_pct=round(x[3] * 100, 3), rule_holds=ok)


r = dip("SW-1-MR2", us, pa["ibs_rule"](us), ibsrow, sma_n=(5,))
OK["SW-1"] = [sum(x["rule_holds"] for x in r), len(r)]

# TUNE-1 HOLD-T: pool, then split per market for the chart
t0 = int(np.datetime64("2023-10-13", "s").astype(np.int64))
pool = []
for sym in ("US500", "US30", "US2000", "USTEC"):
    m = pa["load"](sym)
    m = dict(m, sp=max(m["sp"], 0.0002 * float(np.median(m["c"]))))
    q = pa["rsi2"](m["c"]), pa["sma"](m["c"], 5), pa["sma"](m["c"], 200)
    pool += [(sym, m, q, x) for x in pa["a1"](m) if x[0] >= t0]
cells, rows = [], []
for k in pick(len(pool)):
    sym, m, q, x = pool[k]
    t = m["t"]
    i = int(np.searchsorted(t, x[0]))
    j = i + x[4]
    a, b = max(i - 15, 0), min(j + 6, len(t))
    cells.append(cell(m["o"][a:b], m["h"][a:b], m["l"][a:b], m["c"][a:b], [(i + 1 - a, B), (j + 1 - a, O)], curves=[(q[1][a:b], (120, 120, 120)), (q[2][a:b], P)]))
    rows.append(dict(a1row(m, *q)(i, j, x), market=sym))
sheet("TUNE-1-DIP", cells)
pd.DataFrame(rows).to_csv(os.path.join(HERE, "TUNE-1-DIP.csv"), index=False)
OK["TUNE-1-DIP"] = [sum(x["rule_holds"] for x in rows), len(rows)]

# F6: 20 signal flips across coins
cl = {}
for c_ in ("BTC", "ETH", "BNB", "SOL", "XRP", "ADA"):
    z = np.load(f"@GANN_ROOT@/research/cross_market/data_edge/C_{c_}_D1.npz")
    cl[c_] = {k: z[k].astype(float) for k in "ohlc"} | {"t": z["t"].astype(np.int64)}
fl = []
for c_, m in cl.items():
    s50 = pa["sma"](m["c"], 50)
    sg = m["c"] > s50
    for i in np.flatnonzero(sg[1:] != sg[:-1]) + 1:
        if i > 60:
            fl.append((c_, int(i), bool(sg[i])))
cells, rows = [], []
for k in pick(len(fl)):
    c_, i, on = fl[k]
    m = cl[c_]
    s50 = pa["sma"](m["c"], 50)
    a, b = i - 20, min(i + 10, len(m["t"]))
    cells.append(cell(m["o"][a:b], m["h"][a:b], m["l"][a:b], m["c"][a:b], [(i - a, B if on else O)], curves=[(s50[a:b], P)]))
    rows.append(dict(coin=c_, day=iso(m["t"][i]), close=m["c"][i], sma50=round(s50[i], 4), prev_close=m["c"][i - 1], prev_sma50=round(s50[i - 1], 4), goes_long=on, rule_holds=bool((m["c"][i] > s50[i]) == on and (m["c"][i - 1] > s50[i - 1]) != on)))
sheet("EDGE-1-F6", cells)
pd.DataFrame(rows).to_csv(os.path.join(HERE, "EDGE-1-F6.csv"), index=False)
OK["EDGE-1-F6"] = [sum(x["rule_holds"] for x in rows), len(rows)]

# Gold intraday, true clock
csv = pd.read_csv(A + "/_copy/data/xauusd_m1_trueutc.csv")
T, o, h, l, c = [csv[x].values for x in ("time", "open", "high", "low", "close")]


def m5(i0, i1):
    k = np.arange(i0, i1)
    g = (T[k] // 300)
    u, st_ = np.unique(g, return_index=True)
    e = np.r_[st_[1:], len(k)]
    return (np.array([o[k[a]] for a in st_]), np.array([h[k[a:b]].max() for a, b in zip(st_, e)]), np.array([l[k[a:b]].min() for a, b in zip(st_, e)]), np.array([c[k[b - 1]] for b in e]), T[k[st_]])


def gold_sheet(name, ts, side, px, ex_ts, tpsl):
    cells, rows = [], []
    for k in pick(len(ts)):
        i = int(np.searchsorted(T, ts[k]))
        j = int(np.searchsorted(T, ex_ts[k]))
        a, b = max(i - 60, 0), min(max(j, i + 30) + 60, len(T))
        O_, H_, L_, C_, tt = m5(a, b)
        hl = [(px[k], B)] + [(p, cl) for p, cl in ((tpsl[0][k], G), (tpsl[1][k], R_)) if np.isfinite(p)]
        cells.append(cell(O_, H_, L_, C_, [(int(np.searchsorted(tt, T[i])), B), (int(np.searchsorted(tt, T[min(j, len(T) - 1)])), O)], hlines=hl))
        rows.append(dict(entry=iso(ts[k]), side=int(side[k]), entry_px=round(float(px[k]), 2), exit=iso(ex_ts[k])))
    sheet(name, cells)
    pd.DataFrame(rows).to_csv(os.path.join(HERE, name + ".csv"), index=False)


h1 = pd.read_csv(A + "/phaseC/h1_true_utc_trades.csv")
sec = lambda s: (pd.to_datetime(s, utc=True).astype("datetime64[s, UTC]").astype("int64")).values
sd = (h1.side.map({"BUY": 1, "SELL": -1, "buy": 1, "sell": -1, 1: 1, -1: -1})).values
gold_sheet("H1-true-utc", sec(h1.entry_ts), sd, h1.entry_px.values, sec(h1.exit_ts), (h1.entry_px.values + sd * 0.8 * h1.atr.values, h1.entry_px.values - sd * 2.4 * h1.atr.values))

# second engine over FINAL_v3 and FINAL_v4, both clocks
xe = {}
for clock, path in (("recorded", "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"), ("true", A + "/_copy/data/xauusd_m1_trueutc.csv")):
    d = pd.read_csv(path).sort_values("time")
    Tt, Oo, Hh, Ll, Cc = [d[x].values.astype(float) if x != "time" else d[x].values.astype(np.int64) for x in ("time", "open", "high", "low", "close")]
    for nm in ("v3", "v4"):
        f = pd.read_csv(A + f"/phaseC/fable_{nm}_{clock}.csv")
        ts = (pd.to_datetime(f.ts, utc=True).astype("datetime64[s, UTC]").astype("int64")).values
        sg = f.dir.map({"BUY": 1, "SELL": -1}).values
        i0 = np.searchsorted(Tt, ts)
        pnl, why, gaps = [], [], 0
        for k in range(len(f)):
            end = int(np.searchsorted(Tt, Tt[i0[k]] + 24 * 3600))
            r = simulate(Oo, Hh, Ll, Cc, 0.0, np.array([i0[k]]), np.array([sg[k]]), np.array([f.sl[k]]), np.array([f.tp[k]]), end - i0[k] + 1)
            pnl.append(float(r.pnl[0]) * 100 - 20.0)
            why.append(int(r.reason[0]))
        pnl = np.array(pnl)
        same = np.abs(pnl - f.pnl.values) < 0.5
        xe[f"{nm} {clock}"] = dict(n=len(f), match_within_50c=int(same.sum()), net_orig=round(float(f.pnl.sum())), net_nbe=round(float(pnl.sum())), diff_pct=round(float((pnl.sum() / f.pnl.sum() - 1) * 100), 2), pf_orig=round(pa["pf"](f.pnl.values), 3), pf_nbe=round(pa["pf"](pnl), 3))
        if clock == "true":
            cost = pd.Series(pnl)
            gold_sheet(f"FINAL-{nm}-true-utc", ts, sg, Oo[i0], ts + 3600, (Oo[i0] + sg * f.tp.values, Oo[i0] - sg * f.sl.values))
print(OK)
print(xe)
json.dump(dict(rule_table=OK, cross_engine=xe), open(os.path.join(HERE, "spot_checks.json"), "w"), indent=1)
