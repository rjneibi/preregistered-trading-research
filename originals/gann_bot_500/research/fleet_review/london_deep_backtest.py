"""London deep backtest — the deployed config (verbatim engine) over the full
16.5-year HistData M1 history. Fresh run of the canonical test; descriptive,
reproduces/updates the archived NO-GO record."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "research"))

import ict_london_lab as lab            # noqa: E402
import ict_scalper_london as eng        # noqa: E402


def main() -> int:
    print("building HistData deep feed (5.77M bars) ...", flush=True)
    hm1, hmeta = lab.build_hist_feed()
    print(f"window: NY {hmeta['t0']:%Y-%m-%d} -> {hmeta['t1']:%Y-%m-%d} "
          f"({(hmeta['t1']-hmeta['t0']).days/365.25:.1f}y)")
    ctx = eng.build_day_context(hm1)
    res = lab.run_session(hm1, ctx, lab.SESSIONS[0],
                          hmeta["spread_pts"] * lab.POINT,
                          split_idx=int(hm1.n * eng.IN_SAMPLE_PCT))
    a, i, o = res["all"], res["is"], res["oos"]
    print(f"\nsetups: {res['n_setups']:,} | filled trades: {a['n']}")
    print(f"FULL: WR {a['win_rate']:.1f}%  PF {a['pf']:.3f}  "
          f"net ${res['money']['net_usd']:+,.0f} @1 lot  "
          f"maxDD {res['maxdd']:.1f}%")
    print(f"IS (first 70%): n={i['n']} WR {i['win_rate']:.1f}% PF {i['pf']:.3f}")
    print(f"OOS (last 30%): n={o['n']} WR {o['win_rate']:.1f}% PF {o['pf']:.3f}")
    print("\nper-year (n, PF):")
    for y, (n, p) in res["year_pf"].items():
        bar = "#" * min(40, int(p * 10))
        print(f"  {y}: n={n:>3}  PF {p:5.2f}  {bar}")
    print(f"\nlab gates: {res['checks']}")
    print(f"VERDICT: {res['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
