"""BOT-LAB-1 part C: news trading on XAUUSD M1 (broker time; ET 08:30 = broker 15:30, ET 14:00 =
broker 21:00 all year because the broker shifts with US DST).

Events: FOMC statements 2015-2026 (exact, fable calendar), NFP 2010-2026 (the Friday in days 1-10
whose 15:30 bar shows the release spike - the schedule, not the direction, is read from data),
CPI where the exact date is known (2015, 2025-26).
Rules, each vs the SAME rule at the same clock time on every non-event weekday (twin):
  MOM-k : after k minutes, trade in the direction of the move since release; stop = far side of
          the first-k-minute range; exit after `hold` minutes.
  FADE-k: opposite direction; stop = first-k extreme + 0.5 x that range.
  BRK   : stop orders at the 30-min pre-release range +- 0; first touched side; stop = other side;
          exit after `hold`.
Costs: entry spread $0.80 inside the first 15 min after a release (else $0.35), exit $0.35.
Pass (fixed before the run): PF >= 1.15 in both halves, n >= 30 per half, event mean R above
95% of random equal-size twin samples.
"""
import datetime as dt
import sys

import numpy as np

sys.path.insert(0, r"@GANN_ROOT@/fable-backtesting")
sys.path.insert(0, r"@GANN_ROOT@/research/d_revival")
import data  # noqa: E402
from build_calendar import CPI_KNOWN, FOMC  # noqa: E402

d = data.load()
T, O, H, L, C = d["t"], d["o"], d["h"], d["l"], d["c"]


def bt(day, hh, mm):
    return int(dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=dt.timezone.utc).timestamp())


def at(ts):
    i = int(np.searchsorted(T, ts))
    return i if i < len(T) and T[i] == ts else None


def spike(day):
    i = at(bt(day, 15, 30))
    if i is None or i < 30:
        return 0.0
    pre = np.mean(H[i - 30:i] - L[i - 30:i])
    return (H[i:i + 3].max() - L[i:i + 3].min()) / max(pre, 1e-6)


def nfp_days():
    out = []
    for y in range(2010, 2027):
        for m in range(1, 13):
            fr = [dt.date(y, m, k) for k in range(1, 11) if dt.date(y, m, k).weekday() == 4]
            s = [(spike(f), f) for f in fr]
            if s and max(s)[0] > 4:
                out.append(max(s)[1])
    return out


EVENTS = {"NFP": [(x, 15, 30) for x in nfp_days()],
          "FOMC": [(dt.date.fromisoformat(x), 21, 0) for x in FOMC],
          "CPI": [(dt.date.fromisoformat(x), 15, 30) for x in CPI_KNOWN]}


def trade(i0, rule, k, hold, ent_sp):
    """i0 = release bar index. Returns R or None."""
    if i0 is None or i0 + k + hold + 1 >= len(T) or T[i0 + k + hold] - T[i0] > (k + hold + 30) * 60:
        return None
    if rule == "BRK":
        hi, lo = H[i0 - 30:i0].max(), L[i0 - 30:i0].min()
        for j in range(i0, i0 + 60):
            up, dn = H[j] + 0.35 >= hi, L[j] <= lo
            if up or dn:
                if up and dn:
                    return -1.0                       # both sides in one bar: assume the worst
                sgn = 1 if up else -1
                fill = (max(hi, O[j] + ent_sp) if sgn == 1 else min(lo, O[j]))
                stop = lo if sgn == 1 else hi + 0.35
                return walk(j, sgn, fill, stop, j + hold, start_after_fill=True)
        return None
    seg_h, seg_l = H[i0:i0 + k].max(), L[i0:i0 + k].min()
    move = C[i0 + k - 1] - O[i0]
    if move == 0:
        return None
    sgn = 1 if move > 0 else -1
    if rule == "FADE":
        sgn = -sgn
    j = i0 + k
    fill = O[j] + (ent_sp if sgn == 1 else 0)
    rng = seg_h - seg_l
    if rule == "MOM":
        stop = seg_l if sgn == 1 else seg_h + 0.35
    else:
        stop = seg_l - 0.5 * rng if sgn == 1 else seg_h + 0.5 * rng + 0.35
    return walk(j, sgn, fill, stop, j + hold)


def walk(j, sgn, fill, stop, j_end, start_after_fill=False):
    risk = sgn * (fill - stop)
    if risk <= 0.2:
        return None
    for x in range(j, j_end):
        adv = L[x] if sgn == 1 else H[x] + 0.35
        if sgn * (adv - stop) <= 0:
            op = O[x] if sgn == 1 else O[x] + 0.35
            px = op if (sgn * (op - stop) <= 0 and x > j) else stop
            return sgn * (px - fill) / risk
    ex = C[j_end] if sgn == 1 else C[j_end] + 0.35
    return sgn * (ex - fill) / risk


def stats(r):
    r = np.array([x for x in r if x is not None])
    if len(r) == 0:
        return 0, 0.0, 0.0
    gl = -r[r < 0].sum()
    return len(r), (r[r > 0].sum() / gl if gl else 99), r.mean()


def main():
    rng = np.random.default_rng(1)
    weekdays = {}
    t_day = dt.date(2010, 3, 1)
    while t_day < dt.date(2026, 10, 10):
        if t_day.weekday() < 5:
            weekdays[t_day] = True
        t_day += dt.timedelta(days=1)
    for ev, lst in EVENTS.items():
        evdays = {x[0] for x in lst}
        hh, mm = lst[0][1], lst[0][2]
        print(f"===== {ev}: {len(lst)} events ({lst[0][0]} .. {lst[-1][0]}) at broker {hh:02d}:{mm:02d}")
        for rule, k in [("MOM", 1), ("MOM", 5), ("MOM", 15), ("FADE", 5), ("FADE", 15), ("BRK", 0)]:
            for hold in (30, 120, 360):
                if hh == 21 and hold == 360:
                    continue
                er = [(day, trade(at(bt(day, h_, m_)), rule, k, hold, 0.80)) for day, h_, m_ in lst]
                er = [(a, b) for a, b in er if b is not None]
                if len(er) < 10:
                    continue
                mid = er[len(er) // 2][0]
                n1, pf1, _ = stats([b for a, b in er if a < mid])
                n2, pf2, _ = stats([b for a, b in er if a >= mid])
                n, pf, mean = stats([b for _, b in er])
                tw = [trade(at(bt(x, hh, mm)), rule, k, hold, 0.35) for x in weekdays if x not in evdays]
                tw = np.array([x for x in tw if x is not None])
                draws = np.array([rng.choice(tw, n).mean() for _ in range(2000)])
                pct = (draws < mean).mean()
                ok = pf1 >= 1.15 and pf2 >= 1.15 and n1 >= 30 and n2 >= 30 and pct >= 0.95
                print(f"  {rule:4s} k={k:2d} hold={hold:3d}  n={n:3d} PF={pf:4.2f} avg={mean:+.3f}R | "
                      f"halves PF {pf1:4.2f} / {pf2:4.2f} | twin avg {tw.mean():+.3f}R, beats {pct:4.0%}"
                      f"{'   <== PASS' if ok else ''}")


if __name__ == "__main__":
    main()
