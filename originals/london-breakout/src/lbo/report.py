"""Build report.html (standalone) and results/report_artifact.html (body fragment)."""
import base64
import html
import io
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import plotstyle  # noqa: E402
from .common import RESULTS, ROOT, config  # noqa: E402

FIGS = {}


def fig(name):
    """Decorator: render a chart function in both themes and store base64 PNGs."""
    def wrap(fn):
        def run(*a, **k):
            out = {}
            for theme in ("light", "dark"):
                t = plotstyle.apply(theme)
                f = fn(t, theme, *a, **k)
                buf = io.BytesIO()
                f.savefig(buf, format="png", dpi=130, bbox_inches="tight")
                plt.close(f)
                out[theme] = base64.b64encode(buf.getvalue()).decode()
            FIGS[name] = out
        return run
    return wrap


def load():
    d = {}
    d["s1A"] = json.load(open(RESULTS / "stage1_A.json"))
    d["s1B"] = json.load(open(RESULTS / "stage1_B.json"))
    d["pick"] = json.load(open(RESULTS / "deep_pick" / "summary.json"))
    d["author"] = json.load(open(RESULTS / "deep_author" / "summary.json"))
    d["wfo"] = json.load(open(RESULTS / "wfo.json"))
    d["oos"] = json.load(open(RESULTS / "oos_final.json"))
    d["oos_author"] = json.load(open(RESULTS / "oos_author_reference.json"))
    d["box"] = json.load(open(RESULTS / "box_behaviour_summary.json"))
    d["fixes"] = pd.read_csv(RESULTS / "deep_pick" / "fixes.csv")
    d["mgA"] = pd.read_csv(RESULTS / "stage1_A_merged.csv")
    d["Bsess"] = pd.read_csv(RESULTS / "stage1_B_all_instruments_by_session.csv")
    d["tr_final"] = pd.read_csv(RESULTS / "all_trades_final_k1_incl_oos.csv")
    d["tr_author"] = pd.read_csv(RESULTS / "all_trades_author_reference_k1_incl_oos.csv")
    d["cost_pick"] = pd.read_csv(RESULTS / "deep_pick" / "cost_sizing.csv")
    d["year_pick"] = pd.read_csv(RESULTS / "deep_pick" / "by_year.csv")
    return d


def _shade(ax, tr, t):
    for split, alpha in (("VAL", 0.07), ("OOS", 0.14)):
        x = np.flatnonzero(tr.split.values == split)
        if x.size:
            ax.axvspan(x[0], x[-1], color=t["muted"], alpha=alpha, lw=0)
            ax.text((x[0] + x[-1]) / 2, 1.01, {"VAL": "validation", "OOS": "out-of-sample"}[split],
                    transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=8, color=t["text2"])


@fig("equity")
def ch_equity(t, theme, d):
    f, axes = plt.subplots(1, 2, figsize=(10.5, 3.6))
    for ax, key, title in ((axes[0], "tr_final", "Selected config (frozen)"), (axes[1], "tr_author", "Author-literal reference")):
        tr = d[key].sort_values("entry_min").reset_index(drop=True)
        _shade(ax, tr, t)
        ax.plot(tr.R.cumsum().values, color=t["series"][0], lw=1.8)
        ax.axhline(0, color=t["muted"], lw=0.8)
        ax.set_title(title, loc="left", pad=16)
        ax.set_xlabel("trade number (GER40 + UK100, chronological)")
        ax.set_ylabel("cumulative R, after 1x costs")
    f.tight_layout()
    return f


@fig("drawdown")
def ch_dd(t, theme, d):
    tr = d["tr_final"].sort_values("entry_min").reset_index(drop=True)
    eq = np.cumprod(1 + 0.005 * tr.R.values)
    dd = eq / np.maximum.accumulate(eq) - 1
    f, ax = plt.subplots(figsize=(10.5, 2.6))
    _shade(ax, tr, t)
    ax.fill_between(range(len(dd)), dd * 100, 0, color=t["neg"], alpha=0.35, lw=0)
    ax.plot(dd * 100, color=t["neg"], lw=1.2)
    ax.set_ylabel("drawdown, % (0.5% risk)")
    ax.set_xlabel("trade number")
    ax.set_title("Selected config: equity drawdown at 0.5% risk per trade", loc="left", pad=16)
    return f


@fig("isval")
def ch_isval(t, theme, d):
    mg = d["mgA"]
    x, y = mg.IS_exp.clip(-1, 0.6), mg.VAL_exp.clip(-1, 0.6)
    f, ax = plt.subplots(figsize=(5.6, 4.6))
    hb = ax.hexbin(x, y, gridsize=45, bins="log", cmap=matplotlib.colors.LinearSegmentedColormap.from_list(
        "s", [t["surface"], t["series"][0]]), mincnt=1, linewidths=0)
    ax.axhline(0, color=t["text2"], lw=0.8)
    ax.axvline(0, color=t["text2"], lw=0.8)
    ax.set_xlabel("in-sample expectancy (R/trade, 1x costs)")
    ax.set_ylabel("validation expectancy (R/trade)")
    ax.set_title(f"All {len(mg):,} Variant A configs (both indices pooled)", loc="left")
    ax.text(0.58, 0.55, f"IS>0: {(mg.IS_exp > 0).mean():.0%}\nVAL>0: {(mg.VAL_exp > 0).mean():.1%}",
            ha="right", va="top", color=t["text2"], fontsize=9)
    f.colorbar(hb, ax=ax, label="configs (log)")
    return f


@fig("heat_stop_rr")
def ch_heat(t, theme, d):
    p = d["pick"]["config"]
    mg = d["mgA"]
    sub = mg[(mg.box == p["box"]) & (mg.tf == p["tf"]) & (mg.order == "market") & (mg.strong == p["strong"])
             & (mg.breakout == p["breakout"]) & (mg.window == p["window"])]
    f, axes = plt.subplots(1, 2, figsize=(10.5, 3.4))
    cmap = plotstyle.diverging(theme)
    for ax, part in zip(axes, ("IS", "VAL")):
        pv = sub.pivot_table(index="stop", columns="rr", values=f"{part}_exp")
        pv = pv.reindex(["candle", "in25", "atr1", "mid", "atr2", "opp"])
        im = ax.imshow(pv.values, cmap=cmap, vmin=-0.5, vmax=0.5, aspect="auto")
        ax.set_xticks(range(pv.shape[1]), ["none" if not np.isfinite(c) else f"{c:g}" for c in pv.columns])
        ax.set_yticks(range(pv.shape[0]), pv.index)
        ax.grid(False)
        for i in range(pv.shape[0]):
            for j in range(pv.shape[1]):
                v = pv.values[i, j]
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=7.5, color=t["text"])
        ax.set_xlabel("reward:risk target")
        ax.set_title(f"{'In-sample' if part == 'IS' else 'Validation'}: stop x target", loc="left")
    f.colorbar(im, ax=axes, label="R/trade", shrink=0.9)
    return f


@fig("heat_tf_stop")
def ch_heat2(t, theme, d):
    mg = d["mgA"][d["mgA"].order == "market"]
    f, axes = plt.subplots(1, 2, figsize=(10.5, 2.8))
    cmap = plotstyle.diverging(theme)
    for ax, part in zip(axes, ("IS", "VAL")):
        pv = mg.pivot_table(index="tf", columns="stop", values=f"{part}_exp", aggfunc="median")
        pv = pv[["candle", "in25", "atr1", "mid", "atr2", "opp"]]
        im = ax.imshow(pv.values, cmap=cmap, vmin=-0.5, vmax=0.5, aspect="auto")
        ax.set_xticks(range(pv.shape[1]), pv.columns)
        ax.set_yticks(range(pv.shape[0]), [f"{i}m" for i in pv.index])
        ax.grid(False)
        for i in range(pv.shape[0]):
            for j in range(pv.shape[1]):
                ax.text(j, i, f"{pv.values[i, j]:+.2f}", ha="center", va="center", fontsize=7.5, color=t["text"])
        ax.set_title(f"{'In-sample' if part == 'IS' else 'Validation'}: median over all other settings", loc="left")
    f.colorbar(im, ax=axes, label="R/trade", shrink=0.9)
    return f


@fig("mc")
def ch_mc(t, theme, d):
    fan = np.load(RESULTS / "deep_pick" / "mc_fan_0.005.npy")
    fin = np.load(RESULTS / "deep_pick" / "mc_fin_0.005.npy")
    f, axes = plt.subplots(1, 2, figsize=(10.5, 3.4), gridspec_kw=dict(width_ratios=[2, 1]))
    ax = axes[0]
    for path in fan[:150]:
        ax.plot(path, color=t["series"][0], alpha=0.08, lw=0.8)
    for q, ls in ((5, "--"), (50, "-"), (95, "--")):
        ax.plot(np.percentile(fan, q, axis=0), color=t["text"], lw=1.2, ls=ls)
    ax.axhline(1, color=t["muted"], lw=0.8)
    ax.set_title("Bootstrap equity paths (0.5% risk), 5/50/95th pct", loc="left")
    ax.set_xlabel("trade number")
    ax.set_ylabel("equity multiple")
    ax = axes[1]
    ax.hist(fin, bins=60, color=t["series"][0], alpha=0.8)
    ax.axvline(1, color=t["text2"], lw=1)
    ax.axvline(np.percentile(fin, 5), color=t["neg"], lw=1.2, ls="--")
    ax.set_title("Final equity, 10,000 runs", loc="left")
    ax.set_xlabel("equity multiple")
    f.tight_layout()
    return f


@fig("baseline")
def ch_base(t, theme, d):
    Ra = np.load(RESULTS / "deep_pick" / "R_actual.npy")
    Rm = np.load(RESULTS / "deep_pick" / "R_mirror.npy")
    rng = np.random.default_rng(config()["seed"])
    flips = rng.random((5000, len(Ra))) < 0.5
    means = np.where(flips, Ra, Rm).mean(axis=1)
    f, ax = plt.subplots(figsize=(7.5, 3.2))
    ax.hist(means, bins=60, color=t["muted"], alpha=0.7, label="random direction, same entry times")
    ax.axvline(Ra.mean(), color=t["series"][0], lw=2, label=f"breakout direction {Ra.mean():+.3f}R")
    ax.axvline(Rm.mean(), color=t["series"][1], lw=2, ls="--", label=f"fade the breakout {Rm.mean():+.3f}R")
    ax.set_xlabel("mean R per trade (IS+VAL, 1x costs)")
    ax.set_title("Selected config vs random and fade baselines", loc="left")
    ax.legend(loc="upper left", fontsize=8)
    return f


@fig("costs")
def ch_costs(t, theme, d):
    ks = [0.0, 0.5, 1.0, 2.0]
    f, ax = plt.subplots(figsize=(6.5, 3.2))
    series = [("selected, IS+VAL", [d["pick"]["exp_by_cost"][str(k)] for k in ks]),
              ("selected, OOS", [d["oos"][str(k)]["exp"] for k in ks]),
              ("author-literal, IS+VAL", [d["author"]["exp_by_cost"][str(k)] for k in ks])]
    for i, (lab, ys) in enumerate(series):
        ax.plot(ks, ys, marker="o", ms=6, color=t["series"][i], label=lab)
        ax.annotate(lab, (ks[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=t["text2"])
    ax.axhline(0, color=t["text2"], lw=0.8)
    ax.set_xticks(ks, ["gross", "0.5x", "1x", "2x"])
    ax.set_xlabel("cost multiplier (spread + slippage + commission)")
    ax.set_ylabel("R per trade")
    ax.set_xlim(-0.1, 2.9)
    ax.set_title("Cost sensitivity", loc="left")
    ax.legend(loc="lower left", fontsize=8)
    return f


@fig("years")
def ch_years(t, theme, d):
    y = d["year_pick"]
    f, ax = plt.subplots(figsize=(7.5, 3.0))
    cols = [t["pos"] if v > 0 else t["neg"] for v in y.exp]
    ax.bar(y.year.astype(str), y.exp, color=cols, width=0.6)
    for x, v, n in zip(y.year.astype(str), y.exp, y.n):
        ax.text(x, v + (0.015 if v > 0 else -0.015), f"n={n}", ha="center", va="bottom" if v > 0 else "top", fontsize=7, color=t["text2"])
    oo = d["oos"]["1.0"]
    ax.bar(["OOS"], [oo["exp"]], color=t["muted"], width=0.6)
    ax.axhline(0, color=t["text2"], lw=0.8)
    ax.set_ylabel("R per trade, 1x costs")
    ax.set_title("Selected config by year (2016-17 have no overnight data)", loc="left")
    return f


@fig("wfo")
def ch_wfo(t, theme, d):
    f, ax = plt.subplots(figsize=(7.5, 3.0))
    for i, v in enumerate(("A", "B")):
        s = pd.read_csv(RESULTS / f"wfo_{v}_stitched.csv", index_col=0)
        s.index = pd.to_datetime(s.index)
        c = s.R.cumsum()
        ax.plot(c.index, c.values, color=t["series"][i], label=f"Variant {v}")
        ax.annotate(f"Variant {v}", (c.index[-1], c.values[-1]), xytext=(4, 0), textcoords="offset points", fontsize=8, color=t["text2"])
    ax.axhline(0, color=t["text2"], lw=0.8)
    ax.set_ylabel("cumulative R")
    ax.set_title("Walk-forward, 24m train / 6m test, stitched test windows", loc="left")
    ax.legend(loc="lower left", fontsize=8)
    return f


# ---------------------------------------------------------------- html

def fmt(v, nd=3, pct=False, sign=True):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–"
    if pct:
        return f"{v * 100:.1f}%"
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    return f"{v:+.{nd}f}" if sign else f"{v:.{nd}f}"


def img(name, alt):
    f = FIGS[name]
    return (f'<figure><img class="fig-l" alt="{html.escape(alt)}" src="data:image/png;base64,{f["light"]}">'
            f'<img class="fig-d" alt="{html.escape(alt)}" src="data:image/png;base64,{f["dark"]}"></figure>')


def table(df, cls=""):
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in df.astype(str).values)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def build():
    d = load()
    for fn in (ch_equity, ch_dd, ch_isval, ch_heat, ch_heat2, ch_mc, ch_base, ch_costs, ch_years, ch_wfo):
        fn(d)
    P, Au, O = d["pick"], d["author"], d["oos"]["1.0"]
    st = pd.DataFrame(P["stats_k1"])
    st = {r["index"]: r for r in P["stats_k1"]}
    rcA, rcB = d["s1A"]["rc"], d["s1B"]["rc"]
    wA, wB = d["wfo"]["A"], d["wfo"]["B"]
    gates = [
        ("G1", "Validation expectancy > 0 with t ≥ 2", f'{fmt(st["VAL"]["exp"])}R, t {st["VAL"]["t"]:.2f}, n {int(st["VAL"]["n"])}'),
        ("G2", "Beats random direction, p < 0.05", f'p = {P["baseline"]["p_value"]:.2f}'),
        ("G3", "Positive at 2x costs (IS+VAL)", f'{fmt(P["exp_by_cost"]["2.0"])}R'),
        ("G4", "Hansen SPA p < 0.10 over the whole grid", f'A: p = {rcA["p_hansen_spa"]:.2f} · B: p = {rcB["p_hansen_spa"]:.2f}'),
        ("G5", "Walk-forward stitched expectancy > 0", f'A: {fmt(wA["stitched_exp"])}R (n {wA["stitched_trades"]}) · B: {fmt(wB["stitched_exp"])}R'),
        ("G6", "Locked out-of-sample > 0 at 1x costs", f'{fmt(O["exp"])}R, t {O["t"]:.2f}, n {O["n"]}'),
    ]
    gate_rows = "".join(f'<tr><td class="g">{g}</td><td>{html.escape(q)}</td><td class="num">{html.escape(v)}</td>'
                        f'<td><span class="pill bad">✕ Fail</span></td></tr>' for g, q, v in gates)
    cs = d["cost_pick"]
    cs = cs[(cs.split.isin(["IS", "VAL", "IS+VAL"]))]
    mt = []
    for (k, sp, risk), r in cs.set_index(["cost_mult", "split", "risk"]).iterrows():
        if k not in (1.0,):
            continue
        mt.append([sp, f"{risk:.1%}", int(r.n), fmt(r.win, pct=True), fmt(r.avg_win, 2), fmt(r.avg_loss, 2), fmt(r.exp), fmt(r.pf, 2, sign=False),
                   fmt(r.sharpe, 2), fmt(r.sortino, 2), fmt(r.max_dd, pct=True), int(r.max_dd_days), int(r.longest_losing_streak),
                   fmt(r.cagr, pct=True), fmt(r.pct_months_profitable, pct=True), fmt(r.exposure, pct=True)])
    mt = pd.DataFrame(mt, columns=["split", "risk", "trades", "win", "avg win R", "avg loss R", "exp R", "PF", "Sharpe", "Sortino",
                                   "max DD", "DD days", "losing streak", "CAGR", "months +", "exposure"])
    oos_rows = []
    for lab, src in (("Selected (frozen)", d["oos"]), ("Author-literal reference", d["oos_author"])):
        for k in ("0.0", "1.0", "2.0"):
            r = src[k]
            oos_rows.append([lab, {"0.0": "gross", "1.0": "1x", "2.0": "2x"}[k], r["n"], fmt(r["exp"]), f'{r["t"]:.2f}',
                             fmt(r["win"], pct=True), fmt(r["by_inst"]["GER40"]["exp"]), fmt(r["by_inst"]["UK100"]["exp"]),
                             fmt(r.get("eq_max_dd"), pct=True) if r.get("eq_max_dd") is not None else "–"])
    oos_t = pd.DataFrame(oos_rows, columns=["config", "costs", "trades", "exp R", "t", "win", "GER40", "UK100", "max DD (0.5%)"])
    fx = d["fixes"]
    fx_t = pd.DataFrame({"fix": fx.fix, "IS exp": fx.IS_exp.map(fmt), "Δ IS": fx.IS_d_exp.map(fmt), "VAL exp": fx.VAL_exp.map(fmt),
                         "Δ VAL": fx.VAL_d_exp.map(fmt), "trades kept": fx.n_retained.map(lambda v: f"{v:.0%}"),
                         "kept?": fx.keep.map(lambda k: "yes" if k else "no")})
    rob = []
    for n, v in P["robustness_instruments"].items():
        ra = Au["robustness_instruments"][n]
        rob.append([n, v["IS+VAL"]["n"], fmt(v["gross_IS+VAL"]["exp"]), fmt(v["IS+VAL"]["exp"]), fmt(v["VAL"]["exp"]),
                    ra["IS+VAL"]["n"], fmt(ra["gross_IS+VAL"]["exp"]), fmt(ra["IS+VAL"]["exp"])])
    rob_t = pd.DataFrame(rob, columns=["instrument", "selected n", "selected gross", "selected net", "selected VAL",
                                       "author n", "author gross", "author net"])
    bs = d["Bsess"].pivot(index="inst", columns="session", values="mean_IS")[["asia", "london", "ny"]]
    bsp = d["Bsess"].pivot(index="inst", columns="session", values="share_both_pos")[["asia", "london", "ny"]]
    bcells = ""
    for inst in bs.index:
        tds = "".join(f'<td class="num {"neg" if bs.loc[inst, s] < 0 else "pos"}">{bs.loc[inst, s]:+.2f}<small> · {bsp.loc[inst, s]:.0%}</small></td>' for s in bs.columns)
        bcells += f"<tr><td>{inst}</td>{tds}</tr>"
    bx = {(b["inst"], b["box"]): b for b in d["box"]}
    g0, u0 = bx[("GER40", "utc0007")], bx[("UK100", "utc0007")]
    mc5 = P["monte_carlo"]["0.005"]
    mc1 = P["monte_carlo"]["0.01"]
    n_tot = d["s1A"]["n_configs_total"] + d["s1B"]["n_configs_total"] + 5 * 2160 + P["n_fix_trials"]
    pc = P["config"]
    css = CSS
    body = f"""
<title>London Breakout Study</title>
<meta name="claude:viewport-fit-sides" content="cover">
<style>{css}</style>
<main>
<header class="top">
  <p class="eyebrow">Quant research · GER40 & UK100 · Dukascopy 1m bid/ask, Sep 2013 to Oct 2026</p>
  <h1>London Breakout: is there an edge?</h1>
  <p class="lede">Two versions of the strategy were tested, every vague rule was swept, and the result was checked out-of-sample once. <strong>Neither version has an edge after costs.</strong> The gross effect is a few hundredths of an R per trade. That is real but smaller than the spread, and it has not been stable over time.</p>
</header>

<section class="verdict">
  <div class="vhead"><span class="pill bad big">✕ No edge · abandon</span><span class="muted">confidence: high</span></div>
  <dl class="kv">
    <div><dt>Expected R per trade after costs</dt><dd>{fmt(O["exp"])} OOS · {fmt(st["IS+VAL"]["exp"])} IS+VAL</dd></div>
    <div><dt>Gross (no costs)</dt><dd>{fmt(d["oos"]["0.0"]["exp"])} OOS · {fmt(P["exp_by_cost"]["0.0"])} IS+VAL</dd></div>
    <div><dt>Costs that zero it out</dt><dd>{P["cost_breakeven_mult"]:.2f}× the realistic estimate</dd></div>
    <div><dt>Realistic drawdown, 0.5% risk</dt><dd>median {abs(mc5["boot_dd_median"]):.0%}, 5% worst {abs(mc5["boot_dd_p5"]):.0%}</dd></div>
    <div><dt>Probability of losing money (bootstrap)</dt><dd>{mc5["boot_prob_loss"]:.0%} over 667 trades</dd></div>
    <div><dt>Configurations tried</dt><dd>{n_tot:,}</dd></div>
  </dl>
  <p>Under the conditions that matter (realistic spreads, the London open, 2013-2026), the breakout direction is no better than a coin flip at the same moment: p = {P["baseline"]["p_value"]:.2f}. Fading it is no better either. The best in-sample settings (a wide stop and no target, which simply holds the opening move until the cash close) made money in 2014-2020. They lost in every year from 2021 to 2024, and came out flat in the locked 2024-2026 test. I would not trade it live, and I would not spend paper-trading time on it either.</p>
</section>

<section>
  <h2>Pass/fail gates</h2>
  <p class="note">The gates were frozen in <code>RESEARCH_LOG.md</code> before any grid result was viewed. Any failure in G1-G4 means no edge.</p>
  <div class="tw"><table class="gates"><thead><tr><th></th><th>gate</th><th>result</th><th>status</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
</section>

<section>
  <h2>What was tested</h2>
  <div class="two">
    <div>
      <h3>Variant A · Asian box</h3>
      <p>Mark the Asian-session high and low. After 08:00 London, enter on the first strong candle that closes outside the box. Stop inside the box, fixed RR, one trade per day, flat at 16:30 London.</p>
      <p class="small">Swept: 4 box windows × 1/5/15m × 4 strong-candle rules × 3 breakout rules × 30/60/120 min × 6 stops × 6 targets. Stop-entry orders were tested as well. <b>16,272 configs per index.</b></p>
    </div>
    <div>
      <h3>Variant B · elitrade PDF</h3>
      <p>Previous-session 15m levels (session high/low, fractal swings or pivots). Break on 5m with volume, ATR stop, RR ≥ 3, at most 2 trades, first 30 or 60 min. Run on the Asia, London and NY sessions (New York clock).</p>
      <p class="small">Swept: 3 sessions × 3 level types × 2 windows × 4 volume rules × 2 buffers × 5 ATR stops × 3 targets. <b>2,160 configs per instrument</b>, on 7 instruments.</p>
    </div>
  </div>
  <p class="small">Split: in-sample to 2021-08-01, validation to 2024-03-15, locked out-of-sample to 2026-10-29. Costs: the real Dukascopy bid/ask spread on every bar, plus slippage of 0.5 points per side on indices. Same-bar stop and target always counts as the stop. Exits are simulated on 1m bars for every timeframe.</p>
</section>

<section>
  <h2>Nearly every config that worked in-sample failed in validation</h2>
  <div class="row">{img("isval", "hexbin of in-sample vs validation expectancy")}
  <div class="side"><p>{d["s1A"]["share_IS_pos"]:.0%} of Variant A configs were profitable in-sample. Only {d["s1A"]["share_VAL_pos"]:.1%} were profitable in validation. Their ranking persisted (correlation {d["s1A"]["corr_IS_VAL"]:.2f}), but the whole cloud shifted below zero.</p>
  <p>Across all {rcA["K"]:,} pooled configs, Hansen's SPA test gives p = {rcA["p_hansen_spa"]:.2f} and White's Reality Check p = {rcA["p_white_rc"]:.2f}. The best in-sample result (t = {rcA["best_t"]:.2f}) is about what the best of {rcA["K"]:,} random tries would show.</p>
  <p>Variant B: {d["s1B"]["share_IS_pos"]:.1%} of configs were positive in-sample, none on both indices. SPA p = {rcB["p_hansen_spa"]:.2f}.</p></div></div>
</section>

<section>
  <h2>The frozen configuration</h2>
  <p>This is the best broad plateau in-sample, chosen by the frozen rule. It failed validation and goes forward with that label:</p>
  <ul>
    <li>box {pc["box"].replace("utc2307", "23:00-07:00 UTC")}, {pc["tf"]}m bars, candle range ≥ 1×ATR, whole candle outside the box;</li>
    <li>first {pc["window"]} min after the open;</li>
    <li>stop 25% inside the box, no target, exit 16:30 London.</li>
  </ul>
  <p>Exact rules: <code>config/final_strategy.yaml</code>.</p>
  {img("equity", "cumulative R for the selected and author configs")}
  {img("drawdown", "drawdown of the selected config")}
  {table(mt)}
  <p class="note">IS+VAL rows cover only days with a usable Asian box. Dukascopy has no overnight index prices from 2015 to mid-2018. CAGR and Sharpe use calendar days with a valid box.</p>
</section>

<section>
  <h2>Out-of-sample, run once</h2>
  <p>15 Mar 2024 to 29 Oct 2026. This data was not loaded by any earlier step, and the config was committed (<code>2438440</code>) before this run.</p>
  {table(oos_t)}
  <p class="note">GER40 alone was positive OOS (+0.13R, n = 98). That result is not significant, and it was not a pre-registered hypothesis. Adopting it now would be choosing after the fact. A GER40-only version would need its own pre-registration and fresh forward data.</p>
</section>

<section>
  <h2>Baselines, costs and Monte Carlo</h2>
  <div class="two">{img("baseline", "random direction baseline")}{img("costs", "cost sensitivity")}</div>
  {img("mc", "Monte Carlo bootstrap")}
  <p class="small">Trade-order shuffle, 0.5% risk: median max drawdown {abs(mc5["shuffle_dd_median"]):.0%}, 5th percentile {abs(mc5["shuffle_dd_p5"]):.0%}. Bootstrap final equity: 5th percentile {mc5["boot_final_p5"]:.2f}×, median {mc5["boot_final_median"]:.2f}×. At 1% risk: median drawdown {abs(mc1["boot_dd_median"]):.0%}, 5th percentile {abs(mc1["boot_dd_p5"]):.0%}.</p>
</section>

<section>
  <h2>Parameter surface</h2>
  <p>Look for broad plateaus. The only region that is warm in-sample is the wide stop (opposite box edge) with no target. It turns cold in validation. Candle-extreme stops and 1m signals are destroyed by costs.</p>
  {img("heat_stop_rr", "stop by target heatmap")}
  {img("heat_tf_stop", "timeframe by stop heatmap")}
</section>

<section>
  <h2>Decay and walk-forward</h2>
  <div class="two">{img("years", "expectancy by year")}{img("wfo", "walk-forward stitched")}</div>
  <p class="small">Trend in R per trade: {P["decay"]["slope_R_per_year"]:+.3f}R per year (t = {P["decay"]["t"]:.2f}). Gross expectancy fell from +0.165R in-sample to −0.164R in validation, so cost increases are not the main cause. The walk-forward re-picks the best config from the full grid every 6 months. Its stitched results: Variant A {fmt(wA["stitched_exp"])}R (t {wA["stitched_t"]:.2f}), Variant B {fmt(wB["stitched_exp"])}R (t {wB["stitched_t"]:.2f}).</p>
</section>

<section>
  <h2>Variant B by session</h2>
  <p>Mean in-sample R per trade across all configs, and the share of configs positive in both IS and VAL. No cell holds up. The Asia session loses on overnight spread alone.</p>
  <div class="tw"><table class="heat"><thead><tr><th>instrument</th><th>Asia 19:00-04:00 NY</th><th>London 03:00-12:00</th><th>NY 09:30-16:00</th></tr></thead><tbody>{bcells}</tbody></table></div>
</section>

<section>
  <h2>Other instruments, same rules</h2>
  {table(rob_t)}
  <p class="note">Gross is slightly positive almost everywhere and net is negative almost everywhere. The selected rules are net positive only on US30 (n = 169, in-sample driven).</p>
</section>

<section>
  <h2>The author's paid features and other fixes</h2>
  <p>Each fix was tested on IS and VAL only, under a keep-rule frozen beforehand: it had to improve IS and VAL, improve each index, keep ≥ 40% of trades, and end with VAL > 0. <strong>None qualified.</strong> Break-even, partials and trailing stops move the result by a few hundredths of an R. They change the win rate, not the expectancy.</p>
  {table(fx_t, "compact")}
</section>

<section>
  <h2>Main weaknesses (full list in docs/gaps.md)</h2>
  <ul>
    <li><b>False breakouts are the norm.</b> After the first 5m close outside the box, price closes back inside within 15 minutes {g0["reentry_3_pct"]:.0%} (GER40) / {u0["reentry_3_pct"]:.0%} (UK100) of the time, and before 16:30 {g0["reentry_by_exit_pct"]:.0%} / {u0["reentry_by_exit_pct"]:.0%} of the time.</li>
    <li><b>The rules contradict themselves.</b> The author's 19:00-04:00 NY "Asian" window runs past the London open all year. Variant B's previous session is still open when the next one starts.</li>
    <li><b>Outliers carry it.</b> Dropping the best 5% of trades takes the selected config from −0.03R to −0.24R. 2019 alone made 58% of the in-sample R.</li>
    <li><b>Event days are worse</b> (CPI −0.35R, ECB −0.27R on small samples), but excluding them does not create an edge. 20 Dec - 3 Jan is clearly bad (−0.37R).</li>
    <li><b>The literature's conditions do not hold here.</b> Neither narrow boxes nor high volatility improve results.</li>
  </ul>
</section>

<section>
  <h2>What I would test next</h2>
  <ul>
    <li>Hold-to-close intraday momentum (Gao et al. 2018) on DAX futures at exchange costs, without a bracket. This is the one mechanism with a gross signal in this data, but it needs much lower costs than retail CFDs.</li>
    <li>A paid source of overnight index data for 2015-2018 (Eurex FDAX), to recover the third of the in-sample period that was lost.</li>
    <li>Tick data around 08:00:00 London, to measure real opening spreads and slippage at a specific broker.</li>
    <li>A fresh pre-registration for GER40-only on forward data, if it is pursued at all. The OOS hint is not evidence.</li>
  </ul>
</section>

<footer class="small muted">Reproduce with <code>python run_all.py</code> (see README.md). Code, logs and every intermediate result are in <code>@LBO_ROOT@</code>.</footer>
</main>
"""
    (RESULTS / "report_artifact.html").write_text(body, encoding="utf-8")
    full = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap\">"
            "</head><body>" + body + "</body></html>")
    (ROOT / "report.html").write_text(full, encoding="utf-8")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
/* Layout: single reading column, verdict block first, wide figures and tables scroll inside their own boxes */
:root{
  --bg:#f7f8f9; --panel:#ffffff; --ink:#14171a; --ink2:#4b525a; --rule:#dfe3e7; --accent:#2a78d6;
  --bad:#d03b3b; --bad-bg:#fbeaea; --pos:#2a78d6; --neg:#c43a3a; --cell-pos:#e6f0fb; --cell-neg:#fbecec;
  --fig-l:block; --fig-d:none;
  --sans:'Public Sans', system-ui, -apple-system, 'Segoe UI', sans-serif; --mono:'JetBrains Mono', ui-monospace, Consolas, monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#141517; --panel:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --rule:#2e3033; --accent:#3987e5;
  --bad:#e66767; --bad-bg:#3a2020; --pos:#6aa5ee; --neg:#ec7c7c; --cell-pos:#1b2a3d; --cell-neg:#3a2224;
  --fig-l:none; --fig-d:block; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#141517; --panel:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --rule:#2e3033; --accent:#3987e5;
  --bad:#e66767; --bad-bg:#3a2020; --pos:#6aa5ee; --neg:#ec7c7c; --cell-pos:#1b2a3d; --cell-neg:#3a2224;
  --fig-l:none; --fig-d:block; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55}
main{max-width:1080px;margin:0 auto;padding-block:32px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:40px}
h1{font-size:clamp(28px,4.2vw,40px);line-height:1.12;margin:0;text-wrap:balance;letter-spacing:-0.01em}
h2{font-size:21px;margin:0 0 10px;text-wrap:balance}
h3{font-size:15px;margin:0 0 6px}
p{margin:0 0 10px;max-width:72ch}
ul{margin:0;padding-left:20px;max-width:80ch;display:flex;flex-direction:column;gap:6px}
code{font-family:var(--mono);font-size:.86em;background:var(--panel);border:1px solid var(--rule);border-radius:4px;padding:1px 5px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);margin-bottom:10px}
.lede{font-size:17px;max-width:68ch;margin-top:14px}
.small{font-size:13.5px;color:var(--ink2)} .muted{color:var(--ink2)} .note{font-size:13px;color:var(--ink2);margin-top:8px}
.verdict{background:var(--panel);border:1px solid var(--rule);border-left:4px solid var(--bad);border-radius:6px;padding:22px 24px;display:flex;flex-direction:column;gap:14px}
.vhead{display:flex;gap:14px;align-items:center;flex-wrap:wrap}
.kv{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px 24px;margin:0}
.kv div{min-width:0} .kv dt{font-size:12px;color:var(--ink2);text-transform:uppercase;letter-spacing:.05em}
.kv dd{margin:2px 0 0;font-family:var(--mono);font-size:15px;font-variant-numeric:tabular-nums}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:2px 9px;border-radius:999px;white-space:nowrap}
.pill.bad{background:var(--bad-bg);color:var(--bad)} .pill.big{font-size:14px;padding:4px 12px}
.tw{overflow-x:auto;border:1px solid var(--rule);border-radius:6px;background:var(--panel);margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:13px;font-variant-numeric:tabular-nums}
th,td{padding:7px 10px;border-bottom:1px solid var(--rule);text-align:left;white-space:nowrap}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink2);font-weight:600}
tbody tr:last-child td{border-bottom:0}
td.num{font-family:var(--mono)} td.g{font-family:var(--mono);font-weight:600}
table.gates td:nth-child(2){white-space:normal;min-width:220px}
table.compact td:first-child{white-space:normal;min-width:240px}
table.heat td.pos{background:var(--cell-pos)} table.heat td.neg{background:var(--cell-neg)} table.heat small{color:var(--ink2)}
figure{margin:8px 0;min-width:0}
figure img{width:100%;height:auto;border-radius:4px}
.fig-l{display:var(--fig-l)} .fig-d{display:var(--fig-d)}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:20px;align-items:start}
.two>div{min-width:0}
.row{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);gap:24px;align-items:center}
@media (max-width:760px){.row{grid-template-columns:1fr}}
.side p{font-size:14.5px}
footer{border-top:1px solid var(--rule);padding-top:14px}
a{color:var(--accent)}
"""


if __name__ == "__main__":
    build()
    print("report written")
