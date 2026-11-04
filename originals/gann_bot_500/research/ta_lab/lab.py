"""TA lab: one data loader, one trade simulator, shared by every method test.

Prices: XAUUSD from the broker demo feed terminal, saved as numpy arrays with
time shifted by -3h. The broker runs UTC+3 in EU summer time and UTC+2 in
winter, so winter bars get +1h back here. Spread: per-bar `spread` (points,
0.01 $), floored at 0.20 $.

Every trade is measured in R (its own initial risk) so a $5 stop in 2025 at
3,300 and in 2026 at 4,200 are comparable. Intrabar order is pessimistic:
within one bar the stop is checked before any favourable move.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np

DATA = "@GANN_ROOT@/research/ta_lab/data"


def _last_sunday(y: int, m: int) -> int:
    import calendar
    d = max(w[6] for w in calendar.monthcalendar(y, m))
    return int(datetime(y, m, d, 1, tzinfo=timezone.utc).timestamp())


def load(tf: str = "M5", sym: str = "XAU", min_spread: float = 0.20, point: float = 0.01) -> dict:
    r = np.load(f"{DATA}/{sym}_{tf}.npy")
    t = r["time"].astype(np.int64).copy()
    years = {datetime.fromtimestamp(int(x), timezone.utc).year for x in (t[0], t[-1])}
    years = range(min(years) - 1, max(years) + 1)
    summer = [(_last_sunday(y, 3), _last_sunday(y, 10)) for y in years]
    in_summer = np.zeros(len(t), bool)
    for a, b in summer:
        in_summer |= (t >= a) & (t < b)
    t[~in_summer] += 3600
    spread = np.maximum(r["spread"].astype(float) * point, min_spread)
    return dict(t=t, o=r["open"].astype(float), h=r["high"].astype(float),
                l=r["low"].astype(float), c=r["close"].astype(float), spread=spread)


def atr(d: dict, n: int = 14) -> np.ndarray:
    h, l, c = d["h"], d["l"], d["c"]
    pc = np.concatenate([[c[0]], c[:-1]])
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    out = np.empty_like(tr)
    out[0] = tr[0]
    a = 1.0 / n
    for i in range(1, len(tr)):
        out[i] = out[i - 1] + a * (tr[i] - out[i - 1])
    return out


def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.empty_like(x)
    out[0] = x[0]
    a = 2.0 / (n + 1)
    for i in range(1, len(x)):
        out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


@dataclass
class Order:
    i: int            # bar index when the order is created (decision made on bar i-1 close)
    sgn: int          # +1 buy, -1 sell
    entry: float      # limit price, or None-like NaN for market at open of bar i
    stop: float
    ttl: int          # bars the limit may wait
    tag: str = ""


def simulate(d: dict, orders: list[Order], *, exit_mode: str = "ladder", step_r: float = 0.6,
             tp_r: float = 2.0, max_hold: int = 288, one_at_a_time: bool = True) -> list[dict]:
    """Fill each order on the M-bar path, then exit by:
       ladder: lock ladder in R units - at +k*step_r*R the stop moves to +k*step_r*R
       tp:     fixed take-profit at tp_r R, stop moved to breakeven at +1R
       hold:   close after max_hold bars (also the cap for the other modes)
    Returns one dict per filled trade with r (result in R)."""
    o, h, l, sp, t = d["o"], d["h"], d["l"], d["spread"], d["t"]
    n = len(o)
    trades, busy_until = [], -1
    for od in sorted(orders, key=lambda x: x.i):
        if od.i >= n or (one_at_a_time and od.i <= busy_until):
            continue
        sgn = od.sgn
        # fill
        if np.isnan(od.entry):
            k, px = od.i, o[od.i] + (sp[od.i] if sgn == 1 else 0.0)
        else:
            px, k = od.entry, None
            for j in range(od.i, min(od.i + od.ttl, n)):
                if (sgn == 1 and l[j] + sp[j] <= px) or (sgn == -1 and h[j] >= px):
                    k = j
                    break
            if k is None:
                continue
        risk = sgn * (px - od.stop)
        if risk <= 0.05:
            continue
        lock, best, res, end = od.stop, px, None, min(k + max_hold, n)
        limit_fill = not np.isnan(od.entry)
        for j in range(k, end):
            adverse = l[j] if sgn == 1 else h[j] + sp[j]
            fav = h[j] if sgn == 1 else l[j] + sp[j]
            if sgn * (adverse - lock) <= 0:
                res, jx = sgn * (lock - px), j
                break
            if limit_fill and j == k:
                continue      # the fill bar's favourable extreme came before the fill
            best = max(best, fav) if sgn == 1 else min(best, fav)
            gain_r = sgn * (best - px) / risk
            if exit_mode == "tp":
                if gain_r >= tp_r:
                    res, jx = tp_r * risk, j
                    break
                if gain_r >= 1.0 and sgn * (px - lock) > 0:
                    lock = px
            elif exit_mode == "ladder":
                rung = int(gain_r / step_r + 1e-9)
                if rung >= 1:
                    new = px + sgn * rung * step_r * risk
                    if sgn * (new - lock) > 0:
                        lock = new
        if res is None:
            jx = end - 1
            res = sgn * ((o[jx] if sgn == 1 else o[jx] + sp[jx]) - px)
        trades.append(dict(t=int(t[k]), sgn=sgn, entry=px, risk=risk, r=res / risk, tag=od.tag,
                           bars=jx - k))
        busy_until = jx
    return trades


def stats(trades: list[dict]) -> dict:
    r = np.array([x["r"] for x in trades], float)
    if len(r) == 0:
        return dict(n=0, net=0.0, pf=0.0, win=0.0, dd=0.0, avg=0.0)
    gp, gl = r[r > 0].sum(), -r[r < 0].sum()
    eq = np.cumsum(r)
    dd = float(np.max(np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq))
    return dict(n=len(r), net=float(r.sum()), pf=float(gp / gl) if gl else 99.0,
                win=float((r > 0).mean()), dd=dd, avg=float(r.mean()))


def fmt(s: dict) -> str:
    return (f"n {s['n']:4d}  net {s['net']:+7.1f}R  avg {s['avg']:+.3f}R  PF {s['pf']:4.2f}  "
            f"win {s['win']:.0%}  maxDD {s['dd']:5.1f}R")


def split(trades: list[dict], cut_t: int) -> tuple[list, list]:
    return [x for x in trades if x["t"] < cut_t], [x for x in trades if x["t"] >= cut_t]


def day_index(t: np.ndarray) -> np.ndarray:
    return (t // 86400).astype(np.int64)
