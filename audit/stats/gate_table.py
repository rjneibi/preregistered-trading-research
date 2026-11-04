"""Names the gate each result with PF above 1.1 fails, by how much, with DSR at the ledger count and at the family count. Numbers come from the run files named in each row."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.dirname(HERE)
GB = os.path.join(AUD, "_copy", "goldbot")
sys.path[:0] = [os.path.join(AUD, "phaseE"), os.path.join(GB, "prereg")]
import lib
from cost_matrix import CostMatrix

src = open(os.path.join(HERE, "pass_audit.py"), encoding="utf-8").read().replace("\nmain()\n", "\n")
pa = {"__file__": os.path.join(HERE, "pass_audit.py"), "__name__": "pa"}
exec(compile(src, "pass_audit", "exec"), pa)
SB = pa["SB"]
sys.path[:0] = [SB + "/cross_market", SB + "/tune1"]
import edge_lab
import tune_dip

F = json.load(open(os.path.join(HERE, "family_counts.json")))
fam = F["fragile_family_n"]
gold_n = F["families"]["goldbot pre-July ledger"]["variants"] + F["families"]["goldbot ledger"]["variants"]
M = os.path.join(GB, "results", "cost_matrix.json")
cm = CostMatrix.load(M, stat="median", k_slip=0.5, commission_per_lot_rt=7.0)
cp = CostMatrix.load(M, stat="p90", k_slip=0.5, commission_per_lot_rt=7.0)
HB = json.load(open(os.path.join(AUD, "_copy", "sb_true", "research", "goldbot", "results", "HB_run_binding.json")))
DR = json.load(open(os.path.join(AUD, "phaseC", "dr_matrix.json")))
PS = json.load(open(os.path.join(HERE, "pass_audit.json")))
SC = json.load(open(os.path.join(AUD, "trade_checks", "sc1_check.json")))
P = json.load(open(os.path.join(AUD, "phaseC", "talab_pess.json")))


def dsrs(r, n):
    return round(lib.dsr(r, lib.LEDGER_N), 3), round(lib.dsr(r, n), 3)


rows = []
v = {k: pd.read_csv(os.path.join(AUD, "phaseC", f"fable_{k}_true.csv"), parse_dates=["ts"]) for k in ("v3", "v4")}
for k, t in v.items():
    gross = t.pnl.values + 20.0
    ts = list(t.ts)
    med = np.array([cm.trade_cost_usd(a, a) for a in ts])
    p90 = np.array([cp.trade_cost_usd(a, a) for a in ts])
    v[k] = dict(pf20=lib.pf(t.pnl.values), pfm=lib.pf(gross - med), pfp=lib.pf(gross - p90), r=gross - med, r20=t.pnl.values)
rv3, rv4 = v["v3"], v["v4"]
a, b = dsrs(rv3["r20"], gold_n)
rows.append(dict(id="XAU-FINAL-V3", pf=1.254, basis="true UTC, flat 20-pt cost, n=436", gates=[f"H-B gate 1, PF >= 1.35 at matrix costs: {HB['pf']:.3f}, short by {1.35 - HB['pf']:.3f}", f"H-B gate 2, each era PF >= 1.00: old era {HB['pf_old']:.3f}, short by {1 - HB['pf_old']:.3f}",
                                                                                        f"H-B gate 3, 11 of 15 splits positive: {HB['splits_positive']}, short by {11 - HB['splits_positive']}", f"H-B gate 4, p90 PF >= 1.15: {HB['pf_p90']:.3f}, short by {1.15 - HB['pf_p90']:.3f}; old-era p90 >= 0.90: {HB['pf_p90_old']:.3f}"],
                 why="The 1.254 uses an assumed flat cost well under measured spreads. H-B is the same rule at measured costs, and n matches at 436.", dsr=a, dsr_fam=b, fam_n=gold_n))
a, b = dsrs(rv4["r20"], gold_n)
rows.append(dict(id="XAU-FINAL-V4", pf=1.145, basis="true UTC, flat 20-pt cost, n=577", gates=[f"Programme gate 1, PF >= 1.20: {rv4['pf20']:.3f} at flat cost, short by {1.2 - rv4['pf20']:.3f}", f"Approximate matrix cost, entry hour used for both sides: PF {rv4['pfm']:.3f}, short by {1.2 - rv4['pfm']:.3f}", f"Same approximation at p90: PF {rv4['pfp']:.3f}"],
                 why="No pre-registered gate exists for V4, so H1's gate is used. The check on V3 by the same approximation gives " + f"{rv3['pfm']:.3f} against H-B's {HB['pf']:.3f}.", dsr=a, dsr_fam=b, fam_n=gold_n))
d = DR["true D median"]
dp = DR.get("true D p90", {})
rows.append(dict(id="DR-EDGE-SCREEN D", pf=1.505, basis="true UTC, no spread in the screen, n=1,307", gates=[f"Programme gate 1, PF >= 1.20 at matrix cost: {d['pf']:.3f}, short by {1.2 - d['pf']:.3f}", f"At p90 cost: {dp.get('pf')}"], why="Unthrottled entry screen, not a strategy. The 1.505 has no spread.", dsr=None, dsr_fam=None, fam_n=None))
rows.append(dict(id="XAU-FLIP-RAW TP5/SL15", pf=1.147, basis="true UTC, raw grid cell, flat 20-pt cost", gates=["Programme gate 1, PF >= 1.20: 1.147, short by 0.053", "One cell of a grid, no gate of its own"], why="Grid cell picked after the fact.", dsr=None, dsr_fam=None, fam_n=None))
rows.append(dict(id="SC-1 ORB-30", pf=1.259, basis="no HistData dependence, n=987", gates=["Later sealed read of the live ORB baseline in TUNE-1: PF 0.87, losing", "DSR at ledger N 0.03 against 0.95", "2026 PF 0.88"], why="Stays failed.", dsr=0.03, dsr_fam=None, fam_n=None))

us = pa["load"]("US500")
ra = pa["ret"](pa["a1"](us))
rb = pa["ret"](pa["ibs_rule"](us))
tf = edge_lab.f6()[0].values
pool = []
for sym in tune_dip.HOLD_T:
    m = pa["load"](sym)
    sp = max(m["sp"], 0.0002 * float(np.median(m["c"])))
    pool += [x for x in pa["a1"](dict(m, sp=sp)) if x[0] >= int(np.datetime64("2023-10-13").astype("datetime64[s]").astype(np.int64))]
rt = pa["ret"](pool)
wk = pd.Series(rt).groupby(np.array([x[0] // (7 * 86400) for x in pool])).mean().values
tn = dict(week_clustered_T=len(wk), dsr_ledger=round(lib.dsr(wk, lib.LEDGER_N), 3), dsr_family=round(lib.dsr(wk, fam["TUNE-1-DIP"]), 3))
led = pd.read_csv(os.path.join(AUD, "..", "registry", "trial_ledger.csv"), dtype=str, keep_default_na=False)
led["n"] = pd.to_numeric(led.n_variants, errors="coerce").fillna(0)
dated = {k: int(led[led.date <= d].n.sum()) for k, d in (("XM-1-A1", "2026-10-13"), ("SW-1", "2026-10-13"), ("EDGE-1-F6", "2026-10-14"), ("TUNE-1-DIP", "2026-10-26"))}
for nm, r, pf_ in (("XM-1-A1", ra, 2.372), ("SW-1", rb, 1.741), ("TUNE-1-DIP", rt, 3.05)):
    a, b = dsrs(r, fam[nm])
    rows.append(dict(id=nm, pf=pf_, basis="no HistData dependence", gates=[f"DSR >= 0.95 at ledger N: {a}, short by {0.95 - a:.3f}"], why="Numbers exact. Fragile by the stored PBO, delay and benchmark results.", dsr=a, dsr_fam=b, fam_n=fam[nm], dated_n=dated[nm], dsr_dated=round(lib.dsr(r, dated[nm]), 3)))
a, b = dsrs(tf, fam["EDGE-1-F6"])
rows.append(dict(id="EDGE-1-F6", pf=None, basis="Sharpe 1.52, daily", gates=[f"DSR >= 0.95 at ledger N: {a}, short by {0.95 - a:.3f}", "PBO 0.742 on 5 variants"], why="Numbers exact. E5 reads Sharpe 1.36 to 1.49 on real cost tiers.", dsr=a, dsr_fam=b, fam_n=fam["EDGE-1-F6"], dated_n=dated["EDGE-1-F6"], dsr_dated=round(lib.dsr(tf, dated["EDGE-1-F6"]), 3)))
t12 = {x["label"]: x for x in P["rows"]["round12_py"]}
x = t12["M15 FIXED      2025+#1"]
rows.append(dict(id="TA-LAB-R4 fixed, 2025+", pf=x["stock_pf"], basis="slice, n=398", gates=[f"<2025 slice PF {t12['M15 FIXED      <2025#1']['stock_pf']}, below 1.0", "Beats 45% of twins", f"Same-bar worst case PF {min(x['pessA_pf'], x['pessB_pf'])}"], why="A later slice of a failed rule.", dsr=None, dsr_fam=None, fam_n=None))
rows.append(dict(id="TA-LAB-R11, 2025+", pf=1.15, basis="slice, n=42", gates=["INSUFFICIENT SAMPLE"], why="Under 100 trades.", dsr=None, dsr_fam=None, fam_n=None))
for r in rows:
    if r["id"] == "TUNE-1-DIP":
        r["gates"] += [f"Registered test: 0 of 3 finalists passed", f"Trades cluster in {tn['week_clustered_T']} weeks. Averaged by week, ledger DSR is {tn['dsr_ledger']}"]
        r["why"] = "PF 3.05 is an unregistered read of the baseline, the same rule as XM-1-A1. It is not a fourth independent result."
json.dump(dict(gold_family_n=gold_n, tune_clustered=tn, dated=dated, rows=rows), open(os.path.join(HERE, "gate_table.json"), "w"), indent=1)
print(json.dumps(rows, indent=0)[:5000])
