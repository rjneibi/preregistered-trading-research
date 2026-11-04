"""Build the per-year x UTC-hour cost matrix from all available XAUUSD ticks.

Schema verified against bi5_downloader.py output (DECISIONS.log 2026-07-06):
columns timestamp,askPrice,bidPrice with epoch-ms UTC timestamps — the pack's
time/bid/ask + time_unit="ms" defaults are overridden accordingly.

Excludes: .suspect quarantined months, files < 10 KB (failed downloads), and
files modified in the last 15 minutes (the resumed downloader writes into the
same directory; a partially-written month must not enter the matrix).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from cost_matrix import CostMatrix, build_matrix, save_matrix  # noqa: E402

DL = HERE.parents[2] / "fable-backtesting" / "download"
OUT = HERE.parent / "results" / "cost_matrix.json"


def main() -> int:
    cutoff = time.time() - 15 * 60
    files = sorted(
        f for f in list(DL.glob("xauusd-bi5-*.csv")) + list(DL.glob("xauusd-tick-*.csv"))
        if f.stat().st_size > 10_000 and f.stat().st_mtime < cutoff
    )
    print(f"{len(files)} tick files (excluded: <10KB, .suspect, "
          f"modified <15min ago):")
    for f in files:
        print(f"  {f.name}  {f.stat().st_size / 1e6:,.1f} MB")

    t0 = time.time()
    m = build_matrix(files, time_col="timestamp", bid_col="bidPrice",
                     ask_col="askPrice", time_unit="ms")
    OUT.parent.mkdir(exist_ok=True)
    save_matrix(m, OUT)
    print(f"\nmatrix built in {time.time() - t0:,.0f}s -> {OUT}")

    cm = CostMatrix(m)
    print("\n== coverage ==")
    print(cm.coverage_report())

    print("\n== flags (pinned: n < 10,000 or missing hours) ==")
    flagged = 0
    for y, hs in sorted(m["years"].items()):
        missing = [h for h in range(24) if str(h) not in hs]
        thin = {h: v["n"] for h, v in hs.items() if v["n"] < 10_000}
        if missing or thin:
            flagged += 1
            print(f"  {y}: missing hours {missing or 'none'}; "
                  f"thin buckets {thin or 'none'}")
    covered = sorted(m["years"])
    all_years = [str(y) for y in range(2015, 2027)]
    absent = [y for y in all_years if y not in covered]
    print(f"\nyears covered: {covered}")
    print(f"years ABSENT (fallback to global — logged deviation): {absent}")
    if not flagged and not absent:
        print("no flags")

    print("\n== per-year median/p90 spread ($/oz) ==")
    for y in covered:
        hs = m["years"][y]
        import numpy as np
        meds = [v["median"] for v in hs.values()]
        p90s = [v["p90"] for v in hs.values()]
        print(f"  {y}: hour-median range {min(meds):.3f}-{max(meds):.3f}, "
              f"hour-p90 range {min(p90s):.3f}-{max(p90s):.3f}")
    g = m["fallback"]["_global"]
    print(f"  global fallback: median {g['median']:.3f}, p90 {g['p90']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
