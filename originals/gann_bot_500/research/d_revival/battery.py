import sys, numpy as np, sim, data
d = data.load(); H1, H4, D1 = sim.Bars(d, 3600), sim.Bars(d, 14400), sim.Bars(d, 86400)
def go(label, argv, seed=7):
    tr = sim.run(sim.args(argv), d, H1, H4, D1, seed=seed)
    old = [x for x in tr if x["t"] < 1577836800]; new = [x for x in tr if x["t"] >= 1577836800]
    o = sim.summary(tr, label)
    r = lambda s: (f"{sum(x['r'] for x in s):+6.1f}R/{len(s)}")
    print(f"{'':34s}   2010-19 {r(old)}   2020-26 {r(new)}")
    return tr
runs = [l.split("|") for l in sys.argv[1:]]
for lab, a in runs:
    go(lab, a.split())
