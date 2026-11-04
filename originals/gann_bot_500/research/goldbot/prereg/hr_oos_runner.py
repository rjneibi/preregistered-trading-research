"""HR OOS verdict run (prereg frozen — see HR_PREREGISTRATION.md).

First and only HR computation on post-cutoff data. Thresholds are the
FROZEN IS-calibrated values read from the prereg manifest; ER/regime are
computed over the full H1 series with those thresholds and evaluated ONLY
on post-cutoff trades. All gates on the 1-lot basis per the freeze.
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
MODULES = ROOT / "modules"
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT))

from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.data import load_ohlc, resample_ohlc  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"mod_{name}",
                                                  MODULES / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[f"mod_{name}"] = m
    spec.loader.exec_module(m)
    return m


regime = _load("regime")
START = pd.Timestamp("2015-06-19T00:00:00Z")


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def main() -> int:
    cfg = load_config(ROOT / "config.yaml")
    mcfg = cfg.modules
    manifest = json.loads((RESULTS / "HR_is_manifest.json").read_text())
    th = manifest["thresholds"]
    thr = regime.Thresholds(**th)                 # frozen IS values, verbatim
    cutoff = pd.Timestamp(manifest["is_cutoff"])
    print(f"frozen thresholds {th} | cutoff {cutoff}")

    trades = pd.read_csv(RESULTS / "verdict_trades.csv",
                         parse_dates=["event_ts"])
    oos = trades[trades.event_ts > cutoff].copy()
    print(f"OOS trades: {len(oos)}")

    m1 = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                   data_tz=cfg.data.data_tz,
                   start_utc=START - pd.Timedelta(days=10))
    h1 = resample_ohlc(m1, "1h")
    er = regime.efficiency_ratio(h1["close"], int(mcfg.er_window))
    states = regime.classify_series(er, thr, int(mcfg.confirm_bars))
    state_at_close = pd.Series(states.values, index=h1.index + pd.Timedelta(hours=1))
    oos["regime"] = state_at_close.reindex(oos.event_ts).values
    assert oos.regime.notna().all()

    allowed = list(mcfg.route_pivot_in)
    routed = oos[oos.regime.isin(allowed)]
    res = {
        "n_oos": int(len(oos)), "n_routed": int(len(routed)),
        "unrouted_pf": pf(oos.net_med), "routed_pf": pf(routed.net_med),
        "uplift": pf(routed.net_med) - pf(oos.net_med),
        "routed_pf_p90": pf(routed.net_p90),
        "routed_net": float(routed.net_med.sum()),
        "unrouted_net": float(oos.net_med.sum()),
        "oos_trades_per_state": {k: int(v) for k, v
                                 in oos.regime.value_counts().items()},
        "per_state_pf": {k: pf(g.net_med) for k, g in oos.groupby("regime")},
    }
    gates = {
        "1_routed_oos_pf_ge_1.35": res["routed_pf"] >= 1.35,
        "2_uplift_ge_0.10": res["uplift"] >= 0.10,
        "3_n_routed_ge_70": res["n_routed"] >= 70,
        "4_routed_p90_ge_1.15": res["routed_pf_p90"] >= 1.15,
    }
    ok = all(gates.values())
    verdict = ("HR PASS -> MOMENTUM-only routing earns a shadow-mode slot on "
               "the demo bot (log-only) alongside normal ops gates" if ok else
               "HR FAIL/KILL -> routing overlay closed (the gate working); "
               "sizing-policy redesign remains the open, separate question")
    print(f"unrouted OOS: n={res['n_oos']} PF={res['unrouted_pf']:.3f} "
          f"net=${res['unrouted_net']:,.0f}")
    print(f"routed OOS:   n={res['n_routed']} PF={res['routed_pf']:.3f} "
          f"net=${res['routed_net']:,.0f} p90={res['routed_pf_p90']:.3f} "
          f"uplift={res['uplift']:+.3f}")
    print(f"per-state: {res['oos_trades_per_state']} | PFs "
          f"{ {k: round(v, 3) for k, v in res['per_state_pf'].items()} }")
    print(f"gates: {gates}\n== {verdict} ==")
    (RESULTS / "HR_oos_run.json").write_text(
        json.dumps({**res, "gates": gates, "pass": ok}, indent=1, default=str))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  HR OOS VERDICT: {verdict}\n")
        for k, v in gates.items():
            f.write(f"            HR gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            routed PF {res['routed_pf']:.3f} vs unrouted "
                f"{res['unrouted_pf']:.3f} (uplift {res['uplift']:+.3f}), "
                f"n={res['n_routed']}/{res['n_oos']}, p90 "
                f"{res['routed_pf_p90']:.3f}; predictions Claude FAIL/KILL, "
                f"Rashed PASS\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
