"""Round 1: does any classic method make money on its own (gold, M5, 17 months)?
Every method gets the same two exits (lock ladder 0.6R; TP 2R with BE at 1R) and is
judged on TRAIN (before 2026-02-01) and TEST (after). Baselines: random entries."""
import sys
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "@GANN_ROOT@/research/ta_lab")
from lab import Order, atr, ema, fmt, load, simulate, split, stats, day_index

TF = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "M5"
BPH = {"M5": 12, "M15": 4}[TF]
d = load(TF)
t, o, h, l, c = d["t"], d["o"], d["h"], d["l"], d["c"]
n = len(t)
A = atr(d, 14) * np.sqrt(BPH)          # ~H1 ATR from M5 ATR
CUT = int(datetime(2026, 2, 1, tzinfo=timezone.utc).timestamp())
hour = (t % 86400) / 3600.0
day = day_index(t)
rng = np.random.default_rng(7)
NAN = float("nan")
print(f"M5 {datetime.fromtimestamp(t[0], timezone.utc):%Y-%m-%d} -> "
      f"{datetime.fromtimestamp(t[-1], timezone.utc):%Y-%m-%d}, cut {datetime.fromtimestamp(CUT, timezone.utc):%Y-%m-%d}")

# --- helpers ------------------------------------------------------------------
day_starts = np.flatnonzero(np.diff(day, prepend=day[0] - 1))
H1_trend = ema(c, BPH * 50)            # EMA50 on H1 equivalent
slope = np.sign(H1_trend - np.concatenate([np.full(BPH * 4, H1_trend[0]), H1_trend[:-BPH * 4]]))


def strat_random(trend: bool):
    out = []
    for s in day_starts:
        e = s + 24 * BPH if s + 24 * BPH < n else n
        cand = [i for i in range(s, e) if 7 <= hour[i] < 17]
        if not cand:
            continue
        i = int(rng.choice(cand))
        sgn = int(slope[i - 1]) if trend and slope[i - 1] != 0 else int(rng.choice([-1, 1]))
        out.append(Order(i, sgn, NAN, o[i] - sgn * A[i - 1], 1, "rand"))
    return out


def zigzag(th_mult=2.5):
    """Swing points confirmed when price reverses th_mult*ATR from the extreme.
    Yields (confirm_index, kind, price, start_price) for each completed leg."""
    legs, mode, ext_i, ext = [], 0, 0, c[0]
    last_pivot = c[0]
    for i in range(1, n):
        th = th_mult * A[i - 1]
        if mode >= 0:                               # tracking a high
            if h[i] > ext or mode == 0:
                ext, ext_i = max(ext, h[i]), i if h[i] >= ext else ext_i
                if mode == 0:
                    mode = 1
            if ext - l[i] > th:                     # high confirmed
                legs.append((i, "high", ext, last_pivot))
                last_pivot, mode, ext, ext_i = ext, -1, l[i], i
        else:
            if l[i] < ext:
                ext, ext_i = l[i], i
            if h[i] - ext > th:                     # low confirmed
                legs.append((i, "low", ext, last_pivot))
                last_pivot, mode, ext, ext_i = ext, 1, h[i], i
    return legs


def strat_fib(level=0.618, min_leg_atr=5.0, stop_level=0.886):
    out = []
    for i, kind, piv, start in zigzag():
        leg = abs(piv - start)
        if i + 1 >= n or leg < min_leg_atr * A[i]:
            continue
        if kind == "high":                          # up-leg done: buy the retracement
            entry = piv - level * leg
            stop = piv - stop_level * leg
            out.append(Order(i + 1, 1, entry, stop, 24 * BPH, f"fib{level}"))
        else:
            entry = piv + level * leg
            stop = piv + stop_level * leg
            out.append(Order(i + 1, -1, entry, stop, 24 * BPH, f"fib{level}"))
    return out


def asia_ranges():
    """Asia = 00:00-06:00 UTC each day: (day_start_index, hi, lo, first index after 06:00)."""
    res = []
    for s in day_starts:
        e = min(s + 24 * BPH, n)
        idx = np.arange(s, e)
        a = idx[hour[idx] < 6]
        rest = idx[(hour[idx] >= 6) & (hour[idx] < 16)]
        if len(a) < 2.5 * BPH or len(rest) == 0:
            continue
        res.append((s, h[a].max(), l[a].min(), rest))
    return res


def strat_sweep():
    """Liquidity sweep (ICT): wick through the Asia high/low, close back inside -> fade."""
    out = []
    for s, ah, al, rest in asia_ranges():
        done = set()
        for i in rest:
            if i + 1 >= n:
                break
            if "s" not in done and h[i] > ah and c[i] < ah:
                out.append(Order(i + 1, -1, NAN, h[i] + 0.3, 1, "sweep"))
                done.add("s")
            if "b" not in done and l[i] < al and c[i] > al:
                out.append(Order(i + 1, 1, NAN, l[i] - 0.3, 1, "sweep"))
                done.add("b")
    return out


def strat_breakout():
    """Opposite idea: M5 close beyond the Asia range -> go with it, stop at range middle."""
    out = []
    for s, ah, al, rest in asia_ranges():
        mid = (ah + al) / 2
        for i in rest:
            if i + 1 >= n:
                break
            if c[i] > ah:
                out.append(Order(i + 1, 1, NAN, mid, 1, "brk"))
                break
            if c[i] < al:
                out.append(Order(i + 1, -1, NAN, mid, 1, "brk"))
                break
    return out


def strat_pivot(with_trend: bool):
    """Classic floor pivots from the previous UTC day: buy limit at S1, sell limit at R1."""
    out = []
    prev = None
    for s in day_starts:
        e = min(s + 24 * BPH, n)
        if prev is not None:
            ph, pl, pc = prev
            p = (ph + pl + pc) / 3
            r1, s1 = 2 * p - pl, 2 * p - ph
            r2, s2 = p + (ph - pl), p - (ph - pl)
            if not with_trend or slope[s - 1] > 0:
                out.append(Order(s, 1, s1, s1 - 0.5 * (s1 - s2), e - s, "piv"))
            if not with_trend or slope[s - 1] < 0:
                out.append(Order(s, -1, r1, r1 + 0.5 * (r2 - r1), e - s, "piv"))
        prev = (h[s:e].max(), l[s:e].min(), c[e - 1])
    return out


def strat_round(step=25.0, with_trend=True):
    """Round numbers: each 06:00 UTC, limit at the next $25 level below (buy) / above (sell)."""
    out = []
    for s, ah, al, rest in asia_ranges():
        i = rest[0]
        px = o[i]
        below, above = np.floor(px / step) * step, np.ceil(px / step) * step
        if not with_trend or slope[i - 1] > 0:
            out.append(Order(i, 1, below, below - A[i - 1], 10 * BPH, "round"))
        if not with_trend or slope[i - 1] < 0:
            out.append(Order(i, -1, above, above + A[i - 1], 10 * BPH, "round"))
    return out


METHODS = {
    "random (any direction)": lambda: strat_random(False),
    "random (with H1 trend)": lambda: strat_random(True),
    "fib 38.2%": lambda: strat_fib(0.382, stop_level=0.786),
    "fib 50%": lambda: strat_fib(0.5, stop_level=0.786),
    "fib 61.8%": lambda: strat_fib(0.618, stop_level=0.886),
    "asia sweep fade (ICT)": strat_sweep,
    "asia breakout": strat_breakout,
    "pivot S1/R1": lambda: strat_pivot(False),
    "pivot S1/R1 with trend": lambda: strat_pivot(True),
    "round $25 with trend": lambda: strat_round(25.0, True),
}

if __name__ == "__main__":
    for name, fn in METHODS.items():
        orders = fn()
        for mode, kw in (("ladder0.6R", dict(exit_mode="ladder", step_r=0.6)),
                         ("TP2R+BE", dict(exit_mode="tp", tp_r=2.0))):
            tr = simulate(d, orders, **kw)
            a, b = split(tr, CUT)
            print(f"{name:<24} {mode:<10} TRAIN {fmt(stats(a))}\n{'':<35} TEST  {fmt(stats(b))}")
        print()
