"""Module I (real) — validate the labeling + sizing core on REAL XAUUSD H1 history.

Mirrors run_validation.py, but:
  * bars come from real_data.load(<h1_csv>) instead of the synthetic generator;
  * the ENTRY RULE is NOT reinvented here. Signals are read from a precomputed CSV
    produced OUTSIDE this quarantine by the real live stack (signals.evaluate_signal
    over history, with MetaTrader5). This file never imports MetaTrader5 and never
    invents a rule — it only ingests (bar t, side) and runs everything downstream.

Every gating assert from the synthetic harness is preserved:
  OHLC coherence (in real_data.load), entry_idx == t + N_CONFIRM, non-empty CPCV
  train/test (RuntimeError if any fold empty), zero-violation leakage probe, and
  the feature causality probe. Additions for real data:
  (a) per-split train/test counts + surviving train fraction; loud WARNING if any
      split's train count < 200 (the data-budget signal — not a crash);
  (b) signals sourced from the real rule via CSV;
  (c) pooled OOS calibration (macro + per-class ECE/Brier) and, per CPCV path, the
      realized edge of the sizing decisions (IS/OOS alignment / walk-forward read).

Runtime caveat: USE_HMM_REGIME=True with L_FEATURE_MAX=1512 over ~25k real bars
takes several minutes (rolling HMM refits + 15 XGBoost/Venn-Abers splits).

Usage:
    python run_real.py <h1_ohlc_csv> <signals_csv> [--profile D|R]
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from itertools import combinations

import numpy as np
import pandas as pd

import real_data
from calibration import CLASSES, calibration_report, fit_and_calibrate_split
from config import CONFIG, Config
from cpcv import CombinatorialPurgedCV
from features import assert_no_forward_leak, compute_features
from labeler import label_signals
from optimizer import Setups, solve_sizing
from tail_loss import fit_tail_loss
from timeout_baseline import estimate_timeout_means

_SIDE_MAP = {
    "1": 1, "+1": 1, "buy": 1, "long": 1, "b": 1,
    "-1": -1, "sell": -1, "short": -1, "s": -1,
}


def _print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


# --------------------------------------------------------------------------- #
# Signal CSV ingestion (the live rule's output, produced outside the quarantine)
# --------------------------------------------------------------------------- #
def load_signal_csv(
    path: str, df: pd.DataFrame, profile: str | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Read precomputed signals and align them to positional H1 bar indices.

    Expected columns: ``side`` (+1/-1 or BUY/SELL/long/short) and a time key —
    either ``datetime`` (matched to the H1 index) or ``bar_idx`` (positional).
    Optional ``profile`` (D/R) filtered by ``--profile``. Each kept row yields a
    (signal bar t, side). Timestamps not matching an H1 bar are reported and
    dropped — never silently snapped.
    """
    sig = pd.read_csv(path)
    sig.columns = [str(c).strip().lower() for c in sig.columns]
    if "side" not in sig.columns:
        raise ValueError("signals CSV missing required 'side' column")
    if profile is not None and "profile" in sig.columns:
        before = len(sig)
        sig = sig[sig["profile"].astype(str).str.upper() == profile.upper()]
        print(f"[signals] profile={profile}: kept {len(sig)}/{before} rows")

    # Parse side.
    side = (
        sig["side"].astype(str).str.strip().str.lower().map(_SIDE_MAP).to_numpy()
    )
    if np.any(pd.isna(side)):
        bad = int(pd.isna(side).sum())
        raise ValueError(f"signals CSV has {bad} unparseable 'side' values")
    side = side.astype(int)

    # Map to positional bar index.
    pos_of_time = pd.Series(np.arange(len(df)), index=df.index)
    if "bar_idx" in sig.columns:
        t = pd.to_numeric(sig["bar_idx"], errors="coerce").to_numpy()
        ok = ~np.isnan(t)
    elif "datetime" in sig.columns:
        ts = pd.to_datetime(sig["datetime"], utc=True, errors="coerce")
        ts = pd.DatetimeIndex(ts).tz_localize(None)
        t = pos_of_time.reindex(ts).to_numpy()
        ok = ~np.isnan(t)
    elif "time" in sig.columns:
        ts = pd.to_datetime(sig["time"], unit="s", utc=True, errors="coerce")
        ts = pd.DatetimeIndex(ts).tz_localize(None)
        t = pos_of_time.reindex(ts).to_numpy()
        ok = ~np.isnan(t)
    else:
        raise ValueError("signals CSV needs a 'datetime', 'time', or 'bar_idx' column")

    n_unmatched = int((~ok).sum())
    if n_unmatched:
        print(f"[signals] WARNING: {n_unmatched} signal rows did not match an H1 bar "
              f"(dropped, not snapped)")
    t = t[ok].astype(int)
    side = side[ok]
    # Sort by bar and drop exact duplicate (bar, side) pairs.
    order = np.argsort(t, kind="stable")
    t, side = t[order], side[order]
    _, uniq = np.unique(t, return_index=True)
    if len(uniq) != len(t):
        print(f"[signals] dropped {len(t) - len(uniq)} duplicate-bar signals (kept first)")
    t, side = t[uniq], side[uniq]
    return t, side


# --------------------------------------------------------------------------- #
# Real SL-breach overshoots (return units) for the GPD tail model
# --------------------------------------------------------------------------- #
def compute_sl_overshoots(
    df: pd.DataFrame, labels: pd.DataFrame, cfg: Config
) -> np.ndarray:
    """Measure how far price gapped past the stop on each SL-resolved real trade.

    This is measurement of the same barrier geometry, NOT a new entry rule. For an
    SL row we re-scan to the breaching bar and record (in return units) the excess
    of price beyond the stop level — the empirical slippage tail on real data.
    """
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    out: list[float] = []
    sl_rows = labels[labels["resolution_type"] == "SL"]
    for _, r in sl_rows.iterrows():
        entry_idx = int(r["entry_idx"])
        side = int(r["side"])
        entry = float(r["entry_price"])
        d_sl = float(r["D_SL"])
        sl_level = entry - d_sl if side == 1 else entry + d_sl
        horizon_end = int(r["label_horizon_end"])
        for j in range(entry_idx + 1, horizon_end + 1):
            if side == 1 and low[j] <= sl_level:
                out.append(max(0.0, (sl_level - low[j]) / entry))
                break
            if side == -1 and high[j] >= sl_level:
                out.append(max(0.0, (high[j] - sl_level) / entry))
                break
    return np.asarray(out, dtype=float)


# --------------------------------------------------------------------------- #
# CPCV backtest-path assignment (de Prado): 6 groups, k=2 -> 5 paths
# --------------------------------------------------------------------------- #
def _group_of(t_value: int, bounds: list[tuple[int, int]]) -> int:
    for g, (lo, hi) in enumerate(bounds):
        if lo <= t_value <= hi:
            return g
    return len(bounds) - 1  # clamp the right edge


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-data validation of labelsizing_core")
    ap.add_argument("h1_csv", help="path to real XAUUSD H1 OHLC CSV/parquet")
    ap.add_argument("signals_csv", help="path to precomputed signals CSV (live rule)")
    ap.add_argument("--profile", default=None, help="filter signals by profile (D/R)")
    args = ap.parse_args()

    cfg = CONFIG

    # --- 1. real data + coherence assert (raises loudly on bad bars) --------
    _print_header("1. REAL DATA")
    df = real_data.load(args.h1_csv)  # runs coherence report + assert internally
    print(f"shape: {df.shape}  index: {df.index[0]} .. {df.index[-1]}")

    # --- 2. ingest live-rule signals + LOUD sanity check --------------------
    _print_header("2. SIGNALS (live rule via CSV) + SANITY")
    sig_t, sig_side = load_signal_csv(args.signals_csv, df, args.profile)
    print(f"signals ingested: {len(sig_t)}  "
          f"(BUY={int((sig_side == 1).sum())}  SELL={int((sig_side == -1).sum())})")
    if len(sig_t) == 0:
        raise RuntimeError("no signals matched the H1 frame — check the export/alignment")
    # frequency by year so it can be compared to live profile trade cadence
    yrs = df.index[sig_t].year
    freq = pd.Series(yrs).value_counts().sort_index()
    print("signals per year:")
    for y, c in freq.items():
        print(f"  {y}: {int(c)}")

    labels = label_signals(df, sig_t, sig_side, cfg).reset_index(drop=True)
    if labels.empty:
        raise RuntimeError("no labelable signals (all too close to series end?)")
    dist = labels["resolution_type"].value_counts()
    print(f"\nlabelled signals: {len(labels)}")
    for k in ("TP", "SL", "TIMEOUT"):
        cnt = int(dist.get(k, 0))
        print(f"  {k:8s}: {cnt:6d}  ({100*cnt/len(labels):5.1f}%)")
    # honest degeneracy flags (warn, do not crash)
    for k in ("TP", "SL", "TIMEOUT"):
        frac = dist.get(k, 0) / len(labels)
        if frac < 0.01:
            print(f"  WARNING: class {k} is {100*frac:.2f}% of labels — near-degenerate")
    if dist.get("TIMEOUT", 0) / len(labels) > 0.5:
        print("  WARNING: >50% TIMEOUT — barrier geometry may not fit this regime")
    s0 = labels.iloc[0]
    assert int(s0.entry_idx - s0.signal_idx) == cfg.N_CONFIRM
    print(f"entry geometry: entry_idx - signal_idx = {cfg.N_CONFIRM} == N_CONFIRM  -> PASS")

    # --- features aligned to each signal bar t ------------------------------
    print("\nbuilding causal features (HMM on, L=1512) — this is the slow step ...")
    feats = compute_features(df, cfg)
    feat_aligned = feats.iloc[labels["signal_idx"].to_numpy()].reset_index(drop=True)
    good = feat_aligned.notna().all(axis=1).to_numpy()
    n_drop = int((~good).sum())
    labels = labels.loc[good].reset_index(drop=True)
    feat_aligned = feat_aligned.loc[good].reset_index(drop=True)
    print(f"rows after dropping warmup-NaN features: {len(labels)} (dropped {n_drop})")
    if len(labels) < 50:
        raise RuntimeError(f"too few usable labelled rows ({len(labels)}) for CPCV")

    probe_idx = [int(len(df) * 0.45), int(len(df) * 0.72)]
    assert_no_forward_leak(df, cfg, probe_idx)
    print(f"feature causality probe at {probe_idx}: PASS (prefix == full)")

    # --- 3. CPCV with train-budget visibility -------------------------------
    _print_header("3. CPCV (N=6, k=2 -> 15 splits, 5 paths) — PURGE COST")
    cv = CombinatorialPurgedCV(cfg)
    splits = list(cv.split(labels))  # raises RuntimeError if any fold empty
    n_total = len(labels)
    low_budget = False
    for tr, te, sid in splits:
        frac = len(tr) / n_total
        flag = ""
        if len(tr) < 200:
            flag = "  <<< WARNING: train<200 (data-budget too thin)"
            low_budget = True
        print(f"  split {sid:2d}: train={len(tr):6d} ({frac:5.1%} survive)  "
              f"test={len(te):6d}{flag}")
    if low_budget:
        print("\nWARNING: at least one split has <200 training rows after the 1512-bar "
              "purge. Calibration on those folds is unreliable; treat results as "
              "data-starved, not as a verdict.")

    # --- 4. leakage probe ---------------------------------------------------
    _print_header("4. LEAKAGE PROBE")
    t_vals = labels["signal_idx"].to_numpy()
    bounds = cv._group_bounds(t_vals)
    right_margin = max(cfg.EMBARGO, cfg.L_FEATURE_MAX)
    violations = 0
    for sid, test_groups in enumerate(combinations(range(cfg.N_GROUPS), cfg.K_TEST)):
        tr, _, _ = splits[sid]
        train_t = t_vals[tr]
        for g in test_groups:
            g_lo, g_hi = bounds[g]
            violations += int(np.sum((train_t >= g_lo - cfg.TAU_MAX)
                                     & (train_t <= g_hi + right_margin)))
    assert violations == 0, f"leakage probe found {violations} purge-band violations"
    print(f"train rows inside any purge band: {violations}  -> PASS")

    # --- 5. calibrated classifier + pooled OOS metrics ----------------------
    _print_header("5. CALIBRATION (pooled OOS ECE / Brier)")
    per_split_cal = {}
    timeout_means = {}
    for tr, te, sid in splits:
        timeout_means[sid] = estimate_timeout_means(labels, tr, sid)
        per_split_cal[sid] = fit_and_calibrate_split(feat_aligned, labels, tr, te, cfg)
        print(f"  split {sid:2d} scored: test={len(te):5d}")
    rep = calibration_report(list(per_split_cal.values()))
    print(f"\npooled OOS predictions: {rep['n_pooled']}")
    for name in CLASSES:
        pc = rep["per_class"][name]
        print(f"  {name:8s}: ECE={pc['ece']:.4f}  Brier={pc['brier']:.4f}")
    print(f"  {'MACRO':8s}: ECE={rep['macro_ece']:.4f}  Brier={rep['macro_brier']:.4f}")

    # --- 6. GPD tail loss from REAL SL-breach overshoots --------------------
    _print_header("6. GPD TAIL LOSS (real SL-breach overshoots)")
    overshoots = compute_sl_overshoots(df, labels, cfg)
    med_price = float(df["close"].median())
    med_atr = float(feats["atr14"].median())
    d_sl_ret = cfg.K_SL_ATR * med_atr / med_price
    tail = fit_tail_loss(overshoots, d_sl=d_sl_ret, cfg=cfg)
    print(f"nominal D_SL (return units): {d_sl_ret:.6f}")
    print(f"real SL-breach overshoots: {len(overshoots)}  exceedances={tail.n_exceedances}")
    print(f"xi_hat={tail.xi_hat:.4f}  xi_clamped={tail.xi_clamped:.4f}  "
          f"used_gpd={tail.used_gpd}")
    print(f"E[slippage|breach]={tail.expected_slippage:.6f}  D-bar_SL={tail.d_bar_sl:.6f}")

    # --- 7. sizing LP (M=5) + CVaR exception check --------------------------
    _print_header("7. SIZING LP (M=5) + CVaR EXCEPTION CHECK")
    last_sid = max(per_split_cal)
    setups, w0 = _build_setups(per_split_cal[last_sid], labels, tail, cfg)
    res = solve_sizing(setups, w0, cfg)
    print(f"mode={res.mode}  status={res.status}")
    print(f"w = {np.round(res.w, 5)}")
    print(f"sum|w| = {np.sum(np.abs(res.w)):.5f} (MAX_EXPOSURE={cfg.MAX_EXPOSURE})  "
          f"CVaR_{cfg.CVAR_ALPHA:.2f}={res.cvar_value:.5f} (limit {cfg.CVAR_LIMIT})")
    loss = -(res.scenarios @ res.w)
    exc_rate = float(np.mean(loss > cfg.CVAR_LIMIT))
    bound = (1.0 - cfg.CVAR_ALPHA) + 0.02
    print(f"scenario CVaR-exception rate: {exc_rate:.4f} <= {bound:.4f} ? "
          f"{'PASS' if exc_rate <= bound else 'FAIL'}")

    # de-risk fallback demonstration (kept from the synthetic harness)
    sum_w0 = float(np.sum(np.abs(w0)))
    cfg_inf = replace(cfg, MAX_EXPOSURE=0.3 * sum_w0, MAX_TURNOVER=0.1)
    res2 = solve_sizing(setups, w0, cfg_inf, turnover_hard=True)
    assert res2.mode == "derisk_to_cash"
    print(f"forced-infeasible -> fallback mode={res2.mode}: PASS "
          f"(sum|w0|={sum_w0:.2f} -> sum|w|={np.sum(np.abs(res2.w)):.2f})")

    # --- 8. WALK-FORWARD READ: per-CPCV-path realized edge ------------------
    _print_header("8. WALK-FORWARD READ (per-path realized edge; no go/no-go)")
    _walk_forward_read(labels, per_split_cal, timeout_means, tail, bounds, cfg)

    _print_header("REAL-DATA RUN COMPLETE — all gating asserts passed")
    print("NOTE: gating asserts passing means the harness is sound on real bars. The "
          "edge numbers above are descriptive; judge IS/OOS alignment and the path "
          "spread against your gate — this script intentionally declares no verdict.")


def _realized_return(row: pd.Series, d_sl_ret: float, slip: float) -> float:
    """Directional realized return (return units) of a resolved trade."""
    entry = float(row["entry_price"])
    if row["resolution_type"] == "TP":
        return float(row["D_TP"]) / entry
    if row["resolution_type"] == "SL":
        return -(float(row["D_SL"]) / entry + slip)
    return float(row["realized_return"])  # TIMEOUT (already signed by side)


def _walk_forward_read(labels, per_split_cal, timeout_means, tail, bounds, cfg) -> None:
    """Per-path realized edge of the sizing decisions + sign/spread alignment.

    The raw rule edge (realized return of every signal) is path-independent; the
    SIZED edge (mean realized return of trades the model would size into, E[R]>0)
    varies by path because each path scores rows with a different purged model.
    """
    combos = list(combinations(range(cfg.N_GROUPS), cfg.K_TEST))
    # occurrences[g] = ordered split_ids where group g is a test group (len 5)
    occ: dict[int, list[int]] = {g: [] for g in range(cfg.N_GROUPS)}
    for sid, combo in enumerate(combos):
        for g in combo:
            occ[g].append(sid)
    n_paths = len(occ[0])

    # proba lookup: split_id -> {row_position -> proba vector}
    proba_lookup: dict[int, dict[int, np.ndarray]] = {}
    for sid, cal in per_split_cal.items():
        proba_lookup[sid] = {int(p): cal.proba[i] for i, p in enumerate(cal.test_idx)}

    t_vals = labels["signal_idx"].to_numpy()
    row_group = np.array([_group_of(int(t), bounds) for t in t_vals])

    # path-independent raw edge
    raw = np.array([_realized_return(labels.iloc[i], 0.0, tail.expected_slippage)
                    for i in range(len(labels))])
    print(f"raw rule edge (all {len(raw)} signals, path-independent): "
          f"mean={raw.mean():+.5f}  median={np.median(raw):+.5f}  "
          f"win%={100*np.mean(raw > 0):.1f}")

    print("\nper-path SIZED edge (trades with model E[R]>0):")
    sized_means = []
    for p in range(n_paths):
        rr, taken = [], 0
        for i in range(len(labels)):
            g = int(row_group[i])
            sid = occ[g][p]
            proba = proba_lookup[sid].get(i)
            if proba is None:
                continue
            row = labels.iloc[i]
            entry = float(row["entry_price"])
            d_tp_ret = float(row["D_TP"]) / entry
            dbar_sl_ret = float(row["D_SL"]) / entry + tail.expected_slippage
            side = int(row["side"])
            rbar = timeout_means[sid].get(side, 0.0)
            er = proba[0] * d_tp_ret - proba[1] * dbar_sl_ret + proba[2] * rbar
            if er > 0:
                taken += 1
                rr.append(_realized_return(row, 0.0, tail.expected_slippage))
        if rr:
            m = float(np.mean(rr))
            sized_means.append(m)
            print(f"  path {p}: taken={taken:5d}/{len(labels)}  "
                  f"sized_edge={m:+.5f}  win%={100*np.mean(np.array(rr) > 0):.1f}")
        else:
            print(f"  path {p}: taken=0 (model sized into nothing)")

    if sized_means:
        arr = np.array(sized_means)
        same_sign = bool(np.all(arr > 0) or np.all(arr < 0))
        print(f"\nwalk-forward alignment: {len(arr)} paths  "
              f"mean={arr.mean():+.5f}  spread=[{arr.min():+.5f}, {arr.max():+.5f}]  "
              f"all-same-sign={same_sign}")
        print("(Sign agreement across paths + a tight spread = consistent edge; "
              "wide spread or mixed signs = regime/luck. Your call against the gate.)")


def _build_setups(cal, labels, tail, cfg) -> tuple[Setups, np.ndarray]:
    """M=5 setups (calibrated probs + return-unit barriers) and a starting book."""
    k = min(5, len(cal.test_idx))
    proba = cal.proba[:k]
    rows = labels.iloc[cal.test_idx[:k]]
    entry = rows["entry_price"].to_numpy()
    d_tp = rows["D_TP"].to_numpy() / entry
    d_sl = rows["D_SL"].to_numpy() / entry
    dbar_sl = d_sl + tail.expected_slippage
    rbar_to = np.full(k, float(
        labels.loc[labels["resolution_type"] == "TIMEOUT", "realized_return"].mean()
        if (labels["resolution_type"] == "TIMEOUT").any() else 0.0
    ))
    setups = Setups(
        p_tp=proba[:, 0], p_sl=proba[:, 1], p_to=proba[:, 2],
        d_tp=d_tp, dbar_sl=dbar_sl, rbar_to=rbar_to,
    )
    w0 = np.full(k, 1.0 / k)
    return setups, w0


if __name__ == "__main__":
    main()
