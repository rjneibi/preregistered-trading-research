# D/R three-run variant backtest — A / B / C1-C4

_Generated 2026-07-01T18:15:28Z_

Research-only. No live-code changes. All variant logic in `research/dr_backtest/variants.py` + `run_variants.py`.

## Step 0 — live-config echo (read from files, not hard-coded)

| Field | D (config.py) | R (config_R.py) |
|---|---|---|
| `POLARITY_FLIP` | `True` | `False` |
| `ADX_THRESHOLD` | `0` | `0` |
| `ATR_SL_MULT` | `1.0` | `1.5` |
| `ATR_TP_MULT` | `3.0` | `2.5` |
| `TP_FIXED_POINTS` | `900` | `1000` |
| `PARTIAL_CLOSE_ENABLED` | `True` | `True` |
| `PARTIAL_CLOSE_ATR_MULT` | `1.0` | `1.0` |
| `ATR_ZONE_WIDTH_MULT` | `0.3` | `0.3` |
| `CONFLUENCE_ATR_MULT` | `0.5` | `0.5` |
| `MAX_SPREAD_POINTS` | `40` | `40` |
| `BIAS_TF` | `H4` | `H4` |
| `CONFIRM_TF` | `H1` | `H1` |
| `SWING_LOOKBACK_H4` | `50` | `50` |
| `OPTION_C_ENABLED` | `True` | `False` |
| `MAX_ZONE_TRADES_PER_DAY` | `1` | `2` |
| `MAX_OPEN_TRADES` | `1` | `1` |

**Deltas vs the checklist you gave:**
- **D SL is `1.0×ATR`**, NOT 1.5× (you said 1.5). R matches (1.5×).
- **ADX_THRESHOLD is `0` for BOTH profiles** — the ADX gate is OFF live, not 25. Every arm in this backtest honors that (no ADX filtering).
- TP: D=`900pts` ✓, R=`1000pts` ✓.

## Step 1 — harness audit

1. **Fill model.** Entry fills at the **H1 CLOSE price** of the just-closed bar — matches the live bot semantic where `signals.evaluate_signal` returns a signal at H1 close and `bot.py` places a market order immediately after. No touch/next-bar/body-close variants. Exit prices come from the log's `sl_price`/`tp_price` scanning forward on M1.
2. **Intrabar TP vs SL priority.** When a single M1 bar's range contains BOTH TP and SL, `exit_sim.simulate_trade` flags `AMBIGUOUS_SAME_BAR` and resolves **conservatively as SL first**. The ambiguous count is reported separately; it does NOT enter PF/win-rate.
3. **Spread.** No modeled spread. `MAX_SPREAD_POINTS=40` is not enforced. Live spread is ~13pts (well under the cap) so the effect on aggregate results is small, but intraday gold results here are **modestly optimistic** — 13 pts × 2 (open+close) = 26pts of slippage per round-trip not deducted.
4. **Look-ahead audit.** Every gate reads only bars whose close time is `≤ cursor`:
   * `structure.get_h4_bias` — uses only completed H4 bars (via `completed_h4_before`)
   * `structure.check_zone_polarity` — replaced by `PolarityAdapter` reading only H4 bars with `bar_close < cursor`
   * `structure.h1_close_confirmed` — reads `bars_h1[-2]` = last CLOSED H1 bar (the trailing dummy bar mirrors live's `bars[-1]=forming` indexing)
   * `levels.build_zones` — uses completed D1 (`daily_open` = today's already-open D1 bar's OPEN, prev-day HLC = completed), completed H4 swing, and ATR-14 on closed H1 bars.
   * **Run B trend flag** — `variants.is_trend_day` uses `h1[h1.index <= cursor - 1h]`, i.e. STRICTLY closed H1 bars. Explicit assertion in the helper — the run is invalid if it fails. Confirmed via `assert_no_h1_leak` fired every 5000 evaluations.

## Step 2 — data window (actual)

- **Requested IS:** 2016-01-01 → 2022-12-31.  
- **Requested OOS:** 2023-01-01 → present.
- **HistData actual coverage:** 2015-11-17 00:00:00+00:00 → 2026-06-19 17:57:00+00:00.
- **Effective OOS end (clamp):** 2026-06-19 17:57:00+00:00.

## Step 3 — headline table

| Arm | Profile | IS n | IS PF | IS win% | IS MDD (pts) | OOS n | OOS PF | OOS win% | OOS MDD (pts) | notes |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A | D | 1688 | 1.412 | 0.591 | 8447 | 949 | 1.316 | 0.635 | 18030 | IS tier=validated · OOS tier=validated |
| A | R | 1449 | 0.905 | 0.578 | 50410 | 704 | 1.061 | 0.663 | 24266 | IS tier=validated · OOS tier=validated |
| B | D | 1817 | 1.387 | 0.587 | 8813 | 1026 | 1.310 | 0.633 | 24740 | trend n=477 (validated) PF=1.588 · range PF=1.105 |
| B | R | 1511 | 0.943 | 0.582 | 43922 | 738 | 1.059 | 0.661 | 21977 | trend n=124 (validated) PF=1.062 · range PF=1.058 |
| C1 | D | 1658 | 1.444 | 0.593 | 7767 | 873 | 1.344 | 0.628 | 14717 | IS tier=validated · OOS tier=validated |
| C1 | R | 1447 | 0.904 | 0.578 | 51410 | 691 | 1.061 | 0.663 | 24440 | IS tier=validated · OOS tier=validated |
| C2 | D | 1288 | 1.547 | 0.613 | 10776 | 771 | 1.505 | 0.671 | 11957 | IS tier=validated · OOS tier=validated |
| C2 | R | 1336 | 0.952 | 0.588 | 38357 | 660 | 1.098 | 0.671 | 27318 | IS tier=validated · OOS tier=validated |
| C3 | D | 622 | 1.144 | 0.543 | 11849 | 363 | 1.000 | 0.590 | 24363 | IS tier=validated · OOS tier=validated |
| C3 | R | 244 | 0.650 | 0.512 | 28140 | 111 | 1.156 | 0.658 | 10646 | IS tier=validated · OOS tier=validated |
| C4 | D | 2797 | 1.418 | 0.584 | 7904 | 1507 | 1.246 | 0.624 | 20077 | long n=746 PF=1.392 · short n=761 PF=1.117 |
| C4 | R | 4039 | 0.943 | 0.585 | 71073 | 1970 | 0.966 | 0.643 | 77129 | long n=823 PF=0.983 · short n=1147 PF=0.955 |

## OOS per-year breakdown — Run A (baseline)

| Profile | Year | n | PF | win% | Total pts | MDD (pts) | tier |
|---|---:|---:|---:|---:|---:|---:|---|
| D | 2023 | 206 | 1.500 | 0.597 | 18295.8 | 3936 | validated |
| D | 2024 | 281 | 1.480 | 0.598 | 34432.8 | 7433 | validated |
| D | 2025 | 309 | 1.269 | 0.628 | 33821.8 | 18030 | validated |
| D | 2026 | 153 | 1.175 | 0.771 | 15838.0 | 11957 | validated |
| R | 2023 | 145 | 1.103 | 0.648 | 3720.5 | 8394 | validated |
| R | 2024 | 220 | 1.061 | 0.600 | 4811.2 | 15843 | validated |
| R | 2025 | 208 | 1.054 | 0.673 | 6448.8 | 21253 | validated |
| R | 2026 | 131 | 1.054 | 0.771 | 5142.3 | 17145 | validated |

## Step 4 — T1 pre-registered verdict (per profile)

Conditions (in order):
  a. OOS trend-day n ≥ 15
  b. OOS trend-day PF ≥ 1.20
  c. Run B OOS PF ≥ Run A OOS PF (no dilution)
  d. Run B ranging-day OOS PF ≥ Run A OOS PF − 0.10 (misclassification budget)

**Profile D T1 verdict: NO-GO** — Run B OOS PF 1.310 < Run A OOS PF 1.316 (dilution).  
  · n_trend(OOS)=477, trend PF=1.588, range PF=1.105, A OOS PF=1.316, B OOS PF=1.310
**Profile R T1 verdict: NO-GO** — trend-day OOS PF=1.062 < 1.20.  
  · n_trend(OOS)=124, trend PF=1.062, range PF=1.058, A OOS PF=1.061, B OOS PF=1.059

## C1-C4 contribution ranking (Δ OOS PF vs Run A)

Positive Δ = removing that family HURT (family was contributing edge). Negative Δ = removing that family HELPED (family was diluting).

- **D:** C3 (Fib pivot OFF, ΔPF=0.316) → C4 (H4 bias OFF, ΔPF=0.070) → C1 (Gann OFF, ΔPF=-0.028) → C2 (Fib retr OFF, ΔPF=-0.189) · baseline OOS PF = 1.316
- **R:** C4 (H4 bias OFF, ΔPF=0.095) → C1 (Gann OFF, ΔPF=0.000) → C2 (Fib retr OFF, ΔPF=-0.037) → C3 (Fib pivot OFF, ΔPF=-0.095) · baseline OOS PF = 1.061

---
### Artifacts
- `trades_variants_A_D.jsonl`
- `trades_variants_A_R.jsonl`
- `trades_variants_B_D.jsonl`
- `trades_variants_B_R.jsonl`
- `trades_variants_C1_D.jsonl`
- `trades_variants_C1_R.jsonl`
- `trades_variants_C2_D.jsonl`
- `trades_variants_C2_R.jsonl`
- `trades_variants_C3_D.jsonl`
- `trades_variants_C3_R.jsonl`
- `trades_variants_C4_D.jsonl`
- `trades_variants_C4_R.jsonl`
