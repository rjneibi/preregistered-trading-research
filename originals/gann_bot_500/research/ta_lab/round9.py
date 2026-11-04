"""Round 9: the Asia sweep fade on silver (XAGUSD), round-4 spec unchanged (window 06-20,
minstop 0.5 ATR, ladder 0.4R). Costs scaled to silver's price (gold $0.30 slip / $0.20
spread floor at ~4,200 -> silver $0.005 / $0.003 at ~60). Data: M15 from 2024-01 (so
"<2025" is 2024 only), M5 from 2025-11. Random twin as always."""
import contextlib, io, runpy, sys

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import fmt, load, simulate, stats
from round5 import halves, twin

with contextlib.redirect_stdout(io.StringIO()):
    g4 = runpy.run_path("@GANN_ROOT@/research/ta_lab/round4.py", run_name="r4")
build = g4["build"]
SLIP = 0.005


def run(d, bph, orders):
    tr = simulate(d, orders, exit_mode="ladder", step_r=0.4, max_hold=24 * bph)
    for x in tr:
        x["r"] -= SLIP / x["risk"]
    return tr


for tf, bph in (("M15", 4), ("M5", 12)):
    d = load(tf, sym="XAG", min_spread=0.003, point=0.001)
    oo = build(d, bph, win_end=20, min_stop_atr=0.5, buf=0.005)   # stop buffer scaled to silver
    a, b = halves(run(d, bph, oo))
    ta, tb = halves(run(d, bph, twin(d, bph, oo, (6, 20))))
    if a:
        print(f"{tf} silver sweep fade 2024  {fmt(stats(a))} | twin avg {stats(ta)['avg']:+.3f}R")
    print(f"{tf} silver sweep fade 2025+ {fmt(stats(b))} | twin avg {stats(tb)['avg']:+.3f}R")
