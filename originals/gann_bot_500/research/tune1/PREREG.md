# TUNE-1: push the surviving edges to a higher profit factor, behind a sealed holdout (pre-registered 2026-10-26)

User: "lock yourself in a loop, gather all research we made so far, tune it and be determined to find a higher
profit factor setup". User chose: locked holdout; tune the survivors (not the killed gold ideas).

Survivors (DECISIONS.log): index dip (XM-1 A1 RSI2, SW-1 MR2 IBS; live in the live bot),
USTEC 30-min ORB (SC-1; live in indexbot), analyst signals (excluded), crypto trend (not tradable on MT5).
Analyst signals are NOT tuned here: two excluded studies found tuning and exits did no better than the live rules. Crypto trend is not tradable on the user's venue. Both out of scope.

## Part 1 - index dip (D1)
Engine = SW-1 run(): signal at the close of day i, enter next open, exit at the open after the exit condition or the
max hold; spread 1.5 x median recorded (floor 2 bp); financing 5%/yr long per calendar night. Long only. One position
per config per market. Per-trade net returns; PF = sum wins / sum losses.

Seen data (all tuning happens here): DEV = US500, US30, US2000 CFDs, 2012-08 .. 2023-10-12.
Sealed data (opened once, for finalists + live baselines only):
  HOLD-T  = US500, US30, US2000, USTEC 2023-10-13 .. 2026-10-14 (USTEC was never used for dev).
  HOLD-M  = markets never used by any mean-reversion study, full history: DE40, FRA40, ESP35, AUS200, HK50 (CFDs),
            EWG, EWJ, EWU, EFA, EEM, FXI, INDA, SMH, XLK, XLV, XLP, XLE, VNQ (ETFs).
  Caveat: XM-1/SW-1 picked RSI2<10 and IBS<0.2 after seeing US500/US30 up to 2026-10, so HOLD-T is not virgin for the
  live baselines; it IS virgin for any parameter chosen here.

Grid (frozen in tune_dip.py): entry {RSI2<5..30, IBS<0.1..0.3, RSI2 & IBS combos, N down closes, k-day low,
2-day cumulative RSI2, stretch below SMA5 in ATR} x trend filter {none, >SMA200, >SMA100, >SMA50, SMA50>SMA200}
x exit {close>SMA5, >SMA3, >SMA10, >prev high, IBS>0.8|>prev high, RSI2>50, RSI2>70, first up close} x max hold {5,10,15}.
DEV objective: robust PF = min PF over the 6 cells (3 markets x halves 2012-17 / 2018-23-10), n >= 20 per cell.
Round 2: neighbourhood check, a finalist must sit on a plateau (median robust PF of its grid neighbours >= 1.2).
Finalists: up to 3 configs, plus the two live baselines (rsi2, ibs), all judged on the same sealed data.

PASS (finalist) = all of:
  G1 HOLD-T pooled PF >= 1.30, n >= 30, and PF > the better live baseline's HOLD-T PF.
  G2 HOLD-M pooled PF >= 1.15, PF > 1 in >= 2/3 of HOLD-M markets, and pooled PF > the better baseline's HOLD-M PF.
  G3 random-entry twin (same filter pool, same hold lengths, 1000 draws) p < 0.05 on HOLD-T pooled and HOLD-M pooled.
"Higher PF setup" = a PASS. A finalist that fails G1/G2 vs the baseline is not adopted, even if its PF is high.

## Part 2 - USTEC opening-range breakout (M1, New York clock, SC-1 costs: 1.5x median in-session spread,
## +0.5 spread on stop exits)
DEV = USTEC 2022-07-06 .. 2025-10-12. HOLD-T = USTEC 2025-10-13 .. 2026-10-13. HOLD-M = US500, US30 M1 2012-08 .. 2026-10
(SC-1 saw ORB-30 on these; no tuned parameter has).
Grid (frozen in tune_orb.py): range {5,15,30,45,60 min} x last entry {11:00,12:00,13:30,15:30} x stop {other side,
range mid} x target {EOD, 1R, 2R, 3R} x side {both, long only} x min range {0.15%, 0.3% of price}.
DEV objective: min PF over the DEV halves, n >= 100 per half; plateau check as Part 1. Up to 3 finalists + live ORB-30.
PASS = HOLD-T PF >= 1.2 and > live ORB HOLD-T PF (n >= 100); HOLD-M pooled PF >= 1.1 and > live ORB HOLD-M PF;
same-entries random-direction twin p < 0.05 on HOLD-T.

## Blind prediction Claude
Part 1: dev winners reach robust PF ~1.6-2.0 (vs live ~1.4); on sealed data they shrink toward the baselines.
P(at least one dip finalist PASSES) = 30%. Most likely failure: G1 or G2 "beats the baseline" by too little.
Part 2: P(an ORB finalist PASSES) = 15%; HOLD-M (US500/US30) PF ~1.0-1.1 for everything.
