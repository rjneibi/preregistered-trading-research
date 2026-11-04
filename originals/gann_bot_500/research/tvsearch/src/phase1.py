"""Phase 1 - the Instagram strategy, replicated exactly, then stress-tested.

EMA(9, close) crossing VWAP(OHLC4, session anchor) -> long (calls) on cross up, short (puts) on cross down.
Signal on bar close, fill next open. 1D uses a weekly-anchored VWAP (a session VWAP on daily bars is just OHLC4).
Exit variants (the video gives none besides the $5 target):
  a  TP, else the opposite cross (stop-and-reverse)
  b  TP, else flat at end of session
  c  TP, else the opposite cross or end of session, whichever first
TP sweep $0.25 0.5 1 2 3 5 (the video's $5 is the headline). 1 share / 1 oz per trade. Costs: see engine.COST.
Every row also gets buy-and-hold and a 200-draw random-entry baseline (same signal counts, same exits).
    python src/phase1.py
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import engine  # noqa: E402
import ind  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
TPS = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
VARIANTS = {"a": dict(opp=True), "b": dict(eos=True), "c": dict(opp=True, eos=True)}
N_RAND = 200


def signals(D):
    anchor = D["wk"] if D["tf"] == "D" else D["sess"]
    vw, _ = ind.vwap(D["ohlc4"], D["v"], anchor)
    e = ind.ema(D["c"], 9)
    return ind.cross_up(e, vw), ind.cross_dn(e, vw)


def task(args):
    asset, tf, horizon = args
    D = common.dataset(asset, tf, horizon)
    t0, t1 = common.window(D, horizon)
    L, S = signals(D)
    lo = 0 if t0 is None else int(np.searchsorted(D["t"], t0))
    nL, nS = int(L[lo:].sum()), int(S[lo:].sum())
    cost = engine.COST[asset]
    first = lo
    bh = float(D["c"][-1] - D["o"][first] - D["sp"][first] - 2 * cost["slip"])
    rng = np.random.default_rng(hash((asset, str(tf), horizon)) % 2**32)
    rand = [common.random_masks(rng, D, nL, nS, t0) for _ in range(N_RAND)]
    rows = []
    for vname, vx in VARIANTS.items():
        for tp in TPS:
            ex = dict(vx, tp=tp)
            tr = engine.simulate(D, L, S, ex, cost)
            m = engine.metrics(tr, D, t0, t1)
            rnet = []
            for a, b in rand:
                rt = engine.simulate(D, a, b, ex, cost)
                rnet.append(engine.subset(rt, D, t0, t1)["pnl"].sum())
            rnet = np.array(rnet)
            rows.append(dict(asset=asset, tf=str(tf), horizon=horizon, variant=vname, tp=tp, source=D["note"],
                             start=pd.to_datetime(D["t"][lo], unit="s").date(), end=pd.to_datetime(D["t"][-1], unit="s").date(),
                             signals=nL + nS, buy_hold=bh, rand_median=float(np.median(rnet)) if len(rnet) else np.nan,
                             rand_p95=float(np.percentile(rnet, 95)) if len(rnet) else np.nan,
                             beats_rand=float((rnet < m.get("net", -np.inf)).mean()) if len(rnet) else np.nan,
                             opt_est_per_contract=(50.0 * m["net"]) if asset != "XAU" and "net" in m else np.nan, **m))
    return rows


def main():
    t = time.time()
    jobs = [(a, tf, h) for h in ("primary", "long") for a in common.ASSETS for tf in common.TFS]
    with Pool(min(os.cpu_count() or 4, 12)) as p:
        rows = [r for rs in p.imap_unordered(task, jobs) for r in rs]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "phase1_all.csv"), index=False)
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)
    cols = ["asset", "tf", "variant", "tp", "n", "net", "pf", "win", "maxdd", "tp_rate", "buy_hold", "rand_median", "beats_rand"]
    for h in ("primary", "long"):
        d = df[df.horizon == h]
        print(f"\n===== PHASE 1 {h.upper()} - the video's rule (TP $5), ranked by net $ per share/oz =====")
        print(d[d.tp == 5.0].sort_values("net", ascending=False)[cols].head(20).round(3).to_string(index=False))
        print(f"\n----- {h}: best TP of the sweep per asset (any tf/variant) -----")
        print(d.sort_values("net", ascending=False).groupby("asset").head(5)[cols].round(3).to_string(index=False))
        print(f"\n----- {h}: how often the $5 target is actually hit (median over tf/variants) -----")
        print(d[d.tp == 5.0].groupby("asset")[["tp_rate", "n"]].median().round(3).to_string())
    print(f"\nphase 1 done in {time.time() - t:.0f}s, {len(df)} rows -> results/phase1_all.csv")


if __name__ == "__main__":
    main()
