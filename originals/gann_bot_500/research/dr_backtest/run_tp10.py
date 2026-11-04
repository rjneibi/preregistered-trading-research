"""
Rerun backtest with TP_FIXED_POINTS = 1000 for BOTH D and R (a $10 price move).

Reuses the existing harness unchanged — same Backtester, same exit_sim, same
IS/OOS split, same 2021-06-19 -> 2026-06-19 window, same look-ahead guards,
same partial-close model. The ONLY override is the TP.

Sanity gate: R's live config already has TP_FIXED_POINTS=1000, so R MUST match
the prior run trade-for-trade. If it doesn't, that's a bug — stop and
investigate. D changes from prior 900 to 1000.
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
from research.dr_backtest.metrics import basic_stats, size_label, validation_flags
from research.dr_backtest.veto_screen import compute_veto_per_trade

OUT = REPO / "research" / "dr_backtest"
BT_END   = pd.Timestamp("2026-06-19T17:57:00Z")
BT_START = pd.Timestamp("2021-06-19T00:00:00Z")
LOAD_BUFFER_DAYS = 45
TP_OVERRIDE = 1000.0  # $10 in gold points (100pts/$1)


def _override_tp(prof, tp: float):
    """Return a new ProfileConf identical except TP_FIXED_POINTS = tp."""
    from dataclasses import replace
    return replace(prof, tp_fixed_points=tp)


def run():
    print(f"=== TP-override backtest: TP_FIXED_POINTS = {TP_OVERRIDE} for BOTH D and R ===",
          flush=True)
    print(f"=== window: {BT_START} -> {BT_END} ===", flush=True)

    print(f"[data] loading M1 ...", flush=True)
    m1 = load_m1(BT_START - pd.Timedelta(days=LOAD_BUFFER_DAYS), BT_END)
    print(f"[data] M1 bars: {len(m1):,}", flush=True)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    print(f"[data] H1={len(h1):,}  H4={len(h4):,}  D1={len(d1):,}", flush=True)

    profs = {"D": _override_tp(profile_D(), TP_OVERRIDE),
             "R": _override_tp(profile_R(), TP_OVERRIDE)}
    for name in profs:
        assert profs[name].tp_fixed_points == TP_OVERRIDE, "TP override failed"

    all_entries: dict[str, list[dict]] = {}
    for name, prof in profs.items():
        print(f"\n=== running Profile {name} @ TP={TP_OVERRIDE} ===", flush=True)
        bt = Backtester(prof, h1, h4, d1, m1, atr_h1, assert_no_leak_every=5000)
        entries = bt.run(BT_START, BT_END)
        print(f"[{name}] {len(entries)} unthrottled entry signals", flush=True)
        all_entries[name] = entries

    # simulate exits with the OVERRIDDEN TP
    for name, entries in all_entries.items():
        prof = profs[name]
        print(f"[{name}] simulating exits (TP={prof.tp_fixed_points}) ...", flush=True)
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
        cnt = {"AMBIGUOUS_SAME_BAR":0,"OPEN_AT_HORIZON":0,"OUT_OF_HISTDATA":0}
        for e in entries:
            if e["outcome_status"] in cnt: cnt[e["outcome_status"]] += 1
        print(f"[{name}] ambiguous={cnt['AMBIGUOUS_SAME_BAR']} "
              f"open_horizon={cnt['OPEN_AT_HORIZON']} "
              f"out_of_histdata={cnt['OUT_OF_HISTDATA']}", flush=True)

    # write jsonls
    for name, entries in all_entries.items():
        p = OUT / f"trades_{name}_tp10.jsonl"
        with open(p, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        print(f"[{name}] wrote {p.name}: {len(entries)} trades", flush=True)

    return all_entries


# ─────────────────────────────────────────────────────────────────────
# Sanity gate: R@1000 (this run) must match R@1000 (prior run)
# ─────────────────────────────────────────────────────────────────────
def sanity_check_R(new_entries: list[dict]) -> tuple[bool, str]:
    prior_path = OUT / "trades_R.jsonl"
    if not prior_path.exists():
        return False, "prior trades_R.jsonl not found"
    prior = [json.loads(l) for l in open(prior_path)]
    if len(prior) != len(new_entries):
        return False, (f"row count differs: prior={len(prior)} new={len(new_entries)}")

    # Sort both by entry_ts for stable comparison
    prior_s = sorted(prior, key=lambda e: e["entry_ts"])
    new_s   = sorted(new_entries, key=lambda e: e["entry_ts"])
    mismatches = []
    for p, n in zip(prior_s, new_s):
        for k in ("entry_ts","direction","entry_price","zone_source","zone_level"):
            if p.get(k) != n.get(k):
                mismatches.append((p.get("entry_ts"), k, p.get(k), n.get(k)))
                break
        # exit outcome + pnl (both should match given identical TP/SL)
        for k in ("outcome_status","pnl_points","sl_price","tp_price"):
            if p.get(k) != n.get(k):
                mismatches.append((p.get("entry_ts"), k, p.get(k), n.get(k)))
                break
    if mismatches:
        head = "; ".join(f"{ts}:{k}(prior={a} new={b})" for ts,k,a,b in mismatches[:5])
        return False, f"{len(mismatches)} mismatch(es). First: {head}"
    return True, f"identical trade-for-trade across n={len(prior)}"


# ─────────────────────────────────────────────────────────────────────
# Report builder
# ─────────────────────────────────────────────────────────────────────
def _eligible(entries):
    return [e for e in entries
            if e["outcome_status"] in ("TP","SL","PARTIAL_THEN_TP","PARTIAL_THEN_BE")
            and e["pnl_points"] is not None]

def _is_oos_split(entries, frac_is=0.7):
    if not entries: return [], []
    s = sorted(entries, key=lambda e: e["entry_ts"])
    cut = int(round(len(s)*frac_is))
    return s[:cut], s[cut:]

def _outcome_counts(entries):
    c = {"TP":0,"SL":0,"PARTIAL_THEN_TP":0,"PARTIAL_THEN_BE":0,
         "AMBIGUOUS_SAME_BAR":0,"OPEN_AT_HORIZON":0,"OUT_OF_HISTDATA":0}
    for e in entries:
        c[e["outcome_status"]] = c.get(e["outcome_status"], 0) + 1
    return c

def _fmt(x, prec=None):
    if x is None: return "—"
    if isinstance(x, float):
        if x == float("inf"): return "inf"
        return f"{x:.{prec}f}" if prec is not None else f"{x:g}"
    return str(x)

def _delta(a, b, prec=3):
    if a is None or b is None or a == "inf" or b == "inf": return "—"
    d = b - a
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.{prec}f}"


def write_report(new_D: list[dict], new_R: list[dict], r_ok: bool, r_msg: str):
    prior_D = [json.loads(l) for l in open(OUT / "trades_D.jsonl")]
    prior_R = [json.loads(l) for l in open(OUT / "trades_R.jsonl")]

    lines: list[str] = []
    lines.append("# D/R backtest — TP override to $10 (1000 pts) for BOTH profiles\n")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}._")
    lines.append(f"_Window: {BT_START.date()} -> {BT_END.date()} (5y, same as prior)._\n")

    # ── caveats ────────────────────────────────────────────────────
    lines.append("## Mandatory caveats — read first\n")
    lines.append(
        "1. **Unthrottled != live P&L.** Every H1 close where all six gates pass "
        "is a distinct entry — no `_fired_zones` (1/zone/day for D, 2/zone/day for R), "
        "no `MAX_OPEN_TRADES`, no zone-reentry gates, no trade cooldown, no 3% daily-loss "
        "cap. Aggregate PF / expectancy / MDD read as entry-signal quality, not the equity "
        "curves D or R accounts would produce.")
    lines.append(
        "2. **5-year window is regime-specific.** 2021-06 → 2026-06 covers gold ~$1700→$4500. "
        "Not the full 16-year HistData history — pre-2021 gold ($1100-1700) makes a "
        "$10 TP a 2-3× more meaningful move, which would inflate WR. Do not read this "
        "as a full-history edge measurement.")
    lines.append(
        "3. **HistData is a broker-fill proxy.** Reconstructed exits approximate the live "
        "broker but are not identical to the tick the bot saw.")
    lines.append(
        "4. **Positively-correlated clustered entries → effective sample < raw n.** "
        "Unthrottled entries cluster tightly around a single H4 setup (bias + zone + "
        "confirmation persist across multiple H1 closes), so many of these 1000-plus "
        "'independent' trades are actually the same underlying decision fired again "
        "and again. Treat PF confidence intervals as WIDER than a n>1000 IID sample "
        "would suggest. This is a first-order screen.")
    lines.append(
        "5. **Only TP is overridden.** D SL stays 1.0×ATR, R SL stays 1.5×ATR. Polarity "
        "flip stays ON for D / OFF for R. Partial-close @ 1.0×ATR stays ON for both. "
        "ADX=0, RSI off, spread gate skipped — exactly as in the prior report.")
    lines.append("")

    # ── R sanity gate ─────────────────────────────────────────────
    lines.append("## R sanity gate (must-pass)\n")
    lines.append(
        f"R's live config already uses TP_FIXED_POINTS=1000, so this run MUST reproduce "
        f"the prior R backtest trade-for-trade. Result: **{'PASS' if r_ok else 'FAIL'}** — "
        f"{r_msg}.")
    if not r_ok:
        lines.append("")
        lines.append("**Stopping report here — investigate the mismatch before comparing D.**")
        (OUT / "backtest_tp10_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("")

    # ── D outcome counts + stats side-by-side ──────────────────────
    d900_cnt = _outcome_counts(prior_D);   d1000_cnt = _outcome_counts(new_D)
    d900_elig = _eligible(prior_D);         d1000_elig = _eligible(new_D)
    d900_all = basic_stats([e["pnl_points"] for e in d900_elig])
    d1000_all = basic_stats([e["pnl_points"] for e in d1000_elig])
    d900_is, d900_oos = _is_oos_split(d900_elig, 0.7)
    d1000_is, d1000_oos = _is_oos_split(d1000_elig, 0.7)
    d900_is_s = basic_stats([e["pnl_points"] for e in d900_is])
    d900_oos_s = basic_stats([e["pnl_points"] for e in d900_oos])
    d1000_is_s = basic_stats([e["pnl_points"] for e in d1000_is])
    d1000_oos_s = basic_stats([e["pnl_points"] for e in d1000_oos])

    lines.append("## D @ 900 pts (prior) vs D @ 1000 pts (this run) — outcome counts\n")
    lines.append("| Outcome | D@900 | D@1000 | Δ |")
    lines.append("|---|---:|---:|---:|")
    for k in ("TP","SL","PARTIAL_THEN_TP","PARTIAL_THEN_BE",
              "AMBIGUOUS_SAME_BAR","OPEN_AT_HORIZON","OUT_OF_HISTDATA"):
        d = d1000_cnt.get(k,0) - d900_cnt.get(k,0)
        sign = "+" if d>=0 else ""
        lines.append(f"| {k} | {d900_cnt.get(k,0)} | {d1000_cnt.get(k,0)} | {sign}{d} |")
    lines.append(f"| **Total** | **{sum(d900_cnt.values())}** | "
                 f"**{sum(d1000_cnt.values())}** | "
                 f"{_delta(sum(d900_cnt.values()), sum(d1000_cnt.values()), 0)} |")
    lines.append("")

    lines.append("## D @ 900 vs D @ 1000 — aggregate stats\n")
    lines.append("| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for lbl, (a, b) in [("ALL", (d900_all, d1000_all)),
                        ("IS 70%", (d900_is_s, d1000_is_s)),
                        ("OOS 30%", (d900_oos_s, d1000_oos_s))]:
        lines.append(f"| **{lbl}: D@900** | {a['n']} | {_fmt(a['win_rate'],3)} | "
                     f"{_fmt(a['pf'],3)} | {_fmt(a['expectancy'],1)} | "
                     f"{_fmt(a['avg_win'],1)} | {_fmt(a['avg_loss'],1)} | "
                     f"{_fmt(a['max_drawdown_pts'],1)} |")
        lines.append(f"| **{lbl}: D@1000** | {b['n']} | {_fmt(b['win_rate'],3)} | "
                     f"{_fmt(b['pf'],3)} | {_fmt(b['expectancy'],1)} | "
                     f"{_fmt(b['avg_win'],1)} | {_fmt(b['avg_loss'],1)} | "
                     f"{_fmt(b['max_drawdown_pts'],1)} |")
        # deltas
        def sub(a, b, k, prec=3):
            av, bv = a.get(k), b.get(k)
            if av is None or bv is None: return "—"
            if isinstance(av, float) and av == float("inf"): return "—"
            if isinstance(bv, float) and bv == float("inf"): return "—"
            d = bv - av
            return f"{'+' if d>=0 else ''}{d:.{prec}f}"
        lines.append(f"| **{lbl}: Δ** | {sub(a,b,'n',0)} | {sub(a,b,'win_rate',3)} | "
                     f"{sub(a,b,'pf',3)} | {sub(a,b,'expectancy',1)} | "
                     f"{sub(a,b,'avg_win',1)} | {sub(a,b,'avg_loss',1)} | "
                     f"{sub(a,b,'max_drawdown_pts',1)} |")
    lines.append("")

    lines.append("### D validation flags\n")
    d900_flags = validation_flags(d900_is_s, d900_oos_s)
    d1000_flags = validation_flags(d1000_is_s, d1000_oos_s)
    lines.append(f"- **D@900:** {'(no flags)' if not d900_flags else '; '.join(d900_flags)}")
    lines.append(f"- **D@1000:** {'(no flags)' if not d1000_flags else '; '.join(d1000_flags)}")
    lines.append("")

    # ── R stats (unchanged from prior) ────────────────────────────
    r_elig = _eligible(new_R)
    r_all = basic_stats([e["pnl_points"] for e in r_elig])
    r_is, r_oos = _is_oos_split(r_elig, 0.7)
    r_is_s = basic_stats([e["pnl_points"] for e in r_is])
    r_oos_s = basic_stats([e["pnl_points"] for e in r_oos])
    r_flags = validation_flags(r_is_s, r_oos_s)
    lines.append("## R @ 1000 pts (unchanged from live config; must match prior)\n")
    lines.append("| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for lbl, s in [("ALL", r_all), ("IS 70%", r_is_s), ("OOS 30%", r_oos_s)]:
        lines.append(f"| **R@1000: {lbl}** | {s['n']} | {_fmt(s['win_rate'],3)} | "
                     f"{_fmt(s['pf'],3)} | {_fmt(s['expectancy'],1)} | "
                     f"{_fmt(s['avg_win'],1)} | {_fmt(s['avg_loss'],1)} | "
                     f"{_fmt(s['max_drawdown_pts'],1)} |")
    lines.append(f"\nValidation flags: {'(no flags)' if not r_flags else '; '.join(r_flags)}")
    lines.append("")

    # ── Profits & losses overview ─────────────────────────────────
    lines.append("## Profits & losses overview\n")
    lines.append("Point-P&L across all eligible trades in each bucket. Positive = winner.\n")
    lines.append("| Bucket | n | Total pts | Sum wins | Sum losses | Best trade | Worst trade | Median | Std |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    def pnl_row(label, entries):
        pnl = [e["pnl_points"] for e in entries]
        if not pnl:
            return f"| {label} | 0 | — | — | — | — | — | — | — |"
        import statistics
        wins = [x for x in pnl if x > 0]
        losses = [x for x in pnl if x < 0]
        med = statistics.median(pnl)
        std = statistics.pstdev(pnl) if len(pnl) > 1 else 0.0
        return (f"| {label} | {len(pnl)} | {sum(pnl):+.1f} | {sum(wins):+.1f} | "
                f"{sum(losses):+.1f} | {max(pnl):+.1f} | {min(pnl):+.1f} | "
                f"{med:+.1f} | {std:.1f} |")
    lines.append(pnl_row("D@900",  d900_elig))
    lines.append(pnl_row("D@1000", d1000_elig))
    lines.append(pnl_row("R@1000", r_elig))
    lines.append("")

    # outcome-status distribution overview (win/loss buckets)
    lines.append("### Outcome mix (share of eligible trades)\n")
    lines.append("| Bucket | TP full | SL full | Partial→TP | Partial→BE | Winners share |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    def mix_row(label, cnts, elig):
        n = len(elig)
        tp, sl = cnts.get("TP",0), cnts.get("SL",0)
        ptp, pbe = cnts.get("PARTIAL_THEN_TP",0), cnts.get("PARTIAL_THEN_BE",0)
        winners = sum(1 for e in elig if e["pnl_points"] > 0)
        pct = f"{100*winners/n:.1f}%" if n else "—"
        return f"| {label} | {tp} ({100*tp/n:.0f}%) | {sl} ({100*sl/n:.0f}%) | {ptp} ({100*ptp/n:.0f}%) | {pbe} ({100*pbe/n:.0f}%) | {pct} |"
    r_cnt = _outcome_counts(new_R)
    lines.append(mix_row("D@900",  d900_cnt,  d900_elig))
    lines.append(mix_row("D@1000", d1000_cnt, d1000_elig))
    lines.append(mix_row("R@1000", r_cnt,     r_elig))
    lines.append("")

    # ── Read-out ───────────────────────────────────────────────────
    lines.append("## How to read this\n")
    lines.append(
        "- The TP change moves the take-profit further from entry (900 → 1000 pts = "
        "10% wider TP). Expected qualitative effects on D: (a) some full-TP hits "
        "convert to PARTIAL_THEN_BE (the leg doesn't reach further TP after partial); "
        "(b) some full-TP hits become full SL (the extra distance gives more time to "
        "reverse); (c) trades that DO hit the wider TP capture 100 pts more per full-lot "
        "TP hit, +50 pts per partial→TP. Net direction depends on which channel dominates.")
    lines.append(
        "- **Δ PF and Δ expectancy** in the D table above are the only stats to trust "
        "here — win% shifts driven by TP-hit reclassification are structural, not edge.")
    lines.append(
        "- **R must show zero deltas vs the prior run.** If it does, the harness is "
        "consistent; if not, that's a bug and the whole comparison is suspect.")
    lines.append("")

    # ── Artifacts ──────────────────────────────────────────────────
    lines.append("## Artifacts\n")
    lines.append("- `trades_D_tp10.jsonl` / `trades_R_tp10.jsonl` — per-trade records at TP=1000.")
    lines.append("- `trades_D.jsonl` / `trades_R.jsonl` — prior-run (D@900) for the D comparison.")
    lines.append("- Harness unchanged: `backtest.py`, `data_prep.py`, `exit_sim.py`, "
                 "`metrics.py`, `polarity_pure.py`.")

    (OUT / "backtest_tp10_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[md] wrote {OUT / 'backtest_tp10_report.md'}", flush=True)


def main():
    all_entries = run()
    ok, msg = sanity_check_R(all_entries["R"])
    print(f"\n=== R sanity check: {'PASS' if ok else 'FAIL'} — {msg} ===", flush=True)
    write_report(all_entries["D"], all_entries["R"], ok, msg)


if __name__ == "__main__":
    main()
