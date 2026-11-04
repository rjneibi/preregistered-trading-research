"""
Retrospective veto measurement for Profile D and Profile R.

For every real entry in runtime/daily_log_D.csv and profiles/R/daily_log_R.csv:
  * build a MarketContext at the entry timestamp from HistData M1 completed bars
  * apply the veto for K ∈ {0.5, 1.0, 1.5, 2.0}
  * simulate the trade's exit outcome by scanning HistData M1 forward from the
    entry bar until the SL or TP price is touched (from the log's own sl/tp)
  * partition the trades into VETOED vs KEPT per K and per profile
  * write veto_analysis.md and one .jsonl per (profile, K)

Design notes:
  - Log timestamps are UTC (see bot.py: `datetime.now(timezone.utc).strftime`).
  - HistData `time` is Unix epoch (UTC). Direct equality → no timezone drift.
  - HistData ends 2026-06-19 17:57 UTC. Any trade whose entry ts (or SL/TP
    resolution) falls outside coverage is labelled OUT_OF_HISTDATA and left
    out of the sensitivity tables (still emitted to jsonl for auditing).
  - Points convention for XAUUSD: 1 dollar = 100 points, so a $10 move = 1000
    points. This matches the fixed-TP values in CODEBASE_TRUTH.md (D: 900pts =
    $9; R: 1000pts = $10). P&L is reported in points to avoid lot-value noise.
  - Rows in daily_log_D.csv with entry_type == "MISSED_TIMEOUT" (blank ticket)
    are NOT real trades and are excluded.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "research"))
from market_context.context import MarketContext, veto  # noqa: E402

HISTDATA_PATH = REPO / "research" / "data" / "xauusd_m1_histdata.csv"
D_LOG = REPO / "runtime" / "daily_log_D.csv"
R_LOG = REPO / "profiles" / "R" / "daily_log_R.csv"
OUT_DIR = REPO / "research" / "market_context"

K_GRID = [0.5, 1.0, 1.5, 2.0]
HEADLINE_K = 1.0
POINT_PER_DOLLAR = 100   # XAUUSD


# ─── loaders ─────────────────────────────────────────────────────────────
def load_m1(start_utc: pd.Timestamp, end_utc: pd.Timestamp) -> pd.DataFrame:
    """Read the M1 CSV, keep only rows within [start_utc, end_utc], return UTC-
    tz-aware DatetimeIndex sorted ascending."""
    print(f"[load_m1] reading {HISTDATA_PATH.name}, window "
          f"{start_utc.isoformat()} -> {end_utc.isoformat()}")
    df = pd.read_csv(HISTDATA_PATH)
    df["ts"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("ts").sort_index()
    df = df[(df.index >= start_utc) & (df.index <= end_utc)]
    df = df[["open", "high", "low", "close"]]
    print(f"[load_m1] {len(df):,} bars in window; "
          f"actual coverage {df.index.min()} -> {df.index.max()}")
    return df


def _parse_utc(s: str) -> pd.Timestamp:
    """Log timestamps are naive ISO strings written by datetime.now(timezone.utc)
    .strftime('%Y-%m-%dT%H:%M:%S') — so they are naive-but-representing-UTC."""
    return pd.Timestamp(s).tz_localize("UTC")


def _parse_float(s: str) -> Optional[float]:
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_trades(path: Path, profile: str) -> List[Dict[str, Any]]:
    trades: List[Dict[str, Any]] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry_type = (row.get("entry_type") or "").strip()
            ticket = (row.get("ticket") or "").strip()
            # real trades only — MISSED_TIMEOUT rows have blank ticket
            if entry_type == "MISSED_TIMEOUT" or ticket == "":
                continue
            try:
                ts = _parse_utc(row["timestamp"])
            except Exception:
                continue
            entry_price = _parse_float(row["entry_price"])
            sl_price = _parse_float(row["sl_price"])
            tp_price = _parse_float(row["tp_price"])
            atr = _parse_float(row["atr"])
            direction = (row["direction"] or "").upper().strip()
            if None in (entry_price, sl_price, tp_price, atr) or direction not in ("BUY", "SELL"):
                continue
            trades.append({
                "profile": profile,
                "ticket": ticket,
                "timestamp_utc": ts.isoformat(),
                "timestamp": ts,
                "direction": direction,
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "atr": atr,
                "lots": _parse_float(row.get("lots")) or 0.0,
                "zone_name": row.get("zone_name") or "",
                "entry_type": entry_type or "IMMEDIATE",
            })
    return trades


# ─── outcome simulation ──────────────────────────────────────────────────
def simulate_outcome(trade: Dict[str, Any], m1: pd.DataFrame,
                     max_hours: int = 72) -> Dict[str, Any]:
    """Walk M1 bars forward from the first bar after entry, find first bar to
    touch SL or TP. Return exit info or a status label.

    Returns dict with keys:
      status: 'TP' | 'SL' | 'AMBIGUOUS_SAME_BAR' | 'OPEN_AT_HORIZON' | 'OUT_OF_HISTDATA'
      exit_price, exit_ts, pnl_points, hours_to_exit
    """
    entry_ts = trade["timestamp"]
    entry = trade["entry_price"]
    sl = trade["sl_price"]
    tp = trade["tp_price"]
    is_buy = trade["direction"] == "BUY"
    # walk from the NEXT M1 bar after entry
    fwd = m1[m1.index > entry_ts]
    if fwd.empty or entry_ts > m1.index.max():
        return {"status": "OUT_OF_HISTDATA", "exit_price": None,
                "exit_ts": None, "pnl_points": None, "hours_to_exit": None}
    horizon_end = entry_ts + pd.Timedelta(hours=max_hours)
    fwd = fwd[fwd.index <= horizon_end]
    for ts, row in fwd.iterrows():
        hi, lo = float(row["high"]), float(row["low"])
        hit_tp = (hi >= tp) if is_buy else (lo <= tp)
        hit_sl = (lo <= sl) if is_buy else (hi >= sl)
        if hit_tp and hit_sl:
            # both prices inside same M1 bar — outcome is ambiguous
            hours = (ts - entry_ts).total_seconds() / 3600
            return {"status": "AMBIGUOUS_SAME_BAR", "exit_price": None,
                    "exit_ts": ts.isoformat(), "pnl_points": None,
                    "hours_to_exit": hours}
        if hit_tp:
            hours = (ts - entry_ts).total_seconds() / 3600
            pts = (tp - entry) * POINT_PER_DOLLAR * (1 if is_buy else -1)
            return {"status": "TP", "exit_price": tp, "exit_ts": ts.isoformat(),
                    "pnl_points": round(pts, 1), "hours_to_exit": round(hours, 2)}
        if hit_sl:
            hours = (ts - entry_ts).total_seconds() / 3600
            pts = (sl - entry) * POINT_PER_DOLLAR * (1 if is_buy else -1)
            return {"status": "SL", "exit_price": sl, "exit_ts": ts.isoformat(),
                    "pnl_points": round(pts, 1), "hours_to_exit": round(hours, 2)}
    return {"status": "OPEN_AT_HORIZON", "exit_price": None,
            "exit_ts": None, "pnl_points": None, "hours_to_exit": None}


# ─── stats ───────────────────────────────────────────────────────────────
def stats_block(pnl_pts: List[float]) -> Dict[str, Any]:
    """PF/win-rate/total/avg for a list of point-P&L values."""
    n = len(pnl_pts)
    if n == 0:
        return {"n": 0, "win_rate": None, "total_pts": 0.0,
                "avg_pts": None, "pf": None}
    wins = [x for x in pnl_pts if x > 0]
    losses = [x for x in pnl_pts if x < 0]
    total = sum(pnl_pts)
    win_sum = sum(wins)
    loss_sum = -sum(losses)   # positive
    pf: Optional[float]
    if loss_sum == 0:
        pf = float("inf") if win_sum > 0 else None
    else:
        pf = round(win_sum / loss_sum, 3)
    return {
        "n": n,
        "win_rate": round(len(wins) / n, 3),
        "total_pts": round(total, 1),
        "avg_pts": round(total / n, 1),
        "pf": pf,
    }


def size_label(n: int) -> str:
    if n < 15:
        return "NO CONCLUSION (n<15)"
    if n < 100:
        return "directional only (n<100)"
    return ""


# ─── main ────────────────────────────────────────────────────────────────
def run() -> None:
    d_trades = load_trades(D_LOG, "D")
    r_trades = load_trades(R_LOG, "R")
    print(f"[trades] D real entries: {len(d_trades)} | R real entries: {len(r_trades)}")

    all_ts = [t["timestamp"] for t in d_trades + r_trades]
    if not all_ts:
        print("[abort] no trades to measure"); return
    # load M1 with buffer for context (need up to a few days before the earliest)
    start = min(all_ts) - pd.Timedelta(days=7)
    end = max(all_ts) + pd.Timedelta(days=4)
    m1 = load_m1(start, end)
    m1_end = m1.index.max()

    def _label_coverage(ts: pd.Timestamp) -> bool:
        return ts <= m1_end

    ctx = MarketContext(m1)

    # For each trade, once compute veto info + outcome. veto only depends on
    # context; K applies afterward. So compute nearest-opposing distance once.
    per_trade: List[Dict[str, Any]] = []
    for tr in d_trades + r_trades:
        rec = dict(tr)
        rec.pop("timestamp")   # drop the raw Timestamp — keep timestamp_utc str
        if not _label_coverage(tr["timestamp"]):
            rec.update({"coverage": "OUT_OF_HISTDATA",
                        "opposing_level": None, "distance_atr": None,
                        "outcome": None})
            per_trade.append(rec); continue

        ctx.refresh(tr["timestamp"])
        lv, dist_price = ctx.nearest_opposing_unswept(tr["direction"], tr["entry_price"])
        dist_atr = None if (lv is None or tr["atr"] <= 0) else dist_price / tr["atr"]

        outcome = simulate_outcome(tr, m1)
        rec.update({
            "coverage": outcome["status"] if outcome["status"] == "OUT_OF_HISTDATA" else "IN_HISTDATA",
            "opposing_level": None if lv is None else {
                "source": lv.source, "side": lv.side, "price": lv.price,
                "formed_at": lv.formed_at.isoformat(),
                "swept": lv.swept, "meta": lv.meta,
            },
            "distance_price": None if dist_price is None else round(dist_price, 4),
            "distance_atr": None if dist_atr is None else round(dist_atr, 3),
            "opposing_side_active_count": len(ctx.active_unswept()),
            "outcome": outcome,
        })
        per_trade.append(rec)

    # ── partition per K and per profile ────────────────────────────────
    # rules for the sensitivity tables:
    #   include only IN_HISTDATA trades with a determinate outcome (TP or SL)
    #   AMBIGUOUS_SAME_BAR and OPEN_AT_HORIZON → excluded from PF/win-rate,
    #     but counted separately in the report.
    profile_partitions: Dict[Tuple[str, float], Dict[str, List[Dict]]] = {}
    excluded_counts: Dict[str, Dict[str, int]] = {"D": {}, "R": {}}
    for prof in ("D", "R"):
        rows = [r for r in per_trade if r["profile"] == prof]
        excl = {"OUT_OF_HISTDATA": 0, "AMBIGUOUS_SAME_BAR": 0,
                "OPEN_AT_HORIZON": 0}
        eligible = []
        for r in rows:
            if r["coverage"] == "OUT_OF_HISTDATA":
                excl["OUT_OF_HISTDATA"] += 1; continue
            st = r["outcome"]["status"]
            if st in excl:
                excl[st] += 1; continue
            if st not in ("TP", "SL"):
                continue
            eligible.append(r)
        excluded_counts[prof] = excl
        for K in K_GRID:
            vetoed, kept = [], []
            for r in eligible:
                if r["distance_atr"] is not None and r["distance_atr"] <= K:
                    vetoed.append(r)
                else:
                    kept.append(r)
            profile_partitions[(prof, K)] = {"vetoed": vetoed, "kept": kept,
                                             "eligible_n": len(eligible)}

    # ── write jsonl partitions ─────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for (prof, K), part in profile_partitions.items():
        out = OUT_DIR / f"veto_partition_{prof}_K{K:g}.jsonl"
        with open(out, "w") as f:
            for r in part["vetoed"]:
                f.write(json.dumps({**r, "decision": "VETOED", "K": K}) + "\n")
            for r in part["kept"]:
                f.write(json.dumps({**r, "decision": "KEPT", "K": K}) + "\n")
        print(f"[jsonl] wrote {out.name}: "
              f"{len(part['vetoed'])} vetoed + {len(part['kept'])} kept")

    # also a full per-trade dump for auditing
    full = OUT_DIR / "veto_all_trades.jsonl"
    with open(full, "w") as f:
        for r in per_trade:
            f.write(json.dumps(r) + "\n")
    print(f"[jsonl] wrote {full.name}: {len(per_trade)} trades")

    # ── build the markdown report ──────────────────────────────────────
    md_lines: List[str] = []
    md_lines.append("# Liquidity-context veto measurement — D & R\n")
    md_lines.append(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}._\n")

    # caveats block AT THE TOP
    md_lines.append("## Mandatory caveats — read first\n")
    md_lines.append(
        "1. **Sample size.** Both profiles are young. If the vetoed n for a "
        "profile is <15, the row is labelled **NO CONCLUSION**; <100 is "
        "**directional only**. Do not act on a NO-CONCLUSION line."
    )
    md_lines.append(
        "2. **Timezone alignment.** The bot writes log timestamps with "
        "`datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')` "
        "(bot.py:598/1131/1465/1567) — i.e. naive-strings-that-represent-UTC. "
        "HistData `time` is a Unix epoch (UTC). Both are treated as UTC and "
        "compared by direct equality — no broker-server / NY offsets applied. "
        "The NY-local session windows (03–08 London, 08–17 NY, 19–00 Asia) "
        "are computed by `tz_convert('America/New_York')` on the UTC-indexed "
        "M1 frame, so DST is handled correctly."
    )
    md_lines.append(
        "3. **HistData is a proxy** for actual broker fills. Reconstructed "
        "prior-day / prior-session / Asian-range levels are near-identical to "
        "what the live broker would have shown, but not guaranteed identical "
        "to the tick the bot saw. HistData coverage ends "
        f"**{m1_end.strftime('%Y-%m-%d %H:%M UTC')}** — trades after that are "
        "labelled OUT_OF_HISTDATA and excluded from PF/win-rate."
    )
    md_lines.append(
        "4. **First-order screen only, not a re-backtest.** Assumes trade "
        "independence. Vetoing trade N would not have changed the state or "
        "P&L of trade N+1 in this analysis (no path dependence). Frame "
        "conclusions accordingly."
    )
    md_lines.append(
        "5. **P&L is expressed in points** (XAUUSD: 1 dollar = 100 points). "
        "Outcome (TP or SL) is determined from the log's own `sl_price` and "
        "`tp_price` by scanning HistData M1 forward from the entry bar; the "
        "first bar to touch either wins. If both fall inside the same M1 bar "
        "the trade is flagged AMBIGUOUS_SAME_BAR and excluded from PF/win-"
        "rate stats but reported in the excluded counts."
    )
    md_lines.append("")

    # trade-count summary
    md_lines.append("## Trade set\n")
    for prof in ("D", "R"):
        rows = [r for r in per_trade if r["profile"] == prof]
        excl = excluded_counts[prof]
        n_elig = sum(1 for r in rows
                     if r["coverage"] == "IN_HISTDATA"
                     and r["outcome"]["status"] in ("TP", "SL"))
        md_lines.append(
            f"- **Profile {prof}**: {len(rows)} real entries in log "
            f"(MISSED_TIMEOUT rows already excluded). Eligible for stats "
            f"(TP or SL resolvable in HistData): **{n_elig}**. "
            f"Excluded: OUT_OF_HISTDATA={excl['OUT_OF_HISTDATA']}, "
            f"AMBIGUOUS_SAME_BAR={excl['AMBIGUOUS_SAME_BAR']}, "
            f"OPEN_AT_HORIZON={excl['OPEN_AT_HORIZON']}."
        )
    md_lines.append("")

    # sensitivity tables per profile
    md_lines.append("## Sensitivity table\n")
    md_lines.append("Headline K (pre-registered): **1.0**. Other K reported for sensitivity; "
                    "**do not** pick K by best result.\n")
    for prof in ("D", "R"):
        md_lines.append(f"### Profile {prof}\n")
        md_lines.append("| K | Vetoed n | Vetoed win% | Vetoed avg (pts) | "
                        "Vetoed PF | Kept n | Kept win% | Kept avg (pts) | "
                        "Kept PF | % vetoed | note |")
        md_lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
        for K in K_GRID:
            part = profile_partitions[(prof, K)]
            elig_n = part["eligible_n"]
            v_pnl = [r["outcome"]["pnl_points"] for r in part["vetoed"]]
            k_pnl = [r["outcome"]["pnl_points"] for r in part["kept"]]
            sv = stats_block(v_pnl); sk = stats_block(k_pnl)
            pct = (100 * sv["n"] / elig_n) if elig_n else 0.0
            note = size_label(sv["n"])
            if K == HEADLINE_K:
                note = ("**HEADLINE** " + note).strip()
            def fmt(x):
                return "—" if x is None else (f"{x:g}" if isinstance(x, float) else str(x))
            md_lines.append(
                f"| {K:g} | {sv['n']} | {fmt(sv['win_rate'])} | "
                f"{fmt(sv['avg_pts'])} | {fmt(sv['pf'])} | "
                f"{sk['n']} | {fmt(sk['win_rate'])} | {fmt(sk['avg_pts'])} | "
                f"{fmt(sk['pf'])} | {pct:.0f}% | {note} |"
            )
        md_lines.append("")

    # narrative interpretation guardrails
    md_lines.append("## How to read this\n")
    md_lines.append(
        "- The veto has value **only if the VETOED bucket is net-losing** "
        "(negative avg pts / PF < 1) and it kills a **workable fraction** — "
        "a veto that removes >70% of trades is impractical even if the "
        "killed ones lost slightly."
    )
    md_lines.append(
        "- If VETOED shows a positive avg / PF > 1, the rule is throwing "
        "away winners: **do not promote**."
    )
    md_lines.append(
        "- With small n, sign flips easily. Any row labelled NO CONCLUSION "
        "means the result is dominated by noise, not signal — report it, "
        "do not act on it."
    )
    md_lines.append(
        "- D and R are **not pooled**. Their entry gates differ (D uses the "
        "polarity flip, R does not — CODEBASE_TRUTH.md), so a level that "
        "vetoes a D setup does not necessarily veto the equivalent R setup, "
        "and mixing samples would mask that."
    )
    md_lines.append("")

    md_lines.append("## Artifacts\n")
    for (prof, K) in sorted(profile_partitions):
        md_lines.append(
            f"- `veto_partition_{prof}_K{K:g}.jsonl` — partitioned trades for "
            f"Profile {prof} at K={K:g}."
        )
    md_lines.append(f"- `veto_all_trades.jsonl` — every trade with its computed "
                    f"opposing-level info (VETOED/KEPT decision derived per K).")

    (OUT_DIR / "veto_analysis.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"[md] wrote {OUT_DIR / 'veto_analysis.md'}")


if __name__ == "__main__":
    run()
