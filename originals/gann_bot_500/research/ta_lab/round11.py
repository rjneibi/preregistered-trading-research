"""Round 11: re-check the earlier Fable research (FINAL_v4: H1 close beyond the prior-day
R3/S3 pivot, 12-20 UTC, no Mondays, 1/day, TP 0.8 ATR, SL 2.4 ATR, 24h) in this lab:
same costs ($0.30 slip), pessimistic intrabar, against a random twin. No tuning - the spec
is taken as published, so the whole 2022-2026 M15 record is out of sample for this lab."""
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import Order, atr, fmt, load, simulate, stats
from round5 import halves, twin

NAN = float("nan")
d = load("M15")
t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
n = len(t)
A = atr(d, 14) * 2.0                       # ATR(H1) ~ ATR(M15) x sqrt(4)
day = t // 86400
hour = (t % 86400) / 3600.0
starts = np.flatnonzero(np.diff(day, prepend=day[0] - 1))
orders = []
for a, s in zip(starts[:-1], starts[1:]):
    dow = datetime.fromtimestamp(int(t[s]), timezone.utc).weekday()
    if dow == 0 or day[s] - day[a] > 3:
        continue
    ph, pl, pc = h[a:s].max(), l[a:s].min(), c[s - 1]
    p = (ph + pl + pc) / 3
    r3, s3 = ph + 2 * (p - pl), pl - 2 * (ph - p)
    atr_day = A[s - 1]
    e = min(s + 96, n)
    for i in range(s, e - 1):
        if (t[i] % 3600) != 45 * 60 or not (11.75 <= hour[i] < 19.75):
            continue                      # an H1 close = the M15 bar ending on the hour
        if c[i] > r3:
            orders.append(Order(i + 1, 1, NAN, o[i + 1] - 2.4 * atr_day, 1, "r3"))
            break
        if c[i] < s3:
            orders.append(Order(i + 1, -1, NAN, o[i + 1] + 2.4 * atr_day, 1, "s3"))
            break


def run(oo):
    tr = simulate(d, oo, exit_mode="tp", tp_r=0.8 / 2.4, max_hold=96)
    for x in tr:
        x["r"] -= 0.30 / x["risk"]
    return tr


a, b = halves(run(orders))
ta, tb = halves(run(twin(d, 4, orders, (12, 20))))
print(f"FINAL_v4 <2025 {fmt(stats(a))} | twin avg {stats(ta)['avg']:+.3f}R")
print(f"FINAL_v4 2025+ {fmt(stats(b))} | twin avg {stats(tb)['avg']:+.3f}R")
