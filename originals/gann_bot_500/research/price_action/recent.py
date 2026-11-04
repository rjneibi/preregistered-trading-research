"""PA-1 / PA-1b re-shown on 2025-01-01+ only (user request; descriptive, same rules, no new tuning)."""
import numpy as np
import pa1 as P
import ib_confirm as C
T0 = 1735689600
print("GOLD 2025+   pattern  n   gross   net(cost A $0.40)  net(cost B $0.22)  twin   win")
for tf in (1, 4, 24):
    for pat in ("PIN", "PINX", "ENG", "IB", "NR7", "SFP"):
        tr = [x for x in P.trades(tf, pat) if P.t[x[0]] >= T0]
        if len(tr) < 5:
            continue
        real = P.run(tr); rng = np.random.default_rng(11)
        tw = np.concatenate([P.R(P.run(tr, rng.choice([-1, 1], len(tr))), P.COST) for _ in range(20)])
        r = P.R(real, P.COST)
        print(f"  { {1:'H1',4:'H4',24:'D1'}[tf] } {pat:5s} n{len(r):4d} {P.R(real,0).mean():+.3f}  {r.mean():+.3f}  {P.R(real,P.IC).mean():+.3f}  {tw.mean():+.3f}  {np.mean(r>0):.0%}  sum {r.sum():+.1f}R", flush=True)
print("INSIDE BAR D1, 2025+")
for name, (dn, fn, _, swl, sws) in C.MKTS.items():
    D, F = C.npz(dn), C.npz(fn)
    cost = 1.5 * float(np.median(F["sp"]))
    tr = [x for x in C.trades(D, F) if F["t"][x[0]] >= T0]
    r = np.array([x[1] for x in C.run(F, tr, cost, swl, sws)])
    print(f"  {name:7s} n{len(r):3d} net {r.mean():+.3f}R  sum {r.sum():+.1f}R  win {np.mean(r>0):.0%}")
