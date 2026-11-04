"""Build reports/report.html from results/. The plain-English summary is reports/summary_fragment.html (written by
hand after reading the results, so it says what the numbers say).
    python src/report.py
"""
import html
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
R = lambda *p: os.path.join(ROOT, *p)
TFS = ["1", "2", "3", "5", "10", "15", "30", "45", "60", "120", "240", "D"]


def fmt(v, nd=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "–" if v is None or np.isnan(v) else ("∞" if v > 0 else "-∞")
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    if isinstance(v, (float, np.floating)):
        return f"{v:,.{nd}f}"
    return html.escape(str(v))


def table(df, cols, heads=None, cls="", num_sign=()):
    heads = heads or cols
    h = "".join(f"<th>{html.escape(x)}</th>" for x in heads)
    rows = []
    for _, r in df.iterrows():
        tds = []
        for c in cols:
            v = r[c]
            k = ""
            if c in num_sign and isinstance(v, (float, int, np.floating, np.integer)) and np.isfinite(v):
                k = " class='pos'" if v > 0 else (" class='neg'" if v < 0 else "")
            tds.append(f"<td{k}>{fmt(v)}</td>")
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<div class='tw'><table class='{cls}'><thead><tr>{h}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def p1_pivot(p1, horizon):
    d = p1[(p1.horizon == horizon) & (p1.tp == 5.0)].copy()
    out = []
    for a in ["SPY", "QQQ", "XAU"]:
        for tf in TFS:
            x = d[(d.asset == a) & (d.tf.astype(str) == tf)]
            if not len(x):
                continue
            row = {"asset": a, "tf": tf, "source": x.source.iloc[0], "period": f"{x.start.iloc[0]} → {x.end.iloc[0]}"}
            for v in "abc":
                y = x[x.variant == v]
                if len(y):
                    y = y.iloc[0]
                    flag = "" if y.n >= 30 else "*"
                    row[f"{v}_n"] = f"{int(y.n)}{flag}"
                    row[f"{v}_net"] = y.net if y.n else np.nan
                    row[f"{v}_rand"] = y.beats_rand
            out.append(row)
    return pd.DataFrame(out)


def main():
    p1 = pd.read_csv(R("results", "phase1_all.csv"))
    runs = pd.read_csv(R("results", "all_runs.csv.gz"))
    top = pd.read_csv(R("results", "phase2_top20.csv"))
    wf = pd.read_csv(R("results", "phase2_walkforward.csv"))
    det = json.load(open(R("results", "phase2_details.json")))
    summary = open(R("reports", "summary_fragment.html"), encoding="utf-8").read()
    datalog = [l.strip()[7:] for l in open(R("results", "phase1_log.txt"), encoding="utf-8") if l.strip().startswith("[data]")]
    datalog = list(dict.fromkeys(datalog))

    S = []
    S.append(f"<section><h2>Summary</h2>{summary}</section>")
    S.append("<section><h2>Data and method</h2><ul>"
             "<li><b>XAUUSD</b>: broker XAUUSD from the trading VM — 1-minute bars 2026-07-15 → 2026-10-23 and 5-minute bars "
             "2025-05-29 → 2026-10-23. Bid bars; longs buy at ask (bid + recorded spread, min $0.22). Volume is tick volume.</li>"
             "<li><b>SPY, QQQ</b>: Yahoo chart API, regular hours only — 1-minute (30 days), 5-minute (57 days), hourly (2 years), daily "
             "(10 years). The yfinance package itself is blocked by Windows Application Control on this PC, so the same Yahoo endpoint "
             "is called directly. Free 1-minute history stops at 30 days, so the 'long history' for 1–3-minute SPY/QQQ is the same 30 days.</li>"
             "<li>Every timeframe is resampled from one base series per row (column <i>source</i>), bins anchored at the session open. "
             "Incomplete first/last sessions are dropped.</li>"
             "<li>Signals on bar close, fills at the next bar's open. Stop and target in the same bar → stop assumed. Costs: SPY/QQQ "
             "$0.01/share per side; XAU the bar's spread. P&amp;L is <b>per 1 share / 1 oz</b> (multiply XAU by 100 for 1 lot).</li>"
             "<li>Engine: a custom numpy simulator (vectorbt needs native packages this PC blocks); indicators re-implemented from "
             "TradingView's Pine reference formulas and unit-tested (tests/).</li></ul>"
             "<details><summary>Data validation log</summary><pre>" + html.escape("\n".join(datalog)) + "</pre></details></section>")

    # ---------------- Phase 1
    S.append("<section><h2>Phase 1 — the video strategy (EMA 9 × VWAP OHLC4 session, TP $5)</h2>"
             "<p>Variants: <b>a</b> TP or opposite cross (stop-and-reverse) · <b>b</b> TP or flat at session end · "
             "<b>c</b> TP, opposite cross or session end. <i>rand</i> = share of 200 random-entry runs (same signal count, same exits) "
             "the rule beat. * = fewer than 30 trades (not rankable). 1D uses a weekly VWAP; b/c are empty on 1D because the "
             "fill would always land in the next session.</p>")
    for h, title in (("primary", "Last 30 days"), ("long", "Longest history")):
        pv = p1_pivot(p1, h)
        cols = ["asset", "tf", "source", "period"] + [f"{v}_{k}" for v in "abc" for k in ("n", "net", "rand")]
        heads = ["asset", "tf", "data", "period"] + [f"{v} {k}" for v in "abc" for k in ("trades", "net $", "beats rand")]
        S.append(f"<h3>{title}</h3>" + table(pv, cols, heads, "p1", num_sign={"a_net", "b_net", "c_net"}))
    hr = p1[p1.tp == 5.0].groupby(["horizon", "asset"]).tp_rate.median().unstack(0).reset_index()
    S.append("<h3>How often is the $5 target actually reached?</h3>" + table(hr, list(hr.columns), ["asset", "longest history", "last 30 days"]))
    sw = p1.sort_values("net", ascending=False).groupby(["horizon", "asset"]).head(3)
    sw = sw[["horizon", "asset", "tf", "variant", "tp", "n", "net", "pf", "win", "maxdd", "tp_rate", "beats_rand", "buy_hold", "opt_est_per_contract"]]
    S.append("<h3>TP sweep ($0.25 – $5): best three per asset and horizon</h3>"
             "<p><i>opt est / contract</i> = 0.5 × underlying P&amp;L × 100 — a rough ATM 0DTE proxy that ignores theta, IV and option "
             "spreads. Treat it as an upper bound, not a forecast.</p>"
             + table(sw, list(sw.columns), ["horizon", "asset", "tf", "var", "TP $", "trades", "net $", "PF", "win", "max DD",
                                            "TP hit", "beats rand", "buy & hold", "opt est / contract"], num_sign={"net"}))
    S.append("</section>")

    # ---------------- Phase 2
    ok = runs[runs.oos_n >= 30].copy()
    ok["template"] = ok.cfg.map(lambda s: json.loads(s)["template"])
    tt = ok.groupby("template").apply(lambda g: pd.Series(dict(configs=len(g), is_profitable=(g.is_net > 0).mean(),
                                                              oos_profitable=(g.oos_net > 0).mean(),
                                                              both=((g.is_net > 0) & (g.oos_net > 0)).mean(),
                                                              median_oos_net=g.oos_net.median()))).reset_index()
    cor = ok.groupby(["asset", "tf"]).apply(lambda g: pd.Series(dict(configs=len(g), spearman_is_oos=g.is_sharpe.corr(g.oos_sharpe, method="spearman"),
                                                                    oos_profitable=(g.oos_net > 0).mean()))).reset_index()
    S.append(f"<section><h2>Phase 2 — broad search</h2><p><b>{len(runs):,}</b> configurations tested "
             f"({(runs.phase == 'grid').sum():,} coarse-grid + {(runs.phase == 'optuna').sum():,} Optuna-TPE, the latter optimising "
             f"<i>in-sample</i> Sharpe only); <b>{len(ok):,}</b> have ≥ 30 out-of-sample trades. In-sample = first 70% of each cell's "
             "history, out-of-sample = last 30%.</p>")
    S.append("<h3>By template</h3>" + table(tt, list(tt.columns), ["template", "configs", "IS profitable", "OOS profitable",
                                                                    "both", "median OOS net $"], num_sign={"median_oos_net"}))
    S.append("<h3>Does in-sample predict out-of-sample?</h3><p>Spearman rank correlation between in-sample and out-of-sample "
             "Sharpe across all configs in a cell. Near 0 = picking the in-sample winner is a coin flip.</p>"
             + table(cor, list(cor.columns), ["asset", "tf", "configs", "IS→OOS rank corr", "OOS profitable"], num_sign={"spearman_is_oos"}))
    wf2 = wf.copy(); wf2["folds"] = wf2.folds.astype(str)
    S.append("<h3>Walk-forward</h3><p>History cut into 6 equal blocks; in each fold the config with the best Sharpe on the two "
             "previous blocks is picked blind and traded on the next block. Summed test-block P&amp;L per share/oz:</p>"
             + table(wf2, ["asset", "tf", "wf_test_net", "folds", "configs"], ["asset", "tf", "WF test net $", "per fold", "configs"],
                     num_sign={"wf_test_net"}))
    tcols = ["rank", "asset", "tf", "oos_n", "oos_net", "oos_pf", "oos_win", "oos_sharpe", "oos_sortino", "oos_maxdd", "oos_lose_streak",
             "oos_hold_min", "oos_tp_rate", "oos_exposure", "is_net", "is_pf", "bh_oos", "rand_p95", "beats_rand", "dsr", "stability",
             "mc_net_p5", "mc_dd_p95", "PASS"]
    S.append("<h3>Top 20 by out-of-sample Sharpe</h3><p>Gates: OOS net &gt; 0 and PF ≥ 1.2 · in-sample net &gt; 0 · beats buy-and-hold "
             "over the OOS window · beats ≥ 95% of 200 random-entry runs · deflated Sharpe ≥ 0.95 counting <b>every</b> trial · ≥ 50% of "
             "one-step parameter neighbours profitable OOS. <i>mc</i> = 5,000-run bootstrap of the OOS trades.</p>"
             + table(top, tcols, ["#", "asset", "tf", "OOS trades", "OOS net $", "PF", "win", "Sharpe", "Sortino", "max DD", "lose streak",
                                  "hold min", "TP hit", "exposure", "IS net $", "IS PF", "B&H OOS", "random p95", "beats rand", "DSR",
                                  "stability", "MC net p5", "MC DD p95", "PASS"], num_sign={"oos_net", "is_net"}))
    cfgs = "".join(f"<li><b>#{int(r['rank'])}</b> {r.asset} {int(r.tf)}m — <code>{html.escape(r.cfg)}</code></li>" for _, r in top.iterrows())
    S.append(f"<details><summary>Configurations of the top 20</summary><ol class='cfg'>{cfgs}</ol></details>")
    S.append("<h3>Equity and drawdown (per share/oz, all trades; dashed line = start of out-of-sample)</h3>"
             "<label>Config <select id='pick'></select></label><div id='eq' class='chart'></div><div id='dd' class='chart small'></div>")
    S.append("<h3>Parameter heatmaps (top 3, OOS net $ as two parameters vary)</h3><div id='heat' class='grid3'></div>")
    ph = R("results", "posthoc_xau_top20.csv")
    if os.path.exists(ph):
        x = pd.read_csv(ph)
        S.append("<h3>Post-hoc (not pre-registered): gold's own top 20</h3><p class='callout'>The overall top 20 is all SPY/QQQ 5-minute, "
                 "whose out-of-sample window is only 12 sessions, so gold never reached it. Same gates applied to gold alone (21,521 "
                 "gold trials counted). Note the in-sample column and the side column: most winners are short or two-sided while gold fell "
                 "$565 over the out-of-sample window.</p>"
                 + table(x, ["rank", "tf", "tmpl", "side", "oos_n", "oos_net", "oos_pf", "oos_sharpe", "is_net", "bh_oos", "beats_rand", "dsr",
                             "stability", "PASS"], ["#", "tf", "template", "side", "OOS trades", "OOS net $/oz", "PF", "Sharpe", "IS net $/oz",
                                                   "B&H OOS", "beats rand", "DSR", "stability", "PASS"], num_sign={"oos_net", "is_net"}))
    S.append("</section>")

    S.append("<section><h2>Files</h2><ul><li><code>results/phase1_all.csv</code> — every Phase 1 row</li>"
             "<li><code>results/all_runs.csv.gz</code> — every Phase 2 configuration with IS/OOS/walk-forward metrics</li>"
             "<li><code>results/phase2_top20.csv</code>, <code>phase2_walkforward.csv</code>, <code>phase2_details.json</code></li>"
             "<li><code>pine/top_1..3.pine</code> and <code>pine/video_ema9_vwap_a|b|c.pine</code> — TradingView strategies</li></ul></section>")

    payload = json.dumps(dict(top=top[["rank", "asset", "tf", "oos_net", "PASS"]].to_dict("records"), det=det["details"]))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Strategy Search Report</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.35.2/plotly.min.js"></script>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mute:#6b6a65;--line:#e4e1d8;--card:#fff;--pos:#1f7a4d;--neg:#b3261e;--acc:#3b5bdb}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#151513;--fg:#ecebe6;--mute:#a19f97;--line:#33322e;--card:#1d1d1a;--pos:#5cc08a;--neg:#ff8a80;--acc:#8ea2ff}}}}
:root[data-theme="dark"]{{--bg:#151513;--fg:#ecebe6;--mute:#a19f97;--line:#33322e;--card:#1d1d1a;--pos:#5cc08a;--neg:#ff8a80;--acc:#8ea2ff}}
body{{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;margin:0}}
main{{max-width:1180px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:26px;margin:0 0 4px}} h2{{font-size:20px;margin:36px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}}
h3{{font-size:16px;margin:22px 0 6px}} p,li{{max-width:880px}} .sub{{color:var(--mute)}}
.tw{{overflow-x:auto;border:1px solid var(--line);border-radius:8px;background:var(--card)}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;font-variant-numeric:tabular-nums}}
th,td{{padding:5px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}
th{{position:sticky;top:0;background:var(--card);color:var(--mute);font-weight:600}}
td:first-child,th:first-child{{text-align:left}} .pos{{color:var(--pos)}} .neg{{color:var(--neg)}}
code{{font-size:12px;word-break:break-all}} .cfg li{{margin:4px 0}} pre{{white-space:pre-wrap;font-size:12px}}
.chart{{height:380px}} .chart.small{{height:200px}} .grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}}
.grid3>div{{height:330px}} .callout{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--acc);padding:10px 14px;border-radius:6px}}
select{{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:3px 6px}}
</style></head><body><main>
<h1>VWAP/EMA video strategy + TradingView indicator search</h1>
<p class="sub">SPY · QQQ · XAUUSD — research only, no orders placed. Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}.</p>
{''.join(S)}
</main>
<script>
const P = {payload};
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const lay = (t) => ({{title:{{text:t,font:{{size:13}}}},paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{{color:css('--fg')}},
  margin:{{l:55,r:15,t:30,b:35}},xaxis:{{gridcolor:css('--line')}},yaxis:{{gridcolor:css('--line'),zerolinecolor:css('--mute')}}}});
const sel = document.getElementById('pick');
P.top.forEach(r => {{ const o=document.createElement('option'); o.value=r.rank; o.textContent=`#${{r.rank}} ${{r.asset}} ${{r.tf}}m  OOS ${{r.oos_net.toFixed(2)}}  ${{r.PASS?'PASS':'fail'}}`; sel.appendChild(o); }});
function draw(rank) {{
  const d = P.det[rank]; if(!d) return;
  const x = d.t.map(s => new Date(s*1000));
  let peak=-1e18; const dd = d.cum.map(v => {{ peak=Math.max(peak,v,0); return v-peak; }});
  const split = new Date(d.split*1000);
  const shp = [{{type:'line',x0:split,x1:split,yref:'paper',y0:0,y1:1,line:{{dash:'dash',color:css('--mute')}}}}];
  Plotly.react('eq',[{{x,y:d.cum,mode:'lines',line:{{color:css('--acc'),width:1.6}},name:'cum P&L'}}],Object.assign(lay('Cumulative P&L per share/oz'),{{shapes:shp}}),{{responsive:true,displayModeBar:false}});
  Plotly.react('dd',[{{x,y:dd,mode:'lines',fill:'tozeroy',line:{{color:css('--neg'),width:1}},name:'drawdown'}}],Object.assign(lay('Drawdown'),{{shapes:shp}}),{{responsive:true,displayModeBar:false}});
}}
sel.onchange = () => draw(sel.value); draw(1);
const H = document.getElementById('heat');
[1,2,3].forEach(k => {{ const d=P.det[k]; if(!d||!d.heat) return; const div=document.createElement('div'); H.appendChild(div);
  const h=d.heat; Plotly.newPlot(div,[{{z:h.z,x:h.xs.map(String),y:h.ys.map(String),type:'heatmap',colorscale:'RdBu',zmid:0,
    text:h.z.map(r=>r.map(v=>v==null?'':v.toFixed(1))),texttemplate:'%{{text}}',hovertemplate:h.x+' %{{x}}<br>'+h.y+' %{{y}}<br>OOS $%{{z:.2f}}<extra></extra>'}}],
    Object.assign(lay(`#${{k}}: ${{h.x}} × ${{h.y}}`),{{xaxis:{{title:h.x,type:'category'}},yaxis:{{title:h.y,type:'category'}}}}),{{responsive:true,displayModeBar:false}}); }});
</script></body></html>"""
    open(R("reports", "report.html"), "w", encoding="utf-8").write(page)
    print("wrote reports/report.html", f"{len(page) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
