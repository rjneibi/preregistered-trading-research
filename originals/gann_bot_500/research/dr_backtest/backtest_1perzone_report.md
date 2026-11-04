# D/R backtest — 1-trade-per-zone-per-day throttle vs unthrottled

_Generated 2026-07-01T11:12:26Z._
_Baseline: current-config runs — D@900 (`trades_D.jsonl`), R@1000 (`trades_R.jsonl`)._
_IS/OOS calendar boundary (D): entry_ts ≤ **2025-02-27T21:00:00+00:00** = IS; after = OOS._
_IS/OOS calendar boundary (R): entry_ts ≤ **2025-03-20T18:00:00+00:00** = IS; after = OOS._

## Mandatory caveats — read first

1. **Still not full live replay.** This models the 1-trade-per-zone-per-day rule only. Still absent: `MAX_OPEN_POSITIONS=1`, the 3% daily-loss cap, trade cooldown, and — for R — the `MAX_ZONE_TRADES_PER_DAY=2` re-entry allowance with the profit requirement (R can legitimately take a second trade on the same zone if the first exited in profit). Applying strict 1/zone/day to BOTH profiles for controlled comparison undercounts R's live entry count.
2. **IS/OOS calendar boundary preserved.** The unthrottled 70/30 split produced a specific calendar date per profile; those exact dates are the boundary here. Re-splitting the smaller throttled set 70/30 by count would move the boundary and break comparability — not done.
3. **Same standing caveats as prior runs.** 5-year window is regime-specific (gold $1700 → $4500, does not represent full history). HistData is a broker-fill proxy. Clustered entries mean effective independent sample size is smaller than raw n — treat PF confidence as softer than n implies. These are reported metrics from a deterministic harness, not independently recomputed.
4. **Post-hoc dedup is valid because exits are per-entry-independent** in the harness (no shared position state across trades). Kept trades' exit outcomes are unchanged from the unthrottled run. The throttle key is `(utc_date, zone_source)` — matching live semantics at bot.py:1684 / 1713 where `zone_name = sig['zone_hit']['source']`.

## Dedup ratio

| Profile | Unthrottled entries | Kept (1/zone/day) | Removed | Kept fraction |
|---|---:|---:|---:|---:|
| **D** | 1353 | 1112 | 241 | 82.2% |
| **R** | 1013 | 791 | 222 | 78.1% |

## Outcome counts (kept trades)

| Outcome | D unthrottled | D 1/zone/day | Δ | R unthrottled | R 1/zone/day | Δ |
|---|---:|---:|---:|---:|---:|---:|
| TP | 292 | 239 | -53 | 207 | 152 | -55 |
| SL | 514 | 411 | -103 | 364 | 297 | -67 |
| PARTIAL_THEN_TP | 299 | 248 | -51 | 241 | 189 | -52 |
| PARTIAL_THEN_BE | 246 | 214 | -32 | 200 | 153 | -47 |
| AMBIGUOUS_SAME_BAR | 1 | 0 | -1 | 1 | 0 | -1 |
| OPEN_AT_HORIZON | 1 | 0 | -1 | 0 | 0 | +0 |
| OUT_OF_HISTDATA | 0 | 0 | +0 | 0 | 0 | +0 |

## Profile D — unthrottled vs 1-per-zone-per-day (D@900)

| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **ALL: unthrottled** | 1351 | 0.620 | 1.326 | 97.1 | 637.3 | -782.5 | 18030.3 |
| **ALL: 1/zone/day** | 1112 | 0.630 | 1.368 | 106.9 | 630.7 | -786.5 | 20532.0 |
| **ALL: Δ** | -239 | +0.010 | +0.042 | +9.8 | -6.6 | -4.0 | +2501.7 |
| **IS: unthrottled** | 946 | 0.589 | 1.409 | 88.4 | 517.2 | -525.6 | 8446.7 |
| **IS: 1/zone/day** | 782 | 0.602 | 1.472 | 98.5 | 509.9 | -524.7 | 6958.0 |
| **IS: Δ** | -164 | +0.013 | +0.063 | +10.1 | -7.3 | +0.9 | -1488.7 |
| **OOS: unthrottled** | 405 | 0.691 | 1.241 | 117.5 | 876.2 | -1582.0 | 18030.3 |
| **OOS: 1/zone/day** | 330 | 0.697 | 1.261 | 126.8 | 877.9 | -1600.7 | 20532.0 |
| **OOS: Δ** | -75 | +0.006 | +0.020 | +9.3 | +1.7 | -18.7 | +2501.7 |

### D validation flags
- **D unthrottled:** (no flags)
- **D 1/zone/day:** (no flags)

## Profile R — unthrottled vs 1-per-zone-per-day (R@1000)

| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **ALL: unthrottled** | 1012 | 0.640 | 1.060 | 24.8 | 682.2 | -1145.5 | 24266.4 |
| **ALL: 1/zone/day** | 791 | 0.625 | 1.018 | 7.6 | 677.6 | -1106.7 | 29792.8 |
| **ALL: Δ** | -221 | -0.015 | -0.042 | -17.2 | -4.6 | +38.8 | +5526.4 |
| **IS: unthrottled** | 708 | 0.607 | 1.078 | 23.6 | 539.6 | -774.6 | 15842.6 |
| **IS: 1/zone/day** | 564 | 0.596 | 1.034 | 10.4 | 539.7 | -769.6 | 12178.1 |
| **IS: Δ** | -144 | -0.011 | -0.044 | -13.2 | +0.1 | +5.0 | -3664.5 |
| **OOS: unthrottled** | 304 | 0.717 | 1.042 | 27.6 | 963.4 | -2344.5 | 24266.4 |
| **OOS: 1/zone/day** | 227 | 0.696 | 1.001 | 0.7 | 970.9 | -2220.8 | 29792.8 |
| **OOS: Δ** | -77 | -0.021 | -0.041 | -26.9 | +7.5 | +123.7 | +5526.4 |

### R validation flags
- **R unthrottled:** IS: PF 1.078 < 1.20 — no edge threshold; OOS: PF 1.042 < 1.20 — no edge threshold
- **R 1/zone/day:** IS: PF 1.034 < 1.20 — no edge threshold; OOS: PF 1.001 < 1.20 — no edge threshold; OOS: DD 30% > 25% budget

## Sample-size honesty

| Profile | Split (throttled) | n | Size label |
|---|---|---:|---|
| D | ALL | 1112 | OK (n≥100) |
| D | IS | 782 | OK (n≥100) |
| D | OOS | 330 | OK (n≥100) |
| R | ALL | 791 | OK (n≥100) |
| R | IS | 564 | OK (n≥100) |
| R | OOS | 227 | OK (n≥100) |

## Explicit read — did the throttle help or hurt?

- **D ALL:** PF ROSE from 1.326 → 1.368 (Δ +0.042, +3.2%). So the removed intra-zone repeat entries were **net HURTING** — 1/zone/day discards losers, so this throttle HELPS on the raw signal.
- **D IS:** PF ROSE from 1.409 → 1.472 (Δ +0.063, +4.5%). So the removed intra-zone repeat entries were **net HURTING** — 1/zone/day discards losers, so this throttle HELPS on the raw signal.
- **D OOS:** PF ROSE from 1.241 → 1.261 (Δ +0.020, +1.6%). So the removed intra-zone repeat entries were **net HURTING** — 1/zone/day discards losers, so this throttle HELPS on the raw signal.
- **R ALL:** PF FELL from 1.060 → 1.018 (Δ -0.042, -4.0%). So the removed intra-zone repeat entries were **net HELPING** — 1/zone/day discards winners, so this throttle HURTS on the raw signal.
- **R IS:** PF FELL from 1.078 → 1.034 (Δ -0.044, -4.1%). So the removed intra-zone repeat entries were **net HELPING** — 1/zone/day discards winners, so this throttle HURTS on the raw signal.
- **R OOS:** PF FELL from 1.042 → 1.001 (Δ -0.041, -3.9%). So the removed intra-zone repeat entries were **net HELPING** — 1/zone/day discards winners, so this throttle HURTS on the raw signal.

**Note on interpretation.** A PF drop means the FIRST intra-day trade per zone tends to have worse outcome than the AVERAGE across all fires on that zone that day. A rise means the first is better. In either case the effect is on the *unthrottled* metric — live D throttled to 1/zone/day is closer to the throttled row above; live R (2/zone/day with profit requirement) sits between the two but is not directly modeled here.

## Artifacts

- `trades_D_1pz.jsonl` — D kept trades after 1/zone/day dedup.
- `trades_R_1pz.jsonl` — R kept trades after 1/zone/day dedup.
- `run_1pz.py` — the post-hoc dedup script (no engine changes; reads `trades_{D,R}.jsonl`, writes the `_1pz` variants).
