"""Cost-netted stats with honestly-labeled metrics.

Honesty notes baked into the labels:
  * `sharpe_trade` is PER-TRADE (mean/std of per-trade $), NOT annualized —
    annualizing event-driven trades by sqrt(252) would be fiction;
  * `expectancy_usd` is per 1.0 lot, PRE-leverage;
  * fills are barrier prices (or bar opens on gaps) — an upper bound; demand
    a margin of safety over the printed cost floor.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import clock
from .costs import CostModel
from .cpcv import CombinatorialPurgedCV


def net_trades(trades: pd.DataFrame, cost_model: CostModel,
               regime: str = "realistic") -> pd.DataFrame:
    """Add nights/cost_usd/net_usd columns for one cost regime."""
    t = trades.copy()
    t["nights"] = [clock.nights_held(a, b)
                   for a, b in zip(t["entry_ts"], t["exit_ts"])]
    t["cost_usd"] = [cost_model.round_trip_usd(a, b, regime, nights=n)
                     for a, b, n in zip(t["entry_ts"], t["exit_ts"], t["nights"])]
    t["net_usd"] = t["gross_usd"] - t["cost_usd"]
    return t


def stats(pnl: pd.Series | np.ndarray) -> dict:
    p = pd.Series(pnl, dtype=float).dropna()
    n = len(p)
    if n == 0:
        return {"n": 0, "wins": 0, "losses": 0, "wr": float("nan"),
                "pf": float("nan"), "net_usd": 0.0,
                "expectancy_usd": float("nan"),
                "sharpe_trade": float("nan"), "maxdd_usd": 0.0}
    wins = p[p > 0]
    losses = p[p <= 0]
    gross_w = float(wins.sum())
    gross_l = float(-losses.sum())
    cum = p.cumsum()
    sd = float(p.std(ddof=1)) if n > 1 else float("nan")
    return {
        "n": n, "wins": len(wins), "losses": len(losses),
        "wr": len(wins) / n,
        "pf": gross_w / gross_l if gross_l > 0 else float("inf"),
        "net_usd": float(p.sum()),
        "expectancy_usd": float(p.mean()),
        "sharpe_trade": float(p.mean() / sd) if sd and sd > 0 else float("nan"),
        "maxdd_usd": float((cum.cummax() - cum).max()),
    }


def fmt_stats(s: dict) -> str:
    if s["n"] == 0:
        return "n=0"
    return (f"n={s['n']} wr={s['wr']:.1%} pf={s['pf']:.2f} "
            f"net=${s['net_usd']:,.0f} exp=${s['expectancy_usd']:,.1f}/lot "
            f"sharpe/trade={s['sharpe_trade']:.2f} "
            f"maxDD=${s['maxdd_usd']:,.0f}")


def per_year(trades: pd.DataFrame, col: str = "net_usd") -> pd.DataFrame:
    t = trades.copy()
    t["year"] = pd.to_datetime(t["event_ts"]).dt.year
    rows = [{"year": y, **stats(g[col])} for y, g in t.groupby("year")]
    return pd.DataFrame(rows).set_index("year")


def cpcv_report(trades: pd.DataFrame, splitter: CombinatorialPurgedCV,
                col: str = "net_usd") -> dict:
    """Per-split test-fold stats + per-path aggregation. Phase 1 fits no
    model, so CPCV here measures EDGE STABILITY across purged temporal
    folds — a split's 'test' stats are the rule's performance on that fold
    with its neighborhood purged."""
    labels = trades[["signal_hr"]].rename(columns={"signal_hr": "signal_idx"})
    split_stats = {}
    test_groups = splitter.split_test_groups()
    for train_idx, test_idx, sid in splitter.split(labels):
        split_stats[sid] = {
            "test_groups": test_groups[sid],
            "n_train": len(train_idx),
            **stats(trades.iloc[test_idx][col]),
        }

    # per-path: each path takes each group's fold from a distinct split
    t = labels["signal_idx"].to_numpy()
    bounds = splitter._group_bounds(t)
    path_stats = []
    for k, path in enumerate(splitter.paths()):
        pnl = []
        for g, sid in path.items():
            g_lo, g_hi = bounds[g]
            mask = (t >= g_lo) & (t <= g_hi)
            pnl.append(trades[mask][col])
        p = pd.concat(pnl) if pnl else pd.Series(dtype=float)
        path_stats.append({"path": k, **stats(p)})

    pfs = [s["pf"] for s in split_stats.values() if s["n"] > 0]
    return {
        "splits": split_stats,
        "paths": path_stats,
        "n_splits": len(split_stats),
        "positive_splits": sum(1 for s in split_stats.values()
                               if s["n"] > 0 and s["expectancy_usd"] > 0),
        "median_split_pf": float(np.median(pfs)) if pfs else float("nan"),
        "worst_split_pf": float(np.min(pfs)) if pfs else float("nan"),
    }


def go_no_go(pf_new: float, pf_old: float) -> tuple[bool, str]:
    """The repo's pre-registered gate (STRATEGY_SPECIFICATION.md §9.1):
    realistic-regime PF >= 1.2 on the new era AND >= 1.0 on the old era."""
    ok = pf_new >= 1.2 and pf_old >= 1.0
    verdict = "GO" if ok else "NO-GO"
    return ok, (f"{verdict}: realistic PF new-era={pf_new:.2f} (gate >=1.20), "
                f"old-era={pf_old:.2f} (gate >=1.00)")
