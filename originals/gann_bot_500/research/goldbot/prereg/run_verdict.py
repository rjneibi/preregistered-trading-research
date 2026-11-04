"""Pre-registered verdict run — commit 35deedc gates applied verbatim.

Order (load-bearing, CLAUDE_CODE_PROMPT step 7): (a) H1 rerun unfiltered at
matrix costs + p90 stress; (b) H2 at 0.50; (c) plateau 0.40/0.60;
(d) mechanism control on the old era. Each result is written to results/
before the next starts. No threshold is defined in this file — all gates are
read against PREREGISTRATION.md numbers, which cannot change post-commit.

Cost basis (pinned): per-year x UTC-hour median spread; slippage 0.5 x bucket
spread per side; commission $7/lot RT [BROKER]. No admin fee (not pinned in
the H1 cost basis). Fill mode gap_open — trial #2's basis, carried unchanged.
Flat-20pt kept as a comparison column only.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from goldbot.backtest import stats  # noqa: E402
from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.cpcv import CombinatorialPurgedCV  # noqa: E402
from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr  # noqa: E402
from goldbot.events import generate_events_final  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402
from cost_matrix import CostMatrix  # noqa: E402
from regime import event_regime_mask, mechanism_control  # noqa: E402

RESULTS = ROOT / "results"
MATRIX = RESULTS / "cost_matrix.json"
ERAS = {"old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                pd.Timestamp("2021-06-18T23:59:00Z")),
        "new": (pd.Timestamp("2021-06-19T00:00:00Z"), None)}
WARMUP = pd.Timedelta(days=100)


def pf(x: pd.Series) -> float:
    w, l = float(x[x > 0].sum()), float(-x[x <= 0].sum())
    return w / l if l > 0 else float("inf")


def split_expectancies(trades: pd.DataFrame, col: str) -> tuple[list, str]:
    """15-split test-fold expectancy list, or an error string on collapse."""
    cv = CombinatorialPurgedCV(n_groups=6, k_test=2, tau_max=24,
                               embargo=24, l_feature_max=40)
    labels = trades[["signal_hr"]].rename(columns={"signal_hr": "signal_idx"})
    out = []
    try:
        for _, test_idx, sid in cv.split(labels):
            out.append(round(float(trades.iloc[test_idx][col].mean()), 2))
    except RuntimeError as e:
        return out, f"COLLAPSED: {e}"
    return out, ""


def era_table(trades: pd.DataFrame, col: str) -> dict:
    t = {"full": stats(trades[col])}
    for era in ("old", "new"):
        t[era] = stats(trades[trades.era == era][col])
    return t


def fmt_tbl(tbl: dict) -> str:
    return "\n".join(
        f"  {k:>4}: n={v['n']} wr={v['wr']:.1%} pf={v['pf']:.2f} "
        f"net=${v['net_usd']:,.0f} exp=${v['expectancy_usd']:,.1f}"
        for k, v in tbl.items() if v["n"])


def main() -> int:
    assert MATRIX.exists(), "build results/cost_matrix.json first"
    cfg = load_config(ROOT / "config.yaml")
    cm_med = CostMatrix.load(MATRIX, stat="median", k_slip=0.5,
                             commission_per_lot_rt=7.0)
    cm_p90 = CostMatrix.load(MATRIX, stat="p90", k_slip=0.5,
                             commission_per_lot_rt=7.0)

    print("loading full M1 (2010+ for H2 warm-start) ...", flush=True)
    m1_full = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                        data_tz=cfg.data.data_tz)
    data_end = m1_full.index[-1]

    # ── events + exits, per era (trial #2 basis, unchanged) ─────────────
    e = cfg.exits.final
    all_trades = []
    for era, (start, end) in ERAS.items():
        end = end or data_end
        m1 = m1_full[(m1_full.index >= start - WARMUP) & (m1_full.index <= end)]
        h1 = resample_ohlc(m1, "1h")
        h4 = resample_ohlc(m1, "4h")
        d1 = resample_d1_utc(m1)
        atr_h1 = wilder_atr(h1, e.atr.period)
        events = generate_events_final(h1, h4, d1, atr_h1, cfg, start, end)
        tr = run_exits(m1, events, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr,
                       time_stop_h=e.time_stop_h, fill_mode="gap_open",
                       bail_enabled=e.bail.enabled,
                       hivol_half_x=e.bail.hivol_half_x,
                       lovol_bail_h=e.bail.lovol_bail_h,
                       lovol_bail_x=e.bail.lovol_bail_x)
        tr["era"] = era
        all_trades.append(tr)
    trades = pd.concat(all_trades, ignore_index=True)

    trades["cost_med"] = [cm_med.trade_cost_usd(a, b) for a, b
                          in zip(trades.entry_ts, trades.exit_ts)]
    trades["cost_p90"] = [cm_p90.trade_cost_usd(a, b) for a, b
                          in zip(trades.entry_ts, trades.exit_ts)]
    trades["net_med"] = trades.gross_usd - trades.cost_med
    trades["net_p90"] = trades.gross_usd - trades.cost_p90
    trades["net_flat"] = trades.gross_usd - 20.0          # comparison only

    # ── (a) H1 rerun ─────────────────────────────────────────────────────
    h1_tbl = era_table(trades, "net_med")
    h1_p90 = era_table(trades, "net_p90")
    h1_flat = era_table(trades, "net_flat")
    exps, err = split_expectancies(trades, "net_med")
    n_pos = sum(1 for x in exps if x > 0)
    gates = {
        "1_full_pf_ge_1.20": h1_tbl["full"]["pf"] >= 1.20,
        "2_splits_ge_10of15": (not err) and n_pos >= 10,
        "3_each_era_pf_ge_1.00": (h1_tbl["old"]["pf"] >= 1.00
                                  and h1_tbl["new"]["pf"] >= 1.00),
        "4_n_ge_300": len(trades) >= 300,
    }
    h1_pass = all(gates.values())
    h1_out = {
        "gates": gates, "pass": h1_pass,
        "tables": {"matrix_median": h1_tbl, "p90_stress": h1_p90,
                   "flat_comparison": h1_flat},
        "split_expectancies_med": exps, "split_error": err,
        "positive_splits": n_pos,
        "fallback_hits_med": cm_med.fallback_hits,
        "mean_cost_med_usd": round(float(trades.cost_med.mean()), 2),
        "mean_cost_by_era": {
            era: round(float(trades[trades.era == era].cost_med.mean()), 2)
            for era in ("old", "new")},
    }
    (RESULTS / "H1_rerun.json").write_text(json.dumps(h1_out, indent=1, default=str))
    trades.to_csv(RESULTS / "verdict_trades.csv", index=False)
    print(f"\n== (a) H1 rerun (matrix median costs) ==\n{fmt_tbl(h1_tbl)}")
    print(f"  p90 stress:\n{fmt_tbl(h1_p90)}")
    print(f"  flat-20 comparison:\n{fmt_tbl(h1_flat)}")
    print(f"  mean cost/trade: ${h1_out['mean_cost_med_usd']} "
          f"(old ${h1_out['mean_cost_by_era']['old']}, "
          f"new ${h1_out['mean_cost_by_era']['new']})")
    print(f"  splits positive: {n_pos}/15 {err}")
    print(f"  split expectancies: {exps}")
    print(f"  fallback hits: {cm_med.fallback_hits or 'none'}")
    print(f"  H1 gates: {gates}\n  H1 {'PASS' if h1_pass else 'FAIL'}")

    # ── (b) H2 at 0.50 ───────────────────────────────────────────────────
    pos_full = np.minimum(m1_full.index.searchsorted(
        trades.event_ts.to_numpy()), len(m1_full) - 1)

    def h2_run(threshold: float) -> tuple[dict, np.ndarray]:
        mask = event_regime_mask(m1_full, pos_full, threshold=threshold)
        ft = trades[mask]
        tbl = era_table(ft, "net_med")
        p90_tbl = era_table(ft, "net_p90")
        exps_f, err_f = split_expectancies(ft, "net_med") if len(ft) else ([], "empty")
        return {
            "threshold": threshold, "n": int(len(ft)),
            "tables": {"matrix_median": tbl, "p90_stress": p90_tbl},
            "split_expectancies_med": exps_f, "split_error": err_f,
            "positive_splits": sum(1 for x in exps_f if x > 0),
        }, mask

    h2, mask50 = h2_run(0.50)
    pf50 = h2["tables"]["matrix_median"]["full"]["pf"]
    pf50_p90 = h2["tables"]["p90_stress"]["full"]["pf"]
    (RESULTS / "H2_050.json").write_text(json.dumps(h2, indent=1, default=str))
    print(f"\n== (b) H2 @ 0.50 ==\n{fmt_tbl(h2['tables']['matrix_median'])}")
    print(f"  splits positive: {h2['positive_splits']}/15 {h2['split_error']}")
    print(f"  split expectancies: {h2['split_expectancies_med']}")
    print(f"  p90 full PF: {pf50_p90:.2f}")

    # ── (c) plateau 0.40 / 0.60 ─────────────────────────────────────────
    h2_40, _ = h2_run(0.40)
    h2_60, _ = h2_run(0.60)
    pf40 = h2_40["tables"]["matrix_median"]["full"]["pf"]
    pf60 = h2_60["tables"]["matrix_median"]["full"]["pf"]
    plateau_ok = (pf40 >= 1.10 and pf60 >= 1.10
                  and abs(pf40 - pf50) <= 0.15 and abs(pf60 - pf50) <= 0.15)
    (RESULTS / "H2_plateau.json").write_text(
        json.dumps({"0.40": h2_40, "0.60": h2_60, "primary_pf": pf50,
                    "plateau_ok": plateau_ok}, indent=1, default=str))
    print(f"\n== (c) plateau ==\n  PF @0.40={pf40:.2f} @0.50={pf50:.2f} "
          f"@0.60={pf60:.2f} -> {'OK' if plateau_ok else 'FAIL'}")

    # ── (d) mechanism control (old era) ─────────────────────────────────
    old_idx = (trades.era == "old").to_numpy()
    mech = mechanism_control(trades.net_med.to_numpy()[old_idx],
                             mask50[old_idx], min_n_in=40)
    mech["pf_gap"] = (round(mech["pf_in"] - mech["pf_out"], 3)
                      if np.isfinite(mech["pf_in"]) and np.isfinite(mech["pf_out"])
                      else None)
    (RESULTS / "H2_mechanism.json").write_text(json.dumps(mech, indent=1, default=str))
    print(f"\n== (d) mechanism control (old era) ==\n  {mech}")

    # ── H2 gates ─────────────────────────────────────────────────────────
    h2_gates = {
        "1_filtered_pf_ge_1.25": pf50 >= 1.25,
        "2_splits_ge_11of15": (not h2["split_error"]) and h2["positive_splits"] >= 11,
        "3_p90_pf_ge_1.10": pf50_p90 >= 1.10,
        "4_mechanism_gap_ge_0.15_nin_ge_40": (
            mech["sufficient"] and mech["pf_gap"] is not None
            and mech["pf_gap"] >= 0.15),
        "5_n_ge_150_and_plateau": h2["n"] >= 150 and plateau_ok,
    }
    mech_insufficient = not mech["sufficient"]
    h2_pass = all(h2_gates.values())
    h2_verdict = ("PASS" if h2_pass
                  else "INSUFFICIENT EVIDENCE (n_in < 40)"
                  if mech_insufficient and all(
                      v for k, v in h2_gates.items() if not k.startswith("4"))
                  else "FAIL")
    print(f"\n  H2 gates: {h2_gates}\n  H2 {h2_verdict}")

    # ── decision tree (verbatim) ─────────────────────────────────────────
    if h1_pass:
        decision = ("H1 PASS -> arm Phase 2 executor, unfiltered strategy "
                    "(demo 4-8 weeks per registered ops gates). H2 demoted "
                    "to optional enhancement study.")
    elif h2_pass:
        decision = ("H1 FAIL, H2 PASS -> arm Phase 2 with the FILTERED "
                    "strategy only, at HALF registered risk_per_trade_pct, "
                    "demo >= 8 weeks.")
    else:
        decision = ("BOTH FAIL -> STOP the goldbot-breakout line. Archive "
                    "results. Salvage candidates require fresh "
                    "pre-registration before any backtest.")
    print(f"\n== VERDICT ==\n{decision}")

    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  VERDICT RUN (prereg 35deedc, "
                f"matrix={MATRIX.name}, partial tick coverage per freeze "
                f"deviation).\n")
        for k, v in gates.items():
            f.write(f"            H1 gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            H1: {'PASS' if h1_pass else 'FAIL'} "
                f"(full PF {h1_tbl['full']['pf']:.2f}, old "
                f"{h1_tbl['old']['pf']:.2f}, new {h1_tbl['new']['pf']:.2f}, "
                f"splits {n_pos}/15, n={len(trades)})\n")
        for k, v in h2_gates.items():
            f.write(f"            H2 gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            H2 @0.50: {h2_verdict} (PF {pf50:.2f}, p90 "
                f"{pf50_p90:.2f}, splits {h2['positive_splits']}/15, "
                f"n={h2['n']}, plateau {pf40:.2f}/{pf60:.2f}, mechanism "
                f"gap {mech['pf_gap']} n_in={mech['n_in']})\n")
        f.write(f"            DECISION: {decision}\n")
    print(f"\nverdict appended to {RESULTS / 'DECISIONS.log'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
