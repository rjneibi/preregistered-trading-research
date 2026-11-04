"""Trade simulation on M1 mid prices with spread, commission and slippage.

Fills (d = +1 long / -1 short, half = half spread, slip = slip_ticks * tick):
  entry   market at the open of bar k:  o[k] + d*(half + slip)
  stop    exit-side price (mid - d*half) touches the stop; fills at stop - d*slip, or at the
          exit-side open - d*slip when the bar opens through the stop (gap)
  target  exit-side price touches the target; limit fill at the target, no slippage
  friday  market exit at the exit-side open of the first bar at/after the Friday cutoff, or at
          the previous bar's close when the next bar is already after the weekend
Stop and target in the same M1 bar -> stop (M1 cannot order them; conservative).
R = (d*(exit - entry) - commission) / (d*(entry - stop))."""
import numpy as np
import pandas as pd

WEEKEND_GAP = 12 * 60


def friday_cutoff(t_entry, cut_min):
    day = t_entry // 1440
    dow = (day + 3) % 7                                     # 0 = Monday
    return (day + (4 - dow)) * 1440 + cut_min


def simulate(m, sig, tp, sym, costs, cut_min, mult=1.0, one_open=True):
    """tp: float R multiple or 'liq' (uses sig.liq). Returns one row per trade taken."""
    t, o, h, l, c, sp = m["t"], m["o"], m["h"], m["l"], m["c"], m["sp"]
    slip = mult * costs["slip_ticks"] * sym["tick"]
    comm = mult * sym["comm"]
    measured = costs["spread_mode"] == "measured"
    fixed_half = mult * sym["spread"] / 2
    rows = []
    free_from = -1
    for s in sig.sort_values("k", kind="stable").itertuples(index=False):
        k, d = int(s.k), int(s.dir)
        if one_open and k < free_from:
            continue
        half_k = mult * sp[k] / 2 if measured else fixed_half
        entry = o[k] + d * (half_k + slip)
        risk = d * (entry - s.stop)
        if risk <= 0:
            continue
        if tp == "liq":
            if not np.isfinite(s.liq) or d * (s.liq - entry) <= 0:
                continue
            target = s.liq
        else:
            target = entry + d * tp * risk
        cut = friday_cutoff(int(t[k]), cut_min)
        e = int(np.searchsorted(t, cut))                   # first bar at/after the cutoff
        w = slice(k, max(e, k + 1))
        half = mult * sp[w] / 2 if measured else fixed_half
        adverse = (l[w] if d == 1 else h[w]) - d * half     # worst exit-side price in the bar
        favour = (h[w] if d == 1 else l[w]) - d * half
        hs = np.flatnonzero(d * (adverse - s.stop) <= 0)
        ht = np.flatnonzero(d * (favour - target) >= 0)
        js = k + int(hs[0]) if len(hs) else None
        jt = k + int(ht[0]) if len(ht) else None
        if js is not None and (jt is None or js <= jt):
            j = js
            op = o[j] - d * (mult * sp[j] / 2 if measured else fixed_half)
            px = (op if d * (op - s.stop) < 0 else s.stop) - d * slip
            why = "stop"
        elif jt is not None:
            j, px, why = jt, target, "target"
        elif e < len(t) and t[e] - cut < WEEKEND_GAP:
            j = e
            px = o[e] - d * (mult * sp[e] / 2 if measured else fixed_half)
            why = "friday"
        else:
            j = e - 1                                       # data ends or the market is closed
            px = c[j] - d * (mult * sp[j] / 2 if measured else fixed_half)
            why = "friday" if e < len(t) else "eod"
        r = (d * (px - entry) - comm) / risk
        rows.append((int(t[k]), int(t[j]) + 1, d, entry, s.stop, target, px, risk, r, why, k, j))
        free_from = j + 1
    return pd.DataFrame(rows, columns=["t_entry", "t_exit", "dir", "entry", "stop", "target",
                                       "exit", "risk", "R", "why", "k", "j"])
