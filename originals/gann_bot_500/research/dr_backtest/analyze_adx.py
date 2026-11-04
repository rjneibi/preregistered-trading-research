"""
Arm C5 analysis — would an ADX(14,H4) >= 25 gate have helped D or R?

Reads trades_variants_C5adx_{D,R}.jsonl (record-only run: gate NOT enforced,
adx recorded per entry). Reports, per profile and IS/OOS:
  * unfiltered baseline (should reconcile with Run A)
  * ADX>=25 kept-subset (what the gate would keep)
  * ADX<25 dropped-subset (what the gate would remove)
  * direction split of the effect (does the gate starve BUYs?)
Pre-specified threshold: 25 (directive). Other thresholds descriptive only.
"""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
IS_END = pd.Timestamp("2022-12-31T23:59:59Z")
OOS_START = pd.Timestamp("2023-01-01T00:00:00Z")


def stats(pnl):
    n = len(pnl)
    if not n:
        return dict(n=0, pf=None, wr=None, tot=0.0)
    w = [x for x in pnl if x > 0]; l = [x for x in pnl if x < 0]
    pf = round(sum(w) / -sum(l), 3) if l else float("inf")
    return dict(n=n, pf=pf, wr=round(len(w) / n, 3), tot=round(sum(pnl), 0))


def fmt(s):
    return f"n={s['n']:>4} PF={s['pf']} WR={s['wr']}"


for prof in ("D", "R"):
    rows = [json.loads(l) for l in open(HERE / f"trades_variants_C5adx_{prof}.jsonl")]
    elig = [r for r in rows
            if r["outcome_status"] in ("TP", "SL", "PARTIAL_THEN_TP", "PARTIAL_THEN_BE")
            and r["pnl_points"] is not None]
    n_no_adx = sum(1 for r in elig if r.get("adx_h4") is None)
    print(f"\n===== Profile {prof} — C5 ADX analysis (eligible n={len(elig)}, "
          f"adx-missing={n_no_adx}) =====")
    for label, lo, hi in (("IS 2016-22", None, IS_END), ("OOS 2023-26", OOS_START, None)):
        sub = []
        for r in elig:
            ts = pd.Timestamp(r["entry_ts"])
            if lo is not None and ts < lo: continue
            if hi is not None and ts > hi: continue
            sub.append(r)
        base = stats([r["pnl_points"] for r in sub])
        kept = [r for r in sub if (r.get("adx_h4") or 0) >= 25]
        drop = [r for r in sub if (r.get("adx_h4") or 0) < 25]
        s_k = stats([r["pnl_points"] for r in kept])
        s_d = stats([r["pnl_points"] for r in drop])
        print(f"  {label}:")
        print(f"    unfiltered : {fmt(base)}")
        print(f"    ADX>=25 keep: {fmt(s_k)}   ({100*s_k['n']/base['n']:.0f}% kept)" if base['n'] else "")
        print(f"    ADX<25 drop : {fmt(s_d)}")
        # direction split of the DROPPED set (starvation check)
        d_buy = stats([r["pnl_points"] for r in drop if r["direction"] == "BUY"])
        d_sell = stats([r["pnl_points"] for r in drop if r["direction"] == "SELL"])
        k_buy = stats([r["pnl_points"] for r in kept if r["direction"] == "BUY"])
        k_sell = stats([r["pnl_points"] for r in kept if r["direction"] == "SELL"])
        print(f"    dropped BUY : {fmt(d_buy)}   dropped SELL: {fmt(d_sell)}")
        print(f"    kept BUY    : {fmt(k_buy)}   kept SELL   : {fmt(k_sell)}")
    # descriptive threshold sweep (NOT pre-registered — descriptive only)
    print("  descriptive threshold sweep (OOS PF of kept-subset):")
    oos = [r for r in elig if pd.Timestamp(r["entry_ts"]) >= OOS_START]
    for th in (15, 20, 25, 30):
        k = stats([r["pnl_points"] for r in oos if (r.get("adx_h4") or 0) >= th])
        print(f"    ADX>={th}: {fmt(k)}")
