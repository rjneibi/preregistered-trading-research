# HPF_PREREGISTRATION — Powell presser-fade OOS confirmation (hypothesis HPF)

**Freeze protocol:** fill Rashed's blind prediction below, then
`git add research/powell/ && git commit -m "preregister: HPF freeze - Powell presser fade"`
BEFORE running `py -3.11 powell_verdict.py`. Append hash to
research/goldbot/results/DECISIONS.log.

**Hypothesis under test:** *fading the 14:00→14:30 ET FOMC statement move on
XAUUSD during the press conference (enter 14:30 ET, exit 16:00 ET) carried
positive net edge after measured costs during the Powell chairmanship, and that
edge persisted out-of-sample in 2023–2026-04 (post-publication of the effect).*

**Literature anchor (disclosed):** IJCB v22n1, "The Market Impact of Fed
Communications: The Role of the Press Conference" + CEPR VoxEU column: under
Chair Powell (esp. since 2020-03) the initial statement reaction partially
reverses during the presser; the relationship was flat-to-opposite under
Bernanke/Yellen. Documented on Treasuries/equities — XAUUSD is our extension.

## Registered predictions (blind protocol per prereg-prediction-protocol)
- Rashed (FIRST, blind): FAIL — low confidence (~0.55–0.7 FAIL)
  (recorded 2026-07-08, before Claude's prediction was revealed)
- Claude (Fable 5): sealed 2026-07-08 pre-call, SHA-256
  `a9f0af6e357b848aec41a21448b680453ec832b64bbbc82ccd03084c6d69c8e0`
  (verified against plaintext below after Rashed's call):
  > FAIL — low confidence (~0.55 FAIL / 0.45 PASS). Mechanism likely real in
  > the Powell era but the 5-gate conjunction at n~27 with per-event sd >>
  > mean edge makes PF>=1.20 + worst-slip-positive + permutation a
  > coin-flip-minus; post-2022 publication decay tips it under.
  Blind agreement: both FAIL-low.

## IS exhibit (disclosed to both parties before predictions; 2015–2022)
45 events measured (2 missing months: 2018-09, 2020-09). Corr(stmt_move,
presser_move): Yellen +0.766 (n=12, continuation), Powell −0.210 (n=33,
reversal). Primary config fade_t0_1600ET, Powell era: PF 1.44 / mean +$1.60/oz
realistic slip; PF 1.31 / +$1.20 worst slip; n=33. Yellen control: PF 0.037 /
−$5.15 (fade loses badly pre-Powell — chair-specific, as the literature says).
All 6 fade configs positive IS in Powell era; all 6 momentum mirrors negative.

## Pinned OOS sample (LOCKED until freeze is committed)
Powell-chair scheduled FOMC presser meetings 2023-01-01 → 2026-04-29
(expected n≈27 less any data gaps). Warsh meetings (2026-06-17 onward):
measured, reported descriptively, NO gate — they cannot pass or fail HPF.
Exclusions (pinned): unscheduled meetings 2019-10-04, 2020-03-03, 2020-03-15.

## Pinned configuration family (12 = 2 directions × 3 thresholds × 2 exits)
direction ∈ {fade, momentum of statement move}; |stmt_move| threshold ∈
{$0, $3, $6}/oz; exit ∈ {15:30, 16:00 ET}. Entry: first tick ≥ 14:30:00 ET
(must be ≤ 14:32). Statement move: mid(14:29:59) − mid(13:58:55).
**Primary (the only gated config): fade_t0_1600ET** — no threshold, full-presser
hold. Disclosed: it was the strongest robust IS config; t3 configs showed higher
IS PF but halve n and are threshold-fitted, so they are family-consistency
diagnostics only. Nothing outside this family may be run. Config 13 = new prereg.

## Cost basis (pinned)
Real Dukascopy bid/ask at the actual tick timestamps (buy at ask, sell at bid —
spread charged implicitly) + per-side slippage stress: optimistic $0.00,
realistic $0.10, worst $0.30 per oz. Disclosure: Dukascopy institutional spread
(~$0.35–0.55/oz in the windows) understates retail news spreads; the worst-slip
gate (3) is the guard. Runner: research/powell/powell_verdict.py (self-test
10/10 committed with this freeze).

## Gates — HPF PASS requires ALL of:
1. n(OOS Powell events measured) ≥ 22 (data-coverage gate).
2. Primary fade_t0_1600ET OOS PF ≥ 1.20 at realistic slip.
3. Primary OOS total PnL > 0 at worst slip ($0.30/side).
4. Fade-family consistency: ≥ 4 of 6 fade configs OOS PF ≥ 1.00 at realistic slip.
5. Permutation reality check: primary OOS mean beats the 95th percentile of
   1,000 sign-randomized replicates on the same events/timestamps/costs
   (seed 20260708, pinned in runner).

## Decision tree (committed)
- FAIL → Powell-fade line CLOSED. DECISIONS.log gets the gate table. No retest
  on the same sample; the only legitimate revival is a Warsh-era forward study.
- PASS → **does NOT go live and does NOT size.** The tradeable population
  (Powell-chair pressers) is extinct as of 2026-05; a PASS only upgrades the
  mechanism to "validated historical anomaly" and opens a Warsh forward
  paper-study: log the fade paper-trade at each Warsh presser; a live prereg
  requires ≥ 8 Warsh events AND that forward sample net-positive. The Yellen
  control (fade PF 0.03) is standing evidence that chair transitions can
  invert this trade.
- Anti-gate-shopping: no configs, windows, thresholds, or slip levels added or
  edited after any OOS result is seen.

## Ledger delta (append to master Trials Ledger before committing)
| # | Trial | Outcome |
|---|-------|---------|
| +1 | HPF primary fade_t0_1600ET OOS | pending |
| +2..12 | HPF family diagnostics (11 configs, not gated) | pending |
| +13 | HPF permutation baseline machinery | n/a (control) |

## Known-unverified inputs
Dukascopy spread understates retail broker news-window spread (worst-slip gate
mitigates; live application would need broker-measured news spreads). Presser
start assumed 14:30:00 ET exactly for all scheduled meetings 2015–2026
(Fed-documented; not per-meeting verified). Statement release assumed 14:00 ET
(true for all scheduled meetings in sample). Missing months 2018-09 / 2020-09
(quarantined data) drop 2 IS events — disclosed above, no OOS impact expected.
2026 gold price ~2× 2023 → $-denominated thresholds/slippage are relatively
smaller late-sample (biases threshold configs, not the ungated primary's
realistic gate; worst-slip gate absorbs part).
