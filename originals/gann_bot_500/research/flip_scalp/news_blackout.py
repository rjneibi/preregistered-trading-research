"""
STATUS: RESEARCH-ONLY (2026-07-02). Round 3b — news-calendar blackout.

Data: ALFRED release dates (St. Louis Fed) in calendar/*.csv (xlsx content):
  fomc = FOMC Press Release (statement days, 14:00 ET)
  cpi  = Consumer Price Index (08:30 ET)
  nfp  = Employment Situation (08:30 ET)

Pre-registered rule: skip entries whose UTC calendar date is a release date
(day-level blackout, no intraday tuning). Applied to FINAL_v1 and to the
ADX-gated pyramid, both eras. Effect could go either way a priori — news
volatility both creates flips and resolves them; the data decides.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs                                   # noqa: E402
from research.dr_backtest.data_prep import (                   # noqa: E402
    load_m1, resample_ohlc, resample_d1_utc,
)
from innovate_r3s3 import SimX, r3s3_level, stats, OUT          # noqa: E402
from regime_switch import (                                     # noqa: E402
    wilder_adx_d1, regime_at, load_events, P0, ADX_TH,
)

CAL = OUT / "calendar"


def main():
    cal = json.loads((CAL / "news_days.json").read_text())
    days = {pd.Timestamp(d).date() for d in cal["days"]}
    print(f"blackout days: {len(days)}  ({cal['note']})")

    for era in ("new", "old"):
        if era == "new":
            start, end, fname, scale = (pd.Timestamp("2021-06-19T00:00:00Z"),
                                        pd.Timestamp("2026-06-19T17:57:00Z"),
                                        "events.jsonl", False)
        else:
            start, end, fname, scale = (pd.Timestamp("2015-06-19T00:00:00Z"),
                                        pd.Timestamp("2021-06-18T23:59:00Z"),
                                        "events_2015_2021.jsonl", True)
        rfs.BT_START, rfs.BT_END = start, end
        rfs.apply_config()
        m1 = load_m1(start - pd.Timedelta(days=60), end)
        h4 = resample_ohlc(m1, "4h")
        d1 = resample_d1_utc(m1)
        sim = SimX(m1, h4)
        adx = wilder_adx_d1(d1)
        ev = load_events(fname)

        def run_set(events, gated):
            out = []
            for e in events:
                ts = pd.Timestamp(e["entry_ts"])
                k = (e["h4_close"] / P0) if scale else 1.0
                kw = dict(tp=8. * k, sl=12. * k, level=r3s3_level(e))
                if gated:
                    a = regime_at(adx, ts)
                    if np.isfinite(a) and a > ADX_TH:
                        kw["pyramid_at"] = 4. * k
                out.append(sim.run(e, **kw))
            return out

        on_news = [e for e in ev
                   if pd.Timestamp(e["entry_ts"]).date() in days]
        off_news = [e for e in ev
                    if pd.Timestamp(e["entry_ts"]).date() not in days]
        print(f"\n=== era {era}: n={len(ev)}  on news days: {len(on_news)} "
              f"({len(on_news) / len(ev):.0%}) ===")
        rows = [
            stats("FINAL_v1 all", run_set(ev, False)),
            stats("FINAL_v1 blackout (skip news)", run_set(off_news, False)),
            stats("FINAL_v1 news-days-only", run_set(on_news, False)),
            stats("pyr_adx all", run_set(ev, True)),
            stats("pyr_adx blackout", run_set(off_news, True)),
        ]
        print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
