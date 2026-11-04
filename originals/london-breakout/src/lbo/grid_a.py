"""Variant A stage-1 grid on IS+VAL (OOS bars are not even loaded).

For every configuration it stores IS and VAL summary stats at 1x costs, and the daily
R-sum / trade-count vectors used later for heatmaps, walk-forward, deflated Sharpe and
White's Reality Check.
"""
import itertools
import sys
import time

import numpy as np
import pandas as pd

from . import variant_a as A
from .common import RESULTS, Ctx, config, split_of
from .metrics import r_stats

CACHE = RESULTS / "cache"


def signal_configs():
    g = config()["variant_a"]["grid"]
    for box, tf, strong, brk, win in itertools.product(g["box"], g["tf"], g["strong"], g["breakout"], g["window"]):
        yield A.SigA(box=box, tf=tf, strong=strong, breakout=brk, window=win,
                     buffer_atr=config()["variant_a"]["buffer_atr"] if brk == "buffer" else 0.0), g["stop"]
    s = config()["variant_a"]["stop_order_grid"]
    for box, win, buf in itertools.product(s["box"], s["window"], s["buffer_atr"]):
        yield A.SigA(box=box, tf=15, order="stop", breakout="close", window=win, buffer_atr=buf), s["stop"]


def run(name):
    t0 = time.time()
    ctx = Ctx(name)
    m = ctx.m
    rrs = config()["variant_a"]["grid"]["rr"]
    rrs = [float(r) for r in rrs]
    dates = A.trading_dates(m, ctx.tz)
    days_by_box = {b: A.build_days(m, dates, b, 120, ctx.daily) for b in A.S.BOX_RULES}
    split = split_of(dates)
    nd = len(dates)
    rows, S_list, N_list = [], [], []
    for sc, stops in signal_configs():
        days = days_by_box[sc.box]
        sig = A.signals(m, ctx.bars(sc.tf), ctx.vratio(sc.tf), days, sc)
        for st in stops:
            tr = A.evaluate(m, days, sig, st, rrs, 1.0, ctx.slip, ctx.comm)
            for rr in rrs:
                base = dict(inst=name, box=sc.box, tf=sc.tf, order=sc.order, strong=sc.strong,
                            breakout=sc.breakout, buffer_atr=sc.buffer_atr, window=sc.window,
                            stop=st, rr=rr)
                S = np.zeros(nd, np.float32)
                N = np.zeros(nd, np.int8)
                if len(tr):
                    R = tr[f"R_{rr}"].values
                    ok = np.isfinite(R)
                    np.add.at(S, tr.day.values[ok], R[ok])
                    np.add.at(N, tr.day.values[ok], 1)
                    sp = split[tr.day.values]
                    for part in ("IS", "VAL"):
                        st_ = r_stats(R[(sp == part) & ok])
                        base.update({f"{part}_{k}": v for k, v in st_.items()})
                    base["IS_med_risk"] = float(np.median(tr.risk.values)) if len(tr) else np.nan
                rows.append(base)
                S_list.append(S)
                N_list.append(N)
        print(f"{name} {sc} done {time.time() - t0:.0f}s", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    cfg = pd.DataFrame(rows)
    cfg.index.name = "cfg_id"
    cfg.to_csv(RESULTS / f"stage1_A_{name}.csv")
    np.save(CACHE / f"A1_{name}_S.npy", np.vstack(S_list))
    np.save(CACHE / f"A1_{name}_N.npy", np.vstack(N_list))
    pd.Series([str(d) for d in dates]).to_csv(CACHE / f"A1_{name}_dates.csv", index=False)
    print(f"{name}: {len(cfg)} configs in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
