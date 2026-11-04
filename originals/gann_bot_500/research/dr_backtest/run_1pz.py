"""
Post-hoc 1-trade-per-zone-per-day throttle applied to the existing D@900 and
R@1000 unthrottled trade populations.

WHY POST-HOC (not a re-run): every backtest trade already carries the exact
`zone_source` string the live bot uses as the throttle key (`bot.py:1684`
`zone_name = sig["zone_hit"]["source"]`, then `_zone_blocked(zone_name)` at
`bot.py:1713`). Grouping by (utc_date, zone_source) and keeping the earliest
entry reproduces the live 1-per-zone-per-day rule exactly. Each kept trade's
already-simulated exit remains valid because exits are per-entry-independent
in the current harness (no shared position state).

R's live re-entry allowance (`MAX_ZONE_TRADES_PER_DAY=2` with a profit
requirement) is NOT modeled here — this is a strict 1/zone/day for BOTH
profiles for controlled comparison. Undercounts R's live entries.

IS/OOS CALENDAR BOUNDARY: preserved from the unthrottled run so the buckets
compare apples-to-apples. The unthrottled split was 70% of the trade count
chronological; we pin the boundary DATE from that split and apply it to the
throttled trade set.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from research.dr_backtest.metrics import basic_stats, size_label, validation_flags

OUT = REPO / "research" / "dr_backtest"


# ─────────────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────────────
def load_trades(name: str) -> list[dict]:
    p = OUT / f"trades_{name}.jsonl"
    return [json.loads(l) for l in open(p)]


def save_trades(entries: list[dict], name: str) -> Path:
    p = OUT / f"trades_{name}.jsonl"
    with open(p, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return p


# ─────────────────────────────────────────────────────────────────────
# Throttle
# ─────────────────────────────────────────────────────────────────────
def one_per_zone_per_day(entries: list[dict]) -> list[dict]:
    """Group by (UTC-date-of-entry, zone_source); keep the earliest entry per
    (date, zone) tuple. UTC date because live bot.py uses `_today_midnight_ts()`
    (UTC 00:00) as the trading-day boundary."""
    by_key: dict[tuple[str, str], dict] = {}
    for e in entries:
        ts = pd.Timestamp(e["entry_ts"])
        # entry_ts is tz-aware UTC (bot.py convention + backtest convention)
        date_key = ts.tz_convert("UTC").date().isoformat()
        key = (date_key, e["zone_source"])
        prev = by_key.get(key)
        if prev is None or e["entry_ts"] < prev["entry_ts"]:
            by_key[key] = e
    kept = sorted(by_key.values(), key=lambda e: e["entry_ts"])
    return kept


# ─────────────────────────────────────────────────────────────────────
# IS/OOS with a pinned CALENDAR boundary
# ─────────────────────────────────────────────────────────────────────
def unthrottled_boundary_ts(entries_unthrottled: list[dict],
                            frac_is: float = 0.7) -> pd.Timestamp:
    """The entry_ts of the LAST trade in the unthrottled IS bucket.

    Reproduces the exact split used in the unthrottled report (backtest_report.md
    / run.py:_is_oos_split): sorted by entry_ts, cut = round(n * 0.7). We
    return the ts of the trade at index cut-1 (the last IS entry). Every
    trade with entry_ts <= that is IS; everything after is OOS.
    """
    sorted_u = sorted(entries_unthrottled, key=lambda e: e["entry_ts"])
    cut = int(round(len(sorted_u) * frac_is))
    if cut == 0:
        return pd.Timestamp(sorted_u[0]["entry_ts"])
    last_is = sorted_u[cut - 1]
    return pd.Timestamp(last_is["entry_ts"])


def split_by_boundary(entries: list[dict],
                      boundary_ts: pd.Timestamp) -> tuple[list, list]:
    """IS = entries with entry_ts <= boundary_ts; OOS = the rest."""
    sorted_e = sorted(entries, key=lambda e: e["entry_ts"])
    is_e, oos_e = [], []
    for e in sorted_e:
        if pd.Timestamp(e["entry_ts"]) <= boundary_ts:
            is_e.append(e)
        else:
            oos_e.append(e)
    return is_e, oos_e


# ─────────────────────────────────────────────────────────────────────
# Helpers for report
# ─────────────────────────────────────────────────────────────────────
def _eligible(entries: list[dict]) -> list[dict]:
    return [e for e in entries
            if e["outcome_status"] in ("TP", "SL",
                                        "PARTIAL_THEN_TP", "PARTIAL_THEN_BE")
            and e["pnl_points"] is not None]


def _fmt(x, prec=None):
    if x is None:
        return "—"
    if isinstance(x, float):
        if x == float("inf"):
            return "inf"
        return f"{x:.{prec}f}" if prec is not None else f"{x:g}"
    return str(x)


def _delta(a: dict, b: dict, key: str, prec: int = 3) -> str:
    av, bv = a.get(key), b.get(key)
    if av is None or bv is None:
        return "—"
    if isinstance(av, float) and av == float("inf"):
        return "—"
    if isinstance(bv, float) and bv == float("inf"):
        return "—"
    d = bv - av
    return f"{'+' if d >= 0 else ''}{d:.{prec}f}"


def _outcome_counts(entries: list[dict]) -> dict:
    c = {"TP": 0, "SL": 0, "PARTIAL_THEN_TP": 0, "PARTIAL_THEN_BE": 0,
         "AMBIGUOUS_SAME_BAR": 0, "OPEN_AT_HORIZON": 0, "OUT_OF_HISTDATA": 0}
    for e in entries:
        c[e["outcome_status"]] = c.get(e["outcome_status"], 0) + 1
    return c


# ─────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────
def write_report():
    prior_D = load_trades("D")
    prior_R = load_trades("R")

    kept_D = one_per_zone_per_day(prior_D)
    kept_R = one_per_zone_per_day(prior_R)

    save_trades(kept_D, "D_1pz")
    save_trades(kept_R, "R_1pz")

    boundary_D = unthrottled_boundary_ts(prior_D, 0.7)
    boundary_R = unthrottled_boundary_ts(prior_R, 0.7)

    # split unthrottled with SAME 70% count-cut (matches prior report)
    unth_D_is, unth_D_oos = split_by_boundary(prior_D, boundary_D)
    unth_R_is, unth_R_oos = split_by_boundary(prior_R, boundary_R)
    # split throttled with the SAME calendar boundary
    thr_D_is, thr_D_oos = split_by_boundary(kept_D, boundary_D)
    thr_R_is, thr_R_oos = split_by_boundary(kept_R, boundary_R)

    def _pnls(entries):
        return [e["pnl_points"] for e in _eligible(entries)]

    unth_D_all = basic_stats(_pnls(prior_D))
    unth_D_is_s = basic_stats(_pnls(unth_D_is))
    unth_D_oos_s = basic_stats(_pnls(unth_D_oos))
    thr_D_all = basic_stats(_pnls(kept_D))
    thr_D_is_s = basic_stats(_pnls(thr_D_is))
    thr_D_oos_s = basic_stats(_pnls(thr_D_oos))

    unth_R_all = basic_stats(_pnls(prior_R))
    unth_R_is_s = basic_stats(_pnls(unth_R_is))
    unth_R_oos_s = basic_stats(_pnls(unth_R_oos))
    thr_R_all = basic_stats(_pnls(kept_R))
    thr_R_is_s = basic_stats(_pnls(thr_R_is))
    thr_R_oos_s = basic_stats(_pnls(thr_R_oos))

    lines: list[str] = []
    lines.append("# D/R backtest — 1-trade-per-zone-per-day throttle vs unthrottled\n")
    lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}._")
    lines.append("_Baseline: current-config runs — D@900 (`trades_D.jsonl`), R@1000 (`trades_R.jsonl`)._")
    lines.append(f"_IS/OOS calendar boundary (D): entry_ts ≤ **{boundary_D.isoformat()}** = IS; after = OOS._")
    lines.append(f"_IS/OOS calendar boundary (R): entry_ts ≤ **{boundary_R.isoformat()}** = IS; after = OOS._")
    lines.append("")

    # ── caveats first ────────────────────────────────────────────────
    lines.append("## Mandatory caveats — read first\n")
    lines.append(
        "1. **Still not full live replay.** This models the 1-trade-per-zone-per-day "
        "rule only. Still absent: `MAX_OPEN_POSITIONS=1`, the 3% daily-loss cap, "
        "trade cooldown, and — for R — the `MAX_ZONE_TRADES_PER_DAY=2` re-entry "
        "allowance with the profit requirement (R can legitimately take a second "
        "trade on the same zone if the first exited in profit). Applying strict "
        "1/zone/day to BOTH profiles for controlled comparison undercounts R's "
        "live entry count.")
    lines.append(
        "2. **IS/OOS calendar boundary preserved.** The unthrottled 70/30 split "
        "produced a specific calendar date per profile; those exact dates are the "
        "boundary here. Re-splitting the smaller throttled set 70/30 by count "
        "would move the boundary and break comparability — not done.")
    lines.append(
        "3. **Same standing caveats as prior runs.** 5-year window is regime-"
        "specific (gold $1700 → $4500, does not represent full history). HistData "
        "is a broker-fill proxy. Clustered entries mean effective independent "
        "sample size is smaller than raw n — treat PF confidence as softer than "
        "n implies. These are reported metrics from a deterministic harness, not "
        "independently recomputed.")
    lines.append(
        "4. **Post-hoc dedup is valid because exits are per-entry-independent** "
        "in the harness (no shared position state across trades). Kept trades' "
        "exit outcomes are unchanged from the unthrottled run. The throttle key "
        "is `(utc_date, zone_source)` — matching live semantics at bot.py:1684 / "
        "1713 where `zone_name = sig['zone_hit']['source']`.")
    lines.append("")

    # ── dedup ratio ──────────────────────────────────────────────────
    lines.append("## Dedup ratio\n")
    lines.append("| Profile | Unthrottled entries | Kept (1/zone/day) | Removed | Kept fraction |")
    lines.append("|---|---:|---:|---:|---:|")
    lines.append(f"| **D** | {len(prior_D)} | {len(kept_D)} | "
                 f"{len(prior_D)-len(kept_D)} | {100*len(kept_D)/len(prior_D):.1f}% |")
    lines.append(f"| **R** | {len(prior_R)} | {len(kept_R)} | "
                 f"{len(prior_R)-len(kept_R)} | {100*len(kept_R)/len(prior_R):.1f}% |")
    lines.append("")

    # ── outcome mix per profile ──────────────────────────────────────
    lines.append("## Outcome counts (kept trades)\n")
    lines.append("| Outcome | D unthrottled | D 1/zone/day | Δ | R unthrottled | R 1/zone/day | Δ |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    d_uc, d_kc = _outcome_counts(prior_D), _outcome_counts(kept_D)
    r_uc, r_kc = _outcome_counts(prior_R), _outcome_counts(kept_R)
    for k in ("TP", "SL", "PARTIAL_THEN_TP", "PARTIAL_THEN_BE",
              "AMBIGUOUS_SAME_BAR", "OPEN_AT_HORIZON", "OUT_OF_HISTDATA"):
        du, dk = d_uc.get(k, 0), d_kc.get(k, 0)
        ru, rk = r_uc.get(k, 0), r_kc.get(k, 0)
        lines.append(f"| {k} | {du} | {dk} | {'+' if dk-du>=0 else ''}{dk-du} | "
                     f"{ru} | {rk} | {'+' if rk-ru>=0 else ''}{rk-ru} |")
    lines.append("")

    # ── side-by-side stats per profile ───────────────────────────────
    lines.append("## Profile D — unthrottled vs 1-per-zone-per-day (D@900)\n")
    lines.append("| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for lbl, u, t in [("ALL", unth_D_all, thr_D_all),
                      ("IS", unth_D_is_s, thr_D_is_s),
                      ("OOS", unth_D_oos_s, thr_D_oos_s)]:
        lines.append(f"| **{lbl}: unthrottled** | {u['n']} | {_fmt(u['win_rate'],3)} | "
                     f"{_fmt(u['pf'],3)} | {_fmt(u['expectancy'],1)} | "
                     f"{_fmt(u['avg_win'],1)} | {_fmt(u['avg_loss'],1)} | "
                     f"{_fmt(u['max_drawdown_pts'],1)} |")
        lines.append(f"| **{lbl}: 1/zone/day** | {t['n']} | {_fmt(t['win_rate'],3)} | "
                     f"{_fmt(t['pf'],3)} | {_fmt(t['expectancy'],1)} | "
                     f"{_fmt(t['avg_win'],1)} | {_fmt(t['avg_loss'],1)} | "
                     f"{_fmt(t['max_drawdown_pts'],1)} |")
        lines.append(f"| **{lbl}: Δ** | {_delta(u,t,'n',0)} | {_delta(u,t,'win_rate',3)} | "
                     f"{_delta(u,t,'pf',3)} | {_delta(u,t,'expectancy',1)} | "
                     f"{_delta(u,t,'avg_win',1)} | {_delta(u,t,'avg_loss',1)} | "
                     f"{_delta(u,t,'max_drawdown_pts',1)} |")
    lines.append("")
    lines.append("### D validation flags")
    d_u_flags = validation_flags(unth_D_is_s, unth_D_oos_s)
    d_t_flags = validation_flags(thr_D_is_s, thr_D_oos_s)
    lines.append(f"- **D unthrottled:** {'(no flags)' if not d_u_flags else '; '.join(d_u_flags)}")
    lines.append(f"- **D 1/zone/day:** {'(no flags)' if not d_t_flags else '; '.join(d_t_flags)}")
    lines.append("")

    lines.append("## Profile R — unthrottled vs 1-per-zone-per-day (R@1000)\n")
    lines.append("| Split | n | Win% | PF | Expectancy (pts) | Avg win | Avg loss | MDD (pts) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for lbl, u, t in [("ALL", unth_R_all, thr_R_all),
                      ("IS", unth_R_is_s, thr_R_is_s),
                      ("OOS", unth_R_oos_s, thr_R_oos_s)]:
        lines.append(f"| **{lbl}: unthrottled** | {u['n']} | {_fmt(u['win_rate'],3)} | "
                     f"{_fmt(u['pf'],3)} | {_fmt(u['expectancy'],1)} | "
                     f"{_fmt(u['avg_win'],1)} | {_fmt(u['avg_loss'],1)} | "
                     f"{_fmt(u['max_drawdown_pts'],1)} |")
        lines.append(f"| **{lbl}: 1/zone/day** | {t['n']} | {_fmt(t['win_rate'],3)} | "
                     f"{_fmt(t['pf'],3)} | {_fmt(t['expectancy'],1)} | "
                     f"{_fmt(t['avg_win'],1)} | {_fmt(t['avg_loss'],1)} | "
                     f"{_fmt(t['max_drawdown_pts'],1)} |")
        lines.append(f"| **{lbl}: Δ** | {_delta(u,t,'n',0)} | {_delta(u,t,'win_rate',3)} | "
                     f"{_delta(u,t,'pf',3)} | {_delta(u,t,'expectancy',1)} | "
                     f"{_delta(u,t,'avg_win',1)} | {_delta(u,t,'avg_loss',1)} | "
                     f"{_delta(u,t,'max_drawdown_pts',1)} |")
    lines.append("")
    lines.append("### R validation flags")
    r_u_flags = validation_flags(unth_R_is_s, unth_R_oos_s)
    r_t_flags = validation_flags(thr_R_is_s, thr_R_oos_s)
    lines.append(f"- **R unthrottled:** {'(no flags)' if not r_u_flags else '; '.join(r_u_flags)}")
    lines.append(f"- **R 1/zone/day:** {'(no flags)' if not r_t_flags else '; '.join(r_t_flags)}")
    lines.append("")

    # ── sample-size labels per bucket ────────────────────────────────
    lines.append("## Sample-size honesty\n")
    lines.append("| Profile | Split (throttled) | n | Size label |")
    lines.append("|---|---|---:|---|")
    for name, splits in [
        ("D", [("ALL", thr_D_all), ("IS", thr_D_is_s), ("OOS", thr_D_oos_s)]),
        ("R", [("ALL", thr_R_all), ("IS", thr_R_is_s), ("OOS", thr_R_oos_s)]),
    ]:
        for lbl, s in splits:
            lab = size_label(s["n"]) or "OK (n≥100)"
            lines.append(f"| {name} | {lbl} | {s['n']} | {lab} |")
    lines.append("")

    # ── explicit read ────────────────────────────────────────────────
    lines.append("## Explicit read — did the throttle help or hurt?\n")
    def _judge(name, u, t):
        pf_u, pf_t = u.get("pf"), t.get("pf")
        if pf_u is None or pf_t is None:
            return f"- **{name}:** insufficient data to judge (PF undefined)."
        if isinstance(pf_u, float) and (pf_u == float("inf") or pf_t == float("inf")):
            return f"- **{name}:** PF is infinite in one bucket — not meaningfully comparable."
        d = pf_t - pf_u
        pct = (d / pf_u * 100) if pf_u else 0.0
        direction = "ROSE" if d > 0 else ("FELL" if d < 0 else "was flat")
        implication = (
            "the removed intra-zone repeat entries were **net HELPING** — "
            "1/zone/day discards winners, so this throttle HURTS on the raw signal"
            if d < 0 else
            ("the removed intra-zone repeat entries were **net HURTING** — "
             "1/zone/day discards losers, so this throttle HELPS on the raw signal"
             if d > 0 else "the removed intra-zone entries were P&L-neutral")
        )
        return (f"- **{name}:** PF {direction} from {pf_u:.3f} → {pf_t:.3f} "
                f"(Δ {'+' if d>=0 else ''}{d:.3f}, {'+' if pct>=0 else ''}{pct:.1f}%). "
                f"So {implication}.")
    lines.append(_judge("D ALL", unth_D_all, thr_D_all))
    lines.append(_judge("D IS",  unth_D_is_s, thr_D_is_s))
    lines.append(_judge("D OOS", unth_D_oos_s, thr_D_oos_s))
    lines.append(_judge("R ALL", unth_R_all, thr_R_all))
    lines.append(_judge("R IS",  unth_R_is_s, thr_R_is_s))
    lines.append(_judge("R OOS", unth_R_oos_s, thr_R_oos_s))
    lines.append("")
    lines.append(
        "**Note on interpretation.** A PF drop means the FIRST intra-day trade per "
        "zone tends to have worse outcome than the AVERAGE across all fires on "
        "that zone that day. A rise means the first is better. In either case the "
        "effect is on the *unthrottled* metric — live D throttled to 1/zone/day is "
        "closer to the throttled row above; live R (2/zone/day with profit "
        "requirement) sits between the two but is not directly modeled here.")
    lines.append("")

    # ── artifacts ────────────────────────────────────────────────────
    lines.append("## Artifacts\n")
    lines.append("- `trades_D_1pz.jsonl` — D kept trades after 1/zone/day dedup.")
    lines.append("- `trades_R_1pz.jsonl` — R kept trades after 1/zone/day dedup.")
    lines.append("- `run_1pz.py` — the post-hoc dedup script (no engine changes; "
                 "reads `trades_{D,R}.jsonl`, writes the `_1pz` variants).")

    (OUT / "backtest_1perzone_report.md").write_text("\n".join(lines) + "\n",
                                                     encoding="utf-8")
    print(f"[md] wrote {OUT / 'backtest_1perzone_report.md'}")
    print(f"[jsonl] wrote trades_D_1pz.jsonl ({len(kept_D)} kept from {len(prior_D)})")
    print(f"[jsonl] wrote trades_R_1pz.jsonl ({len(kept_R)} kept from {len(prior_R)})")


if __name__ == "__main__":
    write_report()
