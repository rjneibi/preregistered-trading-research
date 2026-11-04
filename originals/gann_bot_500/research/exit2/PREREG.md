# EXIT-2 pre-registration (frozen 2026-10-14, before any run)

Question (user, 2026-10-14): the old bots' best trades were cut short - the flip bot's 24h hard
close shut a trade "deep in profit", Core+Polarity took small fixed targets. Do the winners get
cut off? Does letting them run turn the flip bot's entries into an edge?

Scope: ENTRIES ARE FIXED (flip_bot v1.2 conviction spec). Only the profit side of the exit varies.
Core+Polarity (D) exits are NOT re-tested here: D-REVIVAL (2026-10-13) already ran its exit/gate
variants and none survived both halves (anti-annexation). D gets a forensic post-mortem only.

Data: research/d_revival/m1.npz XAUUSD M1 bid 2010-01..2026-10 (broker time, converted to UTC
by US-DST rule: -3h in US DST, -2h otherwise). H1 bars built from M1 in UTC.

Entry (flip_bot.py v1.2): prev UTC day pivots PP=(H+L+C)/3, R3=PP+(H-L), S3=PP-(H-L). ATR =
Wilder 14 on UTC H1, hivol = ATR > median of last 90d. Conviction = an H1 close at 12/16/20 UTC
beyond R3 (BUY) / S3 (SELL) - that bar fires both arms. Skip Mondays; skip a level already
crossed by any of the last 10 H4 closes ("dead"); max 1 trade per direction per day.
Enter at the next M1 open. SL = 2.4 ATR. Risk managers kept in EVERY variant: hivol half-out at
-1.2 ATR; lovol bail at -1.0 ATR after 8h. Exits walked on M1, stop checked before target.

Variants (only the profit side differs):
  E0  live: TP +0.8 ATR, hard close 24h
  E1  no TP, hard close 24h
  E2  no TP, hard close 72h
  E3  no TP; at +1 ATR stop to entry, then trail 2.4 ATR behind best; max 5 days
  E4  TP +0.8 ATR, NO time limit (max 10 days)
  E5  TP +2.4 ATR (1:1), hard close 72h
Cost: $0.50 per round trip (spread + slip); stress $1.00. Unit = R (risk = 2.4 ATR).
Random twin: same days, random H1 close time 12-20 UTC, random side, same ATR stop and exit;
average of 20 seeds.

Windows: A = 2010-2017, B = 2018-2026, C = 2023+ (recent).
GATE - a variant Ek PASSES (= worth replacing E0) only if, in ALL of A, B and C:
  1. avgR(Ek) > avgR(E0)
  2. avgR(Ek) - avgR(twin Ek) >= +0.05R
  3. net > 0 at the $1.00 stress cost
and over the full sample the Ek - twin difference has t >= 2.
Anything else = FAIL. No variant is added after the run.

Blind prediction (Claude, before run): all FAIL, confidence 70% - gold is a random walk at these
horizons (WHY-1), so exit shape moves win rate, not expectancy. Possible exception E3/E2 in
B/C because 2021-26 trended (era effect, the known unsolved problem). User prediction: not recorded.
