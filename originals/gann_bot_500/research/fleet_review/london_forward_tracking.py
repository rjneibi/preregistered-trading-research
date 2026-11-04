"""London forward-tracking: replay the DEPLOYED config (verbatim engine)
over the broker's own recent M1 window and report what the detected setups
would have done. Descriptive forward-tracking of the live system — no
variants, no threshold changes, no gates. Read-only.

Also surfaces the fill-mechanics question: the live bot has filled ZERO
orders since deployment; if the simulator fills these same setups, the gap
is ops-relevant (limit-at-FVG-edge fill modeling vs real pendings).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "research"))

import ict_london_lab as lab            # noqa: E402
import ict_scalper_london as eng        # noqa: E402


def main() -> int:
    print("building broker feed (read-only attach) ...", flush=True)
    bm1, bmeta = lab.build_broker_feed()
    print(f"broker M1 window: {bmeta['t0']:%Y-%m-%d} -> {bmeta['t1']:%Y-%m-%d} "
          f"({bm1.n:,} bars, spread {bmeta['spread_pts']:.0f}pt)")
    ctx = eng.build_day_context(bm1)
    spread_price = bmeta["spread_pts"] * lab.POINT
    session = lab.SESSIONS[0]                       # London 02:00-05:00 NY
    res = lab.run_session(bm1, ctx, session, spread_price,
                          split_idx=int(bm1.n * 0.7))
    trades = sorted(res["trades"], key=lambda t: t.fill_idx)
    print(f"\nsetups detected: {res['n_setups']} | simulator-FILLED trades: "
          f"{len(trades)} (live bot filled: 0)")
    cum = 0.0
    for t in trades:
        pts, usd = eng.trade_pnl_usd(t, lab.USD_PER_PT, eng.FIXED_LOT, lab.POINT)
        cum += usd
        s = t.setup
        print(f"  {t.fill_time:%m-%d %H:%M} NY {s.direction} "
              f"entry {t.eff_entry:.2f} sl {s.sl:.2f} tp {t.tp:.2f} "
              f"-> {t.outcome} {pts:+.0f}pts ${usd:+,.0f} (cum ${cum:+,.0f})")
    m = res["all"]
    print(f"\nwindow stats: n={m['n']} WR={m['win_rate']:.1f}% "
          f"PF={m['pf'] if m['pf'] != float('inf') else 'inf'} "
          f"net ${res['money']['net_usd']:+,.0f} @ 1 lot")
    print("(descriptive forward-tracking only — no gates, no verdict; the "
          "16.5y NO-GO and FR-L verdicts stand)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
