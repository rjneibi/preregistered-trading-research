"""Round 2: the round-1 candidates on 4 years of M15, result per calendar year."""
import sys
sys.argv = ["round1.py", "M15"]
sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
import runpy
from datetime import datetime, timezone
g = runpy.run_path("@GANN_ROOT@/research/ta_lab/round1.py", run_name="r1")
from lab import simulate, stats, fmt
d, M = g["d"], g["METHODS"]
years = sorted({datetime.fromtimestamp(int(x), timezone.utc).year for x in d["t"]})
for name in ("random (any direction)", "random (with H1 trend)", "asia sweep fade (ICT)", "asia breakout",
             "pivot S1/R1", "pivot S1/R1 with trend", "fib 61.8%", "fib 50%"):
    tr = simulate(d, M[name](), exit_mode="ladder", step_r=0.6, max_hold=96)
    print(f"{name:<24} ALL  {fmt(stats(tr))}")
    for y in years:
        sub = [x for x in tr if datetime.fromtimestamp(x['t'], timezone.utc).year == y]
        s = stats(sub)
        print(f"{'':<24} {y} n {s['n']:4d} avg {s['avg']:+.3f}R PF {s['pf']:4.2f} net {s['net']:+6.1f}R")
    print()
