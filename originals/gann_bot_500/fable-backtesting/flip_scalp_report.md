# Zone-flip momentum scalp — backtest (enter immediately on flip, fixed-$ TP)

_Generated 2026-07-02T15:55:54Z. Window 2021-06-19 -> 2026-06-19._

## Caveats — read first

1. **This is NOT live D/R logic.** It removes the H4-bias gate, H1 body-close confirmation, and Option-C M1 pullback. Pure breakout-momentum on the polarity-flip event, unthrottled (no cooldown, no max-open cap, no daily loss cap).
2. **Zone construction is the live one** (levels.py + signals._classify_zone imported directly, daily UTC-00:00 build, D-profile params). Flip rule = one H4 close beyond the level, identical to structure.check_zone_polarity / tools/zone_flip_alert.py. Max one flip per zone per day.
3. **Costs:** 20 pts/trade (13 spread + 7 commission). Fill = open of the first M1 bar after the H4 close. Same-M1-bar TP+SL resolved conservatively as SL.
4. **Fixed-$ targets are regime-sensitive** — a $10 move in 2021 ($1800 gold) is 2x the relative move it is at $4000+. Watch the IS/OOS drift.
5. **Dedup:** one trade per (H4 close, direction); `n_zones_flipped` recorded per trade.

## Events

Deduped flip events: **1262** (BUY 756 / SELL 506) over 1826 days (~4.8/week).

## Grid results (pnl in points, $1 = 100 pts; costs included)

| Cell | Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| TP5_SL5 | ALL | 1262 | 0.511 | 0.965 | -8.9 | 480 | -520 | 17680 |
| TP5_SL5 | IS | 883 | 0.515 | 0.981 | -4.7 | 480 | -520 | 17680 |
| TP5_SL5 | OOS | 379 | 0.501 | 0.928 | -18.7 | 480 | -520 | 13440 |
| TP5_SL10 | ALL | 1262 | 0.687 | 1.033 | 10.5 | 480 | -1020 | 19380 |
| TP5_SL10 | IS | 883 | 0.698 | 1.086 | 26.4 | 480 | -1020 | 15420 |
| TP5_SL10 | OOS | 379 | 0.662 | 0.923 | -26.6 | 480 | -1020 | 19380 |
| TP5_SL15 | ALL | 1262 | 0.769 | 1.057 | 20 | 480 | -1508.3 | 26523.3 |
| TP5_SL15 | IS | 883 | 0.769 | 1.063 | 21.8 | 480 | -1503.2 | 26523.3 |
| TP5_SL15 | OOS | 379 | 0.768 | 1.044 | 15.6 | 480 | -1520 | 14800 |
| TP5_FLIPEXIT | ALL | 1262 | 0.883 | 1.18 | 64.5 | 479.7 | -3060.6 | 41162.1 |
| TP5_FLIPEXIT | IS | 883 | 0.852 | 1.137 | 49.2 | 479.5 | -2421.3 | 41162.1 |
| TP5_FLIPEXIT | OOS | 379 | 0.955 | 1.28 | 100.2 | 480 | -7986.7 | 36486.3 |
| TP10_SL5 | ALL | 1262 | 0.346 | 0.997 | -0.9 | 979 | -520 | 34325.6 |
| TP10_SL5 | IS | 883 | 0.336 | 0.954 | -16 | 978.5 | -520 | 34325.6 |
| TP10_SL5 | OOS | 379 | 0.369 | 1.104 | 34.1 | 980 | -520 | 10220 |
| TP10_SL10 **(headline)** | ALL | 1262 | 0.522 | 1.05 | 24.4 | 978.1 | -1017.9 | 33087 |
| TP10_SL10 | IS | 883 | 0.523 | 1.055 | 26.4 | 977.3 | -1017 | 33087 |
| TP10_SL10 | OOS | 379 | 0.52 | 1.04 | 19.6 | 980 | -1020 | 17520 |
| TP10_SL15 | ALL | 1262 | 0.621 | 1.069 | 39.1 | 977.5 | -1500.1 | 50570.3 |
| TP10_SL15 | IS | 883 | 0.612 | 1.03 | 17.4 | 976.4 | -1492.3 | 50570.3 |
| TP10_SL15 | OOS | 379 | 0.644 | 1.165 | 89.5 | 980 | -1520 | 19980 |
| TP10_FLIPEXIT | ALL | 1262 | 0.773 | 1.116 | 78 | 974.1 | -2966.1 | 74951.4 |
| TP10_FLIPEXIT | IS | 883 | 0.717 | 1.091 | 58.2 | 970.9 | -2252.6 | 74951.4 |
| TP10_FLIPEXIT | OOS | 379 | 0.902 | 1.163 | 124.1 | 980 | -7787.1 | 64345 |
| TP15_SL5 | ALL | 1262 | 0.269 | 1.042 | 15.9 | 1474.9 | -520 | 41425.6 |
| TP15_SL5 | IS | 883 | 0.253 | 0.957 | -16.9 | 1472.2 | -520 | 41425.6 |
| TP15_SL5 | OOS | 379 | 0.306 | 1.255 | 92.1 | 1480 | -520 | 10080 |
| TP15_SL10 | ALL | 1262 | 0.429 | 1.085 | 49.5 | 1466.2 | -1017 | 48312.1 |
| TP15_SL10 | IS | 883 | 0.421 | 1.046 | 27.2 | 1459.9 | -1015.7 | 48312.1 |
| TP15_SL10 | OOS | 379 | 0.449 | 1.18 | 101.4 | 1480 | -1020 | 19000 |
| TP15_SL15 | ALL | 1262 | 0.536 | 1.129 | 88.8 | 1453.4 | -1490.4 | 65806.6 |
| TP15_SL15 | IS | 883 | 0.521 | 1.059 | 42.1 | 1440.9 | -1479.1 | 65806.6 |
| TP15_SL15 | OOS | 379 | 0.573 | 1.304 | 197.7 | 1480 | -1520 | 26840 |
| TP15_FLIPEXIT | ALL | 1262 | 0.698 | 1.143 | 125.4 | 1439.1 | -2912.3 | 105804 |
| TP15_FLIPEXIT | IS | 883 | 0.631 | 1.111 | 89 | 1415.3 | -2177 | 105804 |
| TP15_FLIPEXIT | OOS | 379 | 0.855 | 1.199 | 210.1 | 1480 | -7270.7 | 80946.7 |
| TP5_NOSL | ALL | 1262 | 0.956 | 0.926 | -36.4 | 480 | -11369.6 | 134078 |
| TP5_NOSL | IS | 883 | 0.943 | 0.858 | -75.1 | 480 | -9322.4 | 115275 |
| TP5_NOSL | OOS | 379 | 0.987 | 1.128 | 53.6 | 480 | -31841.4 | 56721 |
| TP10_NOSL | ALL | 1262 | 0.921 | 0.869 | -135.4 | 979.2 | -13087 | 288329 |
| TP10_NOSL | IS | 883 | 0.903 | 0.927 | -69.2 | 978.8 | -9781.6 | 146931 |
| TP10_NOSL | OOS | 379 | 0.963 | 0.765 | -289.7 | 980 | -33391.9 | 206375 |
| TP15_NOSL | ALL | 1262 | 0.884 | 0.887 | -166.3 | 1478.7 | -12643.6 | 367005 |
| TP15_NOSL | IS | 883 | 0.862 | 1.019 | 24.2 | 1478.1 | -9044.7 | 128801 |
| TP15_NOSL | OOS | 379 | 0.934 | 0.694 | -610.1 | 1480 | -30206.3 | 341744 |

## Validation flags

**TP5_SL5:** IS: PF 0.981 < 1.20 — no edge threshold; OOS: PF 0.928 < 1.20 — no edge threshold
**TP5_SL10:** IS: PF 1.086 < 1.20 — no edge threshold; OOS: PF 0.923 < 1.20 — no edge threshold
**TP5_SL15:** IS: PF 1.063 < 1.20 — no edge threshold; IS: DD 27% > 25% budget; OOS: PF 1.044 < 1.20 — no edge threshold
**TP5_FLIPEXIT:** IS: PF 1.137 < 1.20 — no edge threshold; IS: DD 41% > 25% budget; OOS: DD 36% > 25% budget
**TP10_SL5:** IS: PF 0.954 < 1.20 — no edge threshold; IS: DD 34% > 25% budget; OOS: PF 1.104 < 1.20 — no edge threshold
**TP10_SL10:** IS: PF 1.055 < 1.20 — no edge threshold; IS: DD 33% > 25% budget; OOS: PF 1.04 < 1.20 — no edge threshold
**TP10_SL15:** IS: PF 1.03 < 1.20 — no edge threshold; IS: DD 51% > 25% budget; OOS: PF 1.165 < 1.20 — no edge threshold
**TP10_FLIPEXIT:** IS: PF 1.091 < 1.20 — no edge threshold; IS: DD 75% > 25% budget; OOS: PF 1.163 < 1.20 — no edge threshold; OOS: DD 64% > 25% budget
**TP15_SL5:** IS: PF 0.957 < 1.20 — no edge threshold; IS: DD 41% > 25% budget
**TP15_SL10:** IS: PF 1.046 < 1.20 — no edge threshold; IS: DD 48% > 25% budget; OOS: PF 1.18 < 1.20 — no edge threshold
**TP15_SL15:** IS: PF 1.059 < 1.20 — no edge threshold; IS: DD 66% > 25% budget; OOS: DD 27% > 25% budget
**TP15_FLIPEXIT:** IS: PF 1.111 < 1.20 — no edge threshold; IS: DD 106% > 25% budget; OOS: PF 1.199 < 1.20 — no edge threshold; OOS: DD 81% > 25% budget
**TP5_NOSL:** IS: PF 0.858 < 1.20 — no edge threshold; IS: DD 115% > 25% budget; OOS: PF 1.128 < 1.20 — no edge threshold; OOS: DD 57% > 25% budget
**TP10_NOSL:** IS: PF 0.927 < 1.20 — no edge threshold; IS: DD 147% > 25% budget; OOS: PF 0.765 < 1.20 — no edge threshold; OOS: DD 206% > 25% budget
**TP15_NOSL:** IS: PF 1.019 < 1.20 — no edge threshold; IS: DD 129% > 25% budget; OOS: PF 0.694 < 1.20 — no edge threshold; OOS: DD 342% > 25% budget

## Headline cell breakdowns (TP10_SL10)

| Slice | n | Win% | PF | Expectancy (pts) |
|---|---:|---:|---:|---:|
| BUY | 756 | 0.528 | 1.074 | 35.6 |
| SELL | 506 | 0.514 | 1.015 | 7.7 |
| multi-zone flips (n_zones>1) | 429 | 0.517 | 1.031 | 15.4 |
| single-zone flips | 833 | 0.525 | 1.06 | 29 |

| Year | n | Win% | PF | Expectancy (pts) |
|---|---:|---:|---:|---:|
| 2021 | 118 | 0.475 | 0.852 | -79.4 |
| 2022 | 247 | 0.534 | 1.115 | 54 |
| 2023 | 230 | 0.504 | 0.975 | -12.4 |
| 2024 | 244 | 0.537 | 1.114 | 53.8 |
| 2025 | 279 | 0.556 | 1.201 | 91.1 |
| 2026 | 144 | 0.479 | 0.884 | -61.7 |

## TP-only, no stop of any kind (30-day hold horizon)

MAE = max adverse excursion: the worst open drawdown a trade sits through before it exits. TIMEOUT = still open after 30 days, marked to market at the last bar.

| Cell | n | TP hit | TIMEOUT | Win% | PF | Expectancy (pts) | MAE med | MAE p90 | MAE max | Hold med (h) | Hold p90 (h) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TP5_NOSL | 1262 | 1207 | 55 | 0.956 | 0.926 | -36.4 | 468 | 4171 | 102597 | 3.1 | 119.2 |
| TP10_NOSL | 1262 | 1161 | 101 | 0.921 | 0.869 | -135.4 | 945 | 7369 | 130980 | 14.6 | 410.7 |
| TP15_NOSL | 1262 | 1114 | 148 | 0.884 | 0.887 | -166.3 | 1280 | 10414 | 130980 | 35.1 | 697.0 |

## Artifacts

- `trades_headline.jsonl` — per-trade records, headline cell.
- `grid_summary.json` — full grid stats.
- `run_flip_scalp.py` — the harness.

