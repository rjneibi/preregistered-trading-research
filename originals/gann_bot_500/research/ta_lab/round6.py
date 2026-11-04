"""Round 6: previous-day high/low sweep fade.
Levels = previous UTC day's high and low. In the trading window an M-bar wicks past one
and closes back inside -> fade at the next open; 1 per day. Same costs/rules as round 5;
settings chosen before 2025, 2025+ untouched, against a random twin."""
import itertools, sys

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import Order, atr, fmt, load, stats
from round5 import NAN, halves, run, twin


def pdh_orders(d, bph, win_h=(6, 20), *, min_stop_atr=0.5, buf=0.3):
    t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
    n = len(t)
    A = atr(d, 14) * np.sqrt(bph)
    hour = (t % 86400) / 3600.0
    day = t // 86400
    starts = np.flatnonzero(np.diff(day, prepend=day[0] - 1))
    out = []
    for a, s in zip(starts[:-1], starts[1:]):
        if day[s] - day[a] != 1:
            continue                                  # skip Monday after the weekend gap
        ph, pl = h[a:s].max(), l[a:s].min()
        idx = np.arange(s, min(s + 24 * bph, n))
        for i in idx[(hour[idx] >= win_h[0]) & (hour[idx] < win_h[1])]:
            if i + 1 >= n:
                break
            hit = None
            if h[i] > ph and c[i] < ph:
                hit = (-1, h[i])
            elif l[i] < pl and c[i] > pl:
                hit = (1, l[i])
            if hit:
                sgn, wick = hit
                entry = o[i + 1]
                stop = wick - sgn * buf
                if sgn * (entry - stop) < min_stop_atr * A[i]:
                    stop = entry - sgn * min_stop_atr * A[i]
                out.append(Order(i + 1, sgn, NAN, stop, 1, "pdh"))
                break
    return out


if __name__ == "__main__":
    m15 = load("M15")
    res = []
    for win, msa, step in itertools.product(((0, 24), (6, 20), (6, 12)), (0.3, 0.5, 0.8), (0.4, 0.6, 1.0)):
        a, b = halves(run(m15, 4, pdh_orders(m15, 4, win, min_stop_atr=msa), step))
        res.append(((win, msa, step), stats(a), stats(b)))
    res.sort(key=lambda x: -x[1]["net"] / (x[1]["dd"] + 5))
    print("top 5 by TRAIN (<2025), TEST (2025+) untouched:")
    for cfg, a, b in res[:5]:
        print(f"  window {cfg[0]} minstop {cfg[1]}ATR ladder {cfg[2]}R\n     TRAIN {fmt(a)}\n     TEST  {fmt(b)}")
    (win, msa, step), _, _ = res[0]
    print(f"\nchosen window {win}, minstop {msa}, ladder {step}R")
    for tf, bph in (("M15", 4), ("M5", 12)):
        d = load(tf)
        oo = pdh_orders(d, bph, win, min_stop_atr=msa)
        for nm, x in (("prev-day sweep", oo), ("random twin", twin(d, bph, oo, win))):
            a, b = halves(run(d, bph, x, step))
            print(f"  {tf} {nm:<15} <2025 {fmt(stats(a))}\n  {'':<19} 2025+ {fmt(stats(b))}")
