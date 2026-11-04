import numpy as np, sim, data, datetime as dt
d = data.load(); H1, H4, D1 = sim.Bars(d, 3600), sim.Bars(d, 14400), sim.Bars(d, 86400)
CUT = 1514764800  # 2018-01-01
def tab(tr, key, title):
    g = {}
    for x in tr: g.setdefault(key(x), []).append(x)
    print(f"-- {title}:   key | 2010-17 n netR avg | 2018-26 n netR avg")
    for k in sorted(g, key=str):
        a = [x["r"] for x in g[k] if x["t"] < CUT]; b = [x["r"] for x in g[k] if x["t"] >= CUT]
        f = lambda r: f"{len(r):4d} {sum(r):+6.1f} {np.mean(r) if r else 0:+.3f}"
        print(f"   {str(k):10s} | {f(a)} | {f(b)}")
fam = lambda x: "gann" if x["zone"][0] in "RS" and x["zone"][1:].isdigit() and int(x["zone"][1:]) >= 45 else ("fib" if x["zone"].startswith("fib") else "pivot")
sess = lambda x: (lambda h: "asia" if h < 7 else ("london" if h < 13 else ("ny" if h < 20 else "late")))(dt.datetime.fromtimestamp(sim.broker_to_utc(x["t"]), dt.timezone.utc).hour)
for lab, argv in [("GROSS spread 0", ["--spread", "0"]), ("NET spread 0.35", [])]:
    tr = sim.run(sim.args(argv), d, H1, H4, D1)
    print("=====", lab)
    tab(tr, fam, "level family"); tab(tr, lambda x: x["pol"], "polarity flipped"); tab(tr, sess, "session (UTC)")
    tab(tr, lambda x: x["dir"], "direction"); tab(tr, lambda x: x["partial"], "partial hit")
