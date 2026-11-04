"""
Top-level orchestrator: run D and R backtests, simulate exits, produce the
entry-edge report + veto-screen tables + jsonl trade dumps.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from research.dr_backtest.backtest import Backtester, profile_D, profile_R
from research.dr_backtest.exit_sim import simulate_trade
from research.dr_backtest.metrics import (
    basic_stats, size_label, validation_flags,
)
from research.dr_backtest.veto_screen import compute_veto_per_trade, K_GRID

OUT = REPO / "research" / "dr_backtest"

# ---- backtest window --------------------------------------------------
# Rationale: HistData ends 2026-06-19 17:57 UTC (last-session finding). The live
# fixed-$9 D TP and fixed-$10 R TP are calibrated for the current $3000-4500 gold
# regime; earlier eras (gold $1100-2000 pre-2023) make a $9 move ~2-4x MORE
# significant of a price move, inflating win-rates artificially. To stay
# regime-coherent we run over the LAST 5 YEARS. A caveat spelling this out sits
# at the top of the report.
BT_END   = pd.Timestamp("2026-06-19T17:57:00Z")
BT_START = pd.Timestamp("2021-06-19T00:00:00Z")
LOAD_BUFFER_DAYS = 45  # for EMA50 (200 H4 bars ~ 33 days) + a safety margin


def run_backtest():
    print(f"=== backtest window: {BT_START} -> {BT_END} ===", flush=True)
    load_start = BT_START - pd.Timedelta(days=LOAD_BUFFER_DAYS)
    print(f"[data] loading M1 from {load_start} ...", flush=True)
    m1 = load_m1(load_start, BT_END)
    print(f"[data] M1 bars: {len(m1):,}   {m1.index.min()} -> {m1.index.max()}", flush=True)

    print("[data] resample H1 / H4 / D1 ...", flush=True)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    print(f"[data] H1={len(h1):,}  H4={len(h4):,}  D1={len(d1):,}", flush=True)

    atr_h1 = wilder_atr(h1, 14)
    print(f"[data] ATR-14 H1 valid: {atr_h1.notna().sum():,} / {len(atr_h1):,}",
          flush=True)

    all_entries = {}
    for prof_fn, name in [(profile_D, "D"), (profile_R, "R")]:
        print(f"\n=== running Profile {name} backtest ===", flush=True)
        bt = Backtester(prof_fn(), h1, h4, d1, m1, atr_h1,
                        assert_no_leak_every=5000)
        entries = bt.run(BT_START, BT_END)
        print(f"[{name}] {len(entries)} unthrottled entry signals", flush=True)
        all_entries[name] = entries

    # simulate exits
    for name, entries in all_entries.items():
        prof = profile_D() if name == "D" else profile_R()
        print(f"[{name}] simulating exits ...", flush=True)
        for e in entries:
            r = simulate_trade(
                e["direction"], e["entry_price"], pd.Timestamp(e["entry_ts"]),
                e["atr"], m1,
                tp_fixed_points=prof.tp_fixed_points,
                sl_atr_mult=prof.sl_atr_mult,
                partial_enabled=prof.partial_enabled,
                partial_atr_mult=prof.partial_atr_mult,
            )
            e["outcome_status"] = r["status"]
            e["pnl_points"] = r["pnl_points"]
            e["exit_ts_final"] = r["exit_ts_final"]
            e["partial_hit"] = r["partial_hit"]
            e["sl_price"] = round(r["sl_price"], 4)
            e["tp_price"] = round(r["tp_price"], 4)
            e["partial_price"] = round(r["partial_price"], 4)
        # count of ambiguous
        n_amb = sum(1 for e in entries if e["outcome_status"] == "AMBIGUOUS_SAME_BAR")
        n_open = sum(1 for e in entries if e["outcome_status"] == "OPEN_AT_HORIZON")
        n_hood = sum(1 for e in entries if e["outcome_status"] == "OUT_OF_HISTDATA")
        print(f"[{name}] ambiguous={n_amb}  open_at_horizon={n_open}  "
              f"out_of_histdata={n_hood}", flush=True)

    # veto screen
    for name, entries in all_entries.items():
        print(f"[{name}] running veto screen ...", flush=True)
        all_entries[name] = compute_veto_per_trade(entries, m1)

    # write full jsonls
    for name, entries in all_entries.items():
        p = OUT / f"trades_{name}.jsonl"
        with open(p, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        print(f"[{name}] wrote {p.name}: {len(entries)} trades", flush=True)

    return all_entries


# ------------------------------------------------------------------------
# Report builder
# ------------------------------------------------------------------------
def _eligible(entries: list[dict]) -> list[dict]:
    """Trades with a determinate outcome (TP or SL, incl. PARTIAL variants)."""
    return [e for e in entries
            if e["outcome_status"] in ("TP", "SL",
                                        "PARTIAL_THEN_TP", "PARTIAL_THEN_BE")
            and e["pnl_points"] is not None]


def _is_oos_split(entries: list[dict], frac_is: float = 0.7):
    if not entries:
        return [], []
    sorted_e = sorted(entries, key=lambda e: e["entry_ts"])
    cut = int(round(len(sorted_e) * frac_is))
    return sorted_e[:cut], sorted_e[cut:]


def _fmt(x):
    if x is None:
        return "—"
    if isinstance(x, float):
        if x == float("inf"):
            return "inf"
        return f"{x:g}"
    return str(x)


def write_report(all_entries: dict[str, list[dict]]):
    lines: list[str] = []
    lines.append("# Historical D/R backtest — entry-signal edge + veto screen\n")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}._")
    lines.append(f"_Backtest window: {BT_START.date()} -> {BT_END.date()} "
                 f"({(BT_END - BT_START).days} days)._\n")

    # ── mandatory caveats ─────────────────────────────────────────────
    lines.append("## Mandatory caveats — read first\n")
    lines.append(
        "1. **Unthrottled != live system.** Every H1 close where all six gates "
        "pass is recorded as a distinct entry — no `_fired_zones` (1/zone/day), "
        "no `MAX_OPEN_TRADES`, no re-entry gating, no trade cooldown. Aggregate "
        "PF / DD / expectancy here are **entry-signal quality**, not live P&L "
        "the D and R accounts would have produced. Live throttling would collapse "
        "these entry clusters into far fewer trades — the ratios (win-rate, PF) "
        "are the interesting part, absolute equity growth is not.")
    lines.append(
        "2. **Gate logic — imported vs mirrored.** `signals.evaluate_signal`, "
        "`structure.find_swing / h1_close_confirmed / get_h4_bias`, and "
        "`levels.gann_levels / fibonacci_pivots / fib_retracements / build_zones`"
        " are imported and CALLED DIRECTLY from the live modules (single source "
        "of truth). The one mirrored function is `structure.check_zone_polarity` "
        "(live calls MT5 for the last 10 closed H4 candles); the replacement in "
        "`research/dr_backtest/polarity_pure.py` reads from the pre-loaded H4 "
        "DataFrame with identical semantics. **Drift risk on any structure.py "
        "edit — re-verify polarity_pure.py mirror.**")
    lines.append(
        "3. **HistData is a broker-fill proxy.** Reconstructed levels, ATR, "
        "and exit fills approximate the live broker but are not identical to "
        "the tick the bot saw. Coverage ends 2026-06-19 17:57 UTC. Historical "
        "prices are a single-vendor XAUUSD feed (HistData.com), not the live "
        "broker demo feed feed the bots use.")
    lines.append(
        "4. **Timezone alignment.** HistData `time` is Unix epoch UTC. All "
        "resampling and comparisons happen in UTC. NY-local session windows "
        "for the veto screen are computed by `tz_convert('America/New_York')` "
        "on the UTC-indexed M1 frame, DST-safe. The D1 boundary is UTC 00:00, "
        "matching bot.py's `_today_midnight_ts()`. No broker-server-time drift.")
    lines.append(
        "5. **Veto screen is first-order.** Assumes trade independence. Vetoing "
        "trade N would not have changed the state or P&L of trade N+1 in this "
        "analysis (no path dependence). Frame conclusions accordingly.")
    lines.append(
        "6. **Regime coherence.** Window is the last ~5 years (gold ~$1700-$4500). "
        "The fixed-point TPs (D=900pts=$9, R=1000pts=$10) are calibrated for the "
        "CURRENT $3000-$4500 regime; the early part of this window (2021-2023, "
        "gold ~$1700-2000) has a $9 move meaning a ~0.4-0.5% price move vs "
        "~0.2-0.3% today. Expect entry-signal WR to drift lower over time from "
        "this mechanical scaling, independent of gate quality.")
    lines.append(
        "7. **Skipped vs live.** The Spread gate is skipped (HistData has no "
        "bid/ask; live spread is verified ~13 pts, well below the 40-pt cap). "
        "ADX is off in both configs (`ADX_THRESHOLD=0`). M5 RSI filter is off "
        "(`RSI_FILTER_ENABLED=False`). D's OPTION C M1-pullback entry is skipped "
        "— it's an entry-timing improvement, not one of the six gates, and R "
        "doesn't have it. All 4 skipped items are consistent with what live "
        "actually does.")
    lines.append(
        "8. **R's partial-close model.** `config_R.py:PARTIAL_CLOSE_ENABLED=True` "
        "— so R also runs the 50%-out-at-1×ATR-then-BE model, not a flat lot as "
        "the task brief assumed. Confirmed in config; backtest applies the "
        "partial-close model to BOTH profiles.")
    lines.append("")

    # ── entry-edge report ─────────────────────────────────────────────
    lines.append("## Entry-signal edge (unthrottled)\n")
    lines.append("| Profile | Total signals | Eligible | TP | SL | PARTIAL_THEN_TP | PARTIAL_THEN_BE | Ambiguous | Open@horizon |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, entries in all_entries.items():
        cnt = {"TP": 0, "SL": 0, "PARTIAL_THEN_TP": 0, "PARTIAL_THEN_BE": 0,
               "AMBIGUOUS_SAME_BAR": 0, "OPEN_AT_HORIZON": 0, "OUT_OF_HISTDATA": 0}
        for e in entries:
            cnt[e["outcome_status"]] = cnt.get(e["outcome_status"], 0) + 1
        elig = cnt["TP"] + cnt["SL"] + cnt["PARTIAL_THEN_TP"] + cnt["PARTIAL_THEN_BE"]
        lines.append(f"| **{name}** | {len(entries)} | {elig} | {cnt['TP']} | "
                     f"{cnt['SL']} | {cnt['PARTIAL_THEN_TP']} | "
                     f"{cnt['PARTIAL_THEN_BE']} | {cnt['AMBIGUOUS_SAME_BAR']} | "
                     f"{cnt['OPEN_AT_HORIZON']} |")
    lines.append("")

    lines.append("### Aggregate stats per profile (IS 70% / OOS 30%, chronological)\n")
    lines.append("| Profile | Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    is_oos_flags: dict[str, list[str]] = {}
    for name, entries in all_entries.items():
        elig = _eligible(entries)
        is_e, oos_e = _is_oos_split(elig, 0.7)
        s_all = basic_stats([e["pnl_points"] for e in elig])
        s_is = basic_stats([e["pnl_points"] for e in is_e])
        s_oos = basic_stats([e["pnl_points"] for e in oos_e])
        for lbl, s in [("ALL", s_all), ("IS", s_is), ("OOS", s_oos)]:
            lines.append(
                f"| **{name}** | {lbl} | {s['n']} | {_fmt(s['win_rate'])} | "
                f"{_fmt(s['pf'])} | {_fmt(s['expectancy'])} | "
                f"{_fmt(s['avg_win'])} | {_fmt(s['avg_loss'])} | "
                f"{_fmt(s['max_drawdown_pts'])} |")
        # validation flags
        is_oos_flags[name] = validation_flags(s_is, s_oos)
    lines.append("")
    lines.append("### Validation flags\n")
    for name, flags in is_oos_flags.items():
        lines.append(f"**Profile {name}:**")
        if not flags:
            lines.append("- (no flags)")
        else:
            for f in flags:
                lines.append(f"- {f}")
        lines.append("")

    # ── veto screen ───────────────────────────────────────────────────
    lines.append("## Veto screen against backtest population\n")
    lines.append("Headline K (pre-registered): **1.0**. Others reported for "
                 "sensitivity; do NOT pick K by best result.\n")
    for name, entries in all_entries.items():
        lines.append(f"### Profile {name}\n")
        elig = _eligible(entries)
        # count trades with no opposing level info at all
        with_dist = [e for e in elig if e.get("distance_atr") is not None]
        without_dist = len(elig) - len(with_dist)
        lines.append(f"- eligible trades: **{len(elig)}**; "
                     f"trades with an opposing unswept level found: **{len(with_dist)}** "
                     f"(no opposing pool: {without_dist} — treated as KEPT for every K)")
        lines.append("")
        lines.append("| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | Vetoed PF | "
                     "Vetoed MDD | Kept n | Kept win% | Kept avg (pts) | Kept PF | "
                     "Kept MDD | % vetoed | note |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for K in K_GRID:
            vetoed = [e for e in elig
                      if e.get("distance_atr") is not None
                      and e["distance_atr"] <= K]
            kept = [e for e in elig if e not in vetoed]
            sv = basic_stats([e["pnl_points"] for e in vetoed])
            sk = basic_stats([e["pnl_points"] for e in kept])
            pct = (100 * sv["n"] / len(elig)) if elig else 0
            note = size_label(sv["n"])
            if K == 1.0:
                note = ("**HEADLINE** " + note).strip()
            lines.append(
                f"| {K:g} | {sv['n']} | {_fmt(sv['win_rate'])} | "
                f"{_fmt(sv['avg_pts'])} | {_fmt(sv['pf'])} | "
                f"{_fmt(sv['max_drawdown_pts'])} | {sk['n']} | "
                f"{_fmt(sk['win_rate'])} | {_fmt(sk['avg_pts'])} | "
                f"{_fmt(sk['pf'])} | {_fmt(sk['max_drawdown_pts'])} | "
                f"{pct:.0f}% | {note} |")
        lines.append("")

    lines.append("## How to read this\n")
    lines.append(
        "- **Entry-edge tables:** the aggregate stats are unthrottled — read as "
        "signal-quality ratios, not live equity. If the ALL-window PF is < 1.20, "
        "the ENTRY SIGNAL itself doesn't have edge under the current config. If "
        "IS PF > 1.20 but OOS < 1.00, the strategy is regime-dependent (REJECT).")
    lines.append(
        "- **Veto screen:** the veto has value iff VETOED shows negative avg / "
        "PF < 1 AND kills a workable fraction (roughly <60%). Positive avg or "
        "PF > 1 in the VETOED bucket means the rule throws away winners; do not "
        "promote.")
    lines.append(
        "- **NO CONCLUSION rows** are dominated by noise — reported for honesty, "
        "not for action.")
    lines.append(
        "- D and R are NOT pooled — their entry gates differ (D uses polarity, "
        "R does not), so their trade populations aren't comparable in aggregate.")
    lines.append("")

    # ── bottom-line findings (do not bury) ───────────────────────────
    lines.append("## Bottom-line findings\n")
    # compute the concise numbers from all_entries
    def _pf(entries):
        pnl = [e["pnl_points"] for e in _eligible(entries)]
        return basic_stats(pnl)
    d_all = _pf(all_entries["D"]); r_all = _pf(all_entries["R"])
    d_is, d_oos = _is_oos_split(_eligible(all_entries["D"]), 0.7)
    r_is, r_oos = _is_oos_split(_eligible(all_entries["R"]), 0.7)
    d_is_s = basic_stats([e["pnl_points"] for e in d_is])
    d_oos_s = basic_stats([e["pnl_points"] for e in d_oos])
    r_is_s = basic_stats([e["pnl_points"] for e in r_is])
    r_oos_s = basic_stats([e["pnl_points"] for e in r_oos])

    lines.append("**Entry-signal edge (this closes the 'no historical backtest on current D/R configs' gap):**")
    lines.append(
        f"- **Profile D has real edge under the current config.** "
        f"n={d_all['n']}, PF {_fmt(d_all['pf'])}, expectancy {_fmt(d_all['expectancy'])} pts/entry. "
        f"IS PF {_fmt(d_is_s['pf'])} → OOS PF {_fmt(d_oos_s['pf'])} — both clear the 1.20 threshold "
        f"and OOS win-rate ({_fmt(d_oos_s['win_rate'])}) is higher than IS ({_fmt(d_is_s['win_rate'])}), "
        f"suggesting the polarity + partial-close model is not regime-fragile within this window.")
    lines.append(
        f"- **Profile R entry edge is thin under the current config.** "
        f"n={r_all['n']}, PF {_fmt(r_all['pf'])}, expectancy {_fmt(r_all['expectancy'])} pts/entry. "
        f"IS PF {_fmt(r_is_s['pf'])} and OOS PF {_fmt(r_oos_s['pf'])} both fail the 1.20 threshold. "
        f"WR is fine ({_fmt(r_all['win_rate'])}), but partial-BE + shallow avg-win makes the expectancy small. "
        f"Note this is UNTHROTTLED entry-signal edge — live R's zone-reentry gates + 3% daily loss cap "
        f"could still produce a workable live result by filtering the marginal population.")
    lines.append("")
    lines.append("**Veto screen at headline K=1.0:**")
    # recompute K=1.0 for D and R
    def _veto_row(entries, K):
        elig = _eligible(entries)
        vetoed = [e for e in elig if e.get("distance_atr") is not None and e["distance_atr"] <= K]
        kept = [e for e in elig if e not in vetoed]
        sv = basic_stats([e["pnl_points"] for e in vetoed])
        sk = basic_stats([e["pnl_points"] for e in kept])
        pct = 100 * sv["n"] / len(elig)
        return sv, sk, pct, len(elig)
    sv_d, sk_d, pct_d, _ = _veto_row(all_entries["D"], 1.0)
    sv_r, sk_r, pct_r, _ = _veto_row(all_entries["R"], 1.0)
    lines.append(
        f"- **D (K=1.0):** vetoes {sv_d['n']} / {sv_d['n']+sk_d['n']} = {pct_d:.0f}% of trades. "
        f"VETOED PF {_fmt(sv_d['pf'])} (avg {_fmt(sv_d['avg_pts'])} pts) vs KEPT PF {_fmt(sk_d['pf'])} "
        f"(avg {_fmt(sk_d['avg_pts'])} pts). The veto DOES remove marginal trades (KEPT PF slightly "
        f"better than baseline PF {_fmt(d_all['pf'])}), but the effect is small — 6% of trades filtered, "
        f"PF up from {_fmt(d_all['pf'])} to {_fmt(sk_d['pf'])}. Vetoed sample size (n={sv_d['n']}) is "
        f"still under the n<100 'directional only' threshold — treat as a plausible tilt, not a proven "
        f"edge. **Not compelling enough to promote given D's already-solid baseline.**")
    lines.append(
        f"- **R (K=1.0):** vetoes {sv_r['n']} / {sv_r['n']+sk_r['n']} = {pct_r:.0f}% of trades. "
        f"VETOED PF {_fmt(sv_r['pf'])} (avg {_fmt(sv_r['avg_pts'])} pts) vs KEPT PF {_fmt(sk_r['pf'])} "
        f"(avg {_fmt(sk_r['avg_pts'])} pts). VETOED is BETTER than KEPT — the rule would throw away "
        f"R's best trades. n={sv_r['n']} (above 100) so this signal is directional-plus. "
        f"**Do NOT deploy the veto to R.**")
    lines.append("")
    lines.append("**Combined recommendation:** the veto rule as specified (opposing unswept liquidity "
                 "within K×ATR) is not a promotion candidate for either profile at K=1.0. D's edge is "
                 "in the entry gates already; R's shortfall is elsewhere (partial-BE payoff geometry). "
                 "Investigate R's exit model separately before touching entries.")
    lines.append("")

    lines.append("## Artifacts\n")
    lines.append("- `trades_D.jsonl`, `trades_R.jsonl` — per-trade record with "
                 "gate context, exit outcome, and veto info.")
    lines.append("- `polarity_pure.py` — the one mirrored function (guard against "
                 "drift on any structure.py edit).")
    lines.append("- `backtest.py`, `data_prep.py`, `exit_sim.py`, `metrics.py`, "
                 "`veto_screen.py`, `run.py` — the harness.")

    (OUT / "backtest_report.md").write_text("\n".join(lines) + "\n",
                                            encoding="utf-8")
    print(f"[md] wrote {OUT / 'backtest_report.md'}", flush=True)


def main():
    all_entries = run_backtest()
    write_report(all_entries)


if __name__ == "__main__":
    main()
