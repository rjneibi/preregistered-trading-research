# GOLD-LIT-1 pre-registration (frozen 2026-10-14, before any run)

User: "why is nothing working on gold - find a method that works scientifically or by known
analysts." So this tests PUBLISHED gold anomalies exactly as published, not our own rules.
Anti-annexation note: BOT-LAB-1 killed "session drift" and found a fake Asia-long edge from the
broker reopen print. H-A is a fresh, explicit re-test of the published form, entering 2h+ after
the reopen, with a +15 min shift check built into the gate.

Data: XAUUSD M1 2010-01..2026-10 (d_revival/m1.npz, converted to UTC as in EXIT-2) and XAUUSD
D1 2004-06..2026-10 (cross_market/data_edge/XAUUSD_D1.npz). Windows A 2010-17 | B 2018-26 |
C 2023+ for intraday; halves 2004-14 | 2015-26 for monthly tests.

H-A1 "hat" Asia leg (Donati & Jung, CBS): every weekday BUY 00:15 UTC, SELL 07:00 UTC. Cost
  $0.40/oz round trip (stress $0.80). No swap (no rollover crossed).
H-A2 "hat" US leg: every weekday SELL 13:00 UTC, BUY back 20:00 UTC. Cost $0.40 (stress $0.80).
  Gate (each leg alone): net mean > 0 in A, B and C; full-sample net t >= 2; still > 0 in B and C
  at stress cost; and the same leg shifted +15 min (00:30 / 13:15 entry) is also > 0 in A, B, C.
H-B seasonality (Baur 2013 autumn; Potrykus & Augustynowicz 2024 winter): long gold only in
  B1 = Sep+Nov, B2 = Dec+Jan+Feb. Financing 3%/yr on long months. Gate: mean monthly return in
  the chosen months > mean of all other months in BOTH halves, Welch t >= 2 full sample, net > 0.
H-C long-horizon momentum (Bartsch, Baur, Dichtl, Drobetz 2018; 24m best): month-end, long next
  month if trailing return > 0, else flat. C1 = 12m, C2 = 24m lookback. Financing 3%/yr on held
  months, 0.05% per switch. Buy-and-hold pays the same 3%. Gate: Sharpe >= buy-and-hold Sharpe in
  BOTH halves AND full-sample max drawdown smaller than buy-and-hold.
No variant is added after the run. A PASS means "worth a demo forward test", nothing more.

Blind predictions (Claude): H-A1 FAIL 65%, H-A2 FAIL 70%, H-B1 FAIL 75%, H-B2 FAIL 70%,
H-C1 FAIL 55%, H-C2 FAIL 55%. User: not recorded.
