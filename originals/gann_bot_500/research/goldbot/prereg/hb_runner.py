"""H-B verdict run — arm B (FINAL_v3 H4) solo (prereg a734cd7, verbatim).

Usage: hb_runner.py [--tag preliminary|binding]
Rebuilds arm B via the identical hp_runner implementation against whatever
cost matrix currently exists; evaluates the stiffened gates incl. the
UNSEEN dimensions (purged splits, p90 stress).
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
from goldbot.cpcv import CombinatorialPurgedCV  # noqa: E402
from goldbot.data import load_ohlc  # noqa: E402
from cost_matrix import CostMatrix  # noqa: E402
from hp_runner import build_arm_b  # noqa: E402

RESULTS = ROOT / "results"


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def main() -> int:
    tag = "binding" if "--tag" in sys.argv and "binding" in sys.argv else "preliminary"
    cfg = load_config(ROOT / "config.yaml")
    cm_med = CostMatrix.load(RESULTS / "cost_matrix.json", stat="median",
                             k_slip=0.5, commission_per_lot_rt=7.0)
    cm_p90 = CostMatrix.load(RESULTS / "cost_matrix.json", stat="p90",
                             k_slip=0.5, commission_per_lot_rt=7.0)
    print(f"H-B {tag.upper()} run | matrix years: "
          f"{sorted(cm_med.m['years'])}", flush=True)
    m1_full = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                        data_tz=cfg.data.data_tz)
    b = build_arm_b(cfg, m1_full, cm_med, cm_p90)

    old = b[b.era == "old"]; new = b[b.era == "new"]
    exps, err = [], ""
    cv = CombinatorialPurgedCV(n_groups=6, k_test=2, tau_max=24,
                               embargo=24, l_feature_max=40)
    labels = b[["signal_hr"]].rename(columns={"signal_hr": "signal_idx"})
    try:
        for _, test_idx, _sid in cv.split(labels):
            exps.append(round(float(b.iloc[test_idx].net_med.mean()), 2))
    except RuntimeError as e:
        err = f"COLLAPSED: {e}"
    n_pos = sum(1 for x in exps if x > 0)

    res = {
        "tag": tag, "matrix_years": sorted(cm_med.m["years"]),
        "n": int(len(b)), "wr": float((b.net_med > 0).mean()),
        "pf": pf(b.net_med), "pf_old": pf(old.net_med), "pf_new": pf(new.net_med),
        "pf_p90": pf(b.net_p90), "pf_p90_old": pf(old.net_p90),
        "net": float(b.net_med.sum()), "pf_flat": pf(b.net_flat),
        "splits_positive": n_pos, "split_expectancies": exps, "split_error": err,
    }
    gates = {
        "1_full_pf_ge_1.35": res["pf"] >= 1.35,
        "2_each_era_ge_1.00": res["pf_old"] >= 1.00 and res["pf_new"] >= 1.00,
        "3_splits_ge_11of15": (not err) and n_pos >= 11,
        "4_p90_full_ge_1.15_and_old_ge_0.90": (res["pf_p90"] >= 1.15
                                               and res["pf_p90_old"] >= 0.90),
        "5_n_ge_300": res["n"] >= 300,
    }
    ok = all(gates.values())
    if tag == "preliminary":
        verdict = ("H-B preliminary PASS (PROVISIONAL — confers nothing; "
                   "binding run on full coverage decides)" if ok else
                   "H-B preliminary FAIL (decisive: survives the optimistic "
                   "cost bias a fortiori) -> arm B solo CLOSED")
    else:
        verdict = ("H-B binding PASS -> arm B is a second-magic demo "
                   "forward-test candidate (round-11 A/B plan)" if ok else
                   "H-B binding FAIL -> arm B solo CLOSED")
    print(f"n={res['n']} WR={res['wr']:.1%} PF={res['pf']:.3f} "
          f"(old {res['pf_old']:.3f} / new {res['pf_new']:.3f}) "
          f"p90 {res['pf_p90']:.3f} (old {res['pf_p90_old']:.3f}) "
          f"net ${res['net']:,.0f} flat-ref {res['pf_flat']:.3f}")
    print(f"splits: {n_pos}/15 positive {err}\n  {exps}")
    print(f"gates: {gates}\n== {verdict} ==")
    out_path = RESULTS / f"HB_run_{tag}.json"
    out_path.write_text(json.dumps({**res, "gates": gates, "pass": ok},
                                   indent=1))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  H-B {tag.upper()} VERDICT "
                f"(prereg a734cd7, matrix years {res['matrix_years']}): "
                f"{verdict}\n")
        for k, v in gates.items():
            f.write(f"            H-B gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            PF {res['pf']:.3f} (old {res['pf_old']:.3f} / "
                f"new {res['pf_new']:.3f}), p90 {res['pf_p90']:.3f} "
                f"(old {res['pf_p90_old']:.3f}), splits {n_pos}/15, "
                f"n={res['n']}; predictions Claude PASS-lean, Rashed FAIL\n")
    print(f"-> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
