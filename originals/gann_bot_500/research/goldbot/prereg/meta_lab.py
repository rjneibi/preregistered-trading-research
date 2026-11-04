"""H-M meta-label laboratory — implements HM_DESIGN.md exactly.

Self-contained pipeline: context series (causal), 8 pinned features, pinned
HistGradientBoosting + Platt calibration, CPCV(6,2) with H1-protocol purging,
train-fold-only threshold selection, shuffled-label control.

No real market data is loaded by importing this module; hm_runner.py (written
only after the HM prereg freeze) wires it to the verdict trade set.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

# ── pinned protocol constants (HM_DESIGN.md §4 — do not edit post-freeze) ──
HGB_PARAMS = dict(max_depth=3, max_iter=200, learning_rate=0.05,
                  min_samples_leaf=25, l2_regularization=1.0,
                  early_stopping=True, validation_fraction=0.15,
                  random_state=42)
TAU_GRID = (0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
TRAIN_RETENTION_MIN = 0.40
N_GROUPS, K_TEST, TAU_H, MARGIN_H = 6, 2, 24, 40
FEATURES = ("hour", "weekday", "tie_entry", "hivol", "vol_pctile_prevday",
            "adx_d1", "news_day", "overshoot_atr")


# ── causal context series ──────────────────────────────────────────────────
def wilder_adx_d1(d1: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder ADX(14) on D1 bars; value at index t uses bars up to AND
    including day t (so callers must .shift(1) for a during-day-t decision)."""
    h = d1["high"].to_numpy(float)
    l = d1["low"].to_numpy(float)
    c = d1["close"].to_numpy(float)
    n = len(d1)
    tr = np.empty(n); pdm = np.zeros(n); ndm = np.zeros(n)
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0
        ndm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    adx = np.full(n, np.nan)
    if n <= 2 * period:
        return pd.Series(adx, index=d1.index, name="adx")
    atr = tr[1:period + 1].sum()
    spdm = pdm[1:period + 1].sum()
    sndm = ndm[1:period + 1].sum()
    dx_hist = []
    for i in range(period + 1, n):
        atr = atr - atr / period + tr[i]
        spdm = spdm - spdm / period + pdm[i]
        sndm = sndm - sndm / period + ndm[i]
        pdi = 100.0 * spdm / atr if atr > 0 else 0.0
        ndi = 100.0 * sndm / atr if atr > 0 else 0.0
        dx = 100.0 * abs(pdi - ndi) / (pdi + ndi) if (pdi + ndi) > 0 else 0.0
        dx_hist.append(dx)
        k = len(dx_hist)
        if k == period:
            adx[i] = float(np.mean(dx_hist))
        elif k > period:
            adx[i] = (adx[i - 1] * (period - 1) + dx) / period
    return pd.Series(adx, index=d1.index, name="adx")


def build_context(m1: pd.DataFrame) -> pd.DataFrame:
    """Per-UTC-day causal context: previous completed day's ADX and relATR
    percentile. Row for day D is safe to use for any decision DURING day D."""
    from regime import daily_rel_atr, trailing_pct_rank  # frozen H2 machinery
    tday = m1.index.tz_convert("UTC").normalize()
    g = m1.groupby(tday)
    d1 = pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(),
                       "close": g["close"].last()})
    adx = wilder_adx_d1(d1.assign(open=g["open"].first()))
    rel = daily_rel_atr(m1)
    pct = trailing_pct_rank(rel, 252)
    # naive-midnight index to align with pivot day keys
    idx = d1.index.tz_localize(None) if d1.index.tz is not None else d1.index
    pct.index = pct.index if pct.index.tz is None else pct.index.tz_localize(None)
    return pd.DataFrame({"adx_d1": adx.shift(1).to_numpy(),
                         "vol_pctile_prevday": pct.shift(1)
                         .reindex(idx).to_numpy()}, index=idx)


def build_features(ev: pd.DataFrame, ctx: pd.DataFrame,
                   news_days: set[str]) -> pd.DataFrame:
    """8 pinned features per event. `ev` needs: event_ts (tz-aware UTC),
    entry_px, level, atr, hivol."""
    ts = pd.to_datetime(ev["event_ts"])
    day = ts.dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
    c = ctx.reindex(day)
    X = pd.DataFrame({
        "hour": ts.dt.hour.to_numpy(),
        "weekday": ts.dt.weekday.to_numpy(),
        "tie_entry": (ts.dt.hour % 4 == 0).astype(int).to_numpy(),
        "hivol": ev["hivol"].astype(int).to_numpy(),
        "vol_pctile_prevday": c["vol_pctile_prevday"].to_numpy(),
        "adx_d1": c["adx_d1"].to_numpy(),
        "news_day": day.dt.strftime("%Y-%m-%d").isin(news_days)
        .astype(int).to_numpy(),
        "overshoot_atr": (np.abs(ev["entry_px"].to_numpy()
                                 - ev["level"].to_numpy())
                          / ev["atr"].to_numpy()),
    })
    assert tuple(X.columns) == FEATURES
    return X


# ── pipeline ───────────────────────────────────────────────────────────────
def _pf(net: np.ndarray) -> float:
    if len(net) == 0:
        return float("nan")
    w, lo = net[net > 0].sum(), net[net <= 0].sum()
    return float(w / abs(lo)) if lo != 0 else float("inf")


def _fit_calibrated(Xtr: np.ndarray, ytr: np.ndarray):
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import HistGradientBoostingClassifier
    base = HistGradientBoostingClassifier(**HGB_PARAMS)
    model = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    model.fit(Xtr, ytr)
    return model


def _pick_tau(p_train: np.ndarray, net_train: np.ndarray) -> float:
    """Pinned policy: max TRAIN filtered PF s.t. retention >= 40%; ties -> lower tau."""
    best_tau, best_pf = TAU_GRID[0], -np.inf
    for tau in TAU_GRID:
        keep = p_train >= tau
        if keep.mean() < TRAIN_RETENTION_MIN:
            continue
        pf = _pf(net_train[keep])
        if np.isfinite(pf) and pf > best_pf + 1e-12:
            best_pf, best_tau = pf, tau
    return best_tau


def cpcv_meta_run(X: pd.DataFrame, y: np.ndarray, net_med: np.ndarray,
                  net_p90: np.ndarray, t_hr: np.ndarray, era_new: np.ndarray,
                  shuffle_labels: bool = False, seed: int = 42) -> dict:
    """The full H-M pipeline. Returns pooled OOS filtered/unfiltered stats,
    per-split records (incl. tau), and gate inputs. With shuffle_labels=True
    the model trains on permuted labels but evaluation uses TRUE nets — the
    negative control."""
    rng = np.random.default_rng(seed)
    y_fit = rng.permutation(y) if shuffle_labels else y
    Xv = X.to_numpy(float)

    lo, hi = int(t_hr.min()), int(t_hr.max())
    edges = np.linspace(lo, hi + 1, N_GROUPS + 1).astype(int)
    bounds = [(int(edges[g]), int(edges[g + 1]) - 1) for g in range(N_GROUPS)]

    splits, pos_splits = [], 0
    kept_med, kept_p90, kept_new = [], [], []
    base_med = []
    kept_unique = np.zeros(len(y), bool)
    for sid, tg in enumerate(combinations(range(N_GROUPS), K_TEST)):
        test = np.zeros(len(y), bool)
        purge = np.zeros(len(y), bool)
        for g in tg:
            g_lo, g_hi = bounds[g]
            test |= (t_hr >= g_lo) & (t_hr <= g_hi)
            purge |= (t_hr >= g_lo - TAU_H) & (t_hr <= g_hi + MARGIN_H)
        train = ~test & ~purge
        if train.sum() < 100 or test.sum() < 10:
            splits.append({"split": sid, "skipped": True})
            continue
        model = _fit_calibrated(Xv[train], y_fit[train])
        p_tr = model.predict_proba(Xv[train])[:, 1]
        tau = _pick_tau(p_tr, net_med[train])
        p_te = model.predict_proba(Xv[test])[:, 1]
        keep = p_te >= tau
        te_idx = np.where(test)[0]
        kept_med.append(net_med[te_idx[keep]])
        kept_p90.append(net_p90[te_idx[keep]])
        kept_new.append(era_new[te_idx[keep]])
        base_med.append(net_med[te_idx])
        kept_unique[te_idx[keep]] = True
        exp_kept = float(net_med[te_idx[keep]].mean()) if keep.any() else float("nan")
        if keep.any() and exp_kept > 0:
            pos_splits += 1
        splits.append({"split": sid, "tau": tau,
                       "n_test": int(test.sum()), "n_kept": int(keep.sum()),
                       "retention": round(float(keep.mean()), 3),
                       "pf_kept": round(_pf(net_med[te_idx[keep]]), 3),
                       "pf_unfiltered": round(_pf(net_med[te_idx]), 3),
                       "exp_kept": round(exp_kept, 2) if keep.any() else None})

    km = np.concatenate(kept_med) if kept_med else np.array([])
    kp = np.concatenate(kept_p90) if kept_p90 else np.array([])
    kn = np.concatenate(kept_new) if kept_new else np.array([], bool)
    bm = np.concatenate(base_med) if base_med else np.array([])
    return {
        "shuffled": shuffle_labels,
        "splits": splits,
        "pooled": {
            "pf_filtered": _pf(km), "pf_unfiltered": _pf(bm),
            "uplift": _pf(km) - _pf(bm) if len(km) and len(bm) else float("nan"),
            "pf_filtered_p90": _pf(kp),
            "pf_filtered_old": _pf(km[~kn]) if len(km) else float("nan"),
            "pf_filtered_new": _pf(km[kn]) if len(km) else float("nan"),
            "n_kept_pooled": int(len(km)),
            "n_kept_unique": int(kept_unique.sum()),
            "retention_unique": float(kept_unique.mean()),
            "positive_splits": pos_splits,
        },
    }


def evaluate_gates(res: dict) -> dict:
    """HM_PREREGISTRATION.md gates 1–6 on a cpcv_meta_run result."""
    p = res["pooled"]
    return {
        "1_filtered_pf_ge_1.40": p["pf_filtered"] >= 1.40,
        "2_uplift_ge_0.15": p["uplift"] >= 0.15,
        "3_old_era_pf_ge_1.05": p["pf_filtered_old"] >= 1.05,
        "4_retention_ge_40pct_and_n_ge_200": (p["retention_unique"] >= 0.40
                                              and p["n_kept_unique"] >= 200),
        "5_splits_ge_11of15": p["positive_splits"] >= 11,
        "6_p90_pf_ge_1.15": p["pf_filtered_p90"] >= 1.15,
    }
