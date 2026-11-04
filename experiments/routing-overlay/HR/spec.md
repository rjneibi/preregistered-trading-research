> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HR_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HR_PREREGISTRATION — ER-regime routing + risk sizing on the conviction arm

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; no HR
computation has touched post-cutoff data at freeze time).

**Contamination disclosure (exactly what was previously observed about the
post-cutoff window):** (a) H1-verdict pooled and per-era PFs at matrix costs
(old 0.95 / new 1.42, full 1.24) over windows straddling the cutoff;
(b) the phase-1 per-year realistic-regime table (2023 PF 1.08, 2024 1.05,
2025 1.92, 2026H1 1.25 — thin-matrix basis); (c) pooled post-cutoff-
overlapping outputs of H-N (news subset), H-P (portfolio), and H-B (arm B).
So the reader should assume we knew the post-cutoff period was FAVORABLE
for the base strategy before designing this overlay. What was NEVER
computed on post-cutoff data: ER values, regime labels, routing outcomes,
or threshold calibration — **the router itself is being tested clean; the
base strategy's OOS is degraded.** Gates are set knowing both.

**Statistical honesty on the IS effect:** the unrouted IS PF of 1.051 on
n=334 is not distinguishable from 1.0 at this dispersion, and the routing
uplift (+0.023 PF) is smaller than the sizing drag (−0.066 PF). The most
likely OOS outcome is a KILL, and that outcome is the gate working, not
failing. Kill threshold, written now: routed OOS PF < 1.35 (gate 1) closes
the routing overlay — no re-thresholding, no basis switch.

## Named parameters (task invariant: all in config, none hardcoded)
From `config.yaml modules:` — er_window=14 (H1 closes), confirm_bars=2,
calib quantiles {mr_enter 0.20, mr_exit 0.35, mom_exit 0.55, mom_enter 0.75},
route_pivot_in=[MOMENTUM], is_fraction=0.70, sizing {risk_fraction 0.01,
start_equity 10000, stop_atr_mult 2.4}, SymbolSpec {tick_size 0.01,
tick_value 1.0, volume_step 0.01, volume_min 0.01, volume_max 100.0}.

**Calibrated thresholds (IS ER distribution ONLY, cutoff 2023-02-23 18:24 UTC;
PLACEHOLDER_THRESHOLDS never used):**
- enter_mr = 0.0962311518
- exit_mr  = 0.1716496503
- exit_mom = 0.2832321672
- enter_mom = 0.4217443250

**Routing decision (deliberate template inversion, recorded):** this repo's
R3/S3 logic is a validated BREAKOUT (fading tested and rejected), i.e. it is
the template taxonomy's "breakout module" → routed to MOMENTUM only. The
IS evidence supports it: 78% of conviction events occur in MOMENTUM state;
NEUTRAL-state trades are the drag (IS PF 0.847, −$1,294).

## IS results (disclosed, confer nothing)
| variant | n | PF (1 lot) | net (1 lot) | sized PF | sized net |
|---|---|---|---|---|---|
| routing OFF | 334 | 1.051 | $2,262 | 0.985 | −$80 |
| route MOMENTUM | 261 | 1.074 | $2,600 | 1.035 | $150 |
| route MEAN_REVERSION | 13 | 2.093 | $956 | 1.640 | $98 |
| route NEUTRAL | 60 | 0.847 | −$1,294 | 0.720 | −$329 |

Diagnostics: flip_count 5,208; bars 42.6% NEUTRAL / 33.0% MOMENTUM /
24.5% MEAN_REVERSION; zero zero-lot skips at $10k equity.

**Anti-annexation clause (binding at freeze):** routing is MOMENTUM-ONLY.
The MEAN_REVERSION row (PF 2.093, n=13) is declared statistical noise —
thirteen trades over eight years cannot distinguish PF 2.1 from 0.9 — and
may NOT be added to the routing set after OOS results are seen. Any
MR-routing idea is a new prereg with its own IS/OOS cycle.

**HEADLINE FINDING OF THIS CYCLE — the sizing inversion:** constant-
dollar-risk ATR sizing flips the unrouted system from marginally profitable
(1-lot PF 1.051) to losing (sized PF 0.985). The edge's return driver is
volatility exposure itself; 1%-risk sizing structurally shorts it. The
sizing drag (−0.066) exceeds the routing uplift (+0.023): the binding
problem is SIZING POLICY, not routing. Any sizing change (slower ATR,
capped divisor, vol-floor) is a NEW experiment under its own prereg — this
document tests routing only, and all its gates are evaluated on the
**1-lot basis** (sizing remains diagnostic here).

**Fill-convention verification (point checked in code):** the sizing
inputs are frozen strictly before fill — `atr` is the day-build snapshot
(last H1 bar closed before day open, events.py::_atr_at_build), and equity
compounds in event order, safe because the 24h single-position block
guarantees prior exit <= next entry. No sizing input can see the fill bar.

## OOS gates (to be frozen with predictions before the OOS run)
1. Routed (MOMENTUM-only) OOS PF ≥ 1.35 at matrix costs.
2. Routed OOS PF − unrouted same-window OOS PF ≥ +0.10.
3. Routed OOS n ≥ 70.
4. Routed OOS p90-cost PF ≥ 1.15.

**Registered predictions (filled at freeze):**
- Claude (Fable 5): FAIL/KILL — most likely on gate 2 (uplift ≥ +0.10 is 4×
  the in-sample effect); a kill here is the gate working.
- Rashed: PASS — the NEUTRAL-state drag is real and stronger post-cutoff.
  (Second head-to-head disagreement of the day.)

## Ledger delta (append at freeze): | 48 | HR regime routing + sizing OOS | pending |
