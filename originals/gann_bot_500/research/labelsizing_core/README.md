# labelsizing_core — synthetic validation of an H1 XAUUSD ML-LP labeling + sizing core

This is a **research / validation harness only**. It validates the *labeling and
sizing core* of an H1 XAUUSD ML-LP pipeline on **synthetic data generated
in-process**. There is **NO live-execution path**: it does not import
MetaTrader5, dispatch orders, or talk to any broker. Nothing outside this
directory is touched, and the synthetic data never leaves the process.

## What it validates

Triple-barrier ternary labeling (TP / SL / TIMEOUT) with SL-first intrabar
resolution and `t + N_CONFIRM` entry; strictly-causal features (including a
self-contained rolling Gaussian-HMM regime); Combinatorial Purged CV with
asymmetric purge + embargo; per-split side-conditioned timeout baseline;
XGBoost 3-class probabilities calibrated with one-vs-rest Inductive Venn-Abers;
a GPD tail-loss model for the effective stop; and a CVXPY CVaR-constrained sizing
LP with a De-Risk-to-Cash fallback.

## Isolated environment

```
py -3.11 -m venv research/labelsizing_core/.venv
research/labelsizing_core/.venv/Scripts/pip install -r research/labelsizing_core/requirements.txt
```

`requirements.txt` deliberately does **not** list MetaTrader5, so research
dependencies never leak into the live bot's environment. Verify isolation:

```
research/labelsizing_core/.venv/Scripts/python research/labelsizing_core/_isolation_check.py   # -> ISOLATION OK
research/labelsizing_core/.venv/Scripts/python research/labelsizing_core/run_validation.py
```

## Asserts that gate correctness

The harness is considered correct only if every one of these passes:

1. **OHLC coherence** — every synthetic bar satisfies `low <= min(open,close)`
   and `high >= max(open,close)` (`synth_data.assert_ohlc_coherent`).
2. **Entry geometry** — `entry_idx == signal_idx + N_CONFIRM`; the barrier window
   starts at the entry, not the signal (`labeler.label_signals`).
3. **Non-empty train/test after purge** — all 15 CPCV splits retain non-empty
   train and test sets, else `RuntimeError` (`cpcv.CombinatorialPurgedCV.split`).
   This is the single most important line in the harness.
4. **Leakage probe** — no training index lies inside
   `[test_start - TAU_MAX, test_end + max(EMBARGO, L_FEATURE_MAX)]` for any split;
   zero violations required (`run_validation` step 4). A separate feature
   causality probe recomputes features on truncated prefixes and asserts equality.
5. **CVaR exception rate** — the fraction of sizing scenarios whose loss breaches
   `CVAR_LIMIT` must be `<= (1 - alpha) + tolerance` (`run_validation` step 7).

Reported (not gated) diagnostics: pooled OOS per-class and macro ECE (adaptive,
equal-mass bins) + Brier; GPD `xi_hat` / clamped `xi` / exceedance count /
effective `D-bar_SL`; and the forced-infeasible De-Risk-to-Cash fallback engaging.

## Honesty notes

* Venn-Abers' distribution-free guarantee assumes exchangeability, which financial
  series violate. Treat the calibration here as robust *empirical* calibration,
  not a guarantee. The per-class-then-renormalize step is a practical
  approximation, not coherent multiclass Venn-Abers.
* The Gaussian-HMM regime is a compact in-house EM implementation (no `hmmlearn`),
  refit on fixed absolute stride boundaries and carried forward — causal and
  prefix-stable, but a simplification of a continuously-refit HMM.

## Files

`config.py` (locked params) · `synth_data.py` (A) · `labeler.py` (B) ·
`features.py` + `hmm_regime.py` + `indicators.py` (C) · `cpcv.py` (D) ·
`timeout_baseline.py` (E) · `calibration.py` (F) · `tail_loss.py` (G) ·
`optimizer.py` (H) · `run_validation.py` (I) · `_isolation_check.py` (guard).
