"""SZ verdict run — sizing policies (prereg frozen, SZ_PREREGISTRATION.md).

Four policies over the full 472-trade conviction stream, chronological
equity walk, era-stratified gates. All constants pinned in the prereg;
nothing fitted here.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT))

from goldbot.config import load_config  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"mod_{name}", ROOT / "modules" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[f"mod_{name}"] = m
    spec.loader.exec_module(m)
    return m


sizing = _load("sizing")

CAP = 3.9344          # IS trade-ATR p75 (pinned in prereg)
A0 = 2.8789           # IS trade-ATR median (pinned in prereg)
STOP_MULT = 2.4
START_EQ = 10_000.0


def stop_and_rf(policy: str, atr: float, hivol: bool) -> tuple[float, float]:
    """Return (stop_distance_for_sizing, risk_fraction) per pinned policy."""
    if policy == "B0_flat1pct":
        return STOP_MULT * atr, 0.01
    if policy == "P_regime_tilt":
        return STOP_MULT * atr, (0.01 if hivol else 0.005)
    if policy == "S1_atr_cap":
        return STOP_MULT * min(atr, CAP), 0.01
    if policy == "S2_sqrt":
        return STOP_MULT * float(np.sqrt(atr * A0)), 0.01
    raise ValueError(policy)


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def walk(trades: pd.DataFrame, policy: str, spec) -> pd.DataFrame:
    eq = START_EQ
    rows = []
    for r in trades.sort_values("event_ts").itertuples():
        stop, rf = stop_and_rf(policy, float(r.atr), bool(r.hivol))
        lots = sizing.position_size(eq, rf, stop, spec)
        if lots == 0.0:
            continue
        pnl = float(r.net_med) * lots
        rows.append({"event_ts": r.event_ts, "era": r.era, "pnl": pnl})
        eq += pnl
    return pd.DataFrame(rows)


def era_stats(walked: pd.DataFrame, era: str) -> dict:
    p = walked[walked.era == era].pnl
    cum = p.cumsum()
    mdd = float((cum.cummax() - cum).max()) if len(p) else float("nan")
    net = float(p.sum())
    return {"n": int(len(p)), "pf": pf(p), "net": round(net, 2),
            "maxdd": round(mdd, 2),
            "ratio": round(net / mdd, 3) if mdd and mdd > 0 else float("inf")}


def main() -> int:
    cfg = load_config(ROOT / "config.yaml")
    ss = cfg.modules.sizing.symbol_spec
    spec = sizing.SymbolSpec(ss.tick_size, ss.tick_value, ss.volume_step,
                             ss.volume_min, ss.volume_max)
    trades = pd.read_csv(RESULTS / "verdict_trades.csv",
                         parse_dates=["event_ts"])
    onelot = {e: pf(trades[trades.era == e].net_med) for e in ("old", "new")}
    print(f"1-lot PF reference: old {onelot['old']:.3f} / new {onelot['new']:.3f}")

    out = {}
    for policy in ("B0_flat1pct", "P_regime_tilt", "S1_atr_cap", "S2_sqrt"):
        w = walk(trades, policy, spec)
        out[policy] = {e: era_stats(w, e) for e in ("old", "new")}
        o, n = out[policy]["old"], out[policy]["new"]
        print(f"{policy:>14}: old PF {o['pf']:.3f} net ${o['net']:,.0f} "
              f"DD ${o['maxdd']:,.0f} r {o['ratio']:.2f} | "
              f"new PF {n['pf']:.3f} net ${n['net']:,.0f} "
              f"DD ${n['maxdd']:,.0f} r {n['ratio']:.2f}")

    b, p = out["B0_flat1pct"], out["P_regime_tilt"]
    gates = {}
    for e in ("old", "new"):
        gates[f"1_{e}_pf_beats_baseline_+0.05"] = p[e]["pf"] >= b[e]["pf"] + 0.05
        gates[f"2_{e}_inversion_eliminated"] = p[e]["pf"] >= onelot[e] - 0.02
        gates[f"3_{e}_risk_adjusted_not_worse"] = p[e]["ratio"] >= b[e]["ratio"]
    ok = all(gates.values())

    displaced = None
    if ok:
        for s in ("S1_atr_cap", "S2_sqrt"):
            sg = all([out[s][e]["pf"] >= b[e]["pf"] + 0.05 and
                      out[s][e]["pf"] >= onelot[e] - 0.02 and
                      out[s][e]["ratio"] >= b[e]["ratio"] and
                      out[s][e]["pf"] >= p[e]["pf"] + 0.03
                      for e in ("old", "new")])
            if sg:
                displaced = s
    verdict = (("SZ PASS: regime tilt re-validated at measured costs"
                + (f" (displaced by {displaced})" if displaced else ""))
               if ok else
               "SZ FAIL: sizing line closed this cycle; inversion stands as a "
               "known cost of vol-normalized sizing")
    print(f"\ngates: {gates}\n== {verdict} ==")
    (RESULTS / "SZ_run.json").write_text(
        json.dumps({"onelot_pf": onelot, "policies": out, "gates": gates,
                    "pass": bool(ok), "displaced_by": displaced,
                    "verdict": verdict}, indent=1, default=str))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  SZ VERDICT (frozen prereg): "
                f"{verdict}\n")
        for k, v in gates.items():
            f.write(f"            SZ gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            tilt old PF {p['old']['pf']:.3f} vs baseline "
                f"{b['old']['pf']:.3f} (1-lot {onelot['old']:.3f}); new "
                f"{p['new']['pf']:.3f} vs {b['new']['pf']:.3f} "
                f"(1-lot {onelot['new']:.3f}); predictions (BLIND protocol) "
                f"Rashed PASS-high, Claude PASS-medium\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
