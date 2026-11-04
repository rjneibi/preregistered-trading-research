> Copied as found from `originals/gann_bot_500/research/sweep_mtf/PREREG.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# SWEEP-MTF-1: video "liquidity sweep" setup, HTF level + LTF close-back (pre-registered 2026-10-26, before any run)

User pasted a chat about an ICT/SMC video (XAUUSD; pairings 4H->15M, 1H->M5) and asked to backtest it.
Kill-list context: PA-1 SFP (single-TF 20-bar swing failure, H1/H4/D1) FAIL; TA-LAB Asia sweep fade = look-ahead leak;
NY/London-range and previous-day sweeps FAIL; own_sweep: stop-outs do not reverse more than random. This is a NEW
mechanism variant (two-timeframe: N=3 fractal swing on the higher TF, close-back confirmation on the lower TF), so it
gets its own pre-registration instead of riding on an old one (anti-annexation).

Data: d_revival/m1.npz XAU M1 bid 2010-01..2026-10-12, converted to UTC (same to_utc as pa1). All timeframes are built
from M1 in UTC, so they line up exactly. Bid only -> flat cost $0.30 spread + $0.10 slippage = $0.40/oz round trip
(also shown: $0, IC Raw $0.22, stress $0.80).

Rules (short side; longs mirror on swing lows):
1. HTF swing high: bar j with high strictly above the highs of the 3 bars on each side. Usable only after bar j+3 closed.
2. Sweep: first LTF bar after confirmation whose high > level. The level is consumed then (one trade per level max).
3. Confirmation: the first LTF bar in the 12 bars starting at the sweep bar that has high > level and close < level.
   No such close within 12 LTF bars -> setup cancelled.
4. Entry: short at the next LTF bar's open (skipped if that bar starts > 60 min later, e.g. weekend).
5. Stop: highest LTF high from the sweep bar to the confirmation bar + $0.20. Skipped if entry >= stop.
6. Target: 2R and 3R. Exit simulated on M1; stop and target on the same M1 bar = stop; gap through stop fills at open.
   Time cap 288 LTF bars, then exit at the close.
7. One open position at a time per variant (later signals while in a trade are skipped).

Variants: A H1->M5; B H4->M15; C = A + H4 trend filter (short only if last closed H4 close < H4 EMA50, longs mirror);
D = A + entry time 07:00-20:00 UTC.

Windows: MAIN = last 3 years 2023-10-12..2026-10-12; IS = first 2 years of it, OOS = last 12 months.
HIST = 2010-01..2016-12 and 2017-01..2023-10-11 (older data never used to pick anything).
Target choice: per variant, 2R vs 3R picked by IS net avg R only; only that pick is judged.
Twin: same entries/risk/target/time cap, random direction, 20 seeds.

PASS (per variant, 4 tests): IS net avg R > 0; OOS net avg R > 0 with n >= 30; real - twin >= 0.05R in IS and in OOS;
HIST net avg R > 0 in both halves; t(real vs twin, 2010-2026) >= 2.8. Anything else FAIL.

Blind prediction Claude (confidence 85%): 4/4 FAIL. Gross ~ twin (within 0.05R); win rate ~ 1/(1+target) (32-36% at 2R);
M5 median stop $2-4 so the $0.40 cost takes 0.10-0.20R per trade; C does not beat A by > 0.05R in both IS and OOS;
B has the smallest cost hit (wider stops) but is still ~ twin.
