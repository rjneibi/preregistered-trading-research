"""Round 4: the range-extreme reversion (Asia sweep fade) as a tradable spec.
Choose settings on 2022-07..2024-12 (M15), then check them untouched on 2025-01..2026-10
(M15) and on M5 (2025-05..2026-10, finer intrabar path). Costs: bar spread + $0.30
slippage on every stop exit. Minimum stop distance so R is never a few cents."""
import itertools, sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import Order, atr, fmt, load, simulate, stats

SLIP = 0.30
NAN = float("nan")


def build(d, bph, *, win_end=16, min_stop_atr=0.5, buf=0.3, confirm="close_inside", per_day=1):
    t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
    n = len(t)
    A = atr(d, 14) * np.sqrt(bph)
    hour = (t % 86400) / 3600.0
    day = t // 86400
    starts = np.flatnonzero(np.diff(day, prepend=day[0] - 1))
    out = []
    for s in starts:
        e = min(s + 24 * bph, n)
        idx = np.arange(s, e)
        asia = idx[hour[idx] < 6]
        rest = idx[(hour[idx] >= 6) & (hour[idx] < win_end)]
        if len(asia) < 2.5 * bph or not len(rest):
            continue
        ah, al = h[asia].max(), l[asia].min()
        taken = 0
        for i in rest:
            if i + 1 >= n or taken >= per_day:
                break
            for sgn, ext, swept in ((-1, ah, h[i] > ah), (1, al, l[i] < al)):
                if not swept:
                    continue
                inside = c[i] < ah if sgn == -1 else c[i] > al
                if confirm == "close_inside" and not inside:
                    continue
                entry = o[i + 1]
                wick = h[i] if sgn == -1 else l[i]
                stop = wick - sgn * buf
                min_d = min_stop_atr * A[i]
                if sgn * (entry - stop) < min_d:
                    stop = entry - sgn * min_d
                out.append(Order(i + 1, sgn, NAN, stop, 1, "sweep"))
                taken += 1
                break
    return out


def run(d, bph, orders, step_r, mode):
    tr = simulate(d, orders, exit_mode=mode, step_r=step_r, tp_r=step_r, max_hold=24 * bph)
    for x in tr:                                   # slippage on every exit, in R
        x["r"] -= SLIP / x["risk"]
    return tr


m15 = load("M15")
CUT = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())
grid = list(itertools.product((10, 13, 16, 20), (0.3, 0.5, 0.8), (0.4, 0.6, 1.0), ("ladder",)))
grid += list(itertools.product((10, 13, 16, 20), (0.3, 0.5, 0.8), (1.0, 1.5, 2.0), ("tp",)))
res = []
for win_end, msa, step, mode in grid:
    tr = run(m15, 4, build(m15, 4, win_end=win_end, min_stop_atr=msa), step, mode)
    a = [x for x in tr if x["t"] < CUT]
    b = [x for x in tr if x["t"] >= CUT]
    res.append(((win_end, msa, step, mode), stats(a), stats(b), tr))
res.sort(key=lambda x: -x[1]["net"] / (x[1]["dd"] + 5))
print("top 8 by TRAIN (2022-07..2024), then TEST (2025..2026-10) with the same settings:")
for cfg, a, b, _ in res[:8]:
    print(f"  window 06-{cfg[0]:02d} minstop {cfg[1]}ATR {cfg[3]} {cfg[2]}R\n"
          f"     TRAIN {fmt(a)}\n     TEST  {fmt(b)}")
best = res[0][0]
print("\nchosen:", best)
m5 = load("M5")
tr5 = run(m5, 12, build(m5, 12, win_end=best[0], min_stop_atr=best[1]), best[2], best[3])
print("M5 check (2025-05..2026-10):", fmt(stats(tr5)))
risks = np.array([x["risk"] for x in tr5])
print(f"M5 risk per trade $: median {np.median(risks):.2f}  p10 {np.percentile(risks, 10):.2f}  p90 {np.percentile(risks, 90):.2f}")
print("trades per month (M5):", round(len(tr5) / 17.2, 1))
months = {}
for x in tr5:
    k = datetime.fromtimestamp(x["t"], timezone.utc).strftime("%Y-%m")
    months[k] = months.get(k, 0) + x["r"]
print("M5 R by month:", " ".join(f"{k[2:]}:{v:+.0f}" for k, v in months.items()))
