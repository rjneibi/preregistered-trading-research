"""Trade simulation on 1-minute bars.

Price model: arrays hold MID prices plus a per-bar spread. A long buys at the ask
(mid + k*spread/2) and sells at the bid (mid - k*spread/2); k is the cost multiplier
(0 = gross, 1 = estimated costs, 2 = double). Market and stop orders also pay k*slip per
side; limit (target) orders fill exactly at their price. Commission k*comm per round trip.

Shorts are simulated by negating prices (o,h,l,c -> -o,-l,-h,-c), so there is one code path.

Fill conventions (all conservative):
  * stop and target touched in the same 1m bar -> stop first;
  * stop-entry fill bar: the stop can be hit on that bar, the target cannot;
  * a stop that gaps is filled at the (worse) bar open;
  * a trade still open at the forced-exit time is closed at that bar's open.

R is measured against the planned risk |planned_entry - stop| in mid prices, so all costs
show up as a lower R.
"""
import numpy as np


def window(m, direction, a, b):
    """(o,h,l,c,sp) for bars a..b-1, negated and high/low swapped for a short."""
    o, h, l, c, sp = m["o"][a:b], m["h"][a:b], m["l"][a:b], m["c"][a:b], m["sp"][a:b]
    if direction > 0:
        return o, h, l, c, sp
    return -o, -l, -h, -c, sp


def _fill(o0, sp0, kind, level, k, slip):
    """Entry fill in signed space. market: bar open; stop: max(level, open);
    limit: the level itself (no slippage; a limit that gaps through fills at the open)."""
    ask = o0 + k * sp0 / 2
    if kind == "limit":
        return min(level, ask)
    return (ask if kind == "market" else max(level, ask)) + k * slip


def simulate(m, i0, i_end, direction, planned, stop, rrs, k, slip, comm, kind="market"):
    """Simulate one trade for several targets at once.

    m       : instrument dict of numpy arrays (mid o,h,l,c, sp)
    i0      : index of the entry bar (entry at its open, or stop fill inside it)
    i_end   : index of the forced-exit bar (exit at its open); bars i0..i_end-1 are live
    direction: +1 long / -1 short;  planned, stop: mid prices in REAL (unsigned) space
    rrs     : sequence of reward:risk multiples; np.inf = no target (stop or time only)
    Returns (R array, exit-bar index array, reason array: 1 target, -1 stop, 0 time).
    """
    rrs = np.asarray(rrs, dtype=float)
    n_rr = len(rrs)
    p_plan, p_stop = direction * planned, direction * stop
    risk = p_plan - p_stop
    N = len(m["o"])
    if risk <= 0 or i_end <= i0 or i0 >= N:
        return np.full(n_rr, np.nan), np.full(n_rr, -1), np.zeros(n_rr, int)
    has_exit_bar = i_end < N
    o, h, l, c, sp = window(m, direction, i0, min(i_end + 1, N))
    n = min(i_end, N) - i0                      # live bars
    hs = k * sp / 2
    fill = _fill(o[0], sp[0], kind, p_plan, k, slip)

    bid_l = l[:n] - hs[:n]
    bid_h = h[:n] - hs[:n]
    if kind in ("stop", "limit"):
        bid_h = bid_h.copy()
        bid_h[0] = -np.inf          # unknown whether the high came after the fill
    hit = np.flatnonzero(bid_l <= p_stop)
    s = hit[0] if hit.size else n
    fav = np.maximum.accumulate(bid_h)
    targets = p_plan + rrs * risk
    t_idx = np.searchsorted(fav, targets, side="left")   # first bar with fav >= target
    win = t_idx < s

    if s < n:
        other_px = min(p_stop, o[s] - hs[s]) - k * slip
        other_i, other_why = i0 + s, -1
    else:
        other_px = (o[n] - hs[n] if has_exit_bar else c[n - 1] - hs[n - 1]) - k * slip
        other_i, other_why = (i_end if has_exit_bar else N - 1), 0
    exit_px = np.where(win, targets, other_px)
    reason = np.where(win, 1, other_why)
    exit_i = np.where(win, i0 + t_idx, other_i)
    return (exit_px - fill - k * comm) / risk, exit_i, reason


def simulate_managed(m, i0, i_end, direction, planned, stop, rr, k, slip, comm,
                     kind="market", be_at=None, partial_at=None, partial_frac=0.5,
                     trail_atr=None, atr=None, time_stop=None):
    """Bar-by-bar loop for managed exits (break-even, partial TP, ATR trail).

    be_at      : move stop to planned entry once +be_at R is reached (effective next bar)
    partial_at : close partial_frac at +partial_at R (limit fill)
    trail_atr  : trail stop at (highest bid high since entry) - trail_atr*atr, next bar
    time_stop  : exit at the open of bar i0+time_stop (minutes) if still open
    Returns (R, exit index, reason).
    """
    p_plan, p_stop = direction * planned, direction * stop
    risk = p_plan - p_stop
    N = len(m["o"])
    if risk <= 0 or i_end <= i0 or i0 >= N:
        return np.nan, -1, 0
    if time_stop is not None:
        i_end = min(i_end, i0 + int(time_stop))
    has_exit_bar = i_end < N
    o, h, l, c, sp = window(m, direction, i0, min(i_end + 1, N))
    n = min(i_end, N) - i0
    fill = _fill(o[0], sp[0], kind, p_plan, k, slip)
    target = p_plan + rr * risk if np.isfinite(rr) else np.inf
    cur_stop = p_stop
    open_frac, realised = 1.0, 0.0
    peak = -np.inf
    partial_done = False
    for j in range(n):
        hs = k * sp[j] / 2
        bl, bh = l[j] - hs, h[j] - hs
        if kind in ("stop", "limit") and j == 0:
            bh = -np.inf
        if bl <= cur_stop:                                  # stop first
            px = min(cur_stop, o[j] - hs) - k * slip
            realised += open_frac * (px - fill)
            return (realised - k * comm) / risk, i0 + j, -1
        if partial_at is not None and not partial_done and bh >= p_plan + partial_at * risk:
            realised += partial_frac * (p_plan + partial_at * risk - fill)
            open_frac -= partial_frac
            partial_done = True
        if bh >= target:
            realised += open_frac * (target - fill)
            return (realised - k * comm) / risk, i0 + j, 1
        peak = max(peak, bh)
        # updates take effect from the next bar
        if be_at is not None and peak >= p_plan + be_at * risk:
            cur_stop = max(cur_stop, p_plan)
        if trail_atr is not None and atr is not None and np.isfinite(atr) and peak > p_plan:
            cur_stop = max(cur_stop, peak - trail_atr * atr)
    if has_exit_bar:
        px = o[n] - k * sp[n] / 2 - k * slip
        ei = i_end
    else:
        px = c[n - 1] - k * sp[n - 1] / 2 - k * slip
        ei = N - 1
    realised += open_frac * (px - fill)
    return (realised - k * comm) / risk, ei, 0
