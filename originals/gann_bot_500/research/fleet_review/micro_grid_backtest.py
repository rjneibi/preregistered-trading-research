"""FR-M — Micro pyramiding grid backtest at SPEC size (prereg a87b81e, verbatim).

Entry stream: research/dr_backtest/trades_D.jsonl (Micro gates = D gates).
Grid sim on M1 per FR_PREREGISTRATION.md; matrix costs; 5 pinned variants.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
GOLDBOT = REPO / "research" / "goldbot"
sys.path.insert(0, str(GOLDBOT))
sys.path.insert(0, str(GOLDBOT / "prereg"))

from goldbot.data import load_ohlc  # noqa: E402
from cost_matrix import CostMatrix  # noqa: E402

M1_PATH = REPO / "research" / "data" / "xauusd_m1_histdata.csv"
EVENTS = REPO / "research" / "dr_backtest" / "trades_D.jsonl"
MATRIX = GOLDBOT / "results" / "cost_matrix.json"
OUT = HERE / "FR_M_results.json"
DECISIONS = GOLDBOT / "results" / "DECISIONS.log"

TRANCHES = [5, 10, 20, 30, 35]
LOT = 0.10
TIMER_S = 600
USD_PER_OZ_PER_01LOT = 10.0          # 0.1 lot = 10 oz

VARIANTS = {
    "M0_baseline":  dict(zone_filter=None, grid_sl_atr=None, tp_mode="fixed"),
    "M1_r3s3_only": dict(zone_filter={"R3", "S3"}, grid_sl_atr=None, tp_mode="fixed"),
    "M2_grid_sl":   dict(zone_filter=None, grid_sl_atr=1.0, tp_mode="fixed"),
    "M3_atr_tp":    dict(zone_filter=None, grid_sl_atr=None, tp_mode="atr"),
    "M4_combo":     dict(zone_filter={"R3", "S3"}, grid_sl_atr=1.0, tp_mode="atr"),
}


def pf(x: np.ndarray) -> float:
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def simulate_zone(o, h, l, c, t, i0, idx_t, side, atr, tp_usd, grid_sl_atr,
                  spread_fn, hours, years):
    """One zone through the tranche grid. Returns (net_usd, n_trades,
    n_tranches_reached, status)."""
    s = side
    entry1 = o[i0]
    grid_sl = entry1 - s * grid_sl_atr * atr if grid_sl_atr else None
    k = 0                       # tranche index
    j = i0
    open_entry = entry1
    gross = 0.0
    cost = 0.0
    n_trades = 0
    reached = 1
    size = TRANCHES[0]
    n_trades += size
    cost += size * (2 * spread_fn(years[i0], hours[i0]) * USD_PER_OZ_PER_01LOT
                    + 0.70)
    status = "timer"
    while j <= idx_t:
        hi, lo, op = h[j], l[j], o[j]
        # pessimistic order: grid SL first
        if grid_sl is not None and ((lo <= grid_sl) if s > 0 else (hi >= grid_sl)):
            fill = op if ((op <= grid_sl) if s > 0 else (op >= grid_sl)) else grid_sl
            gross += size * USD_PER_OZ_PER_01LOT * s * (fill - open_entry)
            status = "grid_sl"
            return gross - cost, n_trades, reached, status
        if j == idx_t:
            gross += size * USD_PER_OZ_PER_01LOT * s * (c[idx_t] - open_entry)
            status = "timer"
            return gross - cost, n_trades, reached, status
        hit_tp = (hi >= open_entry + tp_usd) if s > 0 else (lo <= open_entry - tp_usd)
        if hit_tp:
            gross += size * USD_PER_OZ_PER_01LOT * tp_usd
            k += 1
            if k >= len(TRANCHES):
                return gross - cost, n_trades, reached, "complete"
            j += 1                                  # next tranche at NEXT bar open
            if j > idx_t:
                return gross - cost, n_trades, reached, "complete_last"
            size = TRANCHES[k]
            open_entry = o[j]
            reached = k + 1
            n_trades += size
            cost += size * (2 * spread_fn(years[j], hours[j])
                            * USD_PER_OZ_PER_01LOT + 0.70)
            continue
        j += 1
    return gross - cost, n_trades, reached, status


def main() -> int:
    events = [json.loads(x) for x in EVENTS.read_text().splitlines() if x.strip()]
    print(f"{len(events)} D-gate entry events loaded")
    cm = CostMatrix.load(MATRIX, stat="median", k_slip=0.5)
    cell = {}

    def spread_fn(y, hh):
        key = (y, hh)
        if key not in cell:
            cell[key] = cm.spread_usd(pd.Timestamp(year=y, month=1, day=1,
                                                   hour=hh, tz="UTC").replace(year=y))
        return cell[key]

    # NOTE: cm.spread_usd only uses .year/.hour, so the dummy date is safe.
    print("loading M1 ...", flush=True)
    m1 = load_ohlc(M1_PATH, start_utc=pd.Timestamp("2021-06-01T00:00:00Z"))
    o = m1["open"].to_numpy(float); h = m1["high"].to_numpy(float)
    l = m1["low"].to_numpy(float); c = m1["close"].to_numpy(float)
    t = m1.index.values
    hours = m1.index.hour.to_numpy()
    years = m1.index.year.to_numpy()

    results = {}
    for name, v in VARIANTS.items():
        rows = []
        for ev in events:
            if v["zone_filter"] and ev["zone_source"] not in v["zone_filter"]:
                continue
            ts = pd.Timestamp(ev["entry_ts"]).tz_convert("UTC").tz_localize(None)
            i0 = int(t.searchsorted(ts.to_datetime64()))
            if i0 >= len(t) - 2:
                continue
            idx_t = int(t.searchsorted((ts + pd.Timedelta(seconds=TIMER_S))
                                       .to_datetime64(), side="right")) - 1
            idx_t = max(idx_t, i0)
            side = 1 if ev["direction"] == "BUY" else -1
            atr = float(ev["atr"])
            tp_usd = 1.00 if v["tp_mode"] == "fixed" else max(0.30 * atr, 0.40)
            net, n_tr, reached, status = simulate_zone(
                o, h, l, c, t, i0, idx_t, side, atr, tp_usd,
                v["grid_sl_atr"], spread_fn, hours, years)
            rows.append({"ts": str(ev["entry_ts"]), "zone": ev["zone_source"],
                         "net": net, "n_trades": n_tr, "reached": reached,
                         "status": status})
        df = pd.DataFrame(rows)
        if df.empty:
            results[name] = {"n": 0}
            print(f"{name}: no events after filter")
            continue
        net = df["net"].to_numpy()
        cut = int(len(df) * 0.70)
        cum = np.cumsum(net)
        res = {
            "n_zones": len(df), "zone_wr": float((net > 0).mean()),
            "net_usd": float(net.sum()), "pf": pf(net),
            "oos_pf": pf(net[cut:]), "oos_n": int(len(net) - cut),
            "is_pf": pf(net[:cut]),
            "worst_zone": float(net.min()), "best_zone": float(net.max()),
            "maxdd": float((np.maximum.accumulate(cum) - cum).max()),
            "avg_trades_per_zone": float(df["n_trades"].mean()),
            "status_mix": {k: int(v_) for k, v_
                           in df["status"].value_counts().items()},
            "gates": {},
        }
        res["gates"] = {
            "1_full_pf_ge_1.20": res["pf"] >= 1.20,
            "2_oos_pf_ge_1.00": res["oos_pf"] >= 1.00,
            "3_worst_zone_ge_-5000": res["worst_zone"] >= -5000.0,
            "4_n_ge_300": res["n_zones"] >= 300,
        }
        res["pass"] = all(res["gates"].values())
        results[name] = res
        print(f"{name}: n={res['n_zones']} zoneWR={res['zone_wr']:.1%} "
              f"net=${res['net_usd']:,.0f} PF={res['pf']:.3f} "
              f"OOS={res['oos_pf']:.3f} worst=${res['worst_zone']:,.0f} "
              f"maxDD=${res['maxdd']:,.0f} status={res['status_mix']} "
              f"{'PASS' if res['pass'] else 'FAIL'}")

    any_pass = any(r.get("pass") for r in results.values())
    verdict = ("FR-M PASS: " + ", ".join(k for k, r in results.items()
                                         if r.get("pass"))
               if any_pass else
               "FR-M ALL VARIANTS FAIL -> recommend RETIRE Micro (operator confirms)")
    print(f"\n== {verdict} ==")
    OUT.write_text(json.dumps(results, indent=1, default=str))
    with open(DECISIONS, "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  FR-M VERDICT (prereg a87b81e): "
                f"{verdict}\n")
        for k, r in results.items():
            if r.get("n_zones"):
                f.write(f"            {k}: n={r['n_zones']} "
                        f"PF={r['pf']:.3f} OOS={r['oos_pf']:.3f} "
                        f"net=${r['net_usd']:,.0f} "
                        f"worst=${r['worst_zone']:,.0f} "
                        f"{'PASS' if r['pass'] else 'FAIL'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
