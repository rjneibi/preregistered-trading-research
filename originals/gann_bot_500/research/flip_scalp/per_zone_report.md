# Which zone flips can you trust? — per-zone backtest results

_Generated 2026-07-02. Data: 1,262 zone-flip events, XAUUSD, 2021-06-19 → 2026-06-19._

**The test:** every time a zone flipped (H4 close beyond its level), we asked:
did price then make **+$10 in the flip direction before it made -$10 against it?**
Win% above ~51% and PF above 1.0 = the flip has predictive value. PF ≥ 1.20 = your
house "real edge" bar. Costs (spread+commission) included.

## Ranking — all zones with a meaningful sample

| Rank | Zone | Flips (n) | Win% | Profit factor | Verdict |
|---|---|---:|---:|---:|---|
| 1 | **R3** | 216 | 55.6% | **1.21** | ✅ Best flip signal. Prior-day full-range breakout up. |
| 2 | **S3** | 138 | 55.1% | **1.18** | ✅ Same, downside. |
| 3 | S1 | 244 | 53.3% | 1.10 | ➖ Slight tilt, not tradeable alone |
| 4 | S2 | 207 | 52.7% | 1.07 | ➖ Slight tilt |
| 5 | R2 | 335 | 52.5% | 1.07 | ➖ Slight tilt |
| 6 | R1 | 369 | 51.2% | 1.00 | ⚠️ **Pure noise.** Flips every other day, means nothing. |
| 7 | R45 | 84 | 50.0% | 0.96 | ⚠️ Noise |
| 8 | fib_382 | 48 | 50.0% | 0.96 | ⚠️ Noise |
| 9 | S45 | 67 | 44.8% | 0.78 | ❌ **Anti-signal** — flips through it tend to reverse |
| 10 | **fib_618** | 74 | 44.6% | **0.79** | ❌ **Anti-signal.** A close through fib_618 usually = retracement exhausting, not breakout. |
| 11 | fib_786 | 33 | 39.4% | 0.63 | ❌ Anti-signal (small sample) |

Rare flips, too few to trust statistically (n < 20): **R90 went 11/15, PF 2.64** —
far Gann levels almost never flip, and when they do the move is real. PP (n=19,
PF 1.32) similar. Watch these live, but n is too small to bet on.

## Does the good tier survive out-of-sample? (70/30 chronological split)

| Subset | ALL PF | In-sample PF | Out-of-sample PF | Read |
|---|---:|---:|---:|---|
| R3+S3 | 1.196 | 1.232 | 1.118 | Close, but fails the 1.20 bar recently |
| R3 only | 1.209 | 1.092 | 1.537 | Inconsistent between halves |
| S3 only | 1.178 | 1.369 | 0.83 | Inverted — regime-dependent |
| R2+R3+S2+S3 | 1.143 | 1.144 | 1.140 | Very stable, but thin — below 1.20 |

## Bottom line

1. **Trust hierarchy: the further the level from the day's open, the more its flip
   means.** Outer pivots (R3/S3) carry real information; R1 is noise; fib
   retracement flips actually lean the OTHER way.
2. **No zone's flip is a standalone strategy** — even R3/S3 don't clear PF 1.20
   out-of-sample. Best use is as a quality filter inside D's existing confluence
   logic: weight pivot-family flips up, fib flips down (or invert them).
3. **For reading live flip alerts:** a fib_618 or S45/R45 flip line in the alert
   is not confirmation — historically it's a mild fade signal. An R3/S3 or far-Gann
   (R90+) flip is the line worth acting on.

## Files

- `per_zone_accuracy.csv` — full numbers incl. buy/sell splits and no-stop scores
- `flip_scalp_report.md` — the underlying strategy backtest (all exit grids)
- `events.jsonl` — all 1,262 flip events (cached for future analysis)
