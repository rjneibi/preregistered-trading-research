"""H-M verdict run — HM_PREREGISTRATION.md (commit 0a84ca3) applied verbatim.

Rebuilds the exact H1-verdict trade set (same generators/exits/costs as
run_verdict.py) with the `level` column carried from events, builds the two
causal context series on full 2010+ history, then runs the frozen meta-label
pipeline + shuffled-label control + suspicion-clause diagnostics.
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

from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr  # noqa: E402
from goldbot.events import generate_events_final  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402
from cost_matrix import CostMatrix  # noqa: E402
from meta_lab import (FEATURES, build_context, build_features, cpcv_meta_run,  # noqa: E402
                      evaluate_gates)

RESULTS = ROOT / "results"
MATRIX = RESULTS / "cost_matrix.json"
NEWS = ROOT.parents[1] / "fable-backtesting" / "calendar" / "news_days.json"
ERAS = {"old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                pd.Timestamp("2021-06-18T23:59:00Z")),
        "new": (pd.Timestamp("2021-06-19T00:00:00Z"), None)}
WARMUP = pd.Timedelta(days=100)


def rebuild_trades(cfg, m1_full):
    e = cfg.exits.final
    data_end = m1_full.index[-1]
    out = []
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
        tr = tr.merge(events[["event_ts", "level"]], on="event_ts",
                      validate="one_to_one")
        tr["era"] = era
        out.append(tr)
    return pd.concat(out, ignore_index=True)


def main() -> int:
    assert MATRIX.exists() and NEWS.exists()
    cfg = load_config(ROOT / "config.yaml")
    cm_med = CostMatrix.load(MATRIX, stat="median", k_slip=0.5,
                             commission_per_lot_rt=7.0)
    cm_p90 = CostMatrix.load(MATRIX, stat="p90", k_slip=0.5,
                             commission_per_lot_rt=7.0)
    news_days = set(json.loads(NEWS.read_text())["days"])

    print("loading full M1 (2010+ for context warm-start) ...", flush=True)
    m1_full = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                        data_tz=cfg.data.data_tz)
    trades = rebuild_trades(cfg, m1_full)
    assert len(trades) == 472, f"trade-set drift: {len(trades)} != 472"
    trades["cost_med"] = [cm_med.trade_cost_usd(a, b) for a, b
                          in zip(trades.entry_ts, trades.exit_ts)]
    trades["cost_p90"] = [cm_p90.trade_cost_usd(a, b) for a, b
                          in zip(trades.entry_ts, trades.exit_ts)]
    net_med = (trades.gross_usd - trades.cost_med).to_numpy()
    net_p90 = (trades.gross_usd - trades.cost_p90).to_numpy()
    y = (net_med > 0).astype(int)
    t_hr = trades.signal_hr.to_numpy()
    era_new = (trades.era == "new").to_numpy()
    print(f"trade set OK: n={len(trades)}, base WR {y.mean():.1%}, "
          f"unfiltered full PF at matrix costs "
          f"{net_med[net_med>0].sum()/abs(net_med[net_med<=0].sum()):.3f}")

    print("building causal context (relATR pctile + ADX) ...", flush=True)
    ctx = build_context(m1_full)
    X = build_features(trades, ctx, news_days)
    nan_counts = X.isna().sum()
    print(f"features built: {list(X.columns)}; NaNs per feature: "
          f"{dict(nan_counts[nan_counts > 0])} (HGB handles NaN natively)")

    # ── the frozen pipeline ──────────────────────────────────────────────
    print("\n== REAL RUN (15 purged splits, train-only tau) ==", flush=True)
    res = cpcv_meta_run(X, y, net_med, net_p90, t_hr, era_new)
    for s in res["splits"]:
        if s.get("skipped"):
            print(f"  split {s['split']:>2}: SKIPPED (degenerate)")
        else:
            print(f"  split {s['split']:>2}: tau={s['tau']} "
                  f"kept {s['n_kept']}/{s['n_test']} ({s['retention']:.0%}) "
                  f"PF {s['pf_unfiltered']} -> {s['pf_kept']} "
                  f"exp_kept ${s['exp_kept']}")
    p = res["pooled"]
    print(f"\npooled OOS: PF {p['pf_unfiltered']:.3f} -> {p['pf_filtered']:.3f} "
          f"(uplift {p['uplift']:+.3f}) | old {p['pf_filtered_old']:.3f} "
          f"new {p['pf_filtered_new']:.3f} | p90 {p['pf_filtered_p90']:.3f} | "
          f"retention {p['retention_unique']:.0%} "
          f"(n_unique={p['n_kept_unique']}) | positive splits "
          f"{p['positive_splits']}/15")

    print("\n== SHUFFLED-LABEL CONTROL ==", flush=True)
    ctrl = cpcv_meta_run(X, y, net_med, net_p90, t_hr, era_new,
                         shuffle_labels=True)
    cp = ctrl["pooled"]
    print(f"control pooled OOS: PF {cp['pf_unfiltered']:.3f} -> "
          f"{cp['pf_filtered']:.3f} (uplift {cp['uplift']:+.3f})")
    ctrl_gates = evaluate_gates(ctrl)
    control_ok = not all(ctrl_gates.values())

    # ── suspicion-clause diagnostics (overshoot_atr) ─────────────────────
    # per-era point-biserial correlation of overshoot with the label
    ov = X["overshoot_atr"].to_numpy()
    def _corr(a, b):
        m = np.isfinite(a) & np.isfinite(b)
        return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 2 else float("nan")
    corr_old = _corr(ov[~era_new], y[~era_new].astype(float))
    corr_new = _corr(ov[era_new], y[era_new].astype(float))
    from sklearn.inspection import permutation_importance
    from meta_lab import _fit_calibrated
    model_diag = _fit_calibrated(X.to_numpy(float), y)
    imp = permutation_importance(model_diag, X.to_numpy(float), y,
                                 n_repeats=10, random_state=42)
    ranks = pd.Series(imp.importances_mean, index=FEATURES) \
        .sort_values(ascending=False)
    overshoot_rank = int(list(ranks.index).index("overshoot_atr")) + 1
    sign_flip = np.isfinite(corr_old) and np.isfinite(corr_new) \
        and np.sign(corr_old) != np.sign(corr_new) \
        and min(abs(corr_old), abs(corr_new)) > 0.02
    voided = overshoot_rank == 1 and sign_flip
    print(f"\nsuspicion clause: overshoot importance rank {overshoot_rank}/8; "
          f"corr(overshoot,y) old {corr_old:+.3f} new {corr_new:+.3f} "
          f"-> {'VOIDED' if voided else 'not triggered'}")
    print(f"importance order: {list(ranks.index)}")

    # ── gates + decision tree ────────────────────────────────────────────
    gates = evaluate_gates(res)
    gates["7_shuffled_control_fails"] = control_ok
    hm_pass = all(gates.values()) and not voided
    if voided:
        verdict = "VOIDED (suspicion clause: round-10 failure signature)"
    elif hm_pass:
        verdict = ("PASS -> shadow mode on demo >= 8 weeks (log-only), "
                   "then enforcing mode at unchanged risk")
    else:
        verdict = ("FAIL -> ML-filter line closed a SECOND time; no third "
                   "attempt until forward journal holds ~950 events")
    print(f"\n  H-M gates: {gates}\n== VERDICT: {verdict} ==")

    out = {"pooled": p, "splits": res["splits"], "control_pooled": cp,
           "gates": gates, "voided": bool(voided),
           "suspicion": {"overshoot_rank": overshoot_rank,
                         "corr_old": corr_old, "corr_new": corr_new,
                         "importance_order": list(ranks.index)},
           "pass": bool(hm_pass), "verdict": verdict,
           "nan_counts": {k: int(v) for k, v in nan_counts.items() if v}}
    (RESULTS / "HM_run.json").write_text(json.dumps(out, indent=1, default=str))

    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  H-M VERDICT RUN (prereg 0a84ca3, "
                f"matrix costs, partial coverage deviation carries).\n")
        for k, v in gates.items():
            f.write(f"            H-M gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            pooled OOS PF {p['pf_unfiltered']:.3f} -> "
                f"{p['pf_filtered']:.3f} (uplift {p['uplift']:+.3f}), old "
                f"{p['pf_filtered_old']:.3f}, new {p['pf_filtered_new']:.3f}, "
                f"p90 {p['pf_filtered_p90']:.3f}, retention "
                f"{p['retention_unique']:.0%}, splits "
                f"{p['positive_splits']}/15; control uplift {cp['uplift']:+.3f}; "
                f"suspicion: overshoot rank {overshoot_rank}, corr "
                f"{corr_old:+.3f}/{corr_new:+.3f}\n")
        f.write(f"            H-M: {verdict}\n")
        f.write(f"            predictions were: Claude MARGINAL-FAIL, Rashed "
                f"MARGINAL\n")
    print(f"\nresults -> {RESULTS / 'HM_run.json'}; verdict appended to "
          f"DECISIONS.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
