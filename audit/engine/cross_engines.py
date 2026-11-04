"""Same synthetic orders through every engine, zero costs. Differences are engine behaviour, not data."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "..", "_copy")
sys.path[:0] = [HERE, os.path.join(C, "goldbot"), os.path.join(C, "crt_fvg"), os.path.join(C, "lbo", "src"), "@GANN_ROOT@/research/ta_lab"]
from nbe import simulate as nbe
from goldbot.triple_barrier import run_exits
from crt_fvg import engine as crt
from lbo import engine as lbo
import lab
import importlib.util

spec = importlib.util.spec_from_file_location("tvengine", os.path.join(C, "tvsearch", "src", "engine.py"))
tv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tv)

MON = 1736121600  # 2025-01-06 00:00 UTC, a Monday
N = 5000
STEP = 40
SD, TD = 1.0, 1.0


def series(seed, gap_rate):
    r = np.random.default_rng(seed)
    x = 2000 + np.cumsum(r.normal(0, 0.03, N * 8)).reshape(N, 8)
    o, h, l, c = x[:, 0].copy(), x.max(1), x.min(1), x[:, -1].copy()
    if gap_rate:
        jump = (r.random(N) < gap_rate) * r.choice([-1, 1], N) * 1.5
        adj = np.cumsum(jump)
        o, h, l, c = o + adj, h + adj, l + adj, c + adj
    return o, h, l, c


def run_all(o, h, l, c):
    i = np.arange(0, N - 2500, STEP)
    s = np.where(np.arange(len(i)) % 2 == 0, 1, -1)
    d = np.full(len(i), SD)
    t = MON + np.arange(N) * 60
    a = nbe(o, h, l, c, 0.0, i, s, d, d * TD, 1400)
    out = {"nbe": a.pnl}
    idx = pd.DatetimeIndex(pd.to_datetime(t, unit="s"))
    m1 = pd.DataFrame(dict(open=o, high=h, low=l, close=c), index=idx)
    ev = pd.DataFrame(dict(event_ts=idx[i], side=s, atr=1.0, hivol=False))
    out["goldbot"] = run_exits(m1, ev, tp_usd=TD, sl_usd=SD, time_stop_h=24, fill_mode="gap_open")["gross_usd"].to_numpy() / 100
    d0 = dict(t=t, o=o, h=h, l=l, c=c, spread=np.zeros(N))
    orders = [lab.Order(int(k), int(u), float("nan"), float(o[k] - u * SD), 1) for k, u in zip(i, s)]
    out["ta_lab"] = np.array([x["r"] * x["risk"] for x in lab.simulate(d0, orders, exit_mode="tp", tp_r=TD, max_hold=1400, one_at_a_time=False)])
    m = dict(o=o, h=h, l=l, c=c, sp=np.zeros(N))
    out["lbo"] = np.array([lbo.simulate(m, int(k), int(k) + 1400, int(u), float(o[k]), float(o[k] - u * SD), [TD], 0.0, 0.0, 0.0)[0][0] for k, u in zip(i, s)]) * SD
    mc = dict(t=t // 60, o=o, h=h, l=l, c=c, sp=np.zeros(N))
    sig = pd.DataFrame(dict(k=i, dir=s, stop=o[i] - s * SD, liq=np.nan))
    out["crt_fvg"] = crt.simulate(mc, sig, TD, dict(tick=0.01, comm=0.0, spread=0.0), dict(slip_ticks=0.0, spread_mode="measured"), 1200, one_open=False)["R"].to_numpy() * SD
    rows = []
    for k, u in zip(i, s):
        Dd = dict(N=N, o=o, h=h, l=l, c=c, sp=np.zeros(N), sid=np.zeros(N, int), sess_last=np.full(N, N - 1))
        L = np.zeros(N, bool)
        S = np.zeros(N, bool)
        if k == 0:
            rows.append(np.nan)
            continue
        (L if u > 0 else S)[k - 1] = True
        r = tv.simulate(Dd, L, S, dict(sl=SD, tp=TD, tbars=1400), dict(slip=0.0, comm=0.0))
        rows.append(float(r["pnl"][0]))
    out["tvsearch"] = np.array(rows)
    return out


def main():
    rep = {}
    for name, gap in (("smooth", 0.0), ("gapped", 0.01)):
        tot = {}
        for seed in range(5):
            o, h, l, c = series(seed, gap)
            r = run_all(o, h, l, c)
            base = r["nbe"]
            for k, v in r.items():
                if k == "nbe":
                    continue
                m = min(len(v), len(base))
                ok = ~np.isnan(v[:m])
                dv = np.abs(v[:m][ok] - base[:m][ok])
                t = tot.setdefault(k, dict(n=0, differ=0, max_abs=0.0, sum_engine=0.0, sum_nbe=0.0, len_mismatch=0))
                t["n"] += int(ok.sum())
                t["differ"] += int((dv > 1e-9).sum())
                t["max_abs"] = max(t["max_abs"], float(dv.max()) if len(dv) else 0.0)
                t["sum_engine"] += float(v[:m][ok].sum())
                t["sum_nbe"] += float(base[:m][ok].sum())
                t["len_mismatch"] += int(len(v) != len(base))
        rep[name] = tot
        print(name, json.dumps(tot, indent=0))
    json.dump(rep, open(os.path.join(HERE, "..", "infrastructure", "cross_engines.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
