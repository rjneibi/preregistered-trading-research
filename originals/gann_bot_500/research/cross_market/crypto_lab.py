"""CR-1: crypto (BTCUSDT, ETHUSDT daily, Binance public data, UTC days 2017-08..2026-10).  (pre-declared)

Two cost worlds:
  CFD  : 0.10% round trip + financing 15%/yr on longs per night (typical retail crypto-CFD swap)
  SPOT : 0.10% round trip, no financing (exchange spot)
Halves: 2017-08..2021-12 | 2022-01..2026-10.  Discovery BTC, confirmation ETH.

A  TREND (long or flat, decided at the daily close, traded next open):
   A1 close > SMA(N), N = 20, 50, 100, 200           A2 30-day return > 0 (time-series momentum)
   A3 20-day breakout, exit 10-day low (Donchian)
   PASS = Sharpe AND MAR (CAGR/maxDD) above buy-and-hold in BOTH halves, on BTC AND ETH, under CFD costs.
B  SWING rules from the index study (swing_lab MR1..MR5, TR1..TR4), long only:
   PASS = PF >= 1.15 both halves, n >= 30 per half, random-twin p < 0.005, ETH PF > 1.
C  WEEKDAY: mean daily return by weekday, both halves (weekend effect).  Report only.
"""
import numpy as np
import pandas as pd

import swing_lab as S
import xm_lab as X

RT = 0.001
HALVES = (("2017-08-01", "2022-01-01"), ("2022-01-01", "2027-01-01"))


def closes(sym):
    d, _ = X.load(sym, "1d")
    return d


def stats(r):
    eq = (1 + r).cumprod()
    yrs = len(r) / 365
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else 0
    return cagr, dd, sh, cagr / -dd if dd < 0 else np.inf


def strat_returns(d, pos, fin):
    """pos: 0/1 decided at close t, held from open t+1 to open t+2 (open-to-open returns)."""
    o = d["o"]
    r_oo = o.shift(-1) / o - 1                      # return from open t to open t+1, earned by pos[t-1]
    p = pos.shift(1).fillna(0)
    trade = p.diff().abs().fillna(p.abs())
    return (p * r_oo - trade * RT / 2 - p * fin / 365).dropna()


def trend_block():
    print("A TREND (long/flat) vs buy-and-hold - Sharpe / MAR / CAGR / maxDD per half, CFD costs [spot Sharpe]")
    res = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        d = closes(sym)
        c = d["c"]
        rules = {f"A1 SMA{n}": (c > c.rolling(n).mean()).astype(float) for n in (20, 50, 100, 200)}
        rules["A2 TSMOM30"] = (c / c.shift(30) > 1).astype(float)
        hi20, lo10 = d["h"].rolling(20).max().shift(1), d["l"].rolling(10).min().shift(1)
        st, pos = 0.0, []
        for x, h_, l_ in zip(c, hi20, lo10):
            st = 1.0 if (st == 0 and x > h_) else (0.0 if (st == 1 and x < l_) else st)
            pos.append(st)
        rules["A3 Donchian20/10"] = pd.Series(pos, index=c.index)
        rules["buy&hold"] = pd.Series(1.0, index=c.index)
        for name, p in rules.items():
            row = []
            for fin_lab, fin in (("cfd", 0.15), ("spot", 0.0)):
                r = strat_returns(d, p, fin)
                for k, (a, b) in enumerate(HALVES):
                    m = (r.index >= a) & (r.index < b)
                    res[(sym, name, fin_lab, k)] = stats(r[m])
            cells = []
            for k in range(2):
                cg, dd, sh, mar = res[(sym, name, "cfd", k)]
                cells.append(f"Sh {sh:4.2f} MAR {mar:5.2f} CAGR {cg*100:+6.1f}% DD {dd*100:6.1f}% [spot Sh {res[(sym, name, 'spot', k)][2]:4.2f}]")
            print(f"  {sym[:3]} {name:17s} " + "  |  ".join(cells))
    print("  verdicts (beat buy&hold on Sharpe AND MAR, both halves, BTC and ETH, CFD costs):")
    for name in [k[1] for k in res if k[0] == "BTCUSDT" and k[2] == "cfd" and k[3] == 0 and k[1] != "buy&hold"]:
        ok = all(res[(s, name, "cfd", k)][2] > res[(s, "buy&hold", "cfd", k)][2] and
                 res[(s, name, "cfd", k)][3] > res[(s, "buy&hold", "cfd", k)][3]
                 for s in ("BTCUSDT", "ETHUSDT") for k in range(2))
        print(f"    {name:17s} {'PASS' if ok else 'fail'}")


def swing_block():
    print("\nB SWING rules from the index study, long only, CFD costs (financing 15%/yr)")
    data = {}
    for s in ("BTCUSDT", "ETHUSDT"):
        d, _ = S.prep(s)
        data[s] = (d, RT * d["c"].median())       # spread as price units at the median level
    for nm in S.RULES:
        if nm == "MR6":
            continue
        d, sp = data["BTCUSDT"]
        side, sig, ex = S.rule(nm, d)
        tr = S.run(d, sp, side, sig, ex, fin_l=0.15)
        if len(tr) < 20:
            print(f"  {nm} n={len(tr)} too few"); continue
        r = np.array([x for _, x, _ in tr])
        t = np.array([x[0] for x in tr])
        a, b = r[t < pd.Timestamp("2022-01-01")], r[t >= pd.Timestamp("2022-01-01")]
        p = S.twin_p(d, sp, side, tr)
        de, spe = data["ETHUSDT"]
        s2, g2, e2 = S.rule(nm, de)
        re_ = np.array([x for _, x, _ in S.run(de, spe, s2, g2, e2, fin_l=0.15)])
        ok = len(a) >= 30 and len(b) >= 30 and X.pf(a) >= 1.15 and X.pf(b) >= 1.15 and p < 0.005 and X.pf(re_) > 1
        print(f"  {nm} BTC n={len(r):4d} win {np.mean(r > 0):.0%} avg {r.mean()*100:+.2f}% PF {X.pf(a):.2f}/{X.pf(b):.2f} "
              f"twin p={p:.3f} | ETH PF {X.pf(re_):.2f} n{len(re_)}  {'PASS' if ok else 'fail'}")


def weekday_block():
    print("\nC WEEKDAY mean daily return % (close-to-close, UTC days)  Mon..Sun")
    for sym in ("BTCUSDT", "ETHUSDT"):
        c = closes(sym)["c"]
        r = c.pct_change().dropna()
        for k, (a, b) in enumerate(HALVES):
            m = r[(r.index >= a) & (r.index < b)]
            g = m.groupby(m.index.dayofweek).mean() * 100
            print(f"  {sym[:3]} half{k + 1}: " + " ".join(f"{v:+.2f}" for v in g.values))


if __name__ == "__main__":
    trend_block()
    swing_block()
    weekday_block()
