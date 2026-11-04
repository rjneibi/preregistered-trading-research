"""E6 per prereg/E6-PAPER.md. Reads only the `trades` table of the demo journal, in read-only mode. Backtester and exit model come from the sandbox unchanged. Dukascopy M1 replaces HistData for the 2026 window."""
import json
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "_copy", "sb_fable_true"))
sys.path[:0] = [ROOT]
os.chdir(ROOT)
from research.dr_backtest.backtest import Backtester, profile_D, profile_R
from research.dr_backtest.data_prep import resample_d1_utc, resample_ohlc, wilder_atr
from research.dr_backtest.exit_sim import simulate_trade

c = sqlite3.connect("file:@GANN_ROOT@/research/trades.db?mode=ro&immutable=1", uri=True)
J = pd.read_sql_query("select profile,open_time,close_time,direction,entry_price,close_price,closed_by,r_achieved,zone_source from trades", c)
J["t0"] = pd.to_datetime(J.open_time.str.slice(0, 19), utc=True)
J["t1"] = pd.to_datetime(J.close_time.str.slice(0, 19), utc=True)
z = np.load("@LBO_ROOT@/data/m1/XAUUSD.npz")
t = z["t"].astype(np.int64)
t = t * 60 if int(t[0]) < 10**8 else t
m1 = pd.DataFrame({"open": z["o"], "high": z["h"], "low": z["l"], "close": z["c"]}, index=pd.to_datetime(t, unit="s", utc=True))
a, b = J.t0.min().floor("h"), J.t1.max().ceil("h")
m1 = m1[(m1.index >= a - pd.Timedelta(days=120)) & (m1.index <= b + pd.Timedelta(days=5))]
h1, h4, d1 = resample_ohlc(m1, "1h"), resample_ohlc(m1, "4h"), resample_d1_utc(m1)
atr = wilder_atr(h1, 14)
rep = dict(window=[str(a), str(b)], journal_n=len(J), label="INSUFFICIENT SAMPLE" if len(J) < 100 else "ok")
pairs = []
for fn, nm in ((profile_D, "D"), (profile_R, "R")):
    prof = fn()
    es = Backtester(prof, h1, h4, d1, m1, atr, assert_no_leak_every=5000).run(a, b)
    seen, one = set(), []
    for e in sorted(es, key=lambda x: pd.Timestamp(x["entry_ts"])):
        k = (pd.Timestamp(e["entry_ts"]).date(), str(e.get("zone_source", e.get("zone", ""))))
        if k in seen:
            continue
        seen.add(k)
        r = simulate_trade(e["direction"], e["entry_price"], pd.Timestamp(e["entry_ts"]), e["atr"], m1, tp_fixed_points=prof.tp_fixed_points, sl_atr_mult=prof.sl_atr_mult,
                           partial_enabled=prof.partial_enabled, partial_atr_mult=prof.partial_atr_mult)
        one.append(dict(t=pd.Timestamp(e["entry_ts"]), side=e["direction"], px=e["entry_price"], status=r["status"], pts=r["pnl_points"], ex=r["exit_ts_final"], risk=e["atr"] * prof.sl_atr_mult))
    J_ = J[J.profile == nm].sort_values("t0")
    used = set()
    rows = []
    for _, x in J_.iterrows():
        cand = [i for i, y in enumerate(one) if i not in used and y["side"] == x.direction and abs((y["t"] - x.t0).total_seconds()) <= 3600]
        if cand:
            i = min(cand, key=lambda k: abs((one[k]["t"] - x.t0).total_seconds()))
            used.add(i)
            y = one[i]
            rows.append(dict(profile=nm, open=str(x.t0), matched=True, entry_gap_usd=round(float(y["px"] - x.entry_price), 2), minutes=round((y["t"] - x.t0).total_seconds() / 60, 1), bot_exit=x.closed_by, bot_r=x.r_achieved, bt_status=y["status"], bt_pts=round(float(y["pts"]), 1), bt_r=round(float(y["pts"]) / 100 / float(y["risk"]), 3),
                             exit_gap_usd=round(float(y["px"] + (1 if x.direction == "BUY" else -1) * float(y["pts"]) / 100 - x.close_price), 2)))
        else:
            rows.append(dict(profile=nm, open=str(x.t0), matched=False, bot_exit=x.closed_by, bot_r=x.r_achieved))
    pairs += rows
    m = [r for r in rows if r["matched"]]
    rep[nm] = dict(journal=len(J_), backtest_one_per_zone_day=len(one), unthrottled=len(es), matched=len(m), bot_only=len(J_) - len(m), backtest_only=len(one) - len(used),
                   median_abs_entry_gap=round(float(np.median([abs(r["entry_gap_usd"]) for r in m])), 2) if m else None, bot_exit_reasons=J_.closed_by.value_counts().to_dict())
pd.DataFrame(pairs).to_csv(os.path.join(HERE, "e6_pairs.csv"), index=False)
n = rep["D"]["matched"] + rep["R"]["matched"]
rep["match_rate"] = round(n / len(J), 3)
rep["exit_gap_median_abs_usd"] = round(float(pd.DataFrame(pairs).exit_gap_usd.abs().median()), 2)
json.dump(rep, open(os.path.join(HERE, "e6_result.json"), "w"), indent=1, default=str)
print(json.dumps(rep, indent=1, default=str))
