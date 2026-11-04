"""Phase 2 - broad search over TradingView built-in indicators, templates, filters and exits, with the anti-overfit gates.

Cells: XAU / SPY / QQQ x 5m, 15m, 1h on the longest history available (XAU M5 2025-05-29.., SPY/QQQ 5m 57 days,
SPY/QQQ 1h 2 years). Split by time: in-sample first 70%, out-of-sample last 30%. Walk-forward: 6 equal blocks,
train on 2 blocks, test on the next (4 folds); the config with the best TRAIN Sharpe (>= 30 trades) is picked blind.
Search per cell: N_RANDOM configs from the coarse grid, then N_OPTUNA TPE trials that maximise IN-SAMPLE daily Sharpe.
Every trial is logged to results/all_runs.csv.gz (parquet needs pyarrow, which Application Control blocks here).
Ranking: OUT-OF-SAMPLE daily Sharpe, only configs with >= 30 OOS trades.
Top 20 get: buy-and-hold and 200-draw random-entry baselines, deflated Sharpe (all trials counted), 5000-run trade
bootstrap, and a one-step parameter-neighbour stability check. Top 3 also get a 2-D parameter heatmap.
PASS = OOS n>=30, OOS net>0 and PF>=1.2, IS net>0, beats buy-and-hold OOS, beats >=95% of random draws,
deflated Sharpe >= 0.95, and >= 50% of parameter neighbours profitable OOS.
    python src/phase2.py
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy.stats import norm, skew, kurtosis

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import engine  # noqa: E402
import strategies as ST  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
CELLS = [(a, tf) for a in common.ASSETS for tf in (5, 15, 60)]
N_RANDOM, N_OPTUNA, N_RAND_BASE, N_BOOT = 6000, 1500, 200, 5000
IS_FRAC, BLOCKS, MIN_N = 0.7, 6, 30


def windows(D):
    t = D["t"]; N = len(t)
    split = int(t[int(IS_FRAC * N)])
    edges = [int(t[int(k * N / BLOCKS)]) for k in range(BLOCKS)] + [int(t[-1]) + 1]
    return split, edges


def daily_sharpe(tr, D, t0, t1):
    m = engine.metrics(tr, D, t0, t1)
    return m


def evaluate(cfg, D, C, split, edges):
    r = ST.build(cfg, D, C)
    if r is None:
        return None
    tr = engine.simulate(D, r[0], r[1], ST.exit_spec(cfg), engine.COST[D["asset"]], D["atr14"])
    row = {"cfg": json.dumps(cfg, sort_keys=True)}
    for tag, a, b in (("is", None, split), ("oos", split, None)):
        m = engine.metrics(tr, D, a, b)
        for k in ("n", "net", "pf", "win", "sharpe", "maxdd", "exp", "tp_rate"):
            row[f"{tag}_{k}"] = m.get(k, np.nan)
    for i in range(2, BLOCKS):
        mt = engine.metrics(tr, D, edges[i - 2], edges[i])
        ms = engine.metrics(tr, D, edges[i], edges[i + 1])
        row[f"wf{i}_tr_sh"], row[f"wf{i}_tr_n"] = mt.get("sharpe", np.nan), mt.get("n", 0)
        row[f"wf{i}_te_net"], row[f"wf{i}_te_n"] = ms.get("net", 0.0), ms.get("n", 0)
    return row


def run_cell(args):
    asset, tf = args
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    D = common.dataset(asset, tf, "long"); C = {}
    split, edges = windows(D)
    rows, seen = [], set()

    def add(cfg, phase):
        key = json.dumps(cfg, sort_keys=True)
        if key in seen:
            return None
        seen.add(key)
        r = evaluate(cfg, D, C, split, edges)
        if r is not None:
            r.update(asset=asset, tf=tf, phase=phase); rows.append(r)
        return r

    rng = np.random.default_rng(abs(hash((asset, tf))) % 2**32)
    for _ in range(N_RANDOM):
        add(ST.make_config(lambda n, o: o[rng.integers(len(o))], asset), "grid")

    def objective(trial):
        cfg = ST.make_config(trial.suggest_categorical, asset)
        r = add(cfg, "optuna")
        if r is None:
            key = json.dumps(cfg, sort_keys=True)
            r = next((x for x in rows if x["cfg"] == key), None)
        if r is None or not r["is_n"] or r["is_n"] < MIN_N or not np.isfinite(r["is_sharpe"]):
            return -5.0
        return float(r["is_sharpe"])

    st = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=7))
    st.optimize(objective, n_trials=N_OPTUNA)
    print(f"  cell {asset} {tf}m: {len(rows)} configs, IS/OOS split {pd.to_datetime(split, unit='s')}", flush=True)
    return rows


# ------------------------------------------------------------------------------------------- analysis
def dsr(daily, n_trials, var_sr):
    """Deflated Sharpe ratio (Bailey & Lopez de Prado 2014), per-day Sharpe."""
    d = np.asarray(daily, float)
    if len(d) < 3 or d.std(ddof=1) == 0:
        return np.nan
    sr = d.mean() / d.std(ddof=1); T = len(d)
    g = 0.5772156649
    sr0 = np.sqrt(var_sr) * ((1 - g) * norm.ppf(1 - 1 / n_trials) + g * norm.ppf(1 - 1 / (n_trials * np.e)))
    den = np.sqrt(max(1 - skew(d) * sr + (kurtosis(d, fisher=False) - 1) / 4 * sr * sr, 1e-12))
    return float(norm.cdf((sr - sr0) * np.sqrt(T - 1) / den))


def daily_pnl(tr, D, t0):
    msk = D["t"] >= t0
    sess = np.unique(D["sid"][msk]); out = np.zeros(len(sess))
    sub = engine.subset(tr, D, t0, None)
    if len(sub["pnl"]):
        ix = np.searchsorted(sess, D["sid"][sub["x"]]); np.add.at(out, ix, sub["pnl"])
    return out


def neighbours(cfg, asset):
    for k in ST.NUMERIC:
        if k not in cfg:
            continue
        g = ST.grid_of(k, asset)
        if not g or cfg[k] not in g:
            continue
        i = g.index(cfg[k])
        for j in (i - 1, i + 1):
            if 0 <= j < len(g):
                yield k, dict(cfg, **{k: g[j]})


def analyse(df):
    ok = df[df.oos_n >= MIN_N].copy()
    var_sr = float(np.nanvar(ok.oos_sharpe / np.sqrt(252)))
    n_trials = len(df)
    top = ok.sort_values("oos_sharpe", ascending=False).head(20)
    details, recs = {}, []
    Ds = {}
    for rank, (_, r) in enumerate(top.iterrows(), 1):
        asset, tf = r.asset, int(r.tf)
        if (asset, tf) not in Ds:
            D = common.dataset(asset, tf, "long"); Ds[(asset, tf)] = (D, {}, *windows(D))
        D, C, split, edges = Ds[(asset, tf)]
        cfg = json.loads(r.cfg); ex = ST.exit_spec(cfg); cost = engine.COST[asset]
        L, S = ST.build(cfg, D, C)
        tr = engine.simulate(D, L, S, ex, cost, D["atr14"])
        m_oos = engine.metrics(tr, D, split, None); m_is = engine.metrics(tr, D, None, split)
        i0 = int(np.searchsorted(D["t"], split))
        bh = float(D["c"][-1] - D["o"][i0])
        rng = np.random.default_rng(rank)
        nL, nS = int(L.sum()), int(S.sum())
        rnet = np.array([engine.subset(engine.simulate(D, *common.random_masks(rng, D, nL, nS, None), ex, cost, D["atr14"]),
                                       D, split, None)["pnl"].sum() for _ in range(N_RAND_BASE)])
        p = engine.subset(tr, D, split, None)["pnl"]
        bs = rng.choice(p, size=(N_BOOT, len(p)), replace=True)
        cs = np.cumsum(bs, 1); dd = (np.maximum.accumulate(np.concatenate([np.zeros((N_BOOT, 1)), cs], 1), 1)[:, 1:] - cs).max(1)
        d = dsr(daily_pnl(tr, D, split), n_trials, var_sr)
        nb = []
        for k, c2 in neighbours(cfg, asset):
            rr = ST.build(c2, D, C)
            if rr is None:
                continue
            t2 = engine.simulate(D, rr[0], rr[1], ST.exit_spec(c2), cost, D["atr14"])
            nb.append((k, c2[k], engine.metrics(t2, D, split, None).get("net", 0.0)))
        stab = float(np.mean([x[2] > 0 for x in nb])) if nb else np.nan
        passed = bool(m_oos["n"] >= MIN_N and m_oos["net"] > 0 and m_oos["pf"] >= 1.2 and m_is.get("net", -1) > 0
                      and m_oos["net"] > bh and (rnet < m_oos["net"]).mean() >= 0.95 and (d or 0) >= 0.95 and (stab or 0) >= 0.5)
        rec = dict(rank=rank, asset=asset, tf=tf, phase=r.phase, cfg=r.cfg, **{f"oos_{k}": v for k, v in m_oos.items()},
                   is_net=m_is.get("net"), is_pf=m_is.get("pf"), is_sharpe=m_is.get("sharpe"), is_n=m_is.get("n"),
                   bh_oos=bh, rand_median=float(np.median(rnet)), rand_p95=float(np.percentile(rnet, 95)),
                   beats_rand=float((rnet < m_oos["net"]).mean()), dsr=d, stability=stab, n_neighbours=len(nb),
                   mc_net_p5=float(np.percentile(bs.sum(1), 5)), mc_net_p50=float(np.percentile(bs.sum(1), 50)),
                   mc_net_p95=float(np.percentile(bs.sum(1), 95)), mc_dd_p50=float(np.percentile(dd, 50)),
                   mc_dd_p95=float(np.percentile(dd, 95)), robust_score=float(m_oos["sharpe"] * (stab if stab == stab else 0)),
                   PASS=passed)
        recs.append(rec)
        allp = tr["pnl"]; te = D["t"][tr["e"]]
        details[rank] = dict(t=[int(x) for x in te], cum=np.cumsum(allp).round(3).tolist(), split=split,
                             neighbours=[(k, v if not isinstance(v, (np.floating,)) else float(v), round(float(n), 3)) for k, v, n in nb])
        if rank <= 3:
            num = [k for k in ST.NUMERIC if k in cfg and ST.grid_of(k, asset)]
            pair = (num + [None, None])[:2]
            if pair[1] is not None:
                gx, gy = ST.grid_of(pair[0], asset), ST.grid_of(pair[1], asset)
                Z = []
                for vy in gy:
                    rowz = []
                    for vx in gx:
                        c2 = dict(cfg, **{pair[0]: vx, pair[1]: vy}); rr = ST.build(c2, D, C)
                        t2 = engine.simulate(D, rr[0], rr[1], ST.exit_spec(c2), cost, D["atr14"]) if rr else None
                        rowz.append(round(float(engine.metrics(t2, D, split, None).get("net", 0.0)), 3) if t2 else None)
                    Z.append(rowz)
                details[rank]["heat"] = dict(x=pair[0], y=pair[1], xs=gx, ys=gy, z=Z)
        print(f"  #{rank} {asset} {tf}m OOS n{m_oos['n']} net {m_oos['net']:+.2f} PF {m_oos['pf']:.2f} sharpe {m_oos['sharpe']:.2f} | "
              f"beats rand {rec['beats_rand']:.0%} DSR {d:.2f} stab {stab:.2f} -> {'PASS' if passed else 'fail'}", flush=True)
    return pd.DataFrame(recs), details, n_trials


def walk_forward(df):
    out = []
    for (asset, tf), g in df.groupby(["asset", "tf"]):
        tot, folds = 0.0, []
        for i in range(2, BLOCKS):
            el = g[(g[f"wf{i}_tr_n"] >= MIN_N) & np.isfinite(g[f"wf{i}_tr_sh"])]
            if not len(el):
                folds.append(None); continue
            best = el.loc[el[f"wf{i}_tr_sh"].idxmax()]
            folds.append(round(float(best[f"wf{i}_te_net"]), 3)); tot += float(best[f"wf{i}_te_net"])
        out.append(dict(asset=asset, tf=tf, wf_test_net=round(tot, 3), folds=folds, configs=len(g)))
    return pd.DataFrame(out)


def main():
    t = time.time()
    with Pool(len(CELLS)) as p:
        rows = [r for rs in p.imap_unordered(run_cell, CELLS) for r in rs]
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "all_runs.csv.gz"), index=False)
    print(f"\nPHASE 2 search: {len(df)} configurations tested in {time.time() - t:.0f}s; "
          f"{(df.oos_n >= MIN_N).sum()} have >= {MIN_N} OOS trades")
    print("\nOOS-profitable share by template (>= 30 OOS trades):")
    ok = df[df.oos_n >= MIN_N]
    print(ok.assign(tmpl=ok.cfg.map(lambda s: json.loads(s)["template"])).groupby("tmpl").apply(
        lambda g: pd.Series(dict(n=len(g), oos_profitable=(g.oos_net > 0).mean(), is_profitable=(g.is_net > 0).mean(),
                                 median_oos_net=g.oos_net.median()))).round(3).to_string())
    print("\nIS vs OOS rank correlation (Spearman, per cell):")
    for (a, tf), g in ok.groupby(["asset", "tf"]):
        print(f"  {a} {tf}m: {g.is_sharpe.corr(g.oos_sharpe, method='spearman'):+.2f} (n {len(g)})")
    wf = walk_forward(df); wf.to_csv(os.path.join(OUT, "phase2_walkforward.csv"), index=False)
    print("\nWalk-forward (best-train config picked blind each fold, summed test P&L per unit):\n" + wf.to_string(index=False))
    print("\nTop 20 by OOS Sharpe:")
    top, details, n_trials = analyse(df)
    top.to_csv(os.path.join(OUT, "phase2_top20.csv"), index=False)
    json.dump(dict(details=details, n_trials=n_trials), open(os.path.join(OUT, "phase2_details.json"), "w"))
    print(f"\nPASS: {int(top.PASS.sum())} of 20 | trials counted for DSR: {n_trials} | done in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
