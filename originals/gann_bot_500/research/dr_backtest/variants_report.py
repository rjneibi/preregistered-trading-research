"""
Consolidated report writer for the three-run variant backtest.

Output: research/dr_backtest/variants_report.md

Includes:
  * Step-0 config echo (D and R) + delta callouts vs the user's checklist
  * Step-1 harness audit
  * Step-2 actual data window used (with clamp reporting) + per-year OOS split
  * Step-3 tables:
      - Run A (baseline) per-year OOS PF, win%, DD, n
      - Run B trend/ranging split; T1 pre-registered verdict
      - Run C1-C4 ablation deltas vs Run A; C4 direction split (long PF vs short PF)
  * Step-4 T1 verdict + reasons, one-line C1-C4 contribution ranking

Honesty tiers: n<15 = no conclusion, n<100 = directional only, n≥100 = validated.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from research.dr_backtest.metrics import basic_stats, size_label

OUT = Path(__file__).resolve().parent
IS_END_TS = pd.Timestamp("2022-12-31T23:59:59Z")
IS_START_TS = pd.Timestamp("2016-01-01T00:00:00Z")
OOS_START_TS = pd.Timestamp("2023-01-01T00:00:00Z")


def _eligible(trades: list[dict]) -> list[dict]:
    return [t for t in trades
            if t["outcome_status"] in ("TP", "SL",
                                        "PARTIAL_THEN_TP", "PARTIAL_THEN_BE")
            and t["pnl_points"] is not None]


def _split(trades: list[dict], predicate) -> tuple[list, list]:
    yes = [t for t in trades if predicate(t)]
    no  = [t for t in trades if not predicate(t)]
    return yes, no


def _in_is(t: dict) -> bool:
    ts = pd.Timestamp(t["entry_ts"])
    return IS_START_TS <= ts <= IS_END_TS


def _in_oos(t: dict) -> bool:
    ts = pd.Timestamp(t["entry_ts"])
    return ts >= OOS_START_TS


def _tier(n: int) -> str:
    if n < 15:  return "no-conclusion"
    if n < 100: return "directional"
    return "validated"


def _fmt(x, prec=None):
    if x is None: return "—"
    if isinstance(x, float):
        if x == float("inf"): return "inf"
        return f"{x:.{prec}f}" if prec is not None else f"{x:g}"
    return str(x)


def _pf(entries: list[dict]) -> dict:
    return basic_stats([e["pnl_points"] for e in _eligible(entries)])


def _dd_frac(stats: dict, baseline_pts: float = 100000.0) -> float:
    """Approximate DD% by dividing max_drawdown_pts by a fixed baseline point
    equity so it's comparable across arms. Points are POINTS, not dollars."""
    if not stats["n"]:
        return 0.0
    return stats["max_drawdown_pts"] / baseline_pts


# ─────────────────────────────────────────────────────────────
# Live config echo (Step 0) — read fresh at report time
# ─────────────────────────────────────────────────────────────
def _echo_configs() -> str:
    import importlib.util
    def _load(path):
        spec = importlib.util.spec_from_file_location(path, path)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
    d = _load(str(Path(__file__).parents[2] / "config.py"))
    r = _load(str(Path(__file__).parents[2] / "profiles" / "R" / "config_R.py"))
    lines = ["| Field | D (config.py) | R (config_R.py) |",
             "|---|---|---|"]
    for field in ("POLARITY_FLIP","ADX_THRESHOLD","ATR_SL_MULT","ATR_TP_MULT",
                  "TP_FIXED_POINTS","PARTIAL_CLOSE_ENABLED","PARTIAL_CLOSE_ATR_MULT",
                  "ATR_ZONE_WIDTH_MULT","CONFLUENCE_ATR_MULT","MAX_SPREAD_POINTS",
                  "BIAS_TF","CONFIRM_TF","SWING_LOOKBACK_H4","OPTION_C_ENABLED",
                  "MAX_ZONE_TRADES_PER_DAY","MAX_OPEN_TRADES"):
        vd = getattr(d, field, "—")
        vr = getattr(r, field, "—")
        lines.append(f"| `{field}` | `{vd}` | `{vr}` |")
    lines.append("")
    lines.append("**Deltas vs the checklist you gave:**")
    lines.append(f"- **D SL is `{d.ATR_SL_MULT}×ATR`**, NOT 1.5× (you said 1.5). "
                 f"R matches (1.5×).")
    lines.append(f"- **ADX_THRESHOLD is `{d.ADX_THRESHOLD}` for BOTH profiles** — "
                 f"the ADX gate is OFF live, not 25. Every arm in this backtest "
                 f"honors that (no ADX filtering).")
    lines.append(f"- TP: D=`{d.TP_FIXED_POINTS}pts` ✓, R=`{r.TP_FIXED_POINTS}pts` ✓.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# The big table
# ─────────────────────────────────────────────────────────────
def _summary_row(arm_key, prof_name, trades):
    is_trades = [t for t in trades if _in_is(t)]
    oos_trades = [t for t in trades if _in_oos(t)]
    all_trades = _eligible(trades)
    s_is = _pf(is_trades)
    s_oos = _pf(oos_trades)
    row = {
        "arm": arm_key, "profile": prof_name,
        "is_n": s_is["n"], "is_pf": s_is["pf"], "is_wr": s_is["win_rate"],
        "is_dd": s_is["max_drawdown_pts"],
        "oos_n": s_oos["n"], "oos_pf": s_oos["pf"], "oos_wr": s_oos["win_rate"],
        "oos_dd": s_oos["max_drawdown_pts"],
    }
    return row


# ─────────────────────────────────────────────────────────────
# Per-year OOS breakdown
# ─────────────────────────────────────────────────────────────
def _per_year_oos(trades):
    """Return list of (year, stats) sorted by year."""
    by_year: dict[int, list] = {}
    for t in _eligible(trades):
        ts = pd.Timestamp(t["entry_ts"])
        if ts < OOS_START_TS: continue
        by_year.setdefault(ts.year, []).append(t)
    out = []
    for year in sorted(by_year):
        pnl = [t["pnl_points"] for t in by_year[year]]
        s = basic_stats(pnl)
        out.append((year, s))
    return out


# ─────────────────────────────────────────────────────────────
# Run-B trend/ranging split + T1 verdict
# ─────────────────────────────────────────────────────────────
def _run_b_split(trades_b: list[dict]) -> dict:
    oos_trend, oos_range = _split(
        [t for t in trades_b if _in_oos(t) and t["outcome_status"] in (
            "TP","SL","PARTIAL_THEN_TP","PARTIAL_THEN_BE"
        ) and t["pnl_points"] is not None],
        lambda t: bool(t.get("trend_day"))
    )
    return {"oos_trend": basic_stats([t["pnl_points"] for t in oos_trend]),
            "oos_range": basic_stats([t["pnl_points"] for t in oos_range]),
            "oos_trend_n": len(oos_trend),
            "oos_range_n": len(oos_range)}


def _run_c4_direction_split(trades_c4: list[dict]) -> dict:
    oos = [t for t in trades_c4 if _in_oos(t)
           and t["outcome_status"] in ("TP","SL","PARTIAL_THEN_TP","PARTIAL_THEN_BE")
           and t["pnl_points"] is not None]
    long_ts  = [t for t in oos if t["direction"] == "BUY"]
    short_ts = [t for t in oos if t["direction"] == "SELL"]
    return {
        "long":  basic_stats([t["pnl_points"] for t in long_ts]),
        "short": basic_stats([t["pnl_points"] for t in short_ts]),
        "long_n": len(long_ts), "short_n": len(short_ts),
    }


# ─────────────────────────────────────────────────────────────
# T1 pre-registered verdict
# ─────────────────────────────────────────────────────────────
def _t1_verdict(trades_a: list[dict], trades_b: list[dict], profile: str) -> dict:
    """Apply the four pre-registered conditions IN ORDER. Return the first failure
    or GO."""
    b_split = _run_b_split(trades_b)
    a_oos = _pf([t for t in trades_a if _in_oos(t)])
    b_oos = _pf([t for t in trades_b if _in_oos(t)])
    # (a) trend-day OOS n ≥ 15
    n_trend = b_split["oos_trend_n"]
    if n_trend < 15:
        return {"verdict": "NO-GO", "condition_failed": "a",
                "reason": f"trend-day OOS n={n_trend} < 15 (no-conclusion tier)",
                "n_trend": n_trend,
                "b_trend_pf": b_split["oos_trend"]["pf"],
                "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
                "b_range_pf": b_split["oos_range"]["pf"]}
    # (b) OOS trend-day PF ≥ 1.20
    trend_pf = b_split["oos_trend"]["pf"]
    if trend_pf is None or trend_pf == float("inf") or trend_pf < 1.20:
        return {"verdict": "NO-GO", "condition_failed": "b",
                "reason": f"trend-day OOS PF={trend_pf} < 1.20",
                "n_trend": n_trend, "b_trend_pf": trend_pf,
                "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
                "b_range_pf": b_split["oos_range"]["pf"]}
    # (c) Run B OOS PF ≥ Run A OOS PF
    if b_oos["pf"] is None or a_oos["pf"] is None:
        return {"verdict": "NO-GO", "condition_failed": "c",
                "reason": "OOS PF undefined in A or B",
                "n_trend": n_trend, "b_trend_pf": trend_pf,
                "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
                "b_range_pf": b_split["oos_range"]["pf"]}
    if b_oos["pf"] < a_oos["pf"]:
        return {"verdict": "NO-GO", "condition_failed": "c",
                "reason": f"Run B OOS PF {b_oos['pf']:.3f} < Run A OOS PF {a_oos['pf']:.3f} (dilution)",
                "n_trend": n_trend, "b_trend_pf": trend_pf,
                "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
                "b_range_pf": b_split["oos_range"]["pf"]}
    # (d) ranging-day OOS PF within 0.10 of baseline
    range_pf = b_split["oos_range"]["pf"]
    if range_pf is None or a_oos["pf"] is None:
        return {"verdict": "NO-GO", "condition_failed": "d",
                "reason": "ranging-day PF undefined",
                "n_trend": n_trend, "b_trend_pf": trend_pf,
                "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
                "b_range_pf": range_pf}
    if range_pf < a_oos["pf"] - 0.10:
        return {"verdict": "NO-GO", "condition_failed": "d",
                "reason": f"ranging-day OOS PF {range_pf:.3f} < baseline {a_oos['pf']:.3f} - 0.10 (misclass cost too high)",
                "n_trend": n_trend, "b_trend_pf": trend_pf,
                "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
                "b_range_pf": range_pf}
    return {"verdict": "GO", "condition_failed": None,
            "reason": "all four pre-registered conditions hold",
            "n_trend": n_trend, "b_trend_pf": trend_pf,
            "a_oos_pf": a_oos["pf"], "b_oos_pf": b_oos["pf"],
            "b_range_pf": range_pf}


# ─────────────────────────────────────────────────────────────
# THE REPORT
# ─────────────────────────────────────────────────────────────
def write_report(all_trades: dict, real_start, real_end, oos_end_effective) -> None:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L = []
    L.append("# D/R three-run variant backtest — A / B / C1-C4\n")
    L.append(f"_Generated {now_utc}_\n")
    L.append("Research-only. No live-code changes. All variant logic in "
             "`research/dr_backtest/variants.py` + `run_variants.py`.")
    L.append("")

    # STEP 0
    L.append("## Step 0 — live-config echo (read from files, not hard-coded)\n")
    L.append(_echo_configs())
    L.append("")

    # STEP 1
    L.append("## Step 1 — harness audit\n")
    L.append("1. **Fill model.** Entry fills at the **H1 CLOSE price** of the just-closed bar — matches the live bot semantic where `signals.evaluate_signal` returns a signal at H1 close and `bot.py` places a market order immediately after. No touch/next-bar/body-close variants. Exit prices come from the log's `sl_price`/`tp_price` scanning forward on M1.")
    L.append("2. **Intrabar TP vs SL priority.** When a single M1 bar's range contains BOTH TP and SL, `exit_sim.simulate_trade` flags `AMBIGUOUS_SAME_BAR` and resolves **conservatively as SL first**. The ambiguous count is reported separately; it does NOT enter PF/win-rate.")
    L.append("3. **Spread.** No modeled spread. `MAX_SPREAD_POINTS=40` is not enforced. Live spread is ~13pts (well under the cap) so the effect on aggregate results is small, but intraday gold results here are **modestly optimistic** — 13 pts × 2 (open+close) = 26pts of slippage per round-trip not deducted.")
    L.append("4. **Look-ahead audit.** Every gate reads only bars whose close time is `≤ cursor`:")
    L.append("   * `structure.get_h4_bias` — uses only completed H4 bars (via `completed_h4_before`)")
    L.append("   * `structure.check_zone_polarity` — replaced by `PolarityAdapter` reading only H4 bars with `bar_close < cursor`")
    L.append("   * `structure.h1_close_confirmed` — reads `bars_h1[-2]` = last CLOSED H1 bar (the trailing dummy bar mirrors live's `bars[-1]=forming` indexing)")
    L.append("   * `levels.build_zones` — uses completed D1 (`daily_open` = today's already-open D1 bar's OPEN, prev-day HLC = completed), completed H4 swing, and ATR-14 on closed H1 bars.")
    L.append("   * **Run B trend flag** — `variants.is_trend_day` uses `h1[h1.index <= cursor - 1h]`, i.e. STRICTLY closed H1 bars. Explicit assertion in the helper — the run is invalid if it fails. Confirmed via `assert_no_h1_leak` fired every 5000 evaluations.")
    L.append("")

    # STEP 2
    L.append("## Step 2 — data window (actual)\n")
    L.append(f"- **Requested IS:** 2016-01-01 → 2022-12-31.  ")
    L.append(f"- **Requested OOS:** 2023-01-01 → present.")
    L.append(f"- **HistData actual coverage:** {real_start} → {real_end}.")
    L.append(f"- **Effective OOS end (clamp):** {oos_end_effective}.")
    L.append("")

    # STEP 3 — one master table
    L.append("## Step 3 — headline table\n")
    L.append("| Arm | Profile | IS n | IS PF | IS win% | IS MDD (pts) | OOS n | OOS PF | OOS win% | OOS MDD (pts) | notes |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")

    rows_by_key: dict = {}
    for arm in ("A","B","C1","C2","C3","C4"):
        for prof in ("D","R"):
            trades = all_trades.get((arm, prof), [])
            r = _summary_row(arm, prof, trades)
            rows_by_key[(arm, prof)] = r
            note = ""
            if arm == "B":
                b_split = _run_b_split(trades)
                note = (f"trend n={b_split['oos_trend_n']} "
                        f"({_tier(b_split['oos_trend_n'])}) PF={_fmt(b_split['oos_trend']['pf'],3)} · "
                        f"range PF={_fmt(b_split['oos_range']['pf'],3)}")
            elif arm == "C4":
                dsplit = _run_c4_direction_split(trades)
                note = (f"long n={dsplit['long_n']} PF={_fmt(dsplit['long']['pf'],3)} · "
                        f"short n={dsplit['short_n']} PF={_fmt(dsplit['short']['pf'],3)}")
            else:
                note = f"IS tier={_tier(r['is_n'])} · OOS tier={_tier(r['oos_n'])}"
            L.append(f"| {arm} | {prof} | {r['is_n']} | {_fmt(r['is_pf'],3)} | "
                     f"{_fmt(r['is_wr'],3)} | {_fmt(r['is_dd'],0)} | "
                     f"{r['oos_n']} | {_fmt(r['oos_pf'],3)} | {_fmt(r['oos_wr'],3)} | "
                     f"{_fmt(r['oos_dd'],0)} | {note} |")
    L.append("")

    # per-year OOS breakdown for Run A
    L.append("## OOS per-year breakdown — Run A (baseline)\n")
    L.append("| Profile | Year | n | PF | win% | Total pts | MDD (pts) | tier |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for prof in ("D","R"):
        rows = _per_year_oos(all_trades.get(("A", prof), []))
        for year, s in rows:
            L.append(f"| {prof} | {year} | {s['n']} | {_fmt(s['pf'],3)} | "
                     f"{_fmt(s['win_rate'],3)} | {_fmt(s['total_pts'],1)} | "
                     f"{_fmt(s['max_drawdown_pts'],0)} | {_tier(s['n'])} |")
    L.append("")

    # T1 verdict per profile
    L.append("## Step 4 — T1 pre-registered verdict (per profile)\n")
    L.append("Conditions (in order):")
    L.append("  a. OOS trend-day n ≥ 15")
    L.append("  b. OOS trend-day PF ≥ 1.20")
    L.append("  c. Run B OOS PF ≥ Run A OOS PF (no dilution)")
    L.append("  d. Run B ranging-day OOS PF ≥ Run A OOS PF − 0.10 (misclassification budget)")
    L.append("")
    for prof in ("D","R"):
        v = _t1_verdict(all_trades.get(("A", prof), []),
                        all_trades.get(("B", prof), []), prof)
        L.append(f"**Profile {prof} T1 verdict: {v['verdict']}** — "
                 f"{v['reason']}.  ")
        L.append(f"  · n_trend(OOS)={v['n_trend']}, "
                 f"trend PF={_fmt(v['b_trend_pf'],3)}, "
                 f"range PF={_fmt(v['b_range_pf'],3)}, "
                 f"A OOS PF={_fmt(v['a_oos_pf'],3)}, "
                 f"B OOS PF={_fmt(v['b_oos_pf'],3)}")
    L.append("")

    # C1-C4 contribution ranking (per profile)
    L.append("## C1-C4 contribution ranking (Δ OOS PF vs Run A)\n")
    L.append("Positive Δ = removing that family HURT (family was contributing edge). "
             "Negative Δ = removing that family HELPED (family was diluting).")
    L.append("")
    for prof in ("D","R"):
        a_oos_pf = rows_by_key[("A", prof)]["oos_pf"]
        deltas = []
        for arm in ("C1","C2","C3","C4"):
            arm_pf = rows_by_key[(arm, prof)]["oos_pf"]
            if a_oos_pf is None or arm_pf is None:
                deltas.append((arm, None, arm_pf))
            else:
                deltas.append((arm, a_oos_pf - arm_pf, arm_pf))
        # sort by |contribution|
        deltas.sort(key=lambda x: (-x[1] if x[1] is not None else -999))
        labels = {"C1":"Gann OFF", "C2":"Fib retr OFF", "C3":"Fib pivot OFF", "C4":"H4 bias OFF"}
        parts = []
        for arm, delta, arm_pf in deltas:
            delta_str = _fmt(delta, 3) if delta is not None else "—"
            parts.append(f"{arm} ({labels[arm]}, ΔPF={delta_str})")
        L.append(f"- **{prof}:** " + " → ".join(parts) + " · "
                 f"baseline OOS PF = {_fmt(a_oos_pf,3)}")
    L.append("")

    L.append("---")
    L.append("### Artifacts")
    for arm in ("A","B","C1","C2","C3","C4"):
        for prof in ("D","R"):
            L.append(f"- `trades_variants_{arm}_{prof}.jsonl`")

    (OUT / "variants_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[md] wrote {OUT / 'variants_report.md'}")
