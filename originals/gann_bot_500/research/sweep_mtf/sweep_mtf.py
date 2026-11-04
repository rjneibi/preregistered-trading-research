"""SWEEP-MTF-1 (PREREG.md frozen before this ran): HTF swing sweep + LTF close-back, XAU 2010-2026.
Run: goldbot venv python sweep_mtf.py  -> results/summary.txt, results/trades_*.csv, results/report_data.json"""
import datetime as dt
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "d_revival"))
from data import load  # noqa: E402

# ---- parameters (frozen in PREREG.md) ----
SWING_N = 3          # HTF bars each side of a swing
CONFIRM_BARS = 12    # LTF bars to see a close back inside, counted from the sweep bar
STOP_BUF = 0.20      # $ above the sweep high
TARGETS = (2.0, 3.0)
CAP_BARS = 288       # time cap in LTF bars
MAX_GAP = 3600       # skip entry if next LTF bar starts later than this (s)
COSTS = {"zero": 0.0, "ic": 0.22, "base": 0.40, "stress": 0.80}
COST = COSTS["base"]
SEEDS = 20
VARIANTS = {"A": (60, 5, None), "B": (240, 15, None), "C": (60, 5, "h4ema"), "D": (60, 5, "session")}
END = 1791763200          # 2026-10-12 UTC (data end)
MAIN0 = END - 3 * 365 * 86400 - 86400   # 2023-10-12
OOS0 = END - 365 * 86400                # 2025-10-12
WIN = {"IS": (MAIN0, OOS0), "OOS": (OOS0, 9e9), "H1 2010-16": (0, 1483228800), "H2 2017-23": (1483228800, MAIN0)}
BIGN = 10 ** 9


def us_dst(y):  # same rule as pa1 / exit2.to_utc
    mar = dt.date(y, 3, 1); nov = dt.date(y, 11, 1)
    s = mar + dt.timedelta(days=(6 - mar.weekday()) % 7 + 7)
    e = nov + dt.timedelta(days=(6 - nov.weekday()) % 7)
    f = lambda d: int(dt.datetime(y, d.month, d.day, tzinfo=dt.timezone.utc).timestamp())
    return f(s), f(e)


def to_utc(tb):
    off = np.full(len(tb), 2 * 3600, dtype=np.int64)
    for y in range(2009, 2028):
        s, e = us_dst(y)
        off[(tb >= s) & (tb < e)] = 3 * 3600
    return tb - off


m = load()
t = to_utc(m["t"]); o, h, l, c = m["o"], m["h"], m["l"], m["c"]
N = len(t)


def bars(minutes, min_frac=0.0):
    key = t // (minutes * 60)
    st = np.flatnonzero(np.diff(key, prepend=key[0] - 1))
    en = np.r_[st[1:], N]
    hh, ll = np.maximum.reduceat(h, st), np.minimum.reduceat(l, st)
    ok = (en - st) >= max(1, min_frac * minutes)
    st, en = st[ok], en[ok]
    return dict(i0=st, ts=key[st] * minutes * 60, te=key[st] * minutes * 60 + minutes * 60,
                o=o[st], h=hh[ok], l=ll[ok], c=c[en - 1])


def swings(B, n=SWING_N):
    """(sign, level, confirm_time): sign -1 = swing high (short setup), +1 = swing low (long setup)."""
    H, L = B["h"], B["l"]
    out = []
    for j in range(n, len(H) - n):
        if H[j] > H[j - n:j].max() and H[j] > H[j + 1:j + n + 1].max():
            out.append((-1, H[j], B["te"][j + n], j))
        if L[j] < L[j - n:j].min() and L[j] < L[j + 1:j + n + 1].min():
            out.append((1, L[j], B["te"][j + n], j))
    return out


def first_cross(LB, p0, sgn, lvl):
    """first LTF index >= p0 whose high > lvl (sgn -1) / low < lvl (sgn +1)."""
    arr = LB["h"] if sgn < 0 else LB["l"]
    step = 512
    while p0 < len(arr):
        seg = arr[p0:p0 + step]
        hit = np.flatnonzero(seg > lvl) if sgn < 0 else np.flatnonzero(seg < lvl)
        if len(hit):
            return p0 + int(hit[0])
        p0 += step; step *= 4
    return None


def ema(x, n):
    out = np.empty(len(x)); a = 2 / (n + 1); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


H4 = bars(240, 0.5)
H4["ema"] = ema(H4["c"], 50)


def h4_trend(ts):
    """+1 if last CLOSED H4 bar close > EMA50, -1 if below."""
    k = np.searchsorted(H4["te"], ts, side="right") - 1
    if k < 50:
        return 0
    return 1 if H4["c"][k] > H4["ema"][k] else -1


def setups(htf, ltf, filt):
    HB, LB = bars(htf, 0.5), bars(ltf)
    out = []
    for sgn, lvl, tc, j in swings(HB):
        p = first_cross(LB, int(np.searchsorted(LB["ts"], tc)), sgn, lvl)
        if p is None:
            continue
        ext = None
        for q in range(p, min(p + CONFIRM_BARS, len(LB["o"]) - 1)):
            wick = LB["h"][q] if sgn < 0 else LB["l"][q]
            ext = wick if ext is None else (max(ext, wick) if sgn < 0 else min(ext, wick))
            if (sgn < 0 and LB["h"][q] > lvl and LB["c"][q] < lvl) or (sgn > 0 and LB["l"][q] < lvl and LB["c"][q] > lvl):
                if LB["ts"][q + 1] - LB["te"][q] > MAX_GAP:
                    break
                k = int(LB["i0"][q + 1]); entry = o[k]
                stop = ext + STOP_BUF if sgn < 0 else ext - STOP_BUF
                risk = sgn * (entry - stop)
                if risk <= 0:
                    break
                ets = int(t[k])
                if filt == "h4ema" and h4_trend(ets) != sgn:
                    break
                if filt == "session" and not (7 <= (ets % 86400) // 3600 < 20):
                    break
                out.append(dict(k=k, sgn=sgn, entry=entry, risk=risk, lvl=lvl, stop=stop,
                                tend=ets + CAP_BARS * ltf * 60, sweep_ts=int(LB["ts"][p]), conf_ts=int(LB["ts"][q]),
                                swing_ts=int(HB["ts"][j]), ltf=ltf))
                break
    out.sort(key=lambda d: d["k"])
    return out


def walk(k, sgn, entry, risk, tgt_r, tend):
    """M1 from k; returns ($/oz pnl, exit index). Stop first on a shared bar; gap through stop fills at open."""
    end = min(int(np.searchsorted(t, tend)), N)
    if end <= k:
        end = k + 1
    stop, tgt = entry - sgn * risk, entry + sgn * tgt_r * risk
    lo, hi = l[k:end], h[k:end]
    hs = (lo <= stop) if sgn > 0 else (hi >= stop)
    ht = (hi >= tgt) if sgn > 0 else (lo <= tgt)
    qs = int(np.argmax(hs)) if hs.any() else BIGN
    qt = int(np.argmax(ht)) if ht.any() else BIGN
    if qs == BIGN and qt == BIGN:
        return sgn * (c[end - 1] - entry), end - 1
    if qs <= qt:
        op = o[k + qs]
        fill = op if ((sgn > 0 and op < stop) or (sgn < 0 and op > stop)) else stop
        return sgn * (fill - entry), k + qs
    return tgt_r * risk, k + qt


def trade_list(S, tgt_r):
    """one position at a time; real direction."""
    tr, busy = [], -1
    for s in S:
        if s["k"] <= busy:
            continue
        p, x = walk(s["k"], s["sgn"], s["entry"], s["risk"], tgt_r, s["tend"])
        tr.append(dict(s, pnl=p, xk=x, tgt_r=tgt_r)); busy = x
    return tr


def twin(tr, tgt_r, rng):
    d = rng.choice([-1, 1], len(tr))
    return [(int(t[x["k"]]), walk(x["k"], int(s), x["entry"], x["risk"], tgt_r, x["tend"])[0], x["risk"])
            for x, s in zip(tr, d)]


def Rv(rows, cost, lo=0, hi=9e9):
    return np.array([(p - cost) / rk for tt, p, rk in rows if lo <= tt < hi])


def stats(r):
    if len(r) == 0:
        return dict(n=0)
    eq = np.cumsum(r); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    ls = cur = 0
    for v in r:
        cur = cur + 1 if v < 0 else 0; ls = max(ls, cur)
    pos, neg = r[r > 0].sum(), -r[r < 0].sum()
    return dict(n=len(r), win=float(np.mean(r > 0)), avg=float(r.mean()), pf=float(pos / neg) if neg else float("inf"),
                dd=float(dd), streak=ls, total=float(r.sum()))


def main():
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    lines, report = [], {}
    P = lambda s="": (print(s, flush=True), lines.append(s))
    for v, (htf, ltf, filt) in VARIANTS.items():
        S = setups(htf, ltf, filt)
        cells = {}
        for tg in TARGETS:
            tr = trade_list(S, tg)
            real = [(int(t[x["k"]]), x["pnl"], x["risk"]) for x in tr]
            rng = np.random.default_rng(11)
            tws = [twin(tr, tg, rng) for _ in range(SEEDS)]
            cells[tg] = (tr, real, tws)
        tg = max(TARGETS, key=lambda g: Rv(cells[g][1], COST, *WIN["IS"]).mean())   # IS-only pick
        P(f"=== Variant {v}: H{htf // 60} -> M{ltf}{' + ' + filt if filt else ''}; setups {len(S)}; IS pick {tg:.0f}R")
        report[v] = dict(pick=tg, cells={})
        for g in TARGETS:
            tr, real, tws = cells[g]
            risks = np.array([x["risk"] for x in tr])
            P(f"  -- target {g:.0f}R{'  (judged)' if g == tg else ''}: median stop ${np.median(risks):.2f} "
              f"(p10 {np.percentile(risks, 10):.2f}, p90 {np.percentile(risks, 90):.2f})")
            for wn, (lo, hi) in [("MAIN 3y", (MAIN0, 9e9))] + list(WIN.items()) + [("ALL 2010-26", (0, 9e9))]:
                r = Rv(real, COST, lo, hi)
                if len(r) == 0:
                    continue
                s = stats(r); tw = np.mean([Rv(x, COST, lo, hi).mean() for x in tws])
                P(f"     {wn:12s} n{s['n']:5d} win {s['win']:.0%} avgR gross {Rv(real, 0, lo, hi).mean():+.3f} "
                  f"IC {Rv(real, .22, lo, hi).mean():+.3f} net {s['avg']:+.3f} stress {Rv(real, .8, lo, hi).mean():+.3f} "
                  f"| twin {tw:+.3f} | PF {s['pf']:.2f} maxDD {s['dd']:.1f}R streak {s['streak']}")
            yrs = sorted({dt.datetime.fromtimestamp(x[0], dt.timezone.utc).year for x in real})
            by = []
            for y in yrs:
                lo = dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp(); hi = dt.datetime(y + 1, 1, 1, tzinfo=dt.timezone.utc).timestamp()
                r = Rv(real, COST, lo, hi); by.append(f"{y}:{r.mean():+.2f}(n{len(r)})")
            P("     by year net: " + " ".join(by))
            # gates
            gi = {w: Rv(real, COST, *WIN[w]) for w in WIN}
            twm = {w: np.mean([Rv(x, COST, *WIN[w]).mean() for x in tws]) for w in WIN}
            ra = Rv(real, COST); ta = np.concatenate([Rv(x, COST) for x in tws])
            tst = (ra.mean() - ta.mean()) / np.sqrt(ra.var(ddof=1) / len(ra) + ta.var(ddof=1) / len(ta))
            gates = {"IS net>0": gi["IS"].mean() > 0, "OOS net>0 n>=30": gi["OOS"].mean() > 0 and len(gi["OOS"]) >= 30,
                     "IS real-twin>=.05": gi["IS"].mean() - twm["IS"] >= .05, "OOS real-twin>=.05": gi["OOS"].mean() - twm["OOS"] >= .05,
                     "HIST both >0": gi["H1 2010-16"].mean() > 0 and gi["H2 2017-23"].mean() > 0, "t>=2.8": tst >= 2.8}
            ok = all(gates.values())
            P(f"     gates: " + ", ".join(f"{k} {'Y' if g_ else 'n'}" for k, g_ in gates.items()) + f" | t {tst:+.2f}"
              + (f" -> {'PASS' if ok else 'FAIL'}" if g == tg else " (not judged)"))
            main_tr = [x for x in tr if t[x["k"]] >= MAIN0]
            mr = Rv(real, COST, MAIN0, 9e9); mz = Rv(real, 0, MAIN0, 9e9)
            report[v]["cells"][str(g)] = dict(
                verdict=("PASS" if ok else "FAIL") if g == tg else None,
                gates={k: bool(x) for k, x in gates.items()}, t=float(tst),
                main=stats(mr), main_gross=float(mz.mean()), is_=stats(gi["IS"]), oos=stats(gi["OOS"]),
                twin_is=float(twm["IS"]), twin_oos=float(twm["OOS"]), med_stop=float(np.median(risks)),
                eq=[[int(t[x["k"]]), round(float((x["pnl"] - COST) / x["risk"]), 3)] for x in main_tr],
                eq_zero=[round(float(x["pnl"] / x["risk"]), 3) for x in main_tr])
            with open(os.path.join(HERE, "results", f"trades_{v}_{g:.0f}R.csv"), "w") as f:
                f.write("entry_utc,side,level,entry,stop,risk,pnl_oz,R_net\n")
                for x in tr:
                    f.write(f"{dt.datetime.fromtimestamp(int(t[x['k']]), dt.timezone.utc):%Y-%m-%d %H:%M},"
                            f"{'long' if x['sgn'] > 0 else 'short'},{x['lvl']:.2f},{x['entry']:.2f},{x['stop']:.2f},"
                            f"{x['risk']:.2f},{x['pnl']:.2f},{(x['pnl'] - COST) / x['risk']:.3f}\n")
        # 5 sample trades from variant A's judged cell, last 3 years (seeded)
        if v == "A":
            tr = [x for x in cells[tg][0] if t[x["k"]] >= MAIN0]
            rng = np.random.default_rng(5)
            wins = [x for x in tr if x["pnl"] > 0]; loss = [x for x in tr if x["pnl"] <= 0]
            pick = [wins[i] for i in rng.choice(len(wins), 2, replace=False)]
            pick += [loss[i] for i in rng.choice(len(loss), 3, replace=False)]
            samp = []
            for x in pick:
                a = int(np.searchsorted(t, x["sweep_ts"] - 36 * 300)); b = min(int(x["xk"]) + 1, N)
                b = max(b, int(np.searchsorted(t, int(t[x["k"]]) + 24 * 300)))
                B5 = {kk: [] for kk in "tohlc"}
                key = t[a:b] // 300
                st = np.flatnonzero(np.diff(key, prepend=key[0] - 1)) + a; en = np.r_[st[1:], b]
                for s0, e0 in zip(st, en):
                    B5["t"].append(int(t[s0] // 300 * 300)); B5["o"].append(float(o[s0])); B5["h"].append(float(h[s0:e0].max()))
                    B5["l"].append(float(l[s0:e0].min())); B5["c"].append(float(c[e0 - 1]))
                samp.append(dict(bars=B5, side="long" if x["sgn"] > 0 else "short", lvl=float(x["lvl"]), entry=float(x["entry"]),
                                 stop=float(x["stop"]), target=float(x["entry"] + x["sgn"] * tg * x["risk"]),
                                 entry_ts=int(t[x["k"]]), exit_ts=int(t[x["xk"]]), sweep_ts=x["sweep_ts"], conf_ts=x["conf_ts"],
                                 swing_ts=x["swing_ts"], R=round(float((x["pnl"] - COST) / x["risk"]), 2)))
            report["samples"] = samp
    with open(os.path.join(HERE, "results", "summary.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(HERE, "results", "report_data.json"), "w") as f:
        json.dump(report, f)


if __name__ == "__main__":
    main()
