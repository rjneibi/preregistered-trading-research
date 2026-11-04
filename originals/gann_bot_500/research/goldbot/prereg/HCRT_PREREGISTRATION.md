# HCRT_PREREGISTRATION — CRT sweep-and-reject on D1 (cheap falsification of the ICT core claim)

**STATUS: VERDICT 2026-07-07 — FAIL (6 of 8 gates). ICT/CRT line on XAUUSD
D1 CLOSED.** Frozen 2026-07-07 (blind protocol; Rashed collected first);
run same day at full measured costs (rebuilt matrix, n=1,986 ticks,
med $0.72). Results: `results/HCRT_run.json`, runner `hcrt_runner.py`.

## VERDICT SUMMARY (added post-run; frozen text below is untouched)
- E1 primary: n=599, net PF **0.860** (−$46.8k/1-lot), old 0.891 / new
  0.832, DSR **0.153**, p95 stress 0.833, PBO 0.557. E2: PF 0.874, DSR
  0.165, no displacement. Gates failed: 1, 2, 3-era, 4, 5, 6.
- **The pattern is ANTI-informative:** CRT-filtered PF 0.874 vs bias-only
  baseline 0.923 — uplift **−0.049** vs required +0.10. The sweep signal
  subtracts edge from its own trend filter.
- **No mirror inversion** (the one gate that passed): mirror continuation
  PF 0.796 < reversion 0.874. Unlike R3/S3 closes-beyond, a D1 sweep
  carries NO directional information either way — both fade and breakout
  lose at costs. Raw unfiltered arms worse still (0.839/0.851, n≈1,250).
- Prediction scoring: both FAIL correct (blind record now 4-for-6).
  Failure-path sub-prediction: **Rashed closer** (flatline + DSR
  suppression; SR −0.037/trade). Claude's mirror-inversion path did NOT
  occur — the sweep is not a continuation signal either.
- Per the decision tree: no threshold shopping, no 4H migration, FVG/QT/SMT
  inherit the negative prior, gamma/CVD spikes stay deferred.

**Standing prior (disclosed):** this is a REVERSAL hypothesis on an instrument
where 17 rounds of R3/S3 work validated the OPPOSITE mechanism (continuation
through levels; fading tested and rejected — flip_bot.py header, MASTER_SUMMARY).
The zone-flip fade line and its no-stop variant were both NO-GO. External
evidence for CRT is vendor marketing; its own proponents concede raw CRT is
"closer to a coin flip." This prereg is run as a falsification test of the
ICT/CRT framework's most mechanizable claim, not as a candidate deployment.
No development capital follows a FAIL.

## Harness prerequisite (blocks the run, not the freeze)

New module `goldbot/dsr.py`, self-tested BEFORE any CRT signal code touches
real data:

- **DSR (Bailey & López de Prado 2014):** probabilistic Sharpe against
  SR₀ = E[max SRᵢ] under N trials, computed on per-trade NET returns with
  sample skew γ₁ and kurtosis γ₂:
  `DSR = Φ[ ((SR−SR₀)·√(T−1)) / √(1 − γ₁·SR + ((γ₂−1)/4)·SR²) ]`,
  `SR₀ = σ_trials · [ (1−γe)·Φ⁻¹(1−1/N) + γe·Φ⁻¹(1−1/(N·e)) ]`
  (γe = Euler–Mascheroni). Required unit tests: N=1 ⇒ SR₀=0 and DSR reduces
  to PSR; Gaussian null with N trials rejects at ≈ the nominal rate.
- **PBO via CSCV:** S=8 contiguous blocks, C(8,4)=70 split combinations,
  rank-logit PBO over the pinned trial matrix (below). Reuses the block
  conventions of `goldbot/cpcv.py`; purge/embargo across block joins ≥ 24h
  (one event horizon).

## Pinned universe (the ENTIRE search space — nothing else may be evaluated)

Data: HistData M1 2010-01→2026-06 resampled to D1 on **UTC-midnight days**
(the repo's validated pivot convention; previous-*trading*-day logic as in
`goldbot/pivots.py`). Intrabar exit resolution on M1 via
`goldbot/triple_barrier.py` (gap_open fills, ambiguous bars counted as stops).
Costs: `goldbot/costs.py` from measured `cost_matrix.json`; headline =
realistic regime. Known caveat: the matrix is a thin sample (standing
disclosure); the p90 stress gate is the compensation.

**Signal (one primary pattern, D1):**
- C1 = trading day T−2: CRH = high(C1), CRL = low(C1).
- C2 = trading day T−1, one-sided sweep only:
  LONG setup: low(C2) < CRL AND close(C2) ∈ [CRL, CRH] AND high(C2) ≤ CRH.
  SHORT setup: mirror. A C2 that violates both boundaries = no signal.
- **HTF structure filter (pinned, not searched):** LONG only if
  close(C2) > EMA200(D1 closes through T−1); SHORT only if below. EMA length
  200 is a convention, no other length may be run.
- Entry: market at day-T open (first M1 bar ≥ 00:00 UTC), direction =
  reversion (long after CRL sweep). Max 1 trade/day; no re-entry.

**Exits:**
- **E1 (primary — pattern-native, zero free parameters):** TP = opposite
  range boundary (long: CRH); SL = C2's sweep extreme (long: low(C2));
  hard close at next 00:00 UTC open (≤24h — inherits flip_bot's no-carry
  boundary; no swap/carry modeling needed by construction).
- **E2 (secondary — inherited live spec, zero NEW parameters):**
  TP +0.8×ATR / SL −2.4×ATR (D1 ATR(14) at T−1), same 24h hard close.
  Displacement rule: E2 replaces E1 only if E2 clears EVERY gate AND beats
  E1's gate-1 PF by ≥ +0.05 in both eras.

**Control arms (diagnostics, not selectable):**
- **Bias-only baseline:** entry at every day-T open in the EMA200 direction,
  E2 exits. Isolates whether "edge" is just the trend filter.
- **Mirror continuation arm:** same signal days, OPPOSITE direction
  (trade the sweep as a breakout), same exit family. The Era-C inversion
  probe.

Trial matrix for PBO: {E1, E2} × {filtered, unfiltered-raw-CRT} = 4 columns
(unfiltered columns are disclosure-only, never selectable). N for DSR = **2**
(E1, E2 — the only selectable trials); DSR at N=10 disclosed as stress.

## Era stratification (pre-committed table; the H2/HV lesson)

No new calendar eras are invented for this test (defining "low-vol periods"
by inspection is peeking). Stratification reuses two PINNED conventions:

- Era axis: OLD (< 2021-06-19T00:00:00Z) / NEW (≥) — `hs_runner.py:43`.
- Vol axis: day-T−1 relative ATR% above/below the full-sample median
  (HV's parameter-free convention).

Every gate metric is reported in the full 2×2 table {OLD,NEW}×{HIvol,LOvol},
each cell with n, net PF, and the mirror-arm PF beside it. This table IS the
Era A/B/C design: LOvol cells = Era A, HIvol cells = Era B, and the
mirror-vs-reversion comparison per cell = the Era C inversion probe.

## Gates — ALL required (evaluated on E1 unless displaced)

0. **Power floor:** filtered signal count n ≥ 100 full-sample. Below floor →
   verdict **INSUFFICIENT POWER**: line closed with no edge claim and no
   filter relaxation; may reopen only when ≥3 more years of D1 data exist.
1. Full-period net PF ≥ **1.30** at realistic matrix costs.
2. **Mechanism control:** CRT-filtered PF minus bias-only-baseline PF ≥
   **+0.10**, both arms under E2 exits (exit family held constant so the gap
   isolates the pattern, not the exit or the trend filter).
3. **Era table:** net PF ≥ **1.00** in OLD and NEW pooled separately; AND no
   inversion — the mirror continuation arm's full-sample PF must NOT exceed
   the reversion arm's. If it does, verdict is FAIL with the finding
   "sweep is a continuation signal, consistent with the R3/S3 prior" — and
   that finding does NOT authorize a sign-flipped variant inside this prereg;
   a continuation-CRT is a fresh prereg with fresh blind predictions.
4. **DSR ≥ 0.95** at N=2 on per-trade net returns (T = trade count).
5. **PBO < 0.50** over the pinned 4-column trial matrix.
6. p90 cost stress: net PF ≥ **1.15**.

## Decision tree (committed)

- PASS → Phase-2 ops prereg for a DEMO-only D1 bot (separate freeze; no live
  capital from this result), and the ICT-derivative backlog (FVG confluence,
  QT time gate) becomes eligible for its own gated preregs.
- FAIL → the ICT/CRT line on XAUUSD D1 is CLOSED: no threshold shopping, no
  alternate EMA lengths, no timeframe migration (4H CRT = fresh prereg, and
  the default is not to run it), and FVG/QT/SMT components inherit the
  negative prior. Gamma/CVD spikes remain deferred regardless of outcome.
- INSUFFICIENT POWER → closed without edge claim (gate 0).

## Registered predictions (BLIND: Rashed first, confidence attached)

- Rashed: **FAIL** (confidence: HIGH, 0.85) — collected blind, first.
  Registered rationale: (1) structural continuation prior at gold levels
  (17 rounds R3/S3 + zone-fade NO-GOs); (2) <24h hard close truncates the
  D1-range-target return distribution below viable R:R; (3) expected mirror
  inversion in HIvol cells (gate 3); (4) DSR multiplicity penalty at
  n≈100–300 (gate 4).
- Claude (Fable 5): **FAIL** (confidence: HIGH, ~0.80) — revealed after.
  Expected failure path: gate 3 mirror inversion (continuation arm beats
  reversion, consistent with the R3/S3 prior), secondarily gate 2 (uplift
  belongs to the EMA200 filter, not the pattern). Blind agreement — both
  FAIL; disagreement is only over WHICH gate kills it first (Rashed leans
  R:R truncation + DSR, Claude leans mirror inversion + mechanism control).

## Ledger delta (at freeze): | 51 | HCRT D1 sweep-and-reject + EMA200 HTF filter (E1 primary, E2 secondary) | pending |
