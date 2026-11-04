"""WHY-1: diagnose why rule-based gold strategies fail (no fixes, only measurements).
Q1 predictability: lag-1 autocorrelation and variance ratio of returns, M5..D1, per era.
Q2 levels: at the first touch of each daily level (pivots, Gann, fib) does price bounce more than
   at placebo levels (same level shifted by a random 0.3-0.7 x daily range)?
Q3 barrier test: for D trades with plain stop/target, actual win rate vs the driftless
   random-walk prediction P(target first) = stop / (stop + target).
Q4 cost share: spread as a fraction of the stop, per era.
"""
import datetime as dt

import numpy as np

import data
import sim

d = data.load()
T, O, H, L, C = d["t"], d["o"], d["h"], d["l"], d["c"]
ERAS = [(2010, 2014), (2014, 2018), (2018, 2022), (2022, 2027)]
ts = lambda y: dt.datetime(y, 1, 1, tzinfo=dt.timezone.utc).timestamp()


def q1():
    print("Q1 PREDICTABILITY - lag-1 autocorrelation of returns | variance ratio VR(4)")
    print("    (random walk: autocorr 0, VR 1.00; trending >1, mean-reverting <1)")
    for name, sec in [("M5", 300), ("M15", 900), ("H1", 3600), ("H4", 14400), ("D1", 86400)]:
        b = sim.Bars(d, sec)
        row = []
        for y0, y1 in ERAS:
            s = (b.t >= ts(y0)) & (b.t < ts(y1))
            r = np.diff(np.log(b.c[s]))
            ac = np.corrcoef(r[:-1], r[1:])[0, 1]
            r4 = np.log(b.c[s][4:]) - np.log(b.c[s][:-4])
            vr = r4.var() / (4 * r.var())
            row.append(f"{ac:+.3f} | {vr:.2f}")
        print(f"  {name:4s} " + "   ".join(f"{y0}-{y1 - 1}: {x}" for (y0, y1), x in zip(ERAS, row)))


def q2(seed=3):
    print("\nQ2 LEVELS - first touch of each daily level: does price bounce +k before breaking -k?")
    print("    k = 0.5 x ATR(H1); bounce = moves k back away before moving k through. Placebo = same")
    print("    level shifted by +-(0.3..0.7) x previous-day range.")
    rng = np.random.default_rng(seed)
    D1 = sim.Bars(d, 86400)
    H1 = sim.Bars(d, 3600)
    res = {"pivot": [], "gann": [], "fib": [], "placebo": []}
    for k in range(60, len(D1.t) - 1):
        s, e = int(D1.s[k]), int(D1.e[k])
        if e - s < 600:
            continue
        hk = int(np.searchsorted(H1.t, D1.t[k])) - 1
        atr = sim.wilder_atr(list(H1.h[hk - 42:hk + 1]), list(H1.l[hk - 42:hk + 1]), list(H1.c[hk - 42:hk + 1]))
        kd = 0.5 * atr
        op = O[s]
        piv = sim.fib_pivots(D1.h[k - 1], D1.l[k - 1], D1.c[k - 1])
        gan = sim.gann_levels(op)
        w0 = max(0, int(np.searchsorted(H1.t, D1.t[k])) - 50)
        sh, sl_ = H1.h[w0:hk].max(), H1.l[w0:hk].min()
        fib = sim.fib_retr(sh, sl_, "up" if op > (sh + sl_) / 2 else "down")
        rngd = D1.h[k - 1] - D1.l[k - 1]
        groups = {"pivot": list(piv.values()), "gann": list(gan.values()), "fib": list(fib.values())}
        groups["placebo"] = [v + rng.choice([-1, 1]) * rng.uniform(.3, .7) * rngd for g in ("pivot", "fib") for v in groups[g]]
        for g, lv in groups.items():
            for v in lv:
                if abs(v - op) < kd:            # already at the level at the open
                    continue
                side = 1 if v < op else -1      # 1: level below price (support test)
                hit = np.flatnonzero((L[s:e] <= v) if side == 1 else (H[s:e] >= v))
                if not len(hit):
                    continue
                j = s + int(hit[0])
                up, dn = v + side * kd, v - side * kd
                out = None
                for x in range(j + 1, min(e, j + 600)):
                    bounce = H[x] >= up if side == 1 else L[x] <= up
                    brk = L[x] <= dn if side == 1 else H[x] >= dn
                    if bounce and brk:
                        out = None
                        break
                    if bounce or brk:
                        out = bool(bounce)
                        break
                if out is not None:
                    res[g].append((int(T[j]), out))
    for g, v in res.items():
        a = np.array([x[1] for x in v])
        t_ = np.array([x[0] for x in v])
        eras = []
        for y0, y1 in ERAS:
            m = (t_ >= ts(y0)) & (t_ < ts(y1))
            eras.append(f"{a[m].mean():.1%}")
        print(f"  {g:8s} n={len(a):6d} bounce {a.mean():.1%}   by era " + " ".join(eras))


def q3_q4():
    print("\nQ3 BARRIERS - D (intended entry) with plain stop/target, no partial/BE/trail")
    print("    random walk predicts win% = stop/(stop+target); gross = zero spread")
    d_ = d
    H1, H4, D1 = sim.Bars(d_, 3600), sim.Bars(d_, 14400), sim.Bars(d_, 86400)
    for tp in (0.5, 1.0, 2.0, 3.0):
        base = ["--entry", "intended", "--tp-mode", "atr", "--tp-atr", str(tp), "--partial", "0", "--be-trail", "0"]
        g = sim.run(sim.args(base + ["--spread", "0"]), d_, H1, H4, D1)
        n = sim.run(sim.args(base), d_, H1, H4, D1)
        wr_g = np.mean([x["r"] > 0 for x in g])
        pred = 1 / (1 + tp)
        print(f"  target {tp:.1f} x stop: predicted win {pred:.1%}  actual gross {wr_g:.1%}  "
              f"gross avg {np.mean([x['r'] for x in g]):+.3f}R  net avg {np.mean([x['r'] for x in n]):+.3f}R  (n={len(g)})")
    print("\nQ4 COST SHARE - spread $0.35 as a fraction of D's stop (1 x ATR H1) = R lost per trade")
    tr = sim.run(sim.args(["--entry", "intended"]), d_, H1, H4, D1)
    t_ = np.array([x["t"] for x in tr])
    atr = np.array([x["atr"] for x in tr])
    for y0, y1 in ERAS:
        m = (t_ >= ts(y0)) & (t_ < ts(y1))
        print(f"  {y0}-{y1 - 1}: median stop ${np.median(atr[m]):5.2f}  spread = {0.35 / np.median(atr[m]):.3f}R per trade")


if __name__ == "__main__":
    q1()
    q2()
    q3_q4()
