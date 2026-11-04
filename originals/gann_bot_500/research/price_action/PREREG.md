# PA-1 — classic price-action patterns on gold (pre-registered 2026-10-14, before any run)

User: "what about price action, dig into it and research about it". Literature: Marshall, Young & Rose (2007) found
28 candlestick signals unprofitable on US large caps; SET-Thailand (SAGE Open 2017) mean returns of most patterns
not different from zero; no peer-reviewed gold test of inside-bar/NR7 (Crabel) found. Our own WHY-1: gold ~random walk.

Data: d_revival/m1.npz XAU M1 2010-2026, converted to UTC (exit2.to_utc). Bars H1, H4, D1 (UTC), a bar needs >=50% of
its minutes. ATR14 (Wilder) on each timeframe.

Patterns on a completed bar i (fixed textbook definitions, no tuning):
- PIN    lower wick >= 2/3 of range and body in the top third -> long (mirror short); range >= 0.5 ATR. Stop: bar extreme.
- PINX   PIN whose wick makes a new 20-bar low (long) / high (short). Stop: bar extreme.
- ENG    engulfing: prior bar opposite colour, body of i covers body of i-1, after a 3-bar move against
         (c[i-1] < c[i-4] for long). Stop: lowest low of i-1, i (mirror).
- IB     inside bar (h<h[i-1], l>l[i-1]); OCO stop entries at mother-bar high/low for the next 3 bars; stop at the other side.
- NR7    narrowest range of 7; OCO stop entries at bar i high/low for the next 3 bars; stop at the other side.
- SFP    swing failure: h[i] > highest high of the prior 20 bars and c[i] below that high -> short (mirror long). Stop: bar extreme.
Entry: next bar open (PIN, PINX, ENG, SFP); stop-entry fill at the level, or the M1 open if gapped through (IB, NR7).
Stop distance floored at 0.25 ATR. Exit: target 2R, else stop, else close after 10 bars of that timeframe.
Same M1 bar holding stop and target -> stop. OCO both sides on one M1 bar -> trade skipped.
One position at a time per pattern x timeframe. Cost $0.40/oz round trip (stress $0.80; IC Raw ~$0.22 shown).
Twin: same trades, same stop/target/exit, random direction (20 seeds).

PASS (per pattern x TF, 18 tests): net avg R > 0 in A 2010-17, B 2018-26 and C 2023+; real - twin >= 0.05R in each;
stress-cost avg R > 0 in B; overall t(real vs twin) >= 2.8 (multiple-testing guard). Anything else FAIL.
Blind prediction: all 18 FAIL; IB/NR7 near zero gross (breakout of compression = symmetric); PIN/ENG ~ twin.
