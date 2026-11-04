"""Tables, gates, twin, walk-forward, Monte Carlo, prop windows, charts and REPORT.md."""
import json

import numpy as np
import pandas as pd

from . import stats as S
from .pipeline import CFG, RES, ROOT, SYMS, TFS, TPS, tp_name

RISK = CFG["account"]["risk"]
V = CFG["validation"]
TPN = [tp_name(t) for t in TPS]


def _m(t):
    return np.datetime64(int(t), "m")


def _load():
    spans = {s: tuple(v) for s, v in json.load(open(RES / "spans.json")).items()}
    full = pd.concat([pd.read_pickle(RES / f"grid_FULL_{s}.pkl") for s in SYMS], ignore_index=True)
    var = pd.concat([pd.read_pickle(RES / f"variants_{s}.pkl") for s in SYMS], ignore_index=True)
    sel = json.load(open(RES / "selection.json"))
    for d in (full, var):
        d["oos"] = [te >= spans[s][1] for te, s in zip(d.t_entry.values, d.sym.values)]
    return spans, full, var, sel


def _span(spans, syms, part):
    a = [spans[s] for s in syms]
    return (min(x[0] for x in a), min(x[1] for x in a)) if part == "IS" else (min(x[1] for x in a), max(x[2] for x in a))


def wfo(full, tf, tp):
    """6m train / 2m test rolling, pooled over symbols; pick by train avg R (n >= min)."""
    d = full[(full.tf == tf) & (full.tp == tp)]
    mon = d.t_entry.values.astype("datetime64[m]").astype("datetime64[M]")
    start, end = mon.min(), mon.max()
    tr_m, te_m = V["wfo_train_months"], V["wfo_test_months"]
    out, s = [], start
    while s + tr_m < end:
        tr = d[(mon >= s) & (mon < s + tr_m)]
        st = tr.groupby("cid").R.agg(["mean", "size"])
        st = st[st["size"] >= V["wfo_min_train_trades"]]
        if len(st):
            cid = st.sort_values(["mean", "size"], ascending=False).index[0]
            te = d[(mon >= s + tr_m) & (mon < s + tr_m + te_m) & (d.cid == cid)]
            out.append(te)
        s = s + te_m
    w = pd.concat(out) if out else d.iloc[:0]
    return dict(n=len(w), avgR=float(w.R.mean()) if len(w) else np.nan, windows=len(out))


def analyse():
    spans, full, var, sel = _load()
    rows, cells, yearly = [], [], []
    for tf in TFS:
        for tp in TPN:
            pick = sel["pooled"][f"{tf}|{tp}"]
            for label, cid in (("tuned", pick["cid"]), ("default", sel["default_cid"])):
                d = full[(full.tf == tf) & (full.tp == tp) & (full.cid == cid)]
                for part in ("IS", "OOS"):
                    dp = d[d.oos == (part == "OOS")]
                    for s in SYMS + ["POOLED"]:
                        ds = dp if s == "POOLED" else dp[dp.sym == s]
                        t0, t1 = _span(spans, SYMS if s == "POOLED" else [s], part)
                        rows.append(dict(cfg=label, cid=cid, tf=tf, tp=tp, part=part, sym=s,
                                         **S.metrics(ds, RISK, t0, t1)))
            d = full[(full.tf == tf) & (full.tp == tp) & (full.cid == pick["cid"])]
            o = d[d.oos]
            vv = var[(var.tf == tf) & (var.tp == tp) & (var.cid == pick["cid"]) & var.oos]
            fl = vv[vv["var"] == "flip"]
            p, twin_avg = S.twin_p(fl.R.values, fl.R_flip.values, V["random_direction_runs"], CFG["seed"])
            g0 = vv[vv["var"] == "x0"][["sym", "k", "R"]].merge(fl[["sym", "k", "R_flip_x0"]], on=["sym", "k"])
            p0, twin0 = S.twin_p(g0.R.values, g0.R_flip_x0.values, V["random_direction_runs"], CFG["seed"])
            t0, t1 = _span(spans, SYMS, "OOS")
            om = S.metrics(o, RISK, t0, t1)
            w = wfo(full, tf, tp)
            xau = o[o.sym == "XAUUSD"]
            cells.append(dict(
                tf=tf, tp=tp, cid=pick["cid"], fallback=pick.get("fallback", False),
                is_avgR=float(d[~d.oos].R.mean()), is_n=int((~d.oos).sum()),
                oos_n=om["n"], oos_avgR=om["avgR"], oos_t=om["t"], oos_pf=om["pf"], oos_win=om["win"],
                oos_x0=float(vv[vv["var"] == "x0"].R.mean()), oos_x2=float(vv[vv["var"] == "x2"].R.mean()),
                oos_measured=float(vv[vv["var"] == "measured"].R.mean()),
                twin_avg=twin_avg, twin_p=p, gross_twin_p=p0,
                wfo_n=w["n"], wfo_avgR=w["avgR"], wfo_windows=w["windows"],
                xau_oos_n=len(xau), xau_oos_avgR=float(xau.R.mean()) if len(xau) else np.nan,
                mc=S.mc_maxdd(o.sort_values("t_exit").R.values, RISK, V["monte_carlo_runs"], CFG["seed"]),
                mc_full=S.mc_maxdd(d.sort_values("t_exit").R.values, RISK, V["monte_carlo_runs"], CFG["seed"]),
                prop=S.prop_windows(o, RISK, t0, t1, V["prop"]),
                prop_xau=S.prop_windows(xau, RISK, t0, t1, V["prop"])))
            for y, g in d.groupby(d.t_entry.values.astype("datetime64[m]").astype("datetime64[Y]")):
                yearly.append(dict(tf=tf, tp=tp, year=int(str(y)[:4]), n=len(g), avgR=float(g.R.mean())))
    c = pd.DataFrame(cells)
    # Holm over the 15 cells on the twin p-value
    order = np.argsort(c.twin_p.fillna(1).values)
    adj = np.empty(len(c))
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(c) - r) * (c.twin_p.fillna(1).values[i])))
        adj[i] = run
    c["twin_p_holm"] = adj
    c["G1"] = (c.oos_n >= 50) & (c.oos_avgR > 0)
    c["G2"] = c.oos_pf >= 1.15
    c["G3"] = c.oos_x2 > 0
    c["G4"] = c.twin_p_holm < 0.05
    c["G5"] = c.wfo_avgR > 0
    c["G6"] = c.xau_oos_avgR > 0
    c["PASS"] = c[["G1", "G2", "G3", "G4", "G5", "G6"]].all(axis=1)
    pd.DataFrame(rows).to_csv(RES / "table_symbols.csv", index=False)
    c.to_pickle(RES / "cells.pkl")
    c.drop(columns=["mc", "mc_full", "prop", "prop_xau"]).to_csv(RES / "cells.csv", index=False)
    pd.DataFrame(yearly).to_csv(RES / "yearly.csv", index=False)
    # trades CSV: selected configs, every symbol, IS and OOS, 1x costs
    keep = []
    for tf in TFS:
        for tp in TPN:
            cid = sel["pooled"][f"{tf}|{tp}"]["cid"]
            keep.append(full[(full.tf == tf) & (full.tp == tp) & (full.cid == cid)])
    tr = pd.concat(keep)
    tr = tr.assign(entry_utc=[_m(x) for x in tr.t_entry], exit_utc=[_m(x) for x in tr.t_exit],
                   period=np.where(tr.oos, "OOS", "IS"))
    tr[["sym", "tf", "tp", "cid", "period", "entry_utc", "exit_utc", "dir", "entry", "stop", "target",
        "exit", "R", "why"]].to_csv(RES / "trades.csv", index=False)
    print(c[["tf", "tp", "is_avgR", "oos_n", "oos_avgR", "oos_pf", "oos_x0", "oos_x2", "twin_avg", "twin_p",
             "wfo_n", "wfo_avgR", "xau_oos_avgR", "PASS"]].round(3).to_string())


# ---------------------------------------------------------------- report
def _charts(full, sel, spans):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import sys
    sys.path.insert(0, "@LBO_ROOT@/src")
    from lbo import plotstyle
    t = plotstyle.apply("light")
    split = np.datetime64(int(min(v[1] for v in spans.values())), "m")
    files = []
    for tf in TFS:
        fig, ax = plt.subplots(figsize=(9, 4.2))
        for i, tp in enumerate(TPN):
            cid = sel["pooled"][f"{tf}|{tp}"]["cid"]
            d = full[(full.tf == tf) & (full.tp == tp) & (full.cid == cid)].sort_values("t_exit")
            eq = S.equity(d.R.values, RISK)[1:] / 1000
            x = d.t_exit.values.astype("datetime64[m]")
            ax.plot(x, eq, color=t["series"][i], label=f"{tp} (n={len(d)})")
            if len(d):
                ax.annotate(tp, (x[-1], eq[-1]), xytext=(4, 0), textcoords="offset points",
                            color=t["text2"], fontsize=8, va="center")
        ax.axvline(split, color=t["muted"], lw=1, ls="--")
        ax.text(split, ax.get_ylim()[1], "  OOS →", color=t["text2"], va="top", fontsize=8.5)
        ax.axhline(100, color=t["muted"], lw=0.8)
        ax.set_title(f"Entry {tf}m: equity, 4 symbols pooled, 1% risk, $100k start")
        ax.set_ylabel("Equity ($k)")
        ax.legend(loc="lower left", ncol=5, fontsize=8)
        f = f"equity_{tf}m.png"
        fig.tight_layout()
        fig.savefig(RES / f, dpi=130)
        plt.close(fig)
        files.append(f)
    fig, axs = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, tf in zip(axs, TFS):
        cid = sel["pooled"][f"{tf}|2R"]["cid"]
        for i, s in enumerate(SYMS):
            d = full[(full.tf == tf) & (full.tp == "2R") & (full.cid == cid) & (full.sym == s)].sort_values("t_exit")
            ax.plot(d.t_exit.values.astype("datetime64[m]"), S.equity(d.R.values, RISK)[1:] / 1000,
                    color=t["series"][i], label=f"{s} (n={len(d)})")
        ax.axvline(split, color=t["muted"], lw=1, ls="--")
        ax.axhline(100, color=t["muted"], lw=0.8)
        ax.set_title(f"{tf}m entry, 2R target, per symbol")
        ax.legend(fontsize=7.5, loc="lower left")
    axs[0].set_ylabel("Equity ($k)")
    fig.tight_layout()
    fig.savefig(RES / "equity_by_symbol_2R.png", dpi=130)
    plt.close(fig)
    return files + ["equity_by_symbol_2R.png"]


def _f(x, nd=2, pct=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "–" if not (isinstance(x, float) and np.isinf(x)) else "∞"
    return f"{x * 100:.{nd - 1}f}%" if pct else f"{x:+.{nd}f}" if isinstance(x, float) else str(x)


def report():
    spans, full, var, sel = _load()
    c = pd.read_pickle(RES / "cells.pkl")
    tab = pd.read_csv(RES / "table_symbols.csv")
    charts = _charts(full, sel, spans)
    split = str(np.datetime64(int(min(v[1] for v in spans.values())), "m").astype("datetime64[D]"))
    npass = int(c.PASS.sum())
    L = ["# CRT-FVG-1: CRT + HTF FVG backtest report", ""]
    L += [f"Data: Dukascopy M1 2013-01 to 2026-10. IS = first 70% (to {split}); OOS = the rest, opened once after the "
          f"IS selection was frozen (`results/selection.json`). {sel['backtests']} IS backtests "
          f"({sel['n_configs']} configs × 3 entry TFs × 5 TP modes × 4 symbols). "
          "Costs: XAU $0.25 + $7/lot, EURUSD 0.5 pip + $7, GBPUSD 1.0 pip + $7, NAS100 1.5 pt; 1 tick slippage on "
          "entries and stops; 1% risk per trade, $100k.", ""]
    L += ["## Verdict", ""]
    L += [f"**{'EDGE' if npass else 'NO EDGE'}: {npass} of 15 pooled cells pass all six gates.**", ""]
    L += ["- The edge does not survive costs or out-of-sample. Every one of the 15 cells is negative OOS after costs "
          "(−0.07R to −0.64R per trade). Even the best of 108 settings was negative in-sample in every cell.",
          "- Before costs the rules are no better than a coin, and slightly worse: in 12 of 15 cells, gross OOS avg R is below "
          "a random-direction twin on the same entries (gross range −0.41R to +0.49R). The "
          "only positive gross cell (5m, liquidity target) depends on a single +23.6R trade. No cell beats the "
          "random-direction twin after correcting for 15 tests.",
          "- Costs are the killer on the short entry timeframes. A 5m stop is about $2.5 on gold and 2.5-3.5 pips on "
          "FX, so spread + commission takes 13% (gold) to 40-60% (FX) of 1R per trade.",
          "- The two gold cells that are positive OOS (5m liq +0.35R n29, 3m 3R +0.25R n12) are noise. The 5m one "
          "lost −0.23R on gold in-sample.",
          "- Prop-firm check: no cell reaches +10% within 30 days in more than 2.3% of windows. At 1-2 trades a month "
          "that is the expected outcome.",
          "- Every walk-forward is negative (−0.13R to −0.39R). In the main 5m/2R cell, 12 of 14 years are negative.",
          ""]
    L += ["## Gates per cell (4 symbols pooled, IS-selected config, OOS)", "",
          "| Entry | TP | IS avg R | OOS n | OOS avg R | PF | gross (0×) | 2× cost | measured spread | twin avg R | twin p (Holm) | WFO avg R (n) | XAU OOS avg R (n) | G1-G6 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in c.itertuples():
        g = "".join("✓" if getattr(r, f"G{i}") else "✕" for i in range(1, 7))
        L.append(f"| {r.tf}m | {r.tp}{' (default)' if r.fallback else ''} | {_f(r.is_avgR)} | {r.oos_n} | "
                 f"{_f(r.oos_avgR)} | {r.oos_pf:.2f} | {_f(r.oos_x0)} | {_f(r.oos_x2)} | {_f(r.oos_measured)} | "
                 f"{_f(r.twin_avg)} | {r.twin_p:.2f} ({r.twin_p_holm:.2f}) | {_f(r.wfo_avgR)} ({r.wfo_n}) | "
                 f"{_f(r.xau_oos_avgR)} ({r.xau_oos_n}) | {g} |")
    L += ["", "G1 OOS avg R > 0 with n ≥ 50 · G2 PF ≥ 1.15 · G3 > 0 at 2× costs · G4 beats random direction "
          "(Holm p < .05) · G5 walk-forward > 0 · G6 XAUUSD alone > 0. "
          "15m cells had no config with ≥ 30 IS trades per symbol, so they use the spec defaults.", ""]
    L += ["## Per symbol × entry TF × TP mode (IS-selected config, OOS, 1× costs)", "",
          "| Symbol | Entry | TP | n | win | avg R | $/trade | PF | max DD | Sharpe | lose streak | trades/mo |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in tab[(tab.cfg == "tuned") & (tab.part == "OOS")].itertuples():
        L.append(f"| {r.sym} | {r.tf}m | {r.tp} | {r.n} | {_f(r.win, 2, True)} | {_f(r.avgR)} | "
                 f"{'–' if not np.isfinite(r.exp_usd) else f'{r.exp_usd:,.0f}'} | {r.pf:.2f} | "
                 f"{_f(r.maxdd, 2, True)} | {_f(r.sharpe)} | {r.lose_streak} | {r.per_month:.2f} |")
    L += ["", "The same table for IS and for the untuned spec defaults is in `results/table_symbols.csv`.", ""]
    L += ["## Spec defaults, untuned (N=2, K=1, no FVG size filter, 4H bias, 0.1 ATR buffer)", "",
          "| Entry | TP | IS n | IS avg R | OOS n | OOS avg R | OOS PF |", "|---|---|---|---|---|---|---|"]
    dft = tab[(tab.cfg == "default") & (tab.sym == "POOLED")]
    for tf in TFS:
        for tp in TPN:
            a = dft[(dft.tf == tf) & (dft.tp == tp) & (dft.part == "IS")].iloc[0]
            b = dft[(dft.tf == tf) & (dft.tp == tp) & (dft.part == "OOS")].iloc[0]
            L.append(f"| {tf}m | {tp} | {a.n} | {_f(a.avgR)} | {b.n} | {_f(b.avgR)} | {b.pf:.2f} |")
    L += ["", "## Monte Carlo (1,000 reshuffles of the OOS trade order, 1% risk) and prop-firm windows", "",
          "| Entry | TP | OOS max DD actual | MC median | MC 95th | MC 99th | prop pass / fail / neither (pooled) | XAU only |",
          "|---|---|---|---|---|---|---|---|"]
    for r in c.itertuples():
        p, q = r.prop, r.prop_xau
        L.append(f"| {r.tf}m | {r.tp} | {_f(r.mc['actual'], 2, True)} | {_f(r.mc['p50'], 2, True)} | "
                 f"{_f(r.mc['p95'], 2, True)} | {_f(r.mc['p99'], 2, True)} | "
                 f"{_f(p['pass'], 2, True)} / {_f(p['fail'], 2, True)} / {_f(p['neither'], 2, True)} | "
                 f"{_f(q['pass'], 2, True)} / {_f(q['fail'], 2, True)} / {_f(q['neither'], 2, True)} |")
    L += ["", "Prop rules: rolling 30-day windows from every OOS weekday; +10% target, −5% day, −10% total; "
          "closed-trade P&L.", ""]
    L += ["## Charts", ""] + [f"![{f}](results/{f})" for f in charts] + [""]
    L += ["## Files", "", "- `results/trades.csv`: every trade of the selected configs (IS and OOS, 1× costs)",
          "- `results/cells.csv`, `results/table_symbols.csv`, `results/yearly.csv`, `results/selection.json`",
          "- `PREREG.md` (frozen plan), `prediction_claude.sealed.txt`", ""]
    (ROOT / "REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("REPORT.md written;", npass, "cells pass")
