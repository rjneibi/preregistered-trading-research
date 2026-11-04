# H-M DESIGN — ML meta-labeling on the conviction dual-arm event set

_Status: DESIGN + reference implementation. No real-data backtest may run until
HM_PREREGISTRATION.md is frozen (predictions filled, committed). This is the
salvage candidate (c) named in the frozen decision tree at commit 35deedc._

## 0. What ML can and cannot do here (read first)

The primary strategy decides **side** (BUY above R3 / SELL below S3, conviction
dual-arm). Meta-labeling (López de Prado, *Advances in Financial Machine
Learning*, ch. 3) trains a SECONDARY classifier to answer one question per
signal: **"given everything knowable at entry time, what is the probability
this particular trade wins?"** — then drops (or later, down-sizes) the
low-probability ones.

- It **can** raise PF: PF = gross wins / gross losses. If the filter removes
  trades that are disproportionately losers, both the numerator survives and
  the denominator shrinks. A filter with even modest skill (AUC 0.58–0.62)
  that drops the worst ~30–40% of trades can plausibly lift OOS PF by
  0.1–0.3. That is the honest ceiling — "modest improvements … risk-adjusted
  metrics remained weak" is the published norm for meta-labeling.
- It **cannot** manufacture edge. If the primary signal is net-negative
  (old era at measured costs: PF 0.95), the filter must find a genuinely
  predictable *subset* that is positive — possible but not guaranteed.
- It **cannot** be trusted by default at our sample size. n = 472 events over
  11 years is tiny for ML. This is the binding constraint on everything below
  and the reason round 10 failed.

## 1. Post-mortem of round 10 (the prior FAILURE) and the five fixes

Round 10 (`fable-backtesting/monthly_and_ml.py`): GradientBoosting on 10
pre-entry features, trained 2015–21, scored 2021–26 → **quintile lift
INVERTED out-of-sample**: the model's favorite trades LOST money (PF 0.85)
and its least-favorite earned PF 2.0. Diagnosis, from the round-9 forensics:
the model's top features (room-to-next-zone, day-extension, overshoot) were
exactly the **era-inconsistent** ones — features whose sign flips with
regime. ML on 565 trades with regime-rotating features = automated
overfitting.

| Round-10 failure cause | H-M fix |
|---|---|
| Era-inconsistent features dominated | Feature set PINNED to cross-era-validated or structural features ONLY; room/day_ext/overshoot-style features EXCLUDED by name (§3) — except overshoot, which is retained under a monotonic-cap argument and flagged as the riskiest inclusion |
| Single train/test split (one era each way) | CPCV 15 purged splits; selection and calibration on train folds only |
| Uncalibrated scores, quintile sort | Platt-calibrated probability + a pinned threshold grid, threshold chosen per-split on TRAIN only |
| Unconstrained tree ensemble | HistGradientBoosting with pinned tiny capacity (depth ≤ 3, leaf ≥ 25, L2, early stop) |
| No negative control | Shuffled-label control run is part of the harness: the identical pipeline on permuted labels MUST fail the gates, or the harness is broken |

## 2. Architecture

```
                     ┌─────────────────────────────────────────────┐
                     │       RESEARCH (this pack, offline)         │
                     │                                             │
 M1 history ──► goldbot events.py ──► triple_barrier.py ──► trades │
                     │   (472 conviction events, verdict basis)    │
                     │                                             │
 M1/D1 context ──► meta_lab.build_features ──► X (8 pinned feats)  │
 news_days.json ─────┘                          y = net_med > 0    │
                     │                                             │
                     │   meta_lab.cpcv_meta_run                    │
                     │   ┌──────────── per split (15×) ─────────┐  │
                     │   │ purge/embargo (24h/40h, H1 protocol) │  │
                     │   │ fit HGB (pinned params) on TRAIN     │  │
                     │   │ Platt-calibrate on TRAIN (3-fold)    │  │
                     │   │ pick τ on TRAIN (pinned grid+policy) │  │
                     │   │ apply keep/drop to TEST fold         │  │
                     │   └──────────────────────────────────────┘  │
                     │   pooled OOS: filtered vs unfiltered PF     │
                     │   + shuffled-label negative control         │
                     └───────────────────┬─────────────────────────┘
                                         │ gates pass (HM prereg)
                                         ▼
                     ┌─────────────────────────────────────────────┐
                     │        SHADOW MODE (demo, Phase 2)          │
                     │ flip_bot computes the same 8 features at    │
                     │ signal time, logs p and keep/drop decision  │
                     │ WITHOUT changing any trade. ≥8 weeks.       │
                     │ Judged on: live p-calibration vs backtest.  │
                     └───────────────────┬─────────────────────────┘
                                         │ shadow gates pass
                                         ▼
                     ┌─────────────────────────────────────────────┐
                     │      ENFORCING MODE (demo → small live)     │
                     │ p < τ  → skip trade                         │
                     │ p ≥ τ  → trade; size *= clip(2p−0.5,0.5,1.5)│
                     │ model.pkl versioned; feature hash checked   │
                     │ at load; stale-model kill (>90d → alert)    │
                     └─────────────────────────────────────────────┘
```

Live integration point (Phase 2+ only): `flip_bot.py` already computes at
signal time everything the features need (ATR, regime median, ADX, news
weight, UTC clock). The feature builder is deliberately restricted to those
quantities so the live port is a ~40-line function plus a pickle load.

## 3. Feature specification (PINNED — the entire feature space)

All features computable at the signal's H1 close, from data strictly before
it. Dimensionless or categorical (no raw prices, no dollar units — price-level
proof by construction).

| # | feature | type | rationale (evidence) |
|---|---|---|---|
| 1 | `hour` (12–20 UTC) | categorical | 16:00–18:00 strongest both eras (round 9, "noted only" → weak prior, structural) |
| 2 | `weekday` (Tue–Fri) | categorical | Tue best / Thu worst BOTH eras (round 9) |
| 3 | `tie_entry` (event hour % 4 == 0) | binary | tie convictions are structurally different from sequential h1→h4 |
| 4 | `hivol` (ATR > 90d median) | binary | validated cross-era (v5.1 exit regime) |
| 5 | `vol_pctile_prevday` (relATR 252d trailing rank, previous completed day) | float 0–1 | causal by construction (H2 machinery, reused as a FEATURE not a gate; its standalone-filter failure does not preclude conditional value) |
| 6 | `adx_d1` (Wilder ADX(14) on D1, previous completed day) | float | ADX≤22 half-size tilt validated cross-era (round 9, adopted live) |
| 7 | `news_day` (FOMC/NFP/CPI) | binary | PF 2.40 news days, consistent cross-era (round 3b); live sizes 1.5× |
| 8 | `overshoot_atr` = \|entry − level\| / ATR | float | RISKIEST inclusion — round 9 flagged raw overshoot era-inconsistent. Retained because ATR-normalization removes the price-level component that drove the inconsistency; if SHAP/permutation importance ranks it #1 in the real run, treat the result with extra suspicion (noted in prereg) |

EXCLUDED by name (round-9/10 era-rotators): room-to-next-zone, day-extension,
direction/side, zone preference, prior win/loss streaks, month/seasonality,
any dollar-denominated feature, anything requiring tick data.

Label: `y = (net_med > 0)` — the trade's outcome at MEASURED matrix costs
(the verdict basis), not flat costs. Meta-labeling on the cost basis that
matters.

## 4. Model + training protocol (PINNED)

- Model: `sklearn.ensemble.HistGradientBoostingClassifier` —
  `max_depth=3, max_iter=200, learning_rate=0.05, min_samples_leaf=25,
  l2_regularization=1.0, early_stopping=True, validation_fraction=0.15,
  random_state=42`. No hyperparameter search. (A search on 472 rows is a
  snooping machine; capacity is pinned low instead.)
- Calibration: Platt sigmoid via `CalibratedClassifierCV(cv=3)` fit on the
  training fold only. (Isotonic needs more data than we have.)
- Threshold policy: grid τ ∈ {0.45, 0.50, 0.55, 0.60, 0.65, 0.70}; per split,
  choose the τ maximizing TRAIN-fold filtered PF **subject to TRAIN retention
  ≥ 40%**; ties → lower τ (more trades). Applied unchanged to the TEST fold.
- Splits: identical to H1 protocol — CPCV(6,2), purge τ=24h, embargo/lookback
  margin 40h on the signal_hr axis.
- Negative control: identical pipeline with labels randomly permuted
  (seeded); its pooled OOS "uplift" must be ≈ 0 and must fail every gate.

## 5. Gates (DRAFT — frozen only when HM_PREREGISTRATION.md is committed)

This is roughly trial #40 of the program and the SECOND attempt at ML
filtering, so the bars are deflated upward. PASS requires ALL of:

1. Pooled OOS **filtered PF ≥ 1.40** at matrix costs (unfiltered baseline 1.24).
2. Pooled OOS **uplift ≥ +0.15 PF** vs the unfiltered same-fold baseline.
3. **Old-era** pooled OOS filtered PF **≥ 1.05** (the era that killed H1 —
   if the filter can't rescue a positive old era, it's a date proxy again).
4. Retention ≥ 40% AND kept OOS n ≥ 200.
5. ≥ 11/15 splits with positive kept-fold expectancy.
6. p90-cost filtered OOS PF ≥ 1.15.
7. Shuffled-label control fails gates 1–6 (harness sanity, not a merit gate).

Decision tree (committed at freeze):
- **PASS** → shadow mode on the demo bot ≥ 8 weeks (log-only), judged on
  calibration drift; then enforcing mode on demo; sizing stays at the H1
  system's registered risk (the filter earns no size increase by itself).
- **FAIL** → ML-filter line closed for a second time. Do not revisit until
  the live/demo journal has accumulated ≥ 2× more events (≈ 950) — the next
  attempt trains on FORWARD data.

## 6. Honest expectations, quantified

- Base rates: 472 events, 72.9% winners at matrix costs. The classifier must
  find structure in the 27.1% minority class with ~128 examples of it.
- If the filter achieves AUC 0.60 and drops 35% of trades, arithmetic on the
  actual verdict trade distribution puts the plausible OOS PF band at
  ~1.35–1.55 (from 1.24), old era ~0.95 → ~1.05–1.20. That's what "works"
  looks like. Anything dramatically better in-sample is overfitting, not
  discovery.
- The most likely honest outcome, given round 10 and the sample size, is
  **FAIL or marginal** — which is why the prereg records predictions before
  the run, again.

## 7. Files

- `HM_PREREGISTRATION.md` — the freeze document (draft until committed with
  predictions).
- `meta_lab.py` — feature builder, ADX/relATR context series, CPCV-nested
  training/calibration/threshold pipeline, shuffled-label control. Self-
  contained; imports goldbot only for config/data helpers.
- `test_hm_pack.py` — synthetic-only self-checks (leakage probes, no-edge
  control must fail gates, planted-edge control must pass detection sanity,
  threshold-on-train-only invariant). Runs with NO real market data.
- Runner (`hm_runner.py`) — to be written AFTER the freeze; it will reuse the
  H1 verdict trade set (`results/verdict_trades.csv`) extended with the
  `level` column carried from events.
