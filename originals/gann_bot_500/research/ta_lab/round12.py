"""Round 12: the round-4 Asia sweep fade had a look-ahead leak. build() took the 96 bars
(M15) after each day start; a UTC gold day has only ~92, so the "Asia range" also held
the NEXT day's 00:00-01:00 bars. Here the range uses the same UTC day only (as the live
bot must). Same spec: 06-20, 1/day, stop wick+0.3 min 0.5 ATR, ladder 0.4R, $0.30 slip,
pessimistic intrabar, vs 20 random twins."""
import contextlib, io, runpy, sys

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import Order, atr, fmt, load, stats
from round5 import halves, twin

with contextlib.redirect_stdout(io.StringIO()):
    g4 = runpy.run_path("@GANN_ROOT@/research/ta_lab/round4.py", run_name="r4")
build_old, run = g4["build"], g4["run"]
NAN = float("nan")


def build_fixed(d, bph, win_end=20, min_stop_atr=0.5, buf=0.3):
    t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
    n = len(t)
    A = atr(d, 14) * np.sqrt(bph)
    hour = (t % 86400) / 3600.0
    day = t // 86400
    starts = np.flatnonzero(np.diff(day, prepend=day[0] - 1))
    ends = np.append(starts[1:], n)
    out = []
    for s, e in zip(starts, ends):                      # bars of this UTC day only
        idx = np.arange(s, e)
        asia = idx[hour[idx] < 6]
        rest = idx[(hour[idx] >= 6) & (hour[idx] < win_end)]
        if len(asia) < 2.5 * bph or not len(rest):
            continue
        ah, al = h[asia].max(), l[asia].min()
        for i in rest:
            if i + 1 >= n:
                break
            hit = None
            for sgn, ext, swept in ((-1, ah, h[i] > ah), (1, al, l[i] < al)):
                if swept and (c[i] < ah if sgn == -1 else c[i] > al):
                    hit = sgn
                    break
            if hit is None:
                continue
            sgn, entry = hit, o[i + 1]
            wick = h[i] if sgn == -1 else l[i]
            stop = wick - sgn * buf
            if sgn * (entry - stop) < min_stop_atr * A[i]:
                stop = entry - sgn * min_stop_atr * A[i]
            out.append(Order(i + 1, sgn, NAN, stop, 1, "sweep"))
            break
    return out


for tf, bph in (("M15", 4), ("M5", 12)):
    d = load(tf)
    for name, oo in (("OLD (leak)", build_old(d, bph, win_end=20, min_stop_atr=0.5)),
                     ("FIXED     ", build_fixed(d, bph))):
        a, b = halves(run(d, bph, oo, 0.4, "ladder"))
        tw = [halves(run(d, bph, twin(d, bph, oo, (6, 20), seed=s), 0.4, "ladder")) for s in range(20)]
        ta = np.array([stats(x[0])["avg"] for x in tw if x[0]])
        tb = np.array([stats(x[1])["avg"] for x in tw if x[1]])
        if a:
            sa = stats(a)
            print(f"{tf} {name} <2025  {fmt(sa)} | twins avg {ta.mean():+.3f}R, beats {np.mean(sa['avg'] > ta):.0%}")
        sb = stats(b)
        print(f"{tf} {name} 2025+  {fmt(sb)} | twins avg {tb.mean():+.3f}R, beats {np.mean(sb['avg'] > tb):.0%}")
