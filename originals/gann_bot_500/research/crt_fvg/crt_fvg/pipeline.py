"""CRT-FVG-1 stages. grid: 108 configs on IS-truncated data only -> select: frozen picks written
and hashed -> full: every config on all data (the OOS opening, once) + cost/spread variants and
direction flips for the picks -> analyse: tables, twin, MC, prop, WFO -> report."""
import hashlib
import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from .data import load_m1, truncate
from .engine import simulate
from .rules import _hhmm, signals

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
CFG = yaml.safe_load(open(ROOT / "config.yaml"))
SYMS = list(CFG["symbols"])
TFS = CFG["rules"]["entry_tfs"]
TPS = CFG["rules"]["tp_modes"]
KEEP = ["t_entry", "t_exit", "dir", "entry", "stop", "target", "exit", "risk", "R", "why", "k"]


def tp_name(tp):
    return "liq" if tp == "liq" else f"{tp:g}R"


def configs():
    g = CFG["validation"]["grid"]
    keys = list(g)
    return [dict(zip(keys, v)) for v in itertools.product(*(g[k] for k in keys))]


DEFAULT_CID = next(i for i, c in enumerate(configs())
                   if all(CFG["rules"][k] == v for k, v in c.items()))


def load(sym):
    return load_m1(CFG["data"]["npz_dir"], sym, CFG["data"]["start"], CFG["data"]["end"])


def split_minute(m):
    t0, t1 = int(m["t"][0]), int(m["t"][-1]) + 1
    return t0, t0 + int(CFG["validation"]["is_frac"] * (t1 - t0)), t1


def _sim(m, sig, tp, sym, mult=1.0, spread_mode=None, one_open=True):
    costs = dict(CFG["costs"], spread_mode=spread_mode or CFG["costs"]["spread_mode"])
    return simulate(m, sig, tp, CFG["symbols"][sym], costs, _hhmm(CFG["rules"]["friday_exit_utc"]),
                    mult, one_open)[KEEP]


def run_grid(sym, is_only):
    m = load(sym)
    t0, ts, t1 = split_minute(m)
    if is_only:
        m = truncate(m, ts)
    cache, out, sigs = {}, [], {}
    for tf in TFS:
        for cid, c in enumerate(configs()):
            sig = signals(m, dict(CFG["rules"], **c), tf, cache)
            sigs[(tf, cid)] = sig
            for tp in TPS:
                tr = _sim(m, sig, tp, sym)
                tr["sym"], tr["tf"], tr["cid"], tr["tp"] = sym, tf, cid, tp_name(tp)
                out.append(tr)
    return pd.concat(out, ignore_index=True), sigs, (t0, ts, t1), m


def _grid_job(sym):
    tr, _, span, _ = run_grid(sym, is_only=True)
    tr.to_pickle(RES / f"grid_IS_{sym}.pkl")
    return sym, span, len(tr)


def stage_grid():
    RES.mkdir(exist_ok=True)
    spans = {}
    with ProcessPoolExecutor(max_workers=4) as ex:
        for sym, span, n in ex.map(_grid_job, SYMS):
            spans[sym] = span
            print("grid IS", sym, n, "trade rows", flush=True)
    json.dump(spans, open(RES / "spans.json", "w"), indent=1)


def stage_select():
    """Pooled pick per (tf, tp) by IS avg R, every symbol >= min_is_trades; also per-symbol picks."""
    g = pd.concat([pd.read_pickle(RES / f"grid_IS_{s}.pkl") for s in SYMS], ignore_index=True)
    mn = CFG["validation"]["min_is_trades"]
    sel = {"pooled": {}, "per_symbol": {}, "default_cid": DEFAULT_CID, "n_configs": len(configs()),
           "backtests": len(configs()) * len(TFS) * len(TPS) * len(SYMS)}
    for (tf, tp), d in g.groupby(["tf", "tp"]):
        cnt = d.groupby(["cid", "sym"]).size().unstack(fill_value=0).reindex(columns=SYMS, fill_value=0)
        elig = cnt.index[(cnt >= mn).all(axis=1)]
        st = d[d.cid.isin(elig)].groupby("cid").R.agg(["mean", "size"])
        if len(st):
            best = st.sort_values(["mean", "size"], ascending=False).index[0]
            sel["pooled"][f"{tf}|{tp}"] = dict(cid=int(best), is_avgR=float(st.loc[best, "mean"]),
                                               is_n=int(st.loc[best, "size"]), eligible=int(len(st)), fallback=False)
        else:
            sel["pooled"][f"{tf}|{tp}"] = dict(cid=DEFAULT_CID, eligible=0, fallback=True)
        for s in SYMS:
            ds = d[d.sym == s].groupby("cid").R.agg(["mean", "size"])
            ds = ds[ds["size"] >= mn]
            sel["per_symbol"][f"{s}|{tf}|{tp}"] = (int(ds.sort_values(["mean", "size"], ascending=False).index[0])
                                                   if len(ds) else None)
    sel["configs"] = configs()
    p = RES / "selection.json"
    json.dump(sel, open(p, "w"), indent=1)
    print("selection frozen sha256", hashlib.sha256(p.read_bytes()).hexdigest()[:12])


def _full_job(sym):
    sel = json.load(open(RES / "selection.json"))
    tr, sigs, span, m = run_grid(sym, is_only=False)
    tr.to_pickle(RES / f"grid_FULL_{sym}.pkl")
    picks = {(int(k.split("|")[0]), k.split("|")[1], v["cid"]) for k, v in sel["pooled"].items()}
    picks |= {(tf, tp, DEFAULT_CID) for tf in TFS for tp in map(tp_name, TPS)}
    extra = []
    for tf, tpn, cid in picks:
        tp = "liq" if tpn == "liq" else float(tpn[:-1])
        sig = sigs[(tf, cid)]
        for var, kw in (("x0", dict(mult=0.0)), ("x2", dict(mult=2.0)), ("measured", dict(spread_mode="measured"))):
            t = _sim(m, sig, tp, sym, **kw)
            t["var"] = var
            extra.append(t.assign(sym=sym, tf=tf, cid=cid, tp=tpn))
        # direction flip of exactly the trades taken at 1x (same entry bar, mirrored stop/target)
        base = _sim(m, sig, tp, sym)
        s2 = sig[sig.k.isin(base.k)].copy()
        o = m["o"][s2.k.values]
        s2["dir"], s2["stop"], s2["liq"] = -s2.dir, 2 * o - s2.stop, 2 * o - s2.liq
        f = _sim(m, s2, tp, sym, one_open=False)[["k", "R"]].rename(columns={"R": "R_flip"})
        f0 = _sim(m, s2, tp, sym, mult=0.0, one_open=False)[["k", "R"]].rename(columns={"R": "R_flip_x0"})
        extra.append(base.merge(f, on="k", how="left").merge(f0, on="k", how="left")
                     .assign(var="flip", sym=sym, tf=tf, cid=cid, tp=tpn))
    pd.concat(extra, ignore_index=True).to_pickle(RES / f"variants_{sym}.pkl")
    return sym, len(tr)


def stage_full():
    if any((RES / f"grid_FULL_{s}.pkl").exists() for s in SYMS):
        raise SystemExit("OOS already opened; delete results/grid_FULL_*.pkl only with a logged reason")
    with ProcessPoolExecutor(max_workers=4) as ex:
        for sym, n in ex.map(_full_job, SYMS):
            print("full", sym, n, flush=True)
