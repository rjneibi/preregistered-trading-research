"""Audit engine: an independent numpy bar simulator, written without reference to the programme's engines.

Bars are BID. Ask = bid + spread. Longs enter at ask, exit at bid. Shorts enter at bid, exit at ask.
A stop is checked before a target in the same bar. A bar opening through a barrier fills at that open.
slip is added against the trader on market fills and stops, never on limit targets.
comm is a price-unit charge per round trip.
"""
import math
from dataclasses import dataclass

import numpy as np


@dataclass
class Result:
    entry_i: np.ndarray
    exit_i: np.ndarray
    side: np.ndarray
    entry: np.ndarray
    exit: np.ndarray
    reason: np.ndarray  # 0 stop, 1 target, 2 time
    ambiguous: np.ndarray
    pnl: np.ndarray     # price units, after spread, slip, comm
    risk: np.ndarray    # planned distance from fill to stop


def simulate(o, h, l, c, spread, entry_i, side, stop_dist, tgt_dist, max_bars, slip=0.0, comm=0.0, one_at_a_time=False):
    """Market order at the open of entry_i. stop_dist and tgt_dist are distances from the fill, NaN disables."""
    n = len(o)
    sp = np.broadcast_to(np.asarray(spread, float), (n,))
    rows = []
    busy = -1
    for k in np.argsort(entry_i, kind="stable"):
        i, s = int(entry_i[k]), int(side[k])
        if i >= n or (one_at_a_time and i <= busy):
            continue
        fill = o[i] + (sp[i] + slip if s > 0 else -slip)
        sd, td = float(stop_dist[k]), float(tgt_dist[k])
        stp = fill - s * sd if not math.isnan(sd) else math.nan
        tgt = fill + s * td if not math.isnan(td) else math.nan
        end = min(i + int(max_bars), n) - 1
        px, why, amb, j = None, 2, False, end
        for j in range(i, end + 1):
            hi, lo, op = (h[j], l[j], o[j]) if s > 0 else (h[j] + sp[j], l[j] + sp[j], o[j] + sp[j])
            hit_s = not math.isnan(stp) and ((lo <= stp) if s > 0 else (hi >= stp))
            hit_t = not math.isnan(tgt) and ((hi >= tgt) if s > 0 else (lo <= tgt))
            if hit_s:
                gap = j > i and ((op <= stp) if s > 0 else (op >= stp))
                px = (op if gap else stp) - s * slip
                why, amb = 0, hit_t
                break
            if hit_t:
                gap = j > i and ((op >= tgt) if s > 0 else (op <= tgt))
                px, why = (op if gap else tgt), 1
                break
        if px is None:
            j = end
            px = (c[j] if s > 0 else c[j] + sp[j]) - s * slip
        rows.append((i, j, s, fill, px, why, amb, s * (px - fill) - comm, sd))
        busy = j
    if not rows:
        return Result(*[np.array([]) for _ in range(9)])
    a = list(zip(*rows))
    return Result(np.array(a[0]), np.array(a[1]), np.array(a[2]), np.array(a[3], float), np.array(a[4], float), np.array(a[5]),
                  np.array(a[6], bool), np.array(a[7], float), np.array(a[8], float))


def lots_for_risk(equity, risk_frac, stop_dist, contract, step, vol_min):
    """Largest lot on the volume grid that risks no more than the budget. Zero if vol_min already exceeds it."""
    lots = equity * risk_frac / (stop_dist * contract)
    lots = math.floor(lots / step + 1e-9) * step
    return round(lots, 8) if lots >= vol_min else 0.0


def closed_resample(t, o, h, l, c, seconds):
    """Resample by bucket start. Only buckets followed by a later bucket are returned, so no forming bar leaks."""
    b = t - t % seconds
    u, first = np.unique(b, return_index=True)
    last = np.r_[first[1:], len(t)] - 1
    H = np.maximum.reduceat(h, first)
    L = np.minimum.reduceat(l, first)
    return u[:-1], o[first][:-1], H[:-1], L[:-1], c[last][:-1]
