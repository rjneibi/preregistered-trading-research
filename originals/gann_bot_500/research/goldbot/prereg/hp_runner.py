"""H-P verdict run — two-arm portfolio at measured costs (prereg 56d89dd, verbatim).

Arm A = the H1-verdict conviction trades (loaded from verdict_trades.csv).
Arm B = FINAL_v3 published spec, generated fresh: H4-close R3/S3 breakout,
skip Monday, closes at 12/16/20 UTC only, max 1 trade/day, TP 1.4xATR /
SL 2.1xATR / 24h, no bail, gap_open. Portfolio = both arms + daily -$1,500
realized-loss breaker (round-12 rule). Costs: H1-verdict wiring.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr  # noqa: E402
from goldbot.events import generate_events_base  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402
from cost_matrix import CostMatrix  # noqa: E402

RESULTS = ROOT / "results"
ERAS = {"old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                pd.Timestamp("2021-06-18T23:59:00Z")),
        "new": (pd.Timestamp("2021-06-19T00:00:00Z"), None)}
WARMUP = pd.Timedelta(days=100)
BREAKER_USD = -1500.0


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def build_arm_b(cfg, m1_full, cm_med, cm_p90):
    data_end = m1_full.index[-1]
    out = []
    for era, (start, end) in ERAS.items():
        end = end or data_end
        m1 = m1_full[(m1_full.index >= start - WARMUP) & (m1_full.index <= end)]
        h1 = resample_ohlc(m1, "1h")
        h4 = resample_ohlc(m1, "4h")
        d1 = resample_d1_utc(m1)
        atr_h1 = wilder_atr(h1, 14)
        ev = generate_events_base(h4, d1, atr_h1, h1.index, cfg, start, end)
        ev = ev[ev.event_ts.dt.hour.isin([12, 16, 20])]          # v3 session lock
        ev = ev.groupby(ev.event_ts.dt.normalize()).head(1)      # max 1 trade/day
        tr = run_exits(m1, ev, k_tp_atr=1.4, k_sl_atr=2.1, time_stop_h=24,
                       fill_mode="gap_open", bail_enabled=False)
        tr["era"] = era
        out.append(tr)
    b = pd.concat(out, ignore_index=True)
    b["cost_med"] = [cm_med.trade_cost_usd(a, x) for a, x
                     in zip(b.entry_ts, b.exit_ts)]
    b["cost_p90"] = [cm_p90.trade_cost_usd(a, x) for a, x
                     in zip(b.entry_ts, b.exit_ts)]
    b["net_med"] = b.gross_usd - b.cost_med
    b["net_p90"] = b.gross_usd - b.cost_p90
    b["net_flat"] = b.gross_usd - 20.0
    return b


def portfolio_with_breaker(all_tr: pd.DataFrame, col: str):
    """Round-12 breaker: skip a NEW entry if realized (closed) P&L of the
    same UTC day, at that entry moment, is <= -$1,500."""
    t = all_tr.sort_values("event_ts").reset_index(drop=True)
    kept = np.ones(len(t), bool)
    closed = []                                # (exit_ts, day, pnl) of kept trades
    for i, row in t.iterrows():
        day = row.event_ts.normalize()
        realized = sum(p for (x_ts, d, p) in closed
                       if d == day and x_ts <= row.event_ts)
        if realized <= BREAKER_USD:
            kept[i] = False
            continue
        closed.append((row.exit_ts, row.exit_ts.normalize(), row[col]))
    return t[kept], int((~kept).sum())


def main() -> int:
    cfg = load_config(ROOT / "config.yaml")
    cm_med = CostMatrix.load(RESULTS / "cost_matrix.json", stat="median",
                             k_slip=0.5, commission_per_lot_rt=7.0)
    cm_p90 = CostMatrix.load(RESULTS / "cost_matrix.json", stat="p90",
                             k_slip=0.5, commission_per_lot_rt=7.0)
    a = pd.read_csv(RESULTS / "verdict_trades.csv",
                    parse_dates=["event_ts", "entry_ts", "exit_ts"])
    a["arm"] = "A_conviction"
    print(f"arm A (conviction): {len(a)} trades, PF med {pf(a.net_med):.3f}")

    print("building arm B (FINAL_v3 H4 arm) ...", flush=True)
    m1_full = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                        data_tz=cfg.data.data_tz)
    b = build_arm_b(cfg, m1_full, cm_med, cm_p90)
    b["arm"] = "B_v3_h4"
    print(f"arm B (v3 H4): {len(b)} trades, PF med {pf(b.net_med):.3f} "
          f"(old {pf(b[b.era=='old'].net_med):.3f} / "
          f"new {pf(b[b.era=='new'].net_med):.3f}, flat {pf(b.net_flat):.3f})")

    cols = ["event_ts", "entry_ts", "exit_ts", "era", "arm",
            "net_med", "net_p90", "net_flat"]
    both = pd.concat([a[cols], b[cols]], ignore_index=True)
    port, n_blocked = portfolio_with_breaker(both, "net_med")
    print(f"portfolio: {len(port)} trades kept, {n_blocked} blocked by breaker")

    res = {
        "arm_a": {"n": len(a), "pf": pf(a.net_med),
                  "net": float(a.net_med.sum())},
        "arm_b": {"n": len(b), "pf": pf(b.net_med),
                  "net": float(b.net_med.sum()),
                  "pf_old": pf(b[b.era == "old"].net_med),
                  "pf_new": pf(b[b.era == "new"].net_med),
                  "pf_flat": pf(b.net_flat)},
        "portfolio": {"n": int(len(port)), "blocked": n_blocked,
                      "pf": pf(port.net_med),
                      "pf_old": pf(port[port.era == "old"].net_med),
                      "pf_new": pf(port[port.era == "new"].net_med),
                      "pf_p90": pf(port.net_p90),
                      "net": float(port.net_med.sum()),
                      "wr": float((port.net_med > 0).mean())},
    }
    ma = a.set_index("event_ts").net_med.resample("ME").sum()
    mb = b.set_index("event_ts").net_med.resample("ME").sum()
    m = pd.concat([ma, mb], axis=1, keys=["a", "b"]).fillna(0.0)
    m = m[(m.a != 0) | (m.b != 0)]
    res["monthly_corr"] = float(m.a.corr(m.b))

    best_single = max(res["arm_a"]["net"], res["arm_b"]["net"])
    gates = {
        "1_portfolio_pf_ge_1.20": res["portfolio"]["pf"] >= 1.20,
        "2_each_era_ge_1.00": (res["portfolio"]["pf_old"] >= 1.00
                               and res["portfolio"]["pf_new"] >= 1.00),
        "3_net_gt_best_single": res["portfolio"]["net"] > best_single,
        "4_monthly_corr_le_0.60": res["monthly_corr"] <= 0.60,
        "5_p90_pf_ge_1.05": res["portfolio"]["pf_p90"] >= 1.05,
    }
    ok = all(gates.values())
    verdict = ("H-P PASS -> portfolio becomes the Phase-2 demo candidate "
               "(subject to H1 confirmation + demo-ops gates)" if ok else
               "H-P FAIL -> conviction solo remains the only line")
    p = res["portfolio"]
    print(f"\nportfolio: PF {p['pf']:.3f} (old {p['pf_old']:.3f} / new "
          f"{p['pf_new']:.3f}, p90 {p['pf_p90']:.3f}) net ${p['net']:,.0f} "
          f"vs best single ${best_single:,.0f}; monthly corr "
          f"{res['monthly_corr']:.2f}")
    print(f"gates: {gates}\n== {verdict} ==")
    (RESULTS / "HP_run.json").write_text(json.dumps({**res, "gates": gates,
                                                     "pass": ok}, indent=1))
    port.to_csv(RESULTS / "HP_portfolio_trades.csv", index=False)
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  H-P VERDICT (prereg 56d89dd): "
                f"{verdict}\n")
        for k, v in gates.items():
            f.write(f"            H-P gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            portfolio PF {p['pf']:.3f} (old {p['pf_old']:.3f}"
                f" / new {p['pf_new']:.3f}, p90 {p['pf_p90']:.3f}), net "
                f"${p['net']:,.0f}, corr {res['monthly_corr']:.2f}, arm B solo "
                f"PF {res['arm_b']['pf']:.3f}; predictions Claude PASS-lean, "
                f"Rashed FAIL\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
