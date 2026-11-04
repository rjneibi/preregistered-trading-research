"""H1 as frozen (prereg 35deedc), twice: recorded clock, then true UTC. Rules, parameters and costs unchanged."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
GB = os.path.join(HERE, "..", "_copy", "goldbot")
sys.path[:0] = [HERE, GB, os.path.join(GB, "prereg")]
import run_verdict as rv
from clockfix import shifted
from cost_matrix import CostMatrix
from goldbot.config import load_config
from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr
from goldbot.events import generate_events_final
from goldbot.triple_barrier import run_exits

HIST = "@GANN_ROOT@/research/data/xauusd_m1_histdata.csv"
ORIG = "@GANN_ROOT@/research/goldbot/results/verdict_trades.csv"


def to_true_utc(m1):
    """See clockfix.py for the measured rule."""
    secs = m1.index.tz_localize(None).values.astype("datetime64[s]").astype(np.int64)
    fix = shifted(secs)
    out = m1.copy()
    out.index = m1.index - pd.to_timedelta(fix.astype(int), unit="h")
    out = out[~out.index.duplicated()].sort_index()
    return out, float(fix.mean())


def run(m1_full, cfg, cm_med, cm_p90):
    e = cfg.exits.final
    data_end = m1_full.index[-1]
    all_t = []
    for era, (start, end) in rv.ERAS.items():
        end = end or data_end
        m1 = m1_full[(m1_full.index >= start - rv.WARMUP) & (m1_full.index <= end)]
        h1, h4, d1 = resample_ohlc(m1, "1h"), resample_ohlc(m1, "4h"), resample_d1_utc(m1)
        atr_h1 = wilder_atr(h1, e.atr.period)
        ev = generate_events_final(h1, h4, d1, atr_h1, cfg, start, end)
        tr = run_exits(m1, ev, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr, time_stop_h=e.time_stop_h, fill_mode="gap_open", bail_enabled=e.bail.enabled,
                       hivol_half_x=e.bail.hivol_half_x, lovol_bail_h=e.bail.lovol_bail_h, lovol_bail_x=e.bail.lovol_bail_x)
        tr["era"] = era
        all_t.append(tr)
    t = pd.concat(all_t, ignore_index=True)
    t["cost_med"] = [cm_med.trade_cost_usd(a, b) for a, b in zip(t.entry_ts, t.exit_ts)]
    t["cost_p90"] = [cm_p90.trade_cost_usd(a, b) for a, b in zip(t.entry_ts, t.exit_ts)]
    t["net_med"] = t.gross_usd - t.cost_med
    t["net_p90"] = t.gross_usd - t.cost_p90
    return t


def summ(t):
    tbl = rv.era_table(t, "net_med")
    p90 = rv.era_table(t, "net_p90")
    ex, err = rv.split_expectancies(t, "net_med")
    return dict(n=len(t), median=tbl, p90=p90, splits_pos=sum(1 for x in ex if x > 0), split_err=err, by_entry_hour={int(h): dict(n=len(g), pf=round(rv.pf(g.net_p90), 3), net=round(g.net_p90.sum())) for h, g in t.groupby(t.entry_ts.dt.hour)},
                resolution=t.resolution.value_counts().to_dict())


cfg = load_config(os.path.join(GB, "config.yaml"))
M = os.path.join(GB, "results", "cost_matrix.json")
cm_med = CostMatrix.load(M, stat="median", k_slip=0.5, commission_per_lot_rt=7.0)
cm_p90 = CostMatrix.load(M, stat="p90", k_slip=0.5, commission_per_lot_rt=7.0)
m1 = load_ohlc(HIST, data_tz="UTC")
rep = {}
a = run(m1, cfg, cm_med, cm_p90)
rep["recorded_clock"] = summ(a)
o = pd.read_csv(ORIG)
rep["trade_match_vs_verdict_trades_csv"] = dict(orig_n=len(o), rerun_n=len(a), net_med_sum_orig=round(float(o.net_med.sum()), 2), net_med_sum_rerun=round(float(a.net_med.sum()), 2),
                                                 same_gross=bool(len(o) == len(a) and np.allclose(o.gross_usd.values, a.gross_usd.values)))
m2, share = to_true_utc(m1)
rep["share_bars_shifted"] = round(share, 4)
b = run(m2, cfg, cm_med, cm_p90)
rep["true_utc"] = summ(b)
ka = set(zip(a.entry_ts.dt.date, a.side))
kb = set(zip(b.entry_ts.dt.date, b.side))
rep["trades_same_day_side"] = len(ka & kb)
a.to_csv(os.path.join(HERE, "h1_recorded_clock_trades.csv"), index=False)
b.to_csv(os.path.join(HERE, "h1_true_utc_trades.csv"), index=False)
json.dump(rep, open(os.path.join(HERE, "h1_clock.json"), "w"), indent=1, default=str)
print(json.dumps({k: rep[k] for k in ("trade_match_vs_verdict_trades_csv", "share_bars_shifted", "trades_same_day_side")}, default=str))
for k in ("recorded_clock", "true_utc"):
    r = rep[k]
    print(k, r["n"], "splits", r["splits_pos"], r["median"], "\n p90", r["p90"], "\n", r["by_entry_hour"], r["resolution"])
