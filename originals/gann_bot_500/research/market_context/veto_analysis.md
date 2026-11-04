# Liquidity-context veto measurement — D & R

_Generated 2026-07-01T09:42:32Z._

## Mandatory caveats — read first

1. **Sample size.** Both profiles are young. If the vetoed n for a profile is <15, the row is labelled **NO CONCLUSION**; <100 is **directional only**. Do not act on a NO-CONCLUSION line.
2. **Timezone alignment.** The bot writes log timestamps with `datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')` (bot.py:598/1131/1465/1567) — i.e. naive-strings-that-represent-UTC. HistData `time` is a Unix epoch (UTC). Both are treated as UTC and compared by direct equality — no broker-server / NY offsets applied. The NY-local session windows (03–08 London, 08–17 NY, 19–00 Asia) are computed by `tz_convert('America/New_York')` on the UTC-indexed M1 frame, so DST is handled correctly.
3. **HistData is a proxy** for actual broker fills. Reconstructed prior-day / prior-session / Asian-range levels are near-identical to what the live broker would have shown, but not guaranteed identical to the tick the bot saw. HistData coverage ends **2026-06-19 17:57 UTC** — trades after that are labelled OUT_OF_HISTDATA and excluded from PF/win-rate.
4. **First-order screen only, not a re-backtest.** Assumes trade independence. Vetoing trade N would not have changed the state or P&L of trade N+1 in this analysis (no path dependence). Frame conclusions accordingly.
5. **P&L is expressed in points** (XAUUSD: 1 dollar = 100 points). Outcome (TP or SL) is determined from the log's own `sl_price` and `tp_price` by scanning HistData M1 forward from the entry bar; the first bar to touch either wins. If both fall inside the same M1 bar the trade is flagged AMBIGUOUS_SAME_BAR and excluded from PF/win-rate stats but reported in the excluded counts.

## Trade set

- **Profile D**: 7 real entries in log (MISSED_TIMEOUT rows already excluded). Eligible for stats (TP or SL resolvable in HistData): **6**. Excluded: OUT_OF_HISTDATA=1, AMBIGUOUS_SAME_BAR=0, OPEN_AT_HORIZON=0.
- **Profile R**: 8 real entries in log (MISSED_TIMEOUT rows already excluded). Eligible for stats (TP or SL resolvable in HistData): **4**. Excluded: OUT_OF_HISTDATA=4, AMBIGUOUS_SAME_BAR=0, OPEN_AT_HORIZON=0.

## Sensitivity table

Headline K (pre-registered): **1.0**. Other K reported for sensitivity; **do not** pick K by best result.

### Profile D

| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | Kept n | Kept win% | Kept avg (pts) | Kept PF | % vetoed | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.5 | 0 | — | — | — | 6 | 0.167 | -1120.3 | 0.436 | 0% | NO CONCLUSION (n<15) |
| 1 | 1 | 1 | 5198.5 | inf | 5 | 0 | -2384.1 | 0 | 17% | **HEADLINE** NO CONCLUSION (n<15) |
| 1.5 | 2 | 0.5 | 1163 | 1.81 | 4 | 0 | -2262 | 0 | 33% | NO CONCLUSION (n<15) |
| 2 | 3 | 0.333 | 237.5 | 1.159 | 3 | 0 | -2478.2 | 0 | 50% | NO CONCLUSION (n<15) |

### Profile R

| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | Kept n | Kept win% | Kept avg (pts) | Kept PF | % vetoed | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0.5 | 0 | — | — | — | 4 | 0.25 | -2119.1 | 0.272 | 0% | NO CONCLUSION (n<15) |
| 1 | 0 | — | — | — | 4 | 0.25 | -2119.1 | 0.272 | 0% | **HEADLINE** NO CONCLUSION (n<15) |
| 1.5 | 1 | 1 | 3160.5 | inf | 3 | 0 | -3879 | 0 | 25% | NO CONCLUSION (n<15) |
| 2 | 1 | 1 | 3160.5 | inf | 3 | 0 | -3879 | 0 | 25% | NO CONCLUSION (n<15) |

## How to read this

- The veto has value **only if the VETOED bucket is net-losing** (negative avg pts / PF < 1) and it kills a **workable fraction** — a veto that removes >70% of trades is impractical even if the killed ones lost slightly.
- If VETOED shows a positive avg / PF > 1, the rule is throwing away winners: **do not promote**.
- With small n, sign flips easily. Any row labelled NO CONCLUSION means the result is dominated by noise, not signal — report it, do not act on it.
- D and R are **not pooled**. Their entry gates differ (D uses the polarity flip, R does not — CODEBASE_TRUTH.md), so a level that vetoes a D setup does not necessarily veto the equivalent R setup, and mixing samples would mask that.

## Artifacts

- `veto_partition_D_K0.5.jsonl` — partitioned trades for Profile D at K=0.5.
- `veto_partition_D_K1.jsonl` — partitioned trades for Profile D at K=1.
- `veto_partition_D_K1.5.jsonl` — partitioned trades for Profile D at K=1.5.
- `veto_partition_D_K2.jsonl` — partitioned trades for Profile D at K=2.
- `veto_partition_R_K0.5.jsonl` — partitioned trades for Profile R at K=0.5.
- `veto_partition_R_K1.jsonl` — partitioned trades for Profile R at K=1.
- `veto_partition_R_K1.5.jsonl` — partitioned trades for Profile R at K=1.5.
- `veto_partition_R_K2.jsonl` — partitioned trades for Profile R at K=2.
- `veto_all_trades.jsonl` — every trade with its computed opposing-level info (VETOED/KEPT decision derived per K).
