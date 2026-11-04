"""Round 8: Asia sweep fade (round-4 spec: window 06-20 UTC, minstop 0.5 ATR, ladder 0.4R,
$0.30 slip) with an H4 trend filter vs without. Trend = sign(close - EMA50 of H4), using
only bars before the signal. Variants: all / with trend / against trend. Random twins
for each variant. <2025 = the period the round-4 spec was chosen on; 2025+ untouched."""
import contextlib, io, runpy, sys

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import ema, fmt, load, stats
from round5 import halves, twin

with contextlib.redirect_stdout(io.StringIO()):
    g4 = runpy.run_path("@GANN_ROOT@/research/ta_lab/round4.py", run_name="r4")
build, run4 = g4["build"], g4["run"]

for tf, bph in (("M15", 4), ("M5", 12)):
    d = load(tf)
    trend = np.sign(d["c"] - ema(d["c"], 50 * 4 * bph))
    allo = build(d, bph, win_end=20, min_stop_atr=0.5)
    variants = {
        "all": allo,
        "with H4 trend": [o for o in allo if trend[o.i - 1] == o.sgn],
        "against H4 trend": [o for o in allo if trend[o.i - 1] == -o.sgn],
    }
    print(f"== {tf}")
    for nm, oo in variants.items():
        a, b = halves(run4(d, bph, oo, 0.4, "ladder"))
        ta, tb = halves(run4(d, bph, twin(d, bph, oo, (6, 20)), 0.4, "ladder"))
        if a:
            print(f"  {nm:<17} <2025 {fmt(stats(a))}   | twin avg {stats(ta)['avg']:+.3f}R")
        print(f"  {nm:<17} 2025+ {fmt(stats(b))}   | twin avg {stats(tb)['avg']:+.3f}R")
