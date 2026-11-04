"""Module F — 3-class calibrated classifier on resolution_type.

Pipeline per CPCV split:
  1. Fit an xgboost ``multi:softprob`` model on the purged training rows, target =
     ``resolution_type`` in {TP, SL, TIMEOUT}.
  2. Carve a CALIBRATION slice from INSIDE the purged training set — the last 20%
     of train by time — and purge it from the model-fitting subset so the
     calibrator sees only out-of-model scores.
  3. Fit one-vs-rest Inductive Venn-Abers per class on that calibration slice and
     renormalise the three calibrated point probabilities to sum to 1.
  4. Score the TEST fold EXACTLY ONCE. No fitting of any kind touches test data.

Reported: ECE with ADAPTIVE (equal-mass) binning and Brier, per class and macro.

HONESTY NOTE
------------
Venn-Abers' distribution-free validity guarantee assumes exchangeability, which
financial time series violate (serial correlation, regime drift). Treat the VA
output here as *robust empirical calibration*, not a guaranteed one. Likewise the
per-class-then-renormalise step is a practical approximation, NOT coherent
multiclass Venn-Abers — multiclass VA is not a simple product of OVR predictors.
For tractability the calibration slice and the score grid used by the isotonic
augmentation are capped; both are documented approximations, consistent with the
above (this is empirical calibration, not a theorem).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBClassifier

from config import Config

CLASSES = ["TP", "SL", "TIMEOUT"]
_CLASS_TO_INT = {c: i for i, c in enumerate(CLASSES)}
_CAL_CAP = 600          # max calibration points fed to the isotonic augmentation
_SCORE_DECIMALS = 3     # bin test scores to this precision for unique evaluation


def _ivap_calibrate(
    cal_scores: np.ndarray, cal_labels: np.ndarray, test_scores: np.ndarray
) -> np.ndarray:
    """Inductive Venn-Abers point prediction p1 / (1 - p0 + p1), one class (OVR).

    ``cal_scores`` are model scores on the calibration slice; ``cal_labels`` the
    binary OVR targets. For each (binned) test score we fit isotonic regression
    twice — augmenting the calibration set with the test point labelled 0 then 1 —
    and read the regressed value at the test score. Evaluations are deduplicated
    over a score grid for speed.
    """
    if len(cal_scores) > _CAL_CAP:
        # Even thinning by time order keeps the slice representative.
        sel = np.linspace(0, len(cal_scores) - 1, _CAL_CAP).astype(int)
        cal_scores = cal_scores[sel]
        cal_labels = cal_labels[sel]

    uniq = np.round(test_scores, _SCORE_DECIMALS)
    grid = np.unique(uniq)
    p_by_grid: dict[float, float] = {}
    for s in grid:
        aug_x = np.append(cal_scores, s)
        iso0 = IsotonicRegression(out_of_bounds="clip")
        iso1 = IsotonicRegression(out_of_bounds="clip")
        iso0.fit(aug_x, np.append(cal_labels, 0.0))
        iso1.fit(aug_x, np.append(cal_labels, 1.0))
        p0 = float(iso0.predict([s])[0])
        p1 = float(iso1.predict([s])[0])
        denom = 1.0 - p0 + p1
        p_by_grid[float(s)] = p1 / denom if denom > 1e-12 else p1
    return np.array([p_by_grid[float(s)] for s in uniq])


@dataclass
class SplitCalibration:
    """Calibrated probabilities for one split's test fold."""

    test_idx: np.ndarray
    proba: np.ndarray          # (n_test, 3) renormalised calibrated probs
    y_true: np.ndarray         # (n_test,) integer class labels


def fit_and_calibrate_split(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    cfg: Config,
) -> SplitCalibration:
    """Fit + calibrate on one split and score its test fold exactly once."""
    y_all = labels["resolution_type"].map(_CLASS_TO_INT).to_numpy()

    # Train rows ordered by time (signal bar) so the calibration carve is the
    # temporally-last 20% — never reorder by anything that could peek ahead.
    order = np.argsort(labels["signal_idx"].to_numpy()[train_idx], kind="stable")
    train_sorted = train_idx[order]
    n_train = len(train_sorted)
    n_cal = max(1, int(round(0.2 * n_train)))
    model_idx = train_sorted[: n_train - n_cal]
    cal_idx = train_sorted[n_train - n_cal:]
    if len(model_idx) == 0:  # degenerate tiny split guard
        model_idx = train_sorted
        cal_idx = train_sorted

    x_cols = list(features.columns)
    x_model = features.iloc[model_idx][x_cols].to_numpy()
    y_model = y_all[model_idx]
    x_cal = features.iloc[cal_idx][x_cols].to_numpy()
    y_cal = y_all[cal_idx]
    x_test = features.iloc[test_idx][x_cols].to_numpy()
    y_test = y_all[test_idx]

    clf = XGBClassifier(
        objective="multi:softprob",
        num_class=3,
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        tree_method="hist",
        random_state=cfg.RANDOM_SEED,
        n_jobs=0,
        eval_metric="mlogloss",
    )
    clf.fit(x_model, y_model)

    cal_raw = clf.predict_proba(x_cal)    # uncalibrated scores on cal slice
    test_raw = clf.predict_proba(x_test)  # uncalibrated scores on test fold

    # OVR Venn-Abers per class, then renormalise to a simplex.
    cal_cols = []
    for c in range(3):
        cal_cols.append(
            _ivap_calibrate(cal_raw[:, c], (y_cal == c).astype(float), test_raw[:, c])
        )
    cal_mat = np.column_stack(cal_cols)
    row_sum = cal_mat.sum(axis=1, keepdims=True)
    row_sum[row_sum <= 1e-12] = 1.0
    cal_mat = cal_mat / row_sum

    return SplitCalibration(test_idx=test_idx, proba=cal_mat, y_true=y_test)


def adaptive_ece(prob: np.ndarray, hit: np.ndarray, n_bins: int = 10) -> float:
    """ECE with equal-MASS (adaptive) bins for one OVR class.

    ``prob`` = calibrated prob of the class; ``hit`` = 1 if that class occurred.
    """
    n = len(prob)
    if n == 0:
        return float("nan")
    order = np.argsort(prob)
    prob_s = prob[order]
    hit_s = hit[order]
    bins = np.array_split(np.arange(n), min(n_bins, n))
    ece = 0.0
    for b in bins:
        if len(b) == 0:
            continue
        conf = prob_s[b].mean()
        acc = hit_s[b].mean()
        ece += (len(b) / n) * abs(acc - conf)
    return float(ece)


def calibration_report(pooled: list[SplitCalibration]) -> dict:
    """Pool all OOS test predictions and compute per-class + macro ECE/Brier."""
    proba = np.vstack([p.proba for p in pooled])
    y = np.concatenate([p.y_true for p in pooled])

    per_class = {}
    eces, briers = [], []
    for c, name in enumerate(CLASSES):
        hit = (y == c).astype(float)
        p = proba[:, c]
        ece = adaptive_ece(p, hit)
        brier = float(np.mean((p - hit) ** 2))
        per_class[name] = {"ece": ece, "brier": brier}
        eces.append(ece)
        briers.append(brier)

    return {
        "n_pooled": int(len(y)),
        "per_class": per_class,
        "macro_ece": float(np.nanmean(eces)),
        "macro_brier": float(np.mean(briers)),
    }
