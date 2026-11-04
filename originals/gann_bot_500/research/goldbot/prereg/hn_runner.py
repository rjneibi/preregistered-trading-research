"""H-N verdict run — news-day edge at measured costs (prereg 56d89dd, verbatim).

Pure subset analysis of the H1-verdict trade set; no simulation, no tuning.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
NEWS = ROOT.parents[1] / "fable-backtesting" / "calendar" / "news_days.json"


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def main() -> int:
    t = pd.read_csv(RESULTS / "verdict_trades.csv", parse_dates=["event_ts"])
    days = set(json.loads(NEWS.read_text())["days"])
    t["news"] = t.event_ts.dt.strftime("%Y-%m-%d").isin(days)
    news, rest = t[t.news], t[~t.news]

    res = {
        "n_news": int(len(news)), "n_rest": int(len(rest)),
        "news_pf_med": pf(news.net_med), "news_pf_p90": pf(news.net_p90),
        "news_pf_old": pf(news[news.era == "old"].net_med),
        "news_pf_new": pf(news[news.era == "new"].net_med),
        "news_wr": float((news.net_med > 0).mean()),
        "news_net": float(news.net_med.sum()),
        "rest_pf_med": pf(rest.net_med),          # descriptive only
        "news_pf_flat": pf(news.net_flat),        # the old evidence basis
    }
    gates = {
        "1_news_pf_ge_1.50_median": res["news_pf_med"] >= 1.50,
        "2_news_pf_ge_1.20_p90": res["news_pf_p90"] >= 1.20,
        "3_each_era_ge_1.10": (res["news_pf_old"] >= 1.10
                               and res["news_pf_new"] >= 1.10),
        "4_n_ge_60": res["n_news"] >= 60,
    }
    ok = all(gates.values())
    verdict = ("H-N PASS: 1.5x news sizing stands, cost-validated" if ok else
               "H-N FAIL -> remove the 1.5x news multiplier from flip_bot "
               "(operator-confirmed live change)")
    print(f"news trades n={res['n_news']} WR={res['news_wr']:.1%} "
          f"net=${res['news_net']:,.0f}")
    print(f"PF: flat {res['news_pf_flat']:.2f} | median {res['news_pf_med']:.2f} "
          f"| p90 {res['news_pf_p90']:.2f} | old {res['news_pf_old']:.2f} "
          f"| new {res['news_pf_new']:.2f} | non-news median "
          f"{res['rest_pf_med']:.2f}")
    print(f"gates: {gates}\n== {verdict} ==")
    (RESULTS / "HN_run.json").write_text(json.dumps({**res, "gates": gates,
                                                     "pass": ok}, indent=1))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  H-N VERDICT (prereg 56d89dd): "
                f"{verdict}\n            n={res['n_news']}, PF flat "
                f"{res['news_pf_flat']:.2f} -> median {res['news_pf_med']:.2f} "
                f"-> p90 {res['news_pf_p90']:.2f}; eras "
                f"{res['news_pf_old']:.2f}/{res['news_pf_new']:.2f}; "
                f"predictions Claude MARGINAL, Rashed FAIL\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
