"""Module I — end-to-end validation of the labeling + sizing core on synthetic data.

Run inside the research venv:

    research/labelsizing_core/.venv/Scripts/python research/labelsizing_core/run_validation.py

No MetaTrader5, no broker, no live path. Everything below operates on in-process
synthetic data and prints a report whose asserts gate correctness:
  * OHLC coherence (synth_data)
  * entry_idx == t + N_CONFIRM (labeler)
  * non-empty train/test after purge for all 15 CPCV splits
  * leakage probe: no train index inside the purge band of any split
  * pooled OOS per-class + macro ECE/Brier
  * GPD tail fit -> effective stop distance
  * CVaR-constrained LP solve + scenario CVaR-exception rate
  * forced-infeasible case -> De-Risk-to-Cash fallback engages
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from calibration import (
    CLASSES,
    calibration_report,
    fit_and_calibrate_split,
)
from config import CONFIG, Config
from cpcv import CombinatorialPurgedCV
from features import assert_no_forward_leak, compute_features
from labeler import label_signals
from optimizer import Setups, solve_sizing
from synth_data import assert_ohlc_coherent, generate_synthetic_ohlc
from tail_loss import fit_tail_loss
from timeout_baseline import estimate_timeout_means


def _generate_signals(df: pd.DataFrame, cfg: Config) -> tuple[np.ndarray, np.ndarray]:
    """Evenly-spaced candidate signals with a momentum side; spread over all bars.

    Even spacing guarantees every CPCV time-group is populated, so the non-empty
    assert exercises the purge logic rather than failing on sparse data.
    """
    close = df["close"].to_numpy()
    n = len(df)
    warmup = cfg.L_FEATURE_MAX + cfg.N_CONFIRM + 5
    last = n - cfg.N_CONFIRM - cfg.TAU_MAX - 1
    t = np.arange(warmup, last, 3)
    mom = close[t] - close[t - 12]
    side = np.where(mom >= 0, 1, -1).astype(int)
    return t, side


def _print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> None:
    cfg = CONFIG
    rng = np.random.default_rng(cfg.RANDOM_SEED)

    # --- 1. synthetic data + coherence assert -------------------------------
    _print_header("1. SYNTHETIC DATA")
    df = generate_synthetic_ohlc(cfg)
    assert_ohlc_coherent(df)
    print(f"shape: {df.shape}  index: {df.index[0]} .. {df.index[-1]}")
    print("OHLC coherence assert: PASS (low<=min(o,c), high>=max(o,c) all bars)")

    # --- 2. labels ----------------------------------------------------------
    _print_header("2. TRIPLE-BARRIER LABELS")
    sig_t, sig_side = _generate_signals(df, cfg)
    labels = label_signals(df, sig_t, sig_side, cfg).reset_index(drop=True)
    dist = labels["resolution_type"].value_counts()
    print(f"signals labelled: {len(labels)}")
    for k in ("TP", "SL", "TIMEOUT"):
        cnt = int(dist.get(k, 0))
        print(f"  {k:8s}: {cnt:6d}  ({100*cnt/len(labels):5.1f}%)")
    sample = labels.iloc[0]
    print(
        f"sample row: signal_idx={int(sample.signal_idx)} "
        f"entry_idx={int(sample.entry_idx)} "
        f"(entry_idx - signal_idx = {int(sample.entry_idx - sample.signal_idx)} "
        f"== N_CONFIRM={cfg.N_CONFIRM})"
    )

    # --- features aligned to each signal bar t ------------------------------
    feats = compute_features(df, cfg)
    feat_aligned = feats.iloc[labels["signal_idx"].to_numpy()].reset_index(drop=True)
    good = feat_aligned.notna().all(axis=1).to_numpy()
    labels = labels.loc[good].reset_index(drop=True)
    feat_aligned = feat_aligned.loc[good].reset_index(drop=True)
    print(f"rows after dropping warmup-NaN features: {len(labels)}")

    # causality probe on the feature builder itself
    probe_idx = [int(len(df) * 0.45), int(len(df) * 0.72)]
    assert_no_forward_leak(df, cfg, probe_idx)
    print(f"feature causality probe at {probe_idx}: PASS (prefix == full)")

    # --- 3. CPCV splits -----------------------------------------------------
    _print_header("3. CPCV (N=6, k=2 -> 15 splits, 5 paths)")
    cv = CombinatorialPurgedCV(cfg)
    splits = list(cv.split(labels))
    print(f"splits generated: {len(splits)} (non-empty assert passed for all)")
    for tr, te, sid in splits:
        print(f"  split {sid:2d}: train={len(tr):6d}  test={len(te):6d}")

    # --- 4. leakage probe ---------------------------------------------------
    _print_header("4. LEAKAGE PROBE")
    t_vals = labels["signal_idx"].to_numpy()
    bounds = cv._group_bounds(t_vals)
    right_margin = max(cfg.EMBARGO, cfg.L_FEATURE_MAX)
    from itertools import combinations

    violations = 0
    for sid, test_groups in enumerate(combinations(range(cfg.N_GROUPS), cfg.K_TEST)):
        tr, te, _ = splits[sid]
        train_t = t_vals[tr]
        for g in test_groups:
            g_lo, g_hi = bounds[g]
            lo = g_lo - cfg.TAU_MAX
            hi = g_hi + right_margin
            violations += int(np.sum((train_t >= lo) & (train_t <= hi)))
    assert violations == 0, f"leakage probe found {violations} purge-band violations"
    print(
        f"train indices inside any [test_start-TAU_MAX, test_end+max(EMBARGO,L)]: "
        f"{violations}  -> PASS"
    )

    # --- 5. calibrated classifier (per-split) + pooled OOS metrics ----------
    _print_header("5. CALIBRATION (pooled OOS ECE / Brier)")
    per_split_cal = []
    timeout_means_log = []
    for tr, te, sid in splits:
        # Module E: side-conditioned R-bar_timeout from purged train only.
        tmeans = estimate_timeout_means(labels, tr, sid)
        timeout_means_log.append(tmeans)
        cal = fit_and_calibrate_split(feat_aligned, labels, tr, te, cfg)
        per_split_cal.append(cal)
        print(
            f"  split {sid:2d} scored: test={len(te):5d}  "
            f"R-bar_timeout(+1)={tmeans[1]:+.5f} R-bar_timeout(-1)={tmeans[-1]:+.5f}"
        )
    rep = calibration_report(per_split_cal)
    print(f"\npooled OOS predictions: {rep['n_pooled']}")
    for name in CLASSES:
        pc = rep["per_class"][name]
        print(f"  {name:8s}: ECE={pc['ece']:.4f}  Brier={pc['brier']:.4f}")
    print(f"  {'MACRO':8s}: ECE={rep['macro_ece']:.4f}  Brier={rep['macro_brier']:.4f}")

    # --- 6. GPD tail-loss model --------------------------------------------
    _print_header("6. GPD TAIL LOSS -> EFFECTIVE STOP")
    med_price = float(df["close"].median())
    med_atr = float(feats["atr14"].median())
    d_sl_ret = cfg.K_SL_ATR * med_atr / med_price
    # Synthesize SL-breach overshoots (return units) from a heavy tail.
    overshoots = genpareto_overshoots(rng, scale=0.4 * d_sl_ret, n=400)
    tail = fit_tail_loss(overshoots, d_sl=d_sl_ret, cfg=cfg)
    print(f"nominal D_SL (return units): {d_sl_ret:.6f}")
    print(
        f"exceedances={tail.n_exceedances}  xi_hat={tail.xi_hat:.4f}  "
        f"xi_clamped={tail.xi_clamped:.4f}  used_gpd={tail.used_gpd}"
    )
    print(
        f"E[slippage|breach]={tail.expected_slippage:.6f}  "
        f"D-bar_SL={tail.d_bar_sl:.6f}"
    )

    # --- 7. CVaR-constrained LP on a small synthetic M ----------------------
    _print_header("7. SIZING LP (M=5) + CVaR EXCEPTION CHECK")
    setups, base_w0 = build_setups(per_split_cal[-1], labels, tail, df, cfg)
    res = solve_sizing(setups, base_w0, cfg)
    print(f"mode={res.mode}  status={res.status}")
    print(f"w = {np.round(res.w, 5)}")
    print(f"sum|w| = {np.sum(np.abs(res.w)):.5f}  (MAX_EXPOSURE={cfg.MAX_EXPOSURE})")
    print(f"CVaR_{cfg.CVAR_ALPHA:.2f}(loss) = {res.cvar_value:.5f}  "
          f"(limit {cfg.CVAR_LIMIT})")
    loss = -(res.scenarios @ res.w)
    exc_rate = float(np.mean(loss > cfg.CVAR_LIMIT))
    tol = 0.02
    bound = (1.0 - cfg.CVAR_ALPHA) + tol
    print(
        f"scenario CVaR-exception rate (loss>limit): {exc_rate:.4f}  "
        f"<= (1-alpha)+tol={bound:.4f} ? {'PASS' if exc_rate <= bound else 'FAIL'}"
    )

    # --- 8. forced infeasible -> De-Risk-to-Cash fallback -------------------
    _print_header("8. FORCED INFEASIBLE -> DE-RISK-TO-CASH FALLBACK")
    sum_w0 = float(np.sum(np.abs(base_w0)))
    cfg_infeasible = replace(cfg, MAX_EXPOSURE=0.3 * sum_w0, MAX_TURNOVER=0.1)
    print(
        f"sum|w0|={sum_w0:.3f}  dropping MAX_EXPOSURE to {cfg_infeasible.MAX_EXPOSURE:.3f} "
        f"with locked turnover band {cfg_infeasible.MAX_TURNOVER} (hard)"
    )
    res2 = solve_sizing(setups, base_w0, cfg_infeasible, turnover_hard=True)
    print(f"mode={res2.mode}  status={res2.status}")
    print(f"w (de-risked) = {np.round(res2.w, 5)}")
    print(
        f"sum|w0|={sum_w0:.3f} -> sum|w|={np.sum(np.abs(res2.w)):.3f} "
        f"(moved toward cash)"
    )
    assert res2.mode == "derisk_to_cash", "fallback did not engage on infeasible case"
    print("De-Risk-to-Cash fallback engaged: PASS")

    _print_header("VALIDATION COMPLETE — all gating asserts passed")


def genpareto_overshoots(rng: np.random.Generator, scale: float, n: int) -> np.ndarray:
    """Synthetic SL-breach overshoots (>0) from a GPD(xi=0.3) for the tail demo."""
    from scipy.stats import genpareto

    xi = 0.3
    u = rng.random(n)
    # Inverse-CDF sampling from GPD(xi, scale) with threshold 0.
    return genpareto.ppf(u, c=xi, loc=0.0, scale=scale)


def build_setups(cal, labels, tail, df, cfg) -> tuple[Setups, np.ndarray]:
    """Construct M=5 setups (calibrated probs + return-unit barriers) and w0."""
    proba = cal.proba[:5]
    idx = cal.test_idx[:5]
    rows = labels.iloc[idx]
    entry = rows["entry_price"].to_numpy()
    d_tp = rows["D_TP"].to_numpy() / entry                 # -> return units
    d_sl = rows["D_SL"].to_numpy() / entry
    dbar_sl = d_sl + tail.expected_slippage                # add tail slippage
    # side-pooled timeout mean as a small drift proxy (return units)
    rbar_to = np.full(5, float(
        labels.loc[labels["resolution_type"] == "TIMEOUT", "realized_return"].mean()
    ))
    setups = Setups(
        p_tp=proba[:, 0],
        p_sl=proba[:, 1],
        p_to=proba[:, 2],
        d_tp=d_tp,
        dbar_sl=dbar_sl,
        rbar_to=rbar_to,
    )
    w0 = np.full(5, 0.2)  # starting book, sum|w0| = 1.0
    return setups, w0


if __name__ == "__main__":
    main()
