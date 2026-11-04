"""Round 5: New York session fade of a London-range sweep.
London range = 06:00-12:00 UTC; during NY (13:30-18:00 UTC) an M-bar that wicks past the
London high/low and closes back inside -> fade at the next open. Same costs and rules as
round 4 ($0.30 slip, min stop, 1 per day, lock ladder). Settings chosen before 2025,
2025+ reported untouched, against a random twin (same day, same window, same stop size)."""
import itertools, sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import Order, atr, fmt, load, simulate, stats

SLIP, NAN = 0.30, float("nan")
CUT = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())


def sweep_orders(d, bph, rng_h=(6, 12), win_h=(13.5, 18), *, min_stop_atr=0.5, buf=0.3):
    t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
    n = len(t)
    A = atr(d, 14) * np.sqrt(bph)
    hour = (t % 86400) / 3600.0
    day = t // 86400
    out = []
    for s in np.flatnonzero(np.diff(day, prepend=day[0] - 1)):
        idx = np.arange(s, min(s + 24 * bph, n))
        rg = idx[(hour[idx] >= rng_h[0]) & (hour[idx] < rng_h[1])]
        win = idx[(hour[idx] >= win_h[0]) & (hour[idx] < win_h[1])]
        if len(rg) < 0.5 * (rng_h[1] - rng_h[0]) * bph or not len(win):
            continue
        rh, rl = h[rg].max(), l[rg].min()
        for i in win:
            if i + 1 >= n:
                break
            hit = None
            if h[i] > rh and c[i] < rh:
                hit = (-1, h[i])
            elif l[i] < rl and c[i] > rl:
                hit = (1, l[i])
            if hit:
                sgn, wick = hit
                entry = o[i + 1]
                stop = wick - sgn * buf
                if sgn * (entry - stop) < min_stop_atr * A[i]:
                    stop = entry - sgn * min_stop_atr * A[i]
                out.append(Order(i + 1, sgn, NAN, stop, 1, "ny_sweep"))
                break
    return out


def twin(d, bph, orders, win_h, seed=11):
    rng = np.random.default_rng(seed)
    t, o = d["t"], d["o"]
    A = atr(d, 14) * np.sqrt(bph)
    out = []
    for od in orders:
        d0 = (t[od.i] // 86400) * 86400
        cand = np.flatnonzero((t >= d0 + win_h[0] * 3600) & (t < d0 + win_h[1] * 3600))
        if not len(cand):
            continue
        i = int(rng.choice(cand))
        sgn = int(rng.choice([-1, 1]))
        dist = abs(o[od.i] - od.stop) / A[od.i - 1] * A[i - 1]
        out.append(Order(i, sgn, NAN, o[i] - sgn * dist, 1, "twin"))
    return out


def run(d, bph, orders, step_r):
    tr = simulate(d, orders, exit_mode="ladder", step_r=step_r, max_hold=24 * bph)
    for x in tr:
        x["r"] -= SLIP / x["risk"]
    return tr


def halves(tr):
    return [x for x in tr if x["t"] < CUT], [x for x in tr if x["t"] >= CUT]


if __name__ == "__main__":
    m15 = load("M15")
    res = []
    for win_end, msa, step in itertools.product((16, 18, 20), (0.3, 0.5, 0.8), (0.4, 0.6, 1.0)):
        oo = sweep_orders(m15, 4, win_h=(13.5, win_end), min_stop_atr=msa)
        a, b = halves(run(m15, 4, oo, step))
        res.append(((win_end, msa, step), stats(a), stats(b)))
    res.sort(key=lambda x: -x[1]["net"] / (x[1]["dd"] + 5))
    print("top 5 by TRAIN (<2025), TEST (2025+) untouched:")
    for cfg, a, b in res[:5]:
        print(f"  NY 13:30-{cfg[0]} minstop {cfg[1]}ATR ladder {cfg[2]}R\n     TRAIN {fmt(a)}\n     TEST  {fmt(b)}")
    (we, msa, step), _, _ = res[0]
    print(f"\nchosen NY 13:30-{we}, minstop {msa}, ladder {step}R")
    for tf, bph in (("M15", 4), ("M5", 12)):
        d = load(tf)
        oo = sweep_orders(d, bph, win_h=(13.5, we), min_stop_atr=msa)
        tw = twin(d, bph, oo, (13.5, we))
        for nm, x in (("NY sweep fade", oo), ("random twin", tw)):
            a, b = halves(run(d, bph, x, step))
            print(f"  {tf} {nm:<14} <2025 {fmt(stats(a))}\n  {'':<18} 2025+ {fmt(stats(b))}")
