"""Variant B grid on IS+VAL: every session x level type x filter x stop x RR."""
import itertools
import sys
import time

import numpy as np
import pandas as pd

from . import sessions as S
from . import variant_a as A
from . import variant_b as B
from .common import RESULTS, Ctx, config, split_of
from .metrics import r_stats

CACHE = RESULTS / "cache"


def run(name):
    t0 = time.time()
    g = config()["variant_b"]
    ctx = Ctx(name, tz=S.NY)
    m = ctx.m
    b5, b15, vr5 = ctx.bars(5), ctx.bars(15), ctx.vratio(5)
    dates = B.trading_dates_ny(m)
    split = split_of(dates)
    nd = len(dates)
    rows, S_list, N_list = [], [], []
    for sess_name in g["sessions"]:
        sess = B.build_sessions(m, b15, dates, sess_name, max(g["window"]))
        for lvl, win, vk, buf in itertools.product(g["levels"], g["window"], g["vol_k"], g["buffer_atr"]):
            sc = B.SigB(session=sess_name, level=lvl, window=win, vol_k=vk, buffer_atr=buf)
            sig = B.signals(m, b5, vr5, sess, sc)
            sv = sess.assign(box_hi=sess[f"{lvl}_up"], box_lo=sess[f"{lvl}_dn"])
            for sa, rr in itertools.product(g["stop_atr"], g["rr"]):
                tr = A.evaluate(m, sv, sig, f"atr{sa}", [float(rr)], 1.0, ctx.slip, ctx.comm,
                                max_trades="two")
                base = dict(inst=name, session=sess_name, level=lvl, window=win, vol_k=vk,
                            buffer_atr=buf, stop_atr=sa, rr=rr)
                Sv = np.zeros(nd, np.float32)
                Nv = np.zeros(nd, np.int8)
                if len(tr):
                    R = tr[f"R_{float(rr)}"].values
                    ok = np.isfinite(R)
                    np.add.at(Sv, tr.day.values[ok], R[ok])
                    np.add.at(Nv, tr.day.values[ok], 1)
                    sp = split[tr.day.values]
                    for part in ("IS", "VAL"):
                        base.update({f"{part}_{k}": v for k, v in r_stats(R[(sp == part) & ok]).items()})
                rows.append(base)
                S_list.append(Sv)
                N_list.append(Nv)
            print(f"{name} {sc} {time.time() - t0:.0f}s", flush=True)
    cfg = pd.DataFrame(rows)
    cfg.index.name = "cfg_id"
    cfg.to_csv(RESULTS / f"stage1_B_{name}.csv")
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(CACHE / f"B1_{name}_S.npy", np.vstack(S_list))
    np.save(CACHE / f"B1_{name}_N.npy", np.vstack(N_list))
    pd.Series([str(d) for d in dates]).to_csv(CACHE / f"B1_{name}_dates.csv", index=False)
    print(f"{name}: {len(cfg)} configs in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
