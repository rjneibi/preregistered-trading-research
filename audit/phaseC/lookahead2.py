"""Truncation lookahead tests for the index, crypto and TradingView signals. Same method and same positive-control idea as Phase B.
The compare window runs to the last visible row: stopping one row short made a one-bar peek invisible and the control caught that.

The control here wraps one clean rule and adds a deliberate one-bar peek, so the harness must flag it.
lbo has its own replay-equivalence test and crt_fvg its truncation tests; both ran in the existing suites and are not repeated.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(HERE, "..", "_copy", "rs_recorded", "research"))
TV = os.path.abspath(os.path.join(HERE, "..", "_copy", "tvsearch", "src"))
sys.path[:0] = [SB + "/cross_market", SB + "/tune1", TV]
rng = np.random.default_rng(20261031)
rep = {}


def cmpmask(f, n, cuts, warm=0):
    """f(k) returns a boolean mask for the first k rows. A row the truncated run can see must keep its value."""
    full = f(n)
    bad, tot = [], 0
    for k in cuts:
        k = int(k)
        a, b = full[warm:k], f(k)[warm:k]
        tot += int(a.sum())
        if not np.array_equal(a, b):
            bad.append(dict(cut=k, differ=int((a != b).sum())))
    return dict(cuts=len(cuts), signals_compared=tot, cuts_differing=len(bad), clean=not bad, example=bad[:2])


def swing():
    import swing_lab as S
    d0, sp = S.prep("US500")
    n = len(d0)
    cuts = np.sort(rng.integers(600, n - 2, 30))
    raw = d0[["o", "h", "l", "c", "sp"]]
    orig = S.X.load

    def prep_at(k):
        S.X.load = lambda sym, tf: (raw.iloc[:k].copy(), sp)
        try:
            return S.prep("US500")[0]
        finally:
            S.X.load = orig

    for name in S.RULES:
        def f(k, name=name):
            d = prep_at(k)
            return np.nan_to_num(S.rule(name, d)[1].astype(float)).astype(bool)
        rep[f"swing_lab {name} entry"] = cmpmask(f, n, cuts, 252)

    def control(k):
        m = np.nan_to_num(S.rule("MR2", prep_at(k))[1].astype(float)).astype(bool)
        return np.r_[m[1:], False]
    rep["CONTROL swing_lab MR2 with one-bar peek"] = cmpmask(control, n, cuts, 252)
    # the exit condition of MR1 and MR2 at each row, from closed data only
    for name in ("MR1", "MR2"):
        def fx(k, name=name):
            d = prep_at(k)
            ex = S.rule(name, d)[2]
            return np.array([bool(ex(j - 1, j)) for j in range(253, len(d))])
        rep[f"swing_lab {name} exit"] = cmpmask(lambda k: np.r_[np.zeros(253, bool), fx(k)], n, cuts[:10], 253)


def tune():
    import tune_dip as T
    z = T.load("US500")[0]
    n = len(z)
    cuts = np.sort(rng.integers(600, n - 2, 20))
    sp0 = T.load("US500")[1]
    orig = T.load
    for key, cfg in (("live_rsi2", ("rsi2", 10)), ("live_ibs", ("ibs", 0.2)), ("F1_stretch", ("stretch", 1.0)), ("F2_rsi2ibs", ("rsi2ibs", (20, 0.2))), ("F3_down3", ("down", 3))):
        def f(k, cfg=cfg):
            T.load = lambda s: (z.iloc[:k].copy(), sp0)
            try:
                return T.entry_mask(T.prep("US500")["F"], cfg)
            finally:
                T.load = orig
        rep[f"tune_dip {key}"] = cmpmask(f, n, cuts, 252)


def crypto():
    import edge_lab as E
    cl = E.crypto_close()
    n = len(cl)
    cuts = np.sort(rng.integers(300, n - 2, 20))

    def f(k):
        c = cl.iloc[:k]
        m = c.rolling(50).mean()
        return np.nan_to_num((c > m).astype(float).where(m.notna()).values)[:, :].astype(bool).ravel(order="F")
    full = (cl > cl.rolling(50).mean()).astype(float).where(cl.rolling(50).mean().notna())
    bad = 0
    tot = 0
    for k in cuts:
        k = int(k)
        c = cl.iloc[:k]
        m = c.rolling(50).mean()
        s = (c > m).astype(float).where(m.notna())
        a, b = full.iloc[:k].values, s.iloc[:k].values
        tot += int(np.nansum(a))
        bad += int(not np.array_equal(np.nan_to_num(a, nan=-1), np.nan_to_num(b, nan=-1)))
    rep["edge_lab F6 signal"] = dict(cuts=len(cuts), signals_compared=tot, cuts_differing=bad, clean=bad == 0)


def tv():
    import common as K
    import strategies as ST
    for asset, tf, hz in (("XAU", 15, "long"), ("SPY", 60, "long")):
        D = K.dataset(asset, tf, hz)
        n = len(D["c"]) if isinstance(D, dict) and "c" in D else None
        if n is None:
            rep[f"tvsearch {asset} {tf}"] = dict(error="unknown dataset shape", keys=str(type(D)))
            continue
        r2 = np.random.default_rng(5)
        cfgs, tries = [], 0
        while len(cfgs) < 40 and tries < 400:
            tries += 1
            cfgs.append(ST.make_config(lambda nm, o: o[r2.integers(len(o))], asset))
        cuts = np.sort(rng.integers(n // 2, n - 3, 6))
        bad, tot, err = [], 0, 0
        for c in cfgs:
            try:
                L, S = ST.build(c, D, {})[:2]
            except Exception:
                err += 1
                continue
            for k in cuts:
                k = int(k)
                Dk = {a: (v[:k] if isinstance(v, np.ndarray) and len(v) == n else v) for a, v in D.items()}
                try:
                    L2, S2 = ST.build(c, Dk, {})[:2]
                except Exception:
                    err += 1
                    continue
                tot += int(L[:k].sum() + S[:k].sum())
                if not (np.array_equal(L[:k], L2[:k]) and np.array_equal(S[:k], S2[:k])):
                    bad.append(dict(tpl=c.get("template"), sys=c.get("sys"), mean=c.get("kind"), cut=k, cfg={a: b for a, b in c.items()}))
        rep[f"tvsearch {asset} {tf}m"] = dict(configs=len(cfgs), cuts=len(cuts), signals_compared=tot, differing=len(bad), errors=err, clean=not bad, example=bad[:4])


for fn in (swing, tune, crypto, tv):
    try:
        fn()
    except Exception as e:
        import traceback
        rep[fn.__name__ + " ERROR"] = traceback.format_exc()[-600:]
for k, v in rep.items():
    print(k, str(v)[:300])
json.dump(rep, open(os.path.join(HERE, "lookahead2.json"), "w"), indent=1, default=str)
