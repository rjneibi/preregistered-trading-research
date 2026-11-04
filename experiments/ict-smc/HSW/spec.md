> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HSW_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HSW_PREREGISTRATION — intraday sweep-and-reclaim at prior-day extremes (session-gated failed-sweep reversal)

**STATUS: VERDICT 2026-07-07 — FAIL (6 of 8 gates). Intraday sweep-reclaim
line on XAUUSD CLOSED; with HCRT, the reversal-at-levels family is closed at
every free-data scale.** Frozen 2f7599a, harness 5501a69 (10/10 synthetic
tests), run same day at full measured costs. Results: `results/HSW_run.json`,
runner `hsw_runner.py`.

## VERDICT SUMMARY (added post-run; frozen text below is untouched)
- Primary E1@d=0.15: n=885, net PF **0.827** (−$42.1k/1-lot), old 0.746 /
  new 0.941, DSR **0.014**, p95 stress 0.775. Only gates 0 (power) and 5
  (PBO 0.000 — nothing to overfit; every column loses) passed.
- **Every arm, every depth, both exit families, both eras net-negative.**
  Depth-monotonic but never viable: E1 PF 0.747 → 0.827 → 0.935 across
  d=0.05/0.15/0.30 (deeper sweep = wider stop = less cost domination, still
  no edge).
- **The reclaim is informationless (HCRT redux):** reclaim-filtered E2 PF
  0.634 vs touch-baseline 0.638 — uplift **−0.004** vs required +0.10.
  Waiting for the "failed sweep" confirmation adds nothing over blindly
  fading any level touch, and both lose heavily.
- **Mirror inversion (again):** continuation arm full-sample PF 0.716 >
  reversal 0.634, driven by new/HIvol (mirror 1.34, and mirror pf_new 1.09)
  — directionally consistent with the 17-round R3/S3 continuation prior.
  Per the frozen decision tree this does NOT authorize a sign-flipped
  variant: the continuation-at-levels line was already run to exhaustion
  and STOPPED 2026-07-06.
- Prediction scoring: **Claude FAIL-high correct, and the registered kill
  path (gate 1 outright, secondarily gate 2) is exactly what happened.
  Rashed PASS-high (≥0.80) — first recorded miss.** Blind record 5-for-8.
- Consequences per the frozen tree: no depth/session/window shopping, no
  level-definition migration (Asia-range/H4/session-open variants inherit
  the negative prior). Remaining evidence-backed kernels (GEX conditioning,
  order-flow imbalance) require paid data and are fresh preregs gated on an
  explicit operator budget decision — this FAIL creates no urgency to buy.

Derived from the evidence review
`research/EVIDENCE_REVIEW_2026-07-07.md` (Osler stop-clustering kernel +
Iwatsubo-Watkins-Xu session seasonality). This is the LAST free-data test of
the reversal-at-levels family on XAUUSD.

**Standing priors (disclosed, all negative):**
- **HCRT FAIL 2026-07-07 (6/8 gates):** the D1 sweep-and-reject was
  ANTI-informative (uplift −0.049 vs its own trend filter) with NO mirror
  inversion — on D1, a sweep carries no directional information either way.
  HCRT's decision tree committed "no timeframe migration; the default is not
  to run" intraday variants. HSW is run as the fresh prereg that tree permits,
  **on operator instruction 2026-07-07**, with the negative prior fully
  inherited. The distinguishing claim (and the only reason this is not
  line-reopening): Osler's documented mechanism is *intraday* stop cascades at
  salient levels during liquid sessions — D1 UTC-midnight candle geometry
  never was the mechanism's habitat. If intraday-at-the-level also fails, the
  family is closed at every scale we can test for free.
- 17 rounds of R3/S3 validated CONTINUATION through levels (then STOPPED);
  zone-fade NO-GO twice; scalp line CLOSED (all 12 configs net-negative —
  hence the pinned anti-scalp floors below).
- Repo blind-prediction base rate: 4-for-6 FAIL calls correct.
This prereg is a falsification test. No development capital follows a FAIL.

## Pinned universe (the ENTIRE search space — nothing else may be evaluated)

Data: HistData M1 2010-01→2026-06 UTC (`data/xauusd_m1_histdata.csv`).
Levels on UTC-midnight trading days (validated `pivots.py`
previous-trading-day convention). Intrabar exits via
`goldbot/triple_barrier.py` (gap_open fills; ambiguous M1 bars counted as
stops). Costs: `goldbot/costs.py` from measured `cost_matrix.json`;
headline = realistic regime; thin-matrix caveat stands, p90 stress gate is
the compensation. ATR reference everywhere: **ATR(H1, 14) Wilder, SMA seed**
(live-config parity), value at the last completed H1 bar before the
penetration-start bar.

**Reference level (ONE definition):** PDH/PDL = previous trading day's
high/low. No other level family (Asia range, session opens, H4 candles,
round numbers) may be evaluated under this prereg.

**Signal (LONG case; SHORT is the exact mirror at PDH):**
- Penetration start: first M1 bar of day T with low < PDL, with bar-open time
  in **07:00–19:59 UTC** (London+NY; pinned from the Iwatsubo NY-informed-
  trading evidence and the live session convention — no other window may be
  selected; an Asia-window arm is disclosure-only).
- Sweep extreme: running min low from penetration start to reclaim.
- Reclaim: first M1 close > PDL within **60 minutes** of penetration start
  (window pinned, not searched). No reclaim in window → no signal, level
  spent for the day.
- Depth requirement: (PDL − sweep extreme) ≥ **d × ATR(H1,14)**,
  d ∈ {0.05, 0.15, 0.30} — the ONLY searched parameter.
- One-sidedness: signal VOID if PDH was already penetrated earlier in day T.
- Entry: open of the next M1 bar after the reclaim close, direction = LONG
  (reversal). Max **1 trade per trading day** (first completed valid signal,
  either side); no re-entry; no pyramiding.

**Exits:**
- **E1 (primary — pattern-native):** SL = sweep extreme, with pinned
  anti-scalp floor: SL distance ≥ 0.5×ATR(H1,14) from entry (widen to the
  floor if the extreme is nearer). TP = prior-day midpoint (PDH+PDL)/2.
  Anti-scalp target guard (H-S lesson, structural, not searched): signal VOID
  in ALL arms if (TP_E1 − entry) < 0.5×ATR(H1,14). Hard close 24h after
  entry (no-carry parity).
- **E2 (secondary — inherited live spec, zero NEW parameters):**
  TP +0.8×ATR / SL −2.4×ATR (H1 ATR14), same 24h hard close.
  Displacement rule (HCRT convention): a non-primary cell displaces the
  primary only if it clears EVERY gate AND beats the primary's gate-1 PF by
  ≥ +0.05 in both eras.

**Primary trial: E1 at d = 0.15.** Selectable trials: {E1,E2} × {0.05, 0.15,
0.30} = **N = 6** for DSR; DSR at N=12 disclosed as stress.

**Control arms (diagnostics, never selectable):**
- **Touch-baseline (mechanism control):** enter at the next M1 open after ANY
  first penetration of PDL/PDH (no reclaim, no depth), same session window,
  same 1/day and one-sidedness rules, same direction convention (fade), E2
  exits. Isolates whether the reclaim component adds information beyond
  generic level-touch mean reversion.
- **Mirror continuation arm:** identical entry bars, OPPOSITE direction,
  mirrored E2 exits. The inversion probe.
- **Asia-window arm (00:00–06:59 UTC penetration start):** disclosure-only.

## Era stratification (pre-committed; identical to HCRT)

- Era axis: OLD (< 2021-06-19T00:00:00Z) / NEW (≥) — `hs_runner.py:43`.
- Vol axis: day-T−1 relative ATR% above/below full-sample median (HV
  parameter-free convention).
Every gate metric reported in the full 2×2 {OLD,NEW}×{HIvol,LOvol} table,
each cell with n, net PF, and the mirror-arm PF beside it.

## Gates — ALL required (evaluated on the primary trial unless displaced)

0. **Power floor:** primary-trial n ≥ 100 full-sample. Below → verdict
   **INSUFFICIENT POWER**: line closed, no edge claim, no filter relaxation.
1. Full-period net PF ≥ **1.30** at realistic matrix costs.
2. **Mechanism control:** reclaim-filtered PF (E2, d=0.15) minus
   touch-baseline PF ≥ **+0.10** (exit family held constant so the gap
   isolates the reclaim pattern).
3. **Era table:** net PF ≥ **1.00** in OLD and NEW pooled separately; AND no
   inversion — mirror continuation full-sample PF must NOT exceed the
   reversal arm's. Inversion ⇒ FAIL with the finding "intraday sweeps are
   continuation, consistent with R3/S3" — which does NOT authorize a
   sign-flipped variant inside this prereg.
4. **DSR ≥ 0.95** at N=6 on per-trade net returns (`goldbot/dsr.py`).
5. **PBO < 0.50** via CSCV (S=8 contiguous blocks, C(8,4)=70 splits,
   purge/embargo ≥ 24h) over the pinned 6-column selectable trial matrix.
6. p90 cost stress: net PF ≥ **1.15**.

## Decision tree (committed)

- PASS → Phase-2 ops prereg for a DEMO-only bot (separate freeze; no live
  capital from this result). The v2 ablation preregs from the evidence review
  (XAGUSD divergence feature — low prior, strict ablation gate; crude
  GC-options GEX overlay from free CME delayed data) become eligible as
  conditioning features on THIS signal only.
- FAIL → the intraday sweep-reclaim line on XAUUSD is CLOSED: no depth
  shopping, no session shopping, no reclaim-window shopping, no
  level-definition migration (Asia-range / H4-candle / session-open variants
  inherit the negative prior; the default is not to run them). Combined with
  HCRT, the reversal-at-levels family on gold is closed at every free-data
  scale. Remaining evidence-backed kernels (gamma conditioning, order-flow
  imbalance) require paid data and are fresh preregs gated on an explicit
  operator budget decision — a FAIL here creates no urgency to buy data.
- INSUFFICIENT POWER → closed without edge claim (gate 0).

## Harness prerequisites (block the run, not the freeze)

- Reuse `goldbot/dsr.py` (self-tested at HCRT), `costs.py`,
  `triple_barrier.py`, `pivots.py`. New `hsw_runner.py`.
- Unit tests on synthetic fixtures BEFORE real data: penetration without
  reclaim; reclaim after the 60-min window; both-sides day (one-sidedness
  void); depth exactly at threshold; session-boundary penetration (06:59 vs
  07:00); anti-scalp floor and target-guard voiding; mirror-arm entry parity.

## Registered predictions (BLIND: Rashed first, confidence attached)

- Rashed: **PASS** (confidence: HIGH, ≥0.80) — collected blind, first.
  Sub-prediction: nearest-to-kill gate = 4–5 (DSR/PBO multiplicity) — i.e.
  he expects the raw edge to be real and the main risk to be the
  statistical correction, not the mechanism.
- Claude (Fable 5): **FAIL** (confidence: HIGH, ~0.80) — revealed after.
  Expected failure path: **gate 1 outright** (intraday fade PF < 1.30 at
  realistic costs), secondarily gate 2 (reclaim uplift over touch-baseline
  < +0.10, the HCRT anti-informative pattern recurring intraday).
  Registered rationale: (1) HCRT showed the sweep pattern carries no
  directional information on D1 in EITHER direction; (2) the zone-fade line
  was NO-GO twice — fading levels on gold has repeatedly lost to costs;
  (3) program base rate (every strategy prereg to date has failed);
  discounted by the one genuine difference — Osler's mechanism is intraday,
  so this test sits closer to the published evidence than HCRT did.
- **BLIND DISAGREEMENT — first in the program.** Rashed PASS-high vs Claude
  FAIL-high. Scoring is symmetric: whichever side is wrong, the miss and its
  registered rationale get recorded in the prediction ledger.

## Ledger delta (at freeze): | 52 | HSW intraday sweep-and-reclaim at PDH/PDL, London+NY, d∈{0.05,0.15,0.30}×{E1,E2} (E1@0.15 primary) | pending |
