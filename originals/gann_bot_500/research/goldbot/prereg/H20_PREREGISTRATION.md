# H-20 PRE-REGISTRATION — Is the 20:00-UTC concentration an hour effect or an overnight-holding effect?

**Status:** FROZEN. No number in this file may change after the freeze hash is recorded in
`DECISIONS.log`.
**Frozen:** 2026-08-23
**Trials Ledger row:** 61
**Freeze mechanism:** SHA-256 of this file. **DECLARED DEVIATION:** the protocol requires a git
commit; `git` is not installed on this host. A content hash recorded in `DECISIONS.log` before any
run is substituted. It is tamper-evident on content, which is the property the git freeze exists to
provide. No threshold is changed by this substitution.
**Blind predictions:** NOT in this file. Sealed separately in `H20_PREDICTION_SEALED.md`, whose
SHA-256 is recorded in `DECISIONS.log` at the same time as this file's. Rashed records his
predictions against this file before opening the sealed file.

---

## 1. Charter — what this trial can and cannot do

**This is a structural disconfound test, not an edge claim.** It carries **NO PASS GATES.** Every
numeric threshold below is a **kill threshold**: clearing it closes nothing further and reopens
nothing. Its most likely function is to close the 20:00 finding.

This framing is mandatory, not stylistic. See §2.

---

## 2. Kill-list screen and anti-annexation statement

**The finding under test.** Free diagnostics on the frozen ledger (cycle 2, 2026-08-23,
`verdict_trades.csv`, n=472, p90 costs, swap included) found net P&L concentrated in a single entry
hour:

| entry hour | n | PF | net | rollover cross% |
|---|---:|---:|---:|---:|
| 12:00 | 106 | 0.942 | −$1,677 | 0.9% |
| 16:00 | 246 | 0.862 | −$6,674 | 23.6% |
| **20:00** | **110** | **1.539** | **+$8,746** | **65.5%** |
| retry hours | 10 | 0.469 | −$1,692 | — |

**Adjacency — stated plainly, because it is severe.**

- **H1 / H2 (goldbot-breakout line, CLOSED).** The conviction R3/S3 rule *is* the breakout line
  H1 tested. H1 died on `full PF >= 1.20` and `each era PF >= 1.00`. **An hour-subset that
  rescues H1's profit factor is exactly what the anti-annexation clause forbids.** This trial is
  therefore constructed so that it *cannot* function as a resurrection: no pass gates, and an
  explicit statement (G5) that clearing any threshold here does not reopen H1.
- **FR-L (London ICT TP variants, ALL FAIL, line retired).** FR-L was killed partly on
  session/window shopping. Selecting the best of several session hours is the same *statistical*
  move. Different engine and different signal (ICT sweep/FVG vs R3/S3 pivot breakout), but the
  methodological hazard transfers in full and is treated as binding.
- **HV (era/regime explanation, all four gates FAILED).** If the 20:00 effect is present in only
  one era it inherits HV's negative prior directly. Gate G4.

**What makes this mechanically — not statistically — different, and therefore worth one trial.**

1. **20:00 UTC is a microstructure boundary, not an arbitrary slice.** It is the COMEX floor close
   and the US equity cash close (16:00 ET under EDT). Liquidity, hedging flow and end-of-day
   positioning discontinuities at that boundary are documented market plumbing, not a fitted
   parameter. The hour was not chosen from a continuum; it is one of exactly three bars the frozen
   spec can fire on.
2. **A 20:00 fill is structurally conditioned, not merely time-labelled.** The frozen spec permits
   one trade per direction per day. A 20:00 fill therefore occurs **only on days the level was not
   breached at 12:00 or 16:00.** The 20:00 cohort is "late-day first breach" — a materially
   different event from the same rule fired earlier in the session, not the same event at a
   different clock time.
3. **The cost gradient runs against the finding.** The 20:00 cohort bears the worst carry burden
   in the sample (65.5% rollover crossing vs 0.9% at 12:00) and is profitable anyway. A
   data-mining artifact would not be expected to survive the heaviest cost handicap in the set.

**None of that is evidence the effect is real.** It is the argument that the question is worth one
frozen trial rather than being killed for free at the mechanism step.

---

## 3. Mechanism — why the market would pay, stated before testing

Two rival mechanisms are consistent with the observation. They are the hypothesis.

**H-A — the hour/late-breach mechanism.** A level that survives the London and NY-morning sessions
and only breaks near the cash close is breaking against a thinner, more one-sided book. End-of-day
hedging and index-rebalance flow is price-insensitive and must transact; a breakout into that flow
continues because the marginal seller has withdrawn for the day. Who is on the other side: the
liquidity provider who must widen or step away into the close, and the systematic hedger with a
mandate to be flat. Why they persist: their participation is structural and calendar-driven, not
opportunistic, so they cannot learn to stop.

**H-B — the overnight-continuation mechanism.** Nothing about 20:00 matters. What pays is holding
through the Asian and next-London sessions, and the 20:00 cohort simply captures more of that by
construction. Who is on the other side: nobody specific — this is a risk premium for carrying
exposure through an illiquid window, not an edge.

**These are not both tolerable.** H-A is a tradable structural claim. H-B is a statement that the
program has been paid for bearing overnight gap risk while explicitly assuming it away, and it
would mean the 20:00 finding is an artifact of the exit policy rather than a property of the
signal. **The purpose of this trial is to decide between them.**

**The confound.** In the existing ledger, entry hour is entangled with overnight holding
(cross% 0.9 / 23.6 / 65.5 by hour). Conditioning on *whether a trade actually crossed* is invalid —
crossing is caused by the trade's own path (slow/adverse trades cross; fast winners do not), so it
is a collider and post-treatment. The confound must be broken by intervention on the exit policy,
not by conditioning.

---

## 4. Design — counterfactual exit arms over identical entry events

Entries are **not** modified. The frozen entry rule is untouched. Only the exit policy varies, and
the same 472 entry events are re-simulated under each arm from M1 bars
(`research\data\xauusd_m1_histdata.csv`, epoch-second `time,open,high,low,close`, 2010→2026-06-19).

| Arm | Exit policy |
|---|---|
| **A — as-is** | Current published policy (server TP/SL, hivol half-out, lovol bail, 24h stop). Regression reference only. |
| **S — same-day** | Server TP/SL active; otherwise **forced flat at 20:45 UTC on the entry day**. A 20:00 entry becomes a ~45-minute hold. **Zero rollover crossings by construction.** |
| **N — next-day** | Server TP/SL active; otherwise **forced flat at 20:45 UTC on the next trading day**. **Exactly one rollover crossing by construction** for every entry hour. |

Rows: entry hour ∈ {12, 16, 20}. Retry hours (13,14,15,17,18,19) pooled and reported, never gated.

**Why this breaks the confound.** Under **Arm S** no trade holds overnight, so hour is fully
disentangled from overnight exposure; any residual hour advantage there is a pure hour effect.
Under **Arm N** every hour holds exactly one night, so overnight exposure is equalised across rows.

**Why this is insensitive to the largest open uncertainty in the program.** Arm S has ~zero
rollover crossings, so the primary contrast G2 is essentially unaffected by the unresolved
historical-swap question (cycle 1's declared defect). That independence is the reason this
experiment is sequenced before the swap work.

**Primary metric.** Net expectancy per trade in **ATR units** (`net / (100 × atr)`, computed
**per trade** then averaged — never `mean(net)/mean(atr)`), at **p90** costs. Dollar figures are
not comparable across eras (cycle 1) and are reported but never gated.

**Swap.** Charged at published 2026 rates (−$70/lot/night long, +$29 short, ×1.4 triple-Wednesday),
per rollover crossing, applied per trade. An era-scaled column is reported for completeness.
The 2026-rate column is the gated one because it is the deployment-relevant case.

---

## 5. Gates — all are KILL thresholds. There is no pass branch.

### G0 — POWER
Arm S must retain `n >= 100` at hour 20 and `n >= 200` at hour 16.
**FAIL BRANCH:** verdict is **INSUFFICIENT POWER**. Line closed, no edge claim, **no gate
relaxation and no pooling of hours to manufacture n**. This is a legitimate terminal result.

### G1 — HARNESS REGRESSION
Arm A must reproduce the published per-hour net P&L of `verdict_trades.csv` to within **±2%** at
every one of the three gated hours.
**FAIL BRANCH:** the re-simulation is not the harness that produced the ledger. **Halt.** Every
downstream number is void. Reconcile against `goldbot/triple_barrier.py` and
`goldbot/events.py` before any further work. Do not proceed to G2 on a failed regression.

### G2 — THE DISCONFOUND (primary)
Let, in R_ATR units under p90 costs:
- `D_hour = E[hour20 | Arm S] − E[hour16 | Arm S]`
- `D_night = E[hour16 | Arm N] − E[hour16 | Arm S]`

**KILL if `D_hour <= 0`.** → The 20:00 advantage does not survive removal of overnight holding.
It is an **overnight-holding artifact**. The 20:00 finding is **CLOSED**.

**KILL if `D_night > 0` AND `D_hour < 0.5 × D_night`.** → The operative variable is overnight
exposure, not the hour. The 20:00 finding is **CLOSED**. Overnight continuation then becomes a
*separate* question that requires its own fresh pre-registration and **may not be annexed to this
trial or to H1** — including the observation that it would be a paid-for-gap-risk claim, not an
edge claim.

### G3 — DEFLATION
Deflated Sharpe of the hour-20 Arm S per-trade net-return series via `goldbot/dsr.py`, with
`trial_srs` = the Sharpes of **all nine declared entry hours (12…20) under Arm S**.
`N_effective = 9`, **pinned now, before any run.**
**KILL if `DSR < 0.95`.** → The concentration does not survive its own selection. **CLOSED**, and
no further entry-hour subset work is permitted anywhere in this program.

### G4 — ERA SIGN STABILITY
Hour-20 Arm S expectancy must be `> 0` in the old era **and** the new era **separately**
(boundary pinned at 2021-06-19T00:00:00Z).
**KILL if either era is `<= 0`.** → Regime-dependent; inherits HV's negative prior directly.
**CLOSED.**

### G5 — COST BAR
Hour-20 Arm S profit factor at p90 costs with swap must exceed **1.00**.
**KILL if `<= 1.00`.**
**Explicit and binding:** 1.00 is a *kill* threshold, deliberately set below H1's 1.20 bar because
this trial is not an edge claim. **Clearing it does not constitute a passing hypothesis and does
not reopen H1 or H2.** Any edge claim arising from this line requires a separate future
pre-registration clearing **1.20 or higher** on data not used here.

### G6 — NO SHOPPING (procedural)
Pinned before the run and unchangeable: the three arms; the 20:45 UTC close time; the hour grouping
{12, 16, 20} with retry hours pooled; `N_effective = 9`; the era boundary 2021-06-19; the p90 cost
column; the swap construction in §4.
**FORBIDDEN on any failure:** changing the close time, re-grouping or re-binning hours, adding or
removing arms, sub-splitting by side or by year, changing `N_effective`, moving the era boundary,
switching cost columns, or running a sensitivity sweep of any kind.

---

## 6. Verdict rule

**ANY of G2, G3, G4, G5 failing ⇒ the 20:00 concentration is CLOSED** and recorded in
`DECISIONS.log` as closed, with the failing gate named.

If all kill thresholds are cleared, the *only* permitted conclusion is:

> "The 20:00-UTC concentration is not explained by overnight holding, survives deflation at
> N_eff = 9, is sign-stable across eras, and exceeds breakeven at p90 costs with swap. This is a
> structural finding about where the frozen rule's P&L lives. **It is not an edge claim, it does
> not reopen H1/H2, and it licenses only one thing: a separate pre-registration testing a
> 20:00-only variant against the 1.20 bar on data not used here.**"

Nothing else may be inferred, and no capital decision follows from this trial under any outcome.

---

## 7. Known defects carried at freeze

1. **Bid-only bars.** `xauusd_m1_histdata.csv` is bid-side. Short-side SL/TP trigger on the ASK in
   MT5, so short stop-outs are under-detected in every arm. Bias direction: **optimistic in all
   arms equally.** The primary contrast G2 is a *difference between arms* and is therefore largely
   protected; the absolute levels in G5 are not, and G5 is optimistic as a result.
2. **Historical swap unresolved.** 2026 rates are charged throughout. Cycle 1 established this
   overstates old-era carry. Arm S has ~zero crossings, so G2 is near-immune; G4's old-era leg is
   the exposed number and is therefore **conservative** (real old-era swap is smaller, so a passing
   old-era sign is not manufactured by this defect, and a failing one might be).
3. **Mark-to-market drawdown not computed here.** This trial gates on expectancy, not drawdown.
   No drawdown or sizing conclusion may be drawn from it.
4. **`n = 110` at hour 20.** Small. G0 admits it at 100 because the frozen spec cannot produce more
   without changing the entry rule, but every conclusion inherits that sample size and the verdict
   rule above forbids treating it as an edge claim precisely for this reason.
