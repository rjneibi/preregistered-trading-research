"""VS-1: make the dip bot volatility- and fear-aware?  (pre-declared, written before any result)

Trades: the live bot's rules (swing_lab MR1 rsi2 + MR2 ibs, next-open execution) on US500, US30 (2013+)
and USTEC (2023+); daily mark-to-market portfolio, 1/3 equity notional per position (= the bot), total
open notional capped at 150%, financing 5%/yr on longs, spread 1.5x median.

Fear measures, known at the signal close:
  F1 realised vol: 20-day stdev of the index's daily returns, ranked in its trailing 252 days
  F2 VIX term structure: VIXY / VIXM (short- vs mid-term VIX futures), ranked in trailing 252 days
     (high = short-term fear above longer-term fear = panic)
  F3 VIX spike: VIXY / SMA20(VIXY)

Sizing schemes (multiplier on the 1/3 notional):
  S0 fixed 1.0                                    (the bot today)
  S1 vol-target: median(vol20, 252d) / vol20, clipped 0.33..2
  S2 fear boost (F2): 1.5 top tercile, 1.0 middle, 0.5 bottom
  S3 fear filter (F2): skip bottom tercile
  S4 fear boost (F1)      S5 fear boost (F3)
PASS  = Sharpe AND MAR (CAGR / maxDD) above S0 in BOTH halves (2013-2019, 2020-2026).
Per-trade check: mean net return by fear tercile; a fear effect counts only if top > bottom in both
halves on >= 4 of 5 markets (US500, US30, USTEC, IWM, EWA).
"""
import numpy as np
import pandas as pd

import swing_lab as S
import xm_lab as X

MKTS = ["US500", "US30", "USTEC"]
BASE, CAP, FIN = 1 / 3, 1.5, 0.05 / 365


def series(sym):
    d, _ = X.load(sym, "D1")
    s = d["c"].copy()
    s.index = s.index.normalize()
    return s[~s.index.duplicated()]


VIXY, VIXM = series("VIXY"), series("VIXM")
F2RAW = (VIXY / VIXM).dropna()
F2 = F2RAW.rolling(252).rank(pct=True)
F3 = (VIXY / VIXY.rolling(20).mean())
F3R = F3.rolling(252).rank(pct=True)


def trades_with_paths(sym, rule):
    d, sp = S.prep(sym)
    side, sig, ex = S.rule(rule, d)
    tr = S.run(d, sp, side, sig, ex)
    o, c, idx = d["o"].values, d["c"].values, d.index
    r = pd.Series(c).pct_change()
    vol20 = r.rolling(20).std()
    f1 = vol20.rolling(252).rank(pct=True)
    vt = (vol20.rolling(252).median() / vol20).clip(0.33, 2.0)
    out = []
    for t_sig, net, hold in tr:
        i = idx.get_loc(t_sig)
        j = i + hold
        days = list(idx[i + 1:j + 2])
        path = [o[i + 1]] + list(c[i + 1:j + 1]) + [o[j + 1]]
        daily = [path[k] / path[k - 1] - 1 for k in range(1, len(path))]
        daily[0] -= sp / o[i + 1]
        for k in range(1, len(days)):
            daily[k] -= (days[k] - days[k - 1]).days * FIN
        dn = t_sig.normalize()
        g = lambda s: float(s.asof(dn)) if len(s.dropna()) and dn >= s.dropna().index[0] else np.nan
        out.append(dict(sym=sym, rule=rule, t=dn, net=net, days=days, daily=daily,
                        f1=float(f1.iloc[i]), vt=float(vt.iloc[i]) if not np.isnan(vt.iloc[i]) else 1.0,
                        f2=g(F2), f3=g(F3R)))
    return out


def mult(scheme, t):
    if scheme == "S0":
        return 1.0
    if scheme == "S1":
        return t["vt"]
    key = {"S2": "f2", "S3": "f2", "S4": "f1", "S5": "f3"}[scheme]
    f = t[key]
    if np.isnan(f):
        return 1.0
    if scheme == "S3":
        return 0.0 if f < 1 / 3 else 1.0
    return 1.5 if f > 2 / 3 else (0.5 if f < 1 / 3 else 1.0)


def portfolio(trades, scheme, start="2013-01-01"):
    trades = sorted([t for t in trades if t["t"] >= pd.Timestamp(start)], key=lambda t: t["days"][0])
    cal = pd.DatetimeIndex(sorted({d for t in trades for d in t["days"]}))
    ret = pd.Series(0.0, index=cal)
    expo = pd.Series(0.0, index=cal)
    open_until = []                                     # (last day, weight)
    for t in trades:
        w = BASE * mult(scheme, t)
        if w <= 0:
            continue
        d0 = t["days"][0]
        live = sum(wt for end, wt in open_until if end >= d0)
        if live + w > CAP + 1e-9:
            continue
        open_until.append((t["days"][-1], w))
        for d, x in zip(t["days"], t["daily"]):
            ret[d] += w * x
            expo[d] += w
    return ret, expo


def metrics(r, e):
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    # Sharpe on calendar business days (flat days count as zero)
    full = r.reindex(pd.bdate_range(r.index[0], r.index[-1]), fill_value=0.0)
    sh = full.mean() / full.std() * np.sqrt(252)
    return cagr, dd, sh, cagr / -dd if dd < 0 else np.inf, e.reindex(full.index, fill_value=0).mean()


if __name__ == "__main__":
    T = [t for m in MKTS for rl in ("MR1", "MR2") for t in trades_with_paths(m, rl)]
    counts = ", ".join(f"{m} {sum(t['sym'] == m for t in T)}" for m in MKTS)
    print(f"trades: {len(T)}  ({counts})")
    print("\nPORTFOLIO (US500+US30+USTEC, rsi2+ibs)          2013-2019                         |  2020-2026")
    base = {}
    for sc in ("S0", "S1", "S2", "S3", "S4", "S5"):
        r, e = portfolio(T, sc)
        row, ok = [], True
        for lab, a, b in (("h1", "2013-01-01", "2020-01-01"), ("h2", "2020-01-01", "2027-01-01")):
            m = (r.index >= a) & (r.index < b)
            cg, dd, sh, mar, ex = metrics(r[m], e[m])
            row.append(f"CAGR {cg*100:+5.1f}% DD {dd*100:6.1f}% Sh {sh:4.2f} MAR {mar:4.2f} expo {ex:4.0%}")
            if sc == "S0":
                base[lab] = (sh, mar)
            else:
                ok &= sh > base[lab][0] and mar > base[lab][1]
        print(f"  {sc}  " + "  |  ".join(row) + ("" if sc == "S0" else f"   {'PASS' if ok else 'fail'}"))

    print("\nPER-TRADE: mean net % by fear tercile (low / mid / high), halves split at 2020")
    ext = T + [t for m in ("IWM", "EWA") for rl in ("MR1", "MR2") for t in trades_with_paths(m, rl)]
    for f in ("f1", "f2", "f3"):
        wins = 0
        for m in MKTS + ["IWM", "EWA"]:
            cells, good = [], True
            for a, b in (("2011-01-01", "2020-01-01"), ("2020-01-01", "2027-01-01")):
                x = [(t[f], t["net"]) for t in ext if t["sym"] == m and a <= str(t["t"].date()) < b and not np.isnan(t[f])]
                if len(x) < 15:
                    cells.append("   (few)          "); continue
                fv, nv = np.array(x).T
                lo, mi, hi = (nv[fv < 1/3].mean(), nv[(fv >= 1/3) & (fv <= 2/3)].mean(), nv[fv > 2/3].mean())
                cells.append(f"{lo*100:+.2f}/{mi*100:+.2f}/{hi*100:+.2f} n{len(x)}")
                good &= hi > lo
            wins += good
            print(f"  {f} {m:5s} " + "  |  ".join(cells))
        print(f"  {f}: high-fear beats low-fear in both halves on {wins}/5 markets -> {'EFFECT' if wins >= 4 else 'no effect'}")
