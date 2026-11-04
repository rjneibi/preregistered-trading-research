"""H-S scalp laboratory — self-contained (drops into research/goldbot/prereg/).

Everything here implements HS_PREREGISTRATION.md exactly. The exit engine is the
same first-touch logic as the goldbot barrier engine but with FIXED $/oz barriers
(scalps target cents, not ATR multiples) and the same deliberate pessimism:
ambiguous bars (both barriers inside one bar) are LOSSES. At scalp scale that is
the dominant case, which is the design: bar-level FAIL is decisive, PASS is weak
and escalates to tick-level re-simulation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------- signals (closed-bar, entry next open: no lookahead) ----------

def zscore_fade_events(df: pd.DataFrame, lookback: int = 60, z_th: float = 2.0,
                       min_gap: int = 5):
    c = df["close"]
    mu = c.rolling(lookback).mean()
    sd = c.rolling(lookback).std(ddof=1)
    z = (c - mu) / sd
    raw_long = (z < -z_th).to_numpy()
    raw_short = (z > z_th).to_numpy()
    return _dedup(np.flatnonzero(raw_long | raw_short),
                  np.where(raw_short[np.flatnonzero(raw_long | raw_short)], -1, 1),
                  min_gap)


def momo_burst_events(df: pd.DataFrame, lookback: int = 20, min_gap: int = 5):
    hi = df["high"].rolling(lookback).max().shift(1)
    lo = df["low"].rolling(lookback).min().shift(1)
    long_ = (df["close"] > hi).to_numpy()
    short = (df["close"] < lo).to_numpy()
    ev = np.flatnonzero(long_ | short)
    return _dedup(ev, np.where(short[ev], -1, 1), min_gap)


def _dedup(events: np.ndarray, sides: np.ndarray, min_gap: int):
    out_e, out_s, last = [], [], -10 ** 9
    for e, s in zip(events, sides):
        if e - last >= min_gap:
            out_e.append(int(e)); out_s.append(int(s)); last = e
    return np.asarray(out_e, int), np.asarray(out_s, int)


def session_mask(index_utc: pd.DatetimeIndex, events: np.ndarray,
                 hours: tuple[int, int] | None) -> np.ndarray:
    if hours is None:
        return np.ones(events.size, bool)
    h = index_utc.hour.to_numpy()[events]
    return (h >= hours[0]) & (h < hours[1])

# ---------- $-barrier exit engine (pessimistic by design) ----------

def dollar_barrier(df: pd.DataFrame, events: np.ndarray, sides: np.ndarray,
                   tp_usd: float, sl_usd: float, horizon: int = 30):
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    n = len(df); rows = []; ambiguous = 0
    for e, s in zip(events, sides):
        i0 = e + 1
        if i0 >= n:
            continue
        entry = o[i0]
        tp = entry + s * tp_usd
        sl = entry - s * sl_usd
        end = min(i0 + horizon, n - 1)
        exit_price, t1, reason = c[end], end, "time"
        for j in range(i0, end + 1):
            if s == 1:
                if o[j] <= sl: exit_price, t1, reason = o[j], j, "sl_gap"; break
                if o[j] >= tp: exit_price, t1, reason = o[j], j, "tp_gap"; break
                hit_tp, hit_sl = h[j] >= tp, l[j] <= sl
            else:
                if o[j] >= sl: exit_price, t1, reason = o[j], j, "sl_gap"; break
                if o[j] <= tp: exit_price, t1, reason = o[j], j, "tp_gap"; break
                hit_tp, hit_sl = l[j] <= tp, h[j] >= sl
            if hit_tp and hit_sl:
                ambiguous += 1; exit_price, t1, reason = sl, j, "ambiguous->sl"; break
            if hit_sl: exit_price, t1, reason = sl, j, "sl"; break
            if hit_tp: exit_price, t1, reason = tp, j, "tp"; break
        rows.append((i0, t1, int(s), float(entry), float(exit_price), reason))
    t = pd.DataFrame(rows, columns=["t0", "t1", "side", "entry", "exit_price", "exit_reason"])
    return t, ambiguous


def pf_net(trades: pd.DataFrame, cost_per_oz, contract_oz: int = 100,
           commission_rt: float = 7.0) -> tuple[float, float, int]:
    """cost_per_oz: float, or callable(entry_ts_pos)->float for matrix costs
    (caller maps positions to timestamps). Returns (PF, expectancy_usd, n)."""
    if trades.empty:
        return float("nan"), float("nan"), 0
    gross = trades["side"] * (trades["exit_price"] - trades["entry"]) * contract_oz
    if callable(cost_per_oz):
        c = np.array([cost_per_oz(p) for p in trades["t0"]]) * contract_oz
    else:
        c = float(cost_per_oz) * contract_oz
    net = gross - c - commission_rt
    w, lo = net[net > 0].sum(), net[net <= 0].sum()
    pf = float(w / abs(lo)) if lo != 0 else float("inf")
    return pf, float(net.mean()), int(len(net))

# ---------- exhibits ----------

def breakeven_frontier(costs=(0.30, 0.62, 0.90),
                       geometries=((0.5, 0.5), (1.0, 1.0), (1.5, 0.75))) -> pd.DataFrame:
    """Required win rate w* = (SL + c) / (TP + SL). Exact algebra, no simulation."""
    rows = [(c, tp, sl, (sl + c) / (tp + sl)) for c in costs for tp, sl in geometries]
    return pd.DataFrame(rows, columns=["cost_usd_oz", "tp", "sl", "required_winrate"])


def move_vs_cost(df: pd.DataFrame, cost_usd_oz: float,
                 horizons=(1, 5, 15, 30, 60)) -> pd.DataFrame:
    """Median and p75 |close move| over each horizon vs all-in cost: what fraction
    of the typically-available move the toll booth takes at each holding period."""
    c = df["close"]
    rows = []
    for hz in horizons:
        mv = (c.shift(-hz) - c).abs().dropna()
        med, p75 = float(mv.median()), float(mv.quantile(0.75))
        rows.append((hz, med, p75, cost_usd_oz / med if med > 0 else np.inf))
    return pd.DataFrame(rows, columns=["horizon_min", "median_abs_move",
                                       "p75_abs_move", "cost_over_median_move"])

# ---------- permutation reality check ----------

def permutation_best_of(df: pd.DataFrame, configs: list[dict], counts: list[int],
                        n_perm: int = 200, cost_per_oz: float = 0.62,
                        seed: int = 0) -> np.ndarray:
    """Best-of-K PF distribution under time-randomized entries: for each replicate,
    draw random entry bars (matched count, random sides) per config, take the max
    PF across the K configs. The winning real config must beat the 95th pct."""
    rng = np.random.default_rng(seed)
    n = len(df)
    best = np.empty(n_perm)
    for r in range(n_perm):
        pfs = []
        for cfg, k in zip(configs, counts):
            ev = np.sort(rng.choice(n - cfg["horizon"] - 2, size=k, replace=False))
            sides = rng.choice([-1, 1], size=k)
            t, _ = dollar_barrier(df, ev, sides, cfg["tp"], cfg["sl"], cfg["horizon"])
            pf, _, _ = pf_net(t, cost_per_oz)
            pfs.append(pf)
        best[r] = np.nanmax(pfs)
    return best
