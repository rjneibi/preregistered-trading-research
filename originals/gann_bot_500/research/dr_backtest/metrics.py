"""
Standard entry-edge metrics + validation flags.
"""
from __future__ import annotations
from typing import Optional


def basic_stats(pnl_pts: list[float]) -> dict:
    n = len(pnl_pts)
    if n == 0:
        return {"n": 0, "win_rate": None, "avg_pts": None, "total_pts": 0.0,
                "avg_win": None, "avg_loss": None, "pf": None, "expectancy": None,
                "max_drawdown_pts": 0.0}
    wins = [x for x in pnl_pts if x > 0]
    losses = [x for x in pnl_pts if x < 0]
    total = sum(pnl_pts)
    win_sum = sum(wins)
    loss_sum = -sum(losses)
    if loss_sum == 0:
        pf: Optional[float] = float("inf") if win_sum > 0 else None
    else:
        pf = round(win_sum / loss_sum, 3)
    avg_win = round(win_sum / len(wins), 1) if wins else None
    avg_loss = round(-loss_sum / len(losses), 1) if losses else None
    # equity-curve max drawdown in points
    peak = 0.0; running = 0.0; mdd = 0.0
    for p in pnl_pts:
        running += p
        if running > peak:
            peak = running
        dd = peak - running
        if dd > mdd:
            mdd = dd
    return {
        "n": n,
        "win_rate": round(len(wins) / n, 3),
        "avg_pts": round(total / n, 1),
        "total_pts": round(total, 1),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "pf": pf,
        "expectancy": round(total / n, 1),
        "max_drawdown_pts": round(mdd, 1),
    }


def size_label(n: int) -> str:
    if n < 15:
        return "NO CONCLUSION (n<15)"
    if n < 100:
        return "directional only (n<100)"
    return ""


def validation_flags(stats_is: dict, stats_oos: dict,
                     equity_start_pts: float = 100000.0) -> list[str]:
    """Bars: PF<1.20, DD>25% (of equity_start_pts baseline), inverted IS/OOS."""
    flags = []
    for label, s in [("IS", stats_is), ("OOS", stats_oos)]:
        if s["n"] < 15:
            flags.append(f"{label}: NO CONCLUSION (n<15)")
        elif s["n"] < 100:
            flags.append(f"{label}: directional only (n<100)")
        if s["pf"] is not None and isinstance(s["pf"], (int, float)) and s["pf"] < 1.20:
            flags.append(f"{label}: PF {s['pf']} < 1.20 — no edge threshold")
        dd_frac = s["max_drawdown_pts"] / equity_start_pts
        if dd_frac > 0.25:
            flags.append(f"{label}: DD {dd_frac:.0%} > 25% budget")
    # inverted IS/OOS
    if (stats_is["pf"] is not None and stats_oos["pf"] is not None
            and isinstance(stats_is["pf"], (int, float))
            and isinstance(stats_oos["pf"], (int, float))
            and stats_is["pf"] > 1.20 and stats_oos["pf"] < 1.00):
        flags.append("REJECT: IS PF > 1.20 but OOS PF < 1.00 (regime dependency)")
    return flags
