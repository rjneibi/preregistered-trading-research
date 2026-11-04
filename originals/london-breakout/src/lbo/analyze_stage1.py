"""Stage-1 analysis: selection by the frozen rule, marginal effects, heatmaps,
Reality Check / SPA and deflated Sharpe over the whole grid."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from .common import RESULTS, config  # noqa: E402
from .robustness import deflated_sharpe, reality_check  # noqa: E402

CACHE = RESULTS / "cache"
FIG = RESULTS / "figs"
PRIMARY = ("GER40", "UK100")

PARAMS = {
    "A": ["box", "tf", "order", "strong", "breakout", "buffer_atr", "window", "stop", "rr"],
    "B": ["session", "level", "window", "vol_k", "buffer_atr", "stop_atr", "rr"],
}
# ordered dimensions used for "one-step neighbour" plateau scoring
ORDERED = {
    "A": {"tf": [1, 5, 15], "window": [30, 60, 120], "rr": [1.0, 1.5, 2.0, 3.0, 4.0, np.inf],
          "stop": ["candle", "in25", "atr1", "mid", "atr2", "opp"]},
    "B": {"window": [30, 60], "vol_k": [0.0, 1.0, 1.5, 2.0], "stop_atr": [0.5, 1.0, 1.5, 2.0, 3.0],
          "rr": [2.0, 3.0, 4.0], "buffer_atr": [0.0, 0.1]},
}


def load(variant):
    frames = []
    for name in PRIMARY:
        f = pd.read_csv(RESULTS / f"stage1_{variant}_{name}.csv")
        frames.append(f)
    keys = PARAMS[variant]
    a, b = frames
    for f in (a, b):
        f["rr"] = f.rr.astype(float)
    mg = a.merge(b, on=keys, suffixes=("_G", "_U"))
    for part in ("IS", "VAL"):
        nG, nU = mg[f"{part}_n_G"].fillna(0), mg[f"{part}_n_U"].fillna(0)
        eG, eU = mg[f"{part}_exp_G"].fillna(0), mg[f"{part}_exp_U"].fillna(0)
        mg[f"{part}_n"] = nG + nU
        mg[f"{part}_exp"] = (eG * nG + eU * nU) / (nG + nU).replace(0, np.nan)
    return mg, frames


def plateau(mg, variant):
    keys = PARAMS[variant]
    lookup = {tuple(getattr(r, k) for k in keys): r.IS_exp for r in mg[keys + ["IS_exp"]].itertuples(index=False)}
    scores = []
    for r in mg[keys + ["IS_exp"]].itertuples(index=False):
        base = {k: getattr(r, k) for k in keys}
        vals = [r.IS_exp]
        for dim, order in ORDERED[variant].items():
            if base[dim] not in order:
                continue
            i = order.index(base[dim])
            for j in (i - 1, i + 1):
                if 0 <= j < len(order):
                    nb = dict(base)
                    nb[dim] = order[j]
                    v = lookup.get(tuple(nb[k] for k in keys))
                    if v is not None and np.isfinite(v):
                        vals.append(v)
        scores.append(np.nanmean(vals))
    return np.array(scores)


def select(mg, variant):
    mn = config()["min_trades_for_selection"]
    elig = (mg.IS_n_G >= mn) & (mg.IS_n_U >= mn) & (mg.IS_exp_G > 0) & (mg.IS_exp_U > 0)
    mg["plateau"] = plateau(mg, variant)
    cand = mg[elig].sort_values("plateau", ascending=False).head(10)
    ok = cand[(cand.VAL_exp_G > 0) & (cand.VAL_exp_U > 0)]
    if len(ok):
        pick, status = ok.sort_values("VAL_exp", ascending=False).iloc[0], "passed validation screen"
    elif len(cand):
        pick, status = cand.iloc[0], "FAILED validation (best plateau carried forward)"
    else:
        best = mg[(mg.IS_n_G >= mn) & (mg.IS_n_U >= mn)].sort_values("IS_exp", ascending=False)
        pick, status = best.iloc[0], "NO eligible config (IS exp > 0 on both); best pooled IS shown"
    return pick, status, int(elig.sum()), cand


def marginals(mg, variant):
    out = {}
    for k in PARAMS[variant]:
        g = mg.groupby(k)
        out[k] = pd.DataFrame({"IS_exp_mean": g.IS_exp.mean(), "VAL_exp_mean": g.VAL_exp.mean(),
                               "IS_share_pos": g.IS_exp.apply(lambda x: (x > 0).mean()),
                               "IS_n_mean": g.IS_n.mean()})
    return out


def heatmap(mg, variant, fixed, rows, cols, value, fname, title):
    sub = mg
    for k, v in fixed.items():
        sub = sub[sub[k] == v]
    pv = sub.pivot_table(index=rows, columns=cols, values=value, aggfunc="mean")
    fig, ax = plt.subplots(figsize=(1.1 * len(pv.columns) + 2.5, 0.5 * len(pv.index) + 1.8))
    lim = np.nanmax(np.abs(pv.values)) or 0.1
    im = ax.imshow(pv.values, cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    ax.set_xticks(range(len(pv.columns)), [str(c) for c in pv.columns])
    ax.set_yticks(range(len(pv.index)), [str(i) for i in pv.index])
    ax.set_xlabel(cols)
    ax.set_ylabel(rows)
    for i in range(pv.shape[0]):
        for j in range(pv.shape[1]):
            v = pv.values[i, j]
            if np.isfinite(v):
                ax.text(j, i, f"{v:+.3f}", ha="center", va="center", fontsize=8)
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, label="expectancy (R/trade, 1x costs)")
    fig.tight_layout()
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / fname, dpi=110)
    plt.close(fig)
    return pv


def multiple_testing(variant):
    """SPA / RC over every config of both primary instruments (IS days only), DSR for the best."""
    from .common import split_of
    Xs, ids = [], []
    for name in PRIMARY:
        S = np.load(CACHE / f"{variant}1_{name}_S.npy")
        dates = pd.read_csv(CACHE / f"{variant}1_{name}_dates.csv").iloc[:, 0].values
        is_mask = split_of(dates) == "IS"
        Xs.append((name, S[:, is_mask], dates[is_mask]))
    # align the two instruments on common IS dates and pool (sum) daily R per config
    common = sorted(set(Xs[0][2]) & set(Xs[1][2]))
    pooled = 0
    for name, X, d in Xs:
        pos = pd.Index(d).get_indexer(common)
        pooled = pooled + X[:, pos].astype(np.float64)
    rc = reality_check(pooled, B=config()["robustness"]["bootstrap_runs"] // 2, seed=config()["seed"])
    sr = pooled.mean(axis=1) / np.where(pooled.std(axis=1) > 0, pooled.std(axis=1), np.nan)
    best = int(np.nanargmax(sr))
    dsr, sr0, srb = deflated_sharpe(pooled[best], sr, len(sr))
    rc.update(dict(dsr_prob=dsr, dsr_sr0_daily=sr0, best_sr_daily=srb,
                   best_sr_annual=srb * np.sqrt(252), best_cfg_row=best, n_trials=len(sr)))
    return rc, pooled


def run(variant):
    mg, frames = load(variant)
    pick, status, n_elig, cand = select(mg, variant)
    marg = marginals(mg, variant)
    rc, _ = multiple_testing(variant)
    res = dict(variant=variant, n_configs_per_instrument=len(frames[0]), n_configs_total=len(frames[0]) * 2,
               n_eligible=n_elig, status=status,
               pick={k: (v.item() if hasattr(v, "item") else v) for k, v in pick.items()},
               share_IS_pos=float((mg.IS_exp > 0).mean()), share_VAL_pos=float((mg.VAL_exp > 0).mean()),
               corr_IS_VAL=float(mg[["IS_exp", "VAL_exp"]].corr().iloc[0, 1]),
               rc=rc)
    mg.to_csv(RESULTS / f"stage1_{variant}_merged.csv", index=False)
    cand.to_csv(RESULTS / f"stage1_{variant}_top10.csv", index=False)
    with open(RESULTS / f"stage1_{variant}_marginals.md", "w") as f:
        for k, df in marg.items():
            f.write(f"\n### {k}\n\n{df.round(4).to_markdown()}\n")
    json.dump(res, open(RESULTS / f"stage1_{variant}.json", "w"), indent=1, default=str)
    return res, mg, pick


if __name__ == "__main__":
    import sys
    r, _, _ = run(sys.argv[1])
    print(json.dumps(r, indent=1, default=str))
