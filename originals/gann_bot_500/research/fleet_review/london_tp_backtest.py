"""FR-L — London ICT TP-rescale experiment (prereg a87b81e, verbatim).

Reuses research/ict_london_lab.py's HistData deep feed and the locked engine;
the ONLY change per variant is compute_tp (ATR- or %-scaled instead of
fixed_1500). Gates = the lab's own. Run with py -3.11 (lab imports MT5;
broker feed is NOT used).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "research"))

import ict_london_lab as lab            # noqa: E402
import ict_scalper_london as eng        # noqa: E402

OUT = HERE / "FR_L_results.json"
DECISIONS = REPO / "research" / "goldbot" / "results" / "DECISIONS.log"

VARIANTS = {
    "atr_1.0": lambda s: 1.0 * s.atr_at,
    "atr_1.5": lambda s: 1.5 * s.atr_at,
    "atr_2.0": lambda s: 2.0 * s.atr_at,
    "pct_0.3": lambda s: 0.003 * s.limit,
    "pct_0.5": lambda s: 0.005 * s.limit,
}


def main() -> int:
    print("building HistData deep feed ...", flush=True)
    hm1, hmeta = lab.build_hist_feed()
    print(f"{hm1.n:,} M1 bars, NY {hmeta['t0']:%Y-%m-%d} -> {hmeta['t1']:%Y-%m-%d}")
    h_ctx = eng.build_day_context(hm1)
    spread_price = hmeta["spread_pts"] * lab.POINT
    split = int(hm1.n * eng.IN_SAMPLE_PCT)
    london = lab.SESSIONS[0]
    orig_tp = eng.compute_tp

    results = {}
    # reference first: the locked baseline (already published; printed for context)
    for name in ["fixed_1500_reference"] + list(VARIANTS):
        if name == "fixed_1500_reference":
            eng.compute_tp = orig_tp
        else:
            dist_fn = VARIANTS[name]

            def patched(s, variant, point, _fn=dist_fn):
                d = _fn(s)
                return s.limit + (-d if s.direction == "SELL" else d)

            eng.compute_tp = patched
        res = lab.run_session(hm1, h_ctx, london, spread_price, split)
        checks = {k: bool(v[0]) for k, v in res["checks"].items()}
        gates = {k: checks[k] for k in
                 ("oos_pf>=1.20", "oos_n>=15", "maxdd<=25%", "not_inverted")}
        rec = {
            "n": res["all"]["n"], "wr": res["all"]["win_rate"],
            "pf": res["all"]["pf"], "is_pf": res["is"]["pf"],
            "oos_pf": res["oos"]["pf"], "oos_n": res["oos"]["n"],
            "maxdd_pct": res["maxdd"],
            "net_usd_1lot": res["money"]["net_usd"],
            "gates": gates,
            "pass": all(gates.values()) and name != "fixed_1500_reference",
        }
        results[name] = rec
        print(f"{name:>22}: n={rec['n']} WR={rec['wr']:.1%} PF={rec['pf']:.3f} "
              f"IS/OOS={rec['is_pf']:.2f}/{rec['oos_pf']:.2f} "
              f"(OOS n={rec['oos_n']}) maxDD={rec['maxdd_pct']:.1f}% "
              f"net=${rec['net_usd_1lot']:,.0f} "
              f"{'PASS' if rec['pass'] else 'FAIL' if name != 'fixed_1500_reference' else '(reference)'}",
              flush=True)

    eng.compute_tp = orig_tp
    any_pass = any(r["pass"] for r in results.values())
    verdict = ("FR-L PASS: " + ", ".join(k for k, r in results.items() if r["pass"])
               if any_pass else
               "FR-L ALL VARIANTS FAIL -> recommend RETIRE London line (operator confirms)")
    print(f"\n== {verdict} ==")
    OUT.write_text(json.dumps(results, indent=1, default=str))
    with open(DECISIONS, "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  FR-L VERDICT (prereg a87b81e): {verdict}\n")
        for k, r in results.items():
            f.write(f"            {k}: n={r['n']} WR={r['wr']:.1%} "
                    f"PF={r['pf']:.3f} OOS={r['oos_pf']:.3f} (n={r['oos_n']}) "
                    f"DD={r['maxdd_pct']:.0f}% "
                    f"{'PASS' if r['pass'] else 'FAIL' if 'reference' not in k else 'ref'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
