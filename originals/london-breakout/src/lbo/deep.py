"""Deep dive on one Variant-A configuration: costs, sizing, breakdowns, baselines,
Monte Carlo, walk-forward, decay, gap table and the section-9 fixes."""
import json
from dataclasses import replace

import numpy as np
import pandas as pd

from . import variant_a as A
from .common import RESULTS, Ctx, config
from .gaps import trade_weak_spots
from .metrics import by_group, full_report, r_stats
from .robustness import (cost_breakeven, mirror_R, monte_carlo, random_direction_test,
                         walk_forward)
from .runner import run_a

PRIMARY = ("GER40", "UK100")
KS = (0.0, 0.5, 1.0, 2.0)


class Setup:
    """One config across instruments, with cached contexts/days so variants are cheap."""

    def __init__(self, sc: A.SigA, stop, rr, insts=PRIMARY, allow_oos=False):
        self.sc, self.stop, self.rr, self.insts = sc, stop, rr, insts
        self.ctx = {n: Ctx(n, allow_oos=allow_oos) for n in insts}
        self.days = {}

    def trades(self, k=1.0, sc=None, stop=None, rr=None, **kw):
        sc = sc or self.sc
        out = []
        for n in self.insts:
            key = (n, sc.box)
            tr, _, d = run_a(n, sc, stop or self.stop, self.rr if rr is None else rr, k=k,
                             ctx=self.ctx[n], days=self.days.get(key), **kw)
            self.days[key] = d
            out.append(tr)
        tr = pd.concat([t for t in out if len(t)], ignore_index=True)
        return tr

    def all_dates(self, split=None):
        ds = set()
        for n in self.insts:
            d = self.days.get((n, self.sc.box))
            if d is not None:
                ds |= set(d.index[d.ok])
        ds = sorted(ds)
        if split:
            from .common import split_of
            ds = [x for x, s in zip(ds, split_of(ds)) if s in split]
        return ds


def stats_table(tr, parts=("IS", "VAL", "IS+VAL")):
    rows = {}
    for p in parts:
        sel = tr[tr.split.isin(p.split("+"))]
        rows[p] = r_stats(sel.R.values)
    return pd.DataFrame(rows).T


def cost_and_sizing(S: Setup, parts=("IS", "VAL")):
    out = {}
    for k in KS:
        tr = S.trades(k=k)
        for p in parts + ("IS+VAL",):
            sel = tr[tr.split.isin(p.split("+"))]
            for risk in config()["risk_fractions"]:
                rep, _, _ = full_report(sel, S.all_dates(p.split("+")), risk=risk)
                out[(k, p, risk)] = rep
    df = pd.DataFrame(out).T
    df.index.names = ["cost_mult", "split", "risk"]
    return df


def breakdowns(tr):
    tr = tr.copy()
    tr["box_quintile"] = pd.cut(tr.width_pct, [-0.01, .2, .4, .6, .8, 1.0], labels=["Q1 narrow", "Q2", "Q3", "Q4", "Q5 wide"])
    tr["vol_regime"] = pd.cut(tr.rv_regime, [0, 0.85, 1.15, 99], labels=["low", "normal", "high"])
    tr["season"] = tr.month.map({12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
                                 6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"})
    return {k: by_group(tr, k) for k in ("year", "dow", "month", "season", "inst", "box_quintile", "vol_regime", "dir")}


def baselines(S: Setup, tr, k=1.0):
    rs = []
    for n in S.insts:
        sub = tr[tr.inst == n]
        if len(sub):
            rs.append(mirror_R(S.ctx[n].m, sub, S.rr, k, S.ctx[n].slip, S.ctx[n].comm))
    Rm = np.concatenate(rs)
    Ra = np.concatenate([tr[tr.inst == n].R.values for n in S.insts])
    return random_direction_test(Ra, Rm, config()["robustness"]["random_baseline_runs"], config()["seed"]), Ra, Rm


def wfo(variant="A"):
    """Walk-forward over the whole stage-1 grid, the two indices pooled per config."""
    from .analyze_stage1 import CACHE
    pooled_S = pooled_N = None
    dates_all = None
    for n in PRIMARY:
        Sm = np.load(CACHE / f"{variant}1_{n}_S.npy")
        Nm = np.load(CACHE / f"{variant}1_{n}_N.npy")
        d = pd.read_csv(CACHE / f"{variant}1_{n}_dates.csv").iloc[:, 0].values
        if dates_all is None:
            dates_all = d
            pooled_S, pooled_N = Sm.astype(np.float64), Nm.astype(np.int32)
        else:
            common = np.intersect1d(dates_all, d)
            i1 = pd.Index(dates_all).get_indexer(common)
            i2 = pd.Index(d).get_indexer(common)
            pooled_S = pooled_S[:, i1] + Sm[:, i2]
            pooled_N = pooled_N[:, i1] + Nm[:, i2]
            dates_all = common
    rc = config()["robustness"]
    r, nn, picks = walk_forward(pooled_S, pooled_N, dates_all, rc["wfo_train_months"], rc["wfo_test_months"], min_trades=60)
    cfg = pd.read_csv(RESULTS / f"stage1_{variant}_GER40.csv")
    for p in picks:
        p["config"] = cfg.iloc[p["cfg"]][[c for c in cfg.columns if c in
                                           ("box", "tf", "order", "strong", "breakout", "window", "stop", "rr",
                                            "session", "level", "vol_k", "stop_atr")]].to_dict()
    return r, nn, picks


def decay(tr):
    y = tr.groupby("year").R.mean()
    yrs = y.index.values.astype(float)
    if len(y) < 3:
        return dict(slope=np.nan)
    # trade-weighted regression of R on year
    X = np.c_[np.ones(len(tr)), tr.year.values.astype(float)]
    beta, *_ = np.linalg.lstsq(X, tr.R.values, rcond=None)
    resid = tr.R.values - X @ beta
    s2 = resid.var(ddof=2)
    cov = s2 * np.linalg.inv(X.T @ X)
    return dict(slope_R_per_year=float(beta[1]), t=float(beta[1] / np.sqrt(cov[1, 1])),
                first_half_exp=float(tr[tr.year <= np.median(yrs)].R.mean()),
                second_half_exp=float(tr[tr.year > np.median(yrs)].R.mean()))


# ---------------------------------------------------------------- section 9 fixes

def fix_candidates(S: Setup):
    """Each candidate: (name, kwargs for Setup.trades, post-filter on trades or None)."""
    sc = S.sc
    c = []
    for bf in ("p20_80", "no_narrow", "no_wide", "narrow", "wide"):
        c.append((f"box_filter={bf}", dict(sc=replace(sc, box_filter=bf)), None))
    for vk in (1.0, 1.5, 2.0):
        c.append((f"volume>= {vk}x median", dict(sc=replace(sc, vol_k=vk)), None))
    for tr_ in ("ema20", "ema50", "prevclose"):
        c.append((f"trend={tr_}", dict(sc=replace(sc, trend=tr_)), None))
    c.append(("fresh break only", dict(sc=replace(sc, fresh=True)), None))
    c.append(("retest entry (limit at box edge)", dict(retest=True), None))
    c.append(("allow reversal trade", dict(max_trades="reversal"), None))
    c.append(("news filter (skip NFP/CPI/ECB days)", {}, lambda t: t[t.events.str.len() == 0]))
    c.append(("break-even at +1R", dict(manage=dict(be_at=1.0)), None))
    c.append(("partial 50% at 1R", dict(manage=dict(partial_at=1.0)), None))
    c.append(("partial 50% at 2R", dict(manage=dict(partial_at=2.0)), None))
    c.append(("BE at 1R + partial at 1R", dict(manage=dict(be_at=1.0, partial_at=1.0)), None))
    for ta in (2.0, 4.0):
        c.append((f"ATR trail {ta}x signal-ATR", dict(manage=dict(trail_atr=ta)), None))
    for ts in (60, 120, 240):
        c.append((f"time exit after {ts} min", dict(manage=dict(time_stop=ts)), None))
    c.append(("confirmation: other index broke same way first", {}, "confirm"))
    c.append(("skip Mondays", {}, lambda t: t[t.dow != 0]))
    return c


def confirm_filter(S: Setup, tr):
    """Keep a trade only if the other index had a same-direction signal entry at or before
    this trade's entry time on the same date (information available at entry)."""
    if len(S.insts) < 2:
        return tr
    first = tr.groupby(["inst", "date"]).agg(entry_min=("entry_min", "min"), dir=("dir", "first"))
    keep = []
    for r in tr.itertuples(index=False):
        other = [n for n in S.insts if n != r.inst][0]
        key = (other, r.date)
        keep.append(key in first.index and first.loc[key, "dir"] == r.dir and first.loc[key, "entry_min"] <= r.entry_min)
    return tr[np.array(keep, bool)]


def evaluate_fixes(S: Setup, base_tr):
    base = {p: base_tr[base_tr.split == p] for p in ("IS", "VAL")}
    rows = []
    for name, kw, post in fix_candidates(S):
        if post == "confirm":
            tr = confirm_filter(S, base_tr)
        else:
            tr = S.trades(k=1.0, **kw) if kw else base_tr
            if callable(post):
                tr = post(tr)
        row = dict(fix=name)
        for p in ("IS", "VAL"):
            sel = tr[tr.split == p]
            st = r_stats(sel.R.values)
            row[f"{p}_n"], row[f"{p}_exp"], row[f"{p}_t"] = st["n"], st["exp"], st["t"]
            row[f"{p}_d_exp"] = st["exp"] - base[p].R.mean()
            for n in S.insts:
                s2 = sel[sel.inst == n]
                row[f"{p}_{n}_d"] = s2.R.mean() - base[p][base[p].inst == n].R.mean() if len(s2) else np.nan
        row["n_retained"] = (row["IS_n"] + row["VAL_n"]) / max(len(base_tr), 1)
        # keep rule (frozen in RESEARCH_LOG): better in IS and in VAL pooled, better on each
        # instrument in IS, keeps >= 40% of trades, and VAL expectancy ends up > 0
        row["keep"] = bool(row["IS_d_exp"] > 0 and row["VAL_d_exp"] > 0
                           and all(row[f"IS_{n}_d"] > 0 for n in S.insts)
                           and row["n_retained"] >= 0.4 and row["VAL_exp"] > 0)
        rows.append(row)
    return pd.DataFrame(rows)


def to_json(obj, path):
    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, pd.DataFrame):
            return o.reset_index().to_dict(orient="records")
        return str(o)
    json.dump(obj, open(path, "w"), indent=1, default=conv)
