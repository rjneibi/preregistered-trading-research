"""
STATUS: RESEARCH-ONLY (2026-07-02). Not wired to any live bot.

Zone-flip momentum scalp backtest ("enter immediately when a zone flips").

Strategy under test (proposed by user, 2026-07-02):
  * Build the day's zones exactly like the live bot (gann_levels + fibonacci_
    pivots + fib_retracements + build_zones, daily at UTC 00:00).
  * A zone FLIPS when an H4 candle CLOSES beyond its level (identical rule to
    structure.check_zone_polarity / tools/zone_flip_alert.py).
  * The moment a flip happens, enter IMMEDIATELY in the direction of the break:
      - H4 close BELOW a support level  -> support becomes resistance -> SELL
      - H4 close ABOVE a resistance     -> resistance becomes support -> BUY
  * Fixed dollar take-profit ($10-15 requested; grid $5/$10/$15) and a fixed
    dollar stop grid, plus an "exit on the next opposite-direction flip"
    variant with no fixed stop.

Contrast with live Profile D: this REMOVES the H4 bias gate, the H1 body-close
confirmation, and the Option-C M1 pullback wait. It is a pure breakout-
momentum play on the polarity-flip event.

Reuses research/dr_backtest for data loading (HistData M1, UTC, look-ahead-
safe resampling) and metrics. Live modules levels.py / signals.py /
structure.py are imported directly for zone construction and classification —
single source of truth. The polarity rule itself is one inequality on the
just-closed H4 bar (see note below), so no adapter is needed.

Look-ahead note: at each H4 close we only test the JUST-CLOSED bar's close
against zone levels of zones that were unflipped at the day's baseline. The
baseline itself uses the 10 H4 closes fully completed BEFORE the day started
(same 10-bar window as check_zone_polarity). Because the 10-close window can
only gain a breach by adding a new close, "zone transitions to flipped" is
exactly equivalent to "this H4 close breached the level" — no future data can
be involved.

Deduplication: one H4 candle can cross several stacked levels at once. The
headline trade series takes at most ONE trade per (H4 close, direction);
the number of zones flipped by that candle is recorded per trade.

Costs: 20 pts ($0.20) per round trip = 13 pts observed live spread + 7 pts
commission (same convention as research/s_exit_grid.py).

Run:  py -3.11 research/flip_scalp/run_flip_scalp.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# silence the live loggers before importing the live modules
for name in ("levels", "signal", "signals", "structure"):
    logging.getLogger(name).setLevel(logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

import config as live_config                                # noqa: E402
import levels as levels_mod                                 # noqa: E402
import signals as signals_mod                               # noqa: E402
import structure as structure_mod                           # noqa: E402

from research.dr_backtest.data_prep import (                # noqa: E402
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr, bars_to_dicts,
    completed_h4_before,
)
from research.dr_backtest.metrics import (                  # noqa: E402
    basic_stats, size_label, validation_flags,
)

OUT = REPO / "research" / "flip_scalp"

# ---- window: same regime-coherence rationale as dr_backtest/run.py --------
BT_END = pd.Timestamp("2026-06-19T17:57:00Z")     # HistData coverage end
BT_START = pd.Timestamp("2021-06-19T00:00:00Z")   # last 5 years
LOAD_BUFFER_DAYS = 45

# ---- live Profile-D zone construction params (config-verified) ------------
GANN_DEGREES = [45, 90, 135, 180, 225, 270, 315, 360]
FIB_LEVELS = [0.382, 0.500, 0.618, 0.786]
ATR_ZONE_MULT = 0.3
SWING_LOOKBACK_H4 = 50

# ---- strategy grid ---------------------------------------------------------
POINT_PER_DOLLAR = 100.0
TP_GRID_PTS = [500.0, 1000.0, 1500.0]     # $5 / $10 / $15
SL_GRID_PTS = [500.0, 1000.0, 1500.0]
COST_PTS = 20.0                            # 13 spread + 7 commission
HORIZON_HOURS = 120                        # 5 days; then mark-to-market TIMEOUT
HEADLINE = (1000.0, 1000.0)                # TP $10 / SL $10


# ─────────────────────────────────────────────────────────────────────────
# Day-level zone construction (mirrors dr_backtest.Backtester snapshots,
# evaluated once per day at the UTC-midnight zone build)
# ─────────────────────────────────────────────────────────────────────────
def apply_config():
    for k, v in [
        ("SYMBOL", "XAUUSD"),
        ("GANN_DEGREES", GANN_DEGREES),
        ("FIB_LEVELS", FIB_LEVELS),
        ("ATR_ZONE_WIDTH_MULT", ATR_ZONE_MULT),
        ("SWING_LOOKBACK_H4", SWING_LOOKBACK_H4),
    ]:
        setattr(live_config, k, v)


def build_day_zones(day_open: pd.Timestamp, d1: pd.DataFrame,
                    h4: pd.DataFrame, atr_h1: pd.Series,
                    h1_index: pd.DatetimeIndex):
    """Zones + original sides + baseline flip state, all as of day_open.

    Returns (zones, atr) or None if inputs are insufficient. Each zone dict:
      {source, level, side_orig, swing_dir, baseline_flipped}
    """
    d1_upto = d1[d1.index <= day_open]
    if len(d1_upto) < 2 or d1_upto.index[-1] != day_open:
        return None                       # no D1 bar opening exactly today
    prev = d1_upto.iloc[-2]
    daily_open = float(d1_upto.iloc[-1]["open"])

    closed_h4 = completed_h4_before(h4, day_open)
    if len(closed_h4) < SWING_LOOKBACK_H4:
        return None
    bars_h4 = bars_to_dicts(closed_h4.tail(250))

    # ATR of the last H1 bar fully closed before day_open
    pos = h1_index.searchsorted(day_open - pd.Timedelta(hours=1), side="right") - 1
    if pos < 0:
        return None
    atr = float(atr_h1.iloc[pos])
    if not np.isfinite(atr) or atr <= 0:
        return None

    gann = levels_mod.gann_levels(daily_open, GANN_DEGREES)
    pivots = levels_mod.fibonacci_pivots(
        float(prev["high"]), float(prev["low"]), float(prev["close"]))
    swing_h, swing_l, sdir = structure_mod.find_swing(bars_h4)
    fibs = levels_mod.fib_retracements(swing_h, swing_l, sdir)
    all_levels = {**gann, **pivots, **fibs}
    raw = levels_mod.build_zones(all_levels, atr, ATR_ZONE_MULT, daily_open,
                                 fib_swing_dir=sdir)

    # baseline: 10 H4 closes fully completed before day_open (live window)
    base_closes = closed_h4["close"].tail(10).tolist()

    zones = []
    for z in raw:
        src = z["source"]
        side = signals_mod._classify_zone(src, z.get("swing_dir"))
        if src.upper() == "PP":           # dynamic PP, as in zone_flip_alert
            side = ("resistance" if daily_open < z["level"]
                    else "support" if daily_open > z["level"] else side)
        if side not in ("support", "resistance"):
            continue
        lvl = float(z["level"])
        if side == "support":
            base_flip = any(c < lvl for c in base_closes)
        else:
            base_flip = any(c > lvl for c in base_closes)
        zones.append({"source": src, "level": lvl, "side_orig": side,
                      "baseline_flipped": base_flip})
    return zones, atr


# ─────────────────────────────────────────────────────────────────────────
# Flip-event scan
# ─────────────────────────────────────────────────────────────────────────
def collect_flip_events(m1: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame,
                        d1: pd.DataFrame, atr_h1: pd.Series) -> list[dict]:
    """One deduped trade candidate per (H4 close, direction)."""
    events: list[dict] = []
    h4_opens = h4.index
    day_opens = d1.index[(d1.index >= BT_START) & (d1.index <= BT_END)]
    h1_index = h1.index

    for i, day_open in enumerate(day_opens):
        if i % 200 == 0:
            print(f"  [scan] day {i:>5}/{len(day_opens)}  "
                  f"events so far: {len(events)}", flush=True)
        built = build_day_zones(day_open, d1, h4, atr_h1, h1_index)
        if built is None:
            continue
        zones, atr = built
        live_zones = [z for z in zones if not z["baseline_flipped"]]
        if not live_zones:
            continue

        next_day = day_open + pd.Timedelta(days=1)
        day_h4 = h4[(h4_opens >= day_open) & (h4_opens < next_day)]

        for open_ts, row in day_h4.iterrows():
            cursor = open_ts + pd.Timedelta(hours=4)
            if cursor > BT_END:
                break
            close = float(row["close"])
            flips_buy, flips_sell = [], []
            still = []
            for z in live_zones:
                if z["side_orig"] == "support" and close < z["level"]:
                    flips_sell.append(z)          # broke below support
                elif z["side_orig"] == "resistance" and close > z["level"]:
                    flips_buy.append(z)           # broke above resistance
                else:
                    still.append(z)
            live_zones = still                    # a zone flips once per day
            for direction, flips in (("BUY", flips_buy), ("SELL", flips_sell)):
                if not flips:
                    continue
                events.append({
                    "entry_ts": cursor.isoformat(),
                    "direction": direction,
                    "h4_close": close,
                    "atr_at_build": atr,
                    "n_zones_flipped": len(flips),
                    "zone_sources": [z["source"] for z in flips],
                    "zone_levels": [z["level"] for z in flips],
                })
    print(f"  [scan] done — {len(events)} deduped flip events", flush=True)
    return events


# ─────────────────────────────────────────────────────────────────────────
# Vectorized M1 exit simulation
# ─────────────────────────────────────────────────────────────────────────
class M1Sim:
    def __init__(self, m1: pd.DataFrame):
        self.t = m1.index.values                  # datetime64[ns], bar OPEN
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)

    def run(self, entry_ts: pd.Timestamp, direction: str,
            tp_pts: float, sl_pts: float | None,
            stop_ts: pd.Timestamp | None = None,
            horizon_hours: int = HORIZON_HOURS) -> dict:
        """Fill at the open of the first M1 bar at/after entry_ts. Conservative:
        same-bar TP+SL resolves as SL. Returns pnl in points BEFORE costs."""
        sign = 1 if direction == "BUY" else -1
        i0 = self.t.searchsorted(np.datetime64(entry_ts))
        if i0 >= len(self.t):
            return {"status": "OUT_OF_HISTDATA", "pnl_points": None}
        fill = self.o[i0]
        tp_px = fill + sign * tp_pts / POINT_PER_DOLLAR
        sl_px = (fill - sign * sl_pts / POINT_PER_DOLLAR
                 if sl_pts is not None else None)

        i_h = self.t.searchsorted(
            np.datetime64(entry_ts + pd.Timedelta(hours=horizon_hours)))
        i_s = (self.t.searchsorted(np.datetime64(stop_ts), side="right")
               if stop_ts is not None else len(self.t) + 1)
        stop_truncates = i_s <= i_h
        i1 = max(min(i_h, i_s), i0 + 1)

        hi, lo = self.h[i0:i1], self.l[i0:i1]
        tp_mask = (hi >= tp_px) if sign > 0 else (lo <= tp_px)
        first_tp = int(tp_mask.argmax()) if tp_mask.any() else None
        first_sl = None
        if sl_px is not None:
            sl_mask = (lo <= sl_px) if sign > 0 else (hi >= sl_px)
            first_sl = int(sl_mask.argmax()) if sl_mask.any() else None

        if first_tp is not None and (first_sl is None or first_tp < first_sl):
            exit_i, status, pnl = i0 + first_tp, "TP", sign * (tp_px - fill)
        elif first_sl is not None:
            status = "AMBIGUOUS_SAME_BAR" if first_tp == first_sl else "SL"
            exit_i, pnl = i0 + first_sl, sign * (sl_px - fill)
        else:
            # window exhausted: exit at the last bar's close, mark-to-market
            status = "FLIP_EXIT" if stop_truncates else "TIMEOUT"
            exit_i, pnl = i1 - 1, sign * (self.c[i1 - 1] - fill)

        # max adverse excursion from fill up to and including the exit bar
        if sign > 0:
            mae = fill - self.l[i0:exit_i + 1].min()
        else:
            mae = self.h[i0:exit_i + 1].max() - fill
        hold_h = float((self.t[exit_i] - self.t[i0])
                       / np.timedelta64(1, "h"))

        return {"status": status,
                "pnl_points": round(pnl * POINT_PER_DOLLAR - COST_PTS, 1),
                "mae_points": round(max(mae, 0.0) * POINT_PER_DOLLAR, 1),
                "hold_hours": round(hold_h, 1),
                "exit_ts": pd.Timestamp(self.t[exit_i]).isoformat()}


# ─────────────────────────────────────────────────────────────────────────
# Grid runner + report
# ─────────────────────────────────────────────────────────────────────────
def is_oos_split(trades: list[dict], frac_is: float = 0.7):
    s = sorted(trades, key=lambda e: e["entry_ts"])
    cut = int(round(len(s) * frac_is))
    return s[:cut], s[cut:]


def cell_stats(trades: list[dict]) -> dict:
    pnl = [t["pnl_points"] for t in trades if t["pnl_points"] is not None]
    return basic_stats(pnl)


def fmt(x):
    if x is None:
        return "—"
    if isinstance(x, float):
        return "inf" if x == float("inf") else f"{x:g}"
    return str(x)


def main():
    apply_config()
    print(f"=== flip-scalp backtest: {BT_START.date()} -> {BT_END.date()} ===",
          flush=True)
    load_start = BT_START - pd.Timedelta(days=LOAD_BUFFER_DAYS)
    m1 = load_m1(load_start, BT_END)
    print(f"[data] M1 bars: {len(m1):,}", flush=True)
    h1 = resample_ohlc(m1, "1h")
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    atr_h1 = wilder_atr(h1, 14)
    print(f"[data] H1={len(h1):,} H4={len(h4):,} D1={len(d1):,}", flush=True)

    events = collect_flip_events(m1, h1, h4, d1, atr_h1)
    sim = M1Sim(m1)

    # opposite-flip lookup for the flip-reverse exit variant
    ev_sorted = sorted(events, key=lambda e: e["entry_ts"])
    buy_ts = [pd.Timestamp(e["entry_ts"]) for e in ev_sorted
              if e["direction"] == "BUY"]
    sell_ts = [pd.Timestamp(e["entry_ts"]) for e in ev_sorted
               if e["direction"] == "SELL"]

    def next_opposite(entry_ts: pd.Timestamp, direction: str):
        pool = sell_ts if direction == "BUY" else buy_ts
        idx = np.searchsorted(pd.DatetimeIndex(pool).values,
                              np.datetime64(entry_ts), side="right")
        return pool[idx] if idx < len(pool) else None

    # ---- run grid ----------------------------------------------------------
    results: dict[str, list[dict]] = {}
    for tp in TP_GRID_PTS:
        for sl in SL_GRID_PTS:
            key = f"TP{tp/100:g}_SL{sl/100:g}"
            trades = []
            for e in ev_sorted:
                r = sim.run(pd.Timestamp(e["entry_ts"]), e["direction"], tp, sl)
                trades.append({**e, **r})
            results[key] = trades
            print(f"[grid] {key}: {cell_stats(trades)['n']} trades", flush=True)
        # flip-reverse exit (no fixed SL) for this TP
        key = f"TP{tp/100:g}_FLIPEXIT"
        trades = []
        for e in ev_sorted:
            ts = pd.Timestamp(e["entry_ts"])
            r = sim.run(ts, e["direction"], tp, None,
                        stop_ts=next_opposite(ts, e["direction"]))
            trades.append({**e, **r})
        results[key] = trades
        print(f"[grid] {key}: {cell_stats(trades)['n']} trades", flush=True)

    # pure "enter and leave": TP only, NO stop of any kind, 30-day horizon
    for tp in TP_GRID_PTS:
        key = f"TP{tp/100:g}_NOSL"
        trades = []
        for e in ev_sorted:
            r = sim.run(pd.Timestamp(e["entry_ts"]), e["direction"], tp, None,
                        horizon_hours=720)
            trades.append({**e, **r})
        results[key] = trades
        print(f"[grid] {key}: {cell_stats(trades)['n']} trades", flush=True)

    # ---- artifacts ---------------------------------------------------------
    hl_key = f"TP{HEADLINE[0]/100:g}_SL{HEADLINE[1]/100:g}"
    with open(OUT / "trades_headline.jsonl", "w") as f:
        for t in results[hl_key]:
            f.write(json.dumps(t) + "\n")

    summary = {}
    for key, trades in results.items():
        is_t, oos_t = is_oos_split(trades)
        summary[key] = {"ALL": cell_stats(trades), "IS": cell_stats(is_t),
                        "OOS": cell_stats(oos_t),
                        "flags": validation_flags(cell_stats(is_t),
                                                  cell_stats(oos_t))}
    (OUT / "grid_summary.json").write_text(json.dumps(summary, indent=2))

    write_report(results, summary, events, hl_key)
    print(f"[done] report: {OUT / 'flip_scalp_report.md'}", flush=True)


def write_report(results, summary, events, hl_key):
    L = []
    L.append("# Zone-flip momentum scalp — backtest "
             "(enter immediately on flip, fixed-$ TP)\n")
    L.append(f"_Generated {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}. "
             f"Window {BT_START.date()} -> {BT_END.date()}._\n")
    L.append("## Caveats — read first\n")
    L.append("1. **This is NOT live D/R logic.** It removes the H4-bias gate, "
             "H1 body-close confirmation, and Option-C M1 pullback. Pure "
             "breakout-momentum on the polarity-flip event, unthrottled "
             "(no cooldown, no max-open cap, no daily loss cap).")
    L.append("2. **Zone construction is the live one** (levels.py + "
             "signals._classify_zone imported directly, daily UTC-00:00 "
             "build, D-profile params). Flip rule = one H4 close beyond the "
             "level, identical to structure.check_zone_polarity / "
             "tools/zone_flip_alert.py. Max one flip per zone per day.")
    L.append(f"3. **Costs:** {COST_PTS:g} pts/trade (13 spread + 7 "
             "commission). Fill = open of the first M1 bar after the H4 "
             "close. Same-M1-bar TP+SL resolved conservatively as SL.")
    L.append("4. **Fixed-$ targets are regime-sensitive** — a $10 move in "
             "2021 ($1800 gold) is 2x the relative move it is at $4000+. "
             "Watch the IS/OOS drift.")
    L.append("5. **Dedup:** one trade per (H4 close, direction); "
             "`n_zones_flipped` recorded per trade.\n")

    n_buy = sum(1 for e in events if e["direction"] == "BUY")
    L.append(f"## Events\n\nDeduped flip events: **{len(events)}** "
             f"(BUY {n_buy} / SELL {len(events) - n_buy}) over "
             f"{(BT_END - BT_START).days} days "
             f"(~{len(events) / ((BT_END - BT_START).days / 7):.1f}/week).\n")

    L.append("## Grid results (pnl in points, $1 = 100 pts; costs included)\n")
    L.append("| Cell | Split | n | Win% | PF | Expectancy (pts) | Avg win | "
             "Avg loss | MDD (pts) |")
    L.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for key in results:
        for lbl in ("ALL", "IS", "OOS"):
            s = summary[key][lbl]
            mark = " **(headline)**" if key == hl_key and lbl == "ALL" else ""
            L.append(f"| {key}{mark} | {lbl} | {s['n']} | {fmt(s['win_rate'])} "
                     f"| {fmt(s['pf'])} | {fmt(s['expectancy'])} | "
                     f"{fmt(s['avg_win'])} | {fmt(s['avg_loss'])} | "
                     f"{fmt(s['max_drawdown_pts'])} |")
    L.append("")
    L.append("## Validation flags\n")
    for key in results:
        flags = summary[key]["flags"]
        L.append(f"**{key}:** " + ("; ".join(flags) if flags else "(none)"))
    L.append("")

    # headline breakdowns
    hl = [t for t in results[hl_key] if t["pnl_points"] is not None]
    L.append(f"## Headline cell breakdowns ({hl_key})\n")
    L.append("| Slice | n | Win% | PF | Expectancy (pts) |")
    L.append("|---|---:|---:|---:|---:|")
    for label, sub in [
        ("BUY", [t for t in hl if t["direction"] == "BUY"]),
        ("SELL", [t for t in hl if t["direction"] == "SELL"]),
        ("multi-zone flips (n_zones>1)",
         [t for t in hl if t["n_zones_flipped"] > 1]),
        ("single-zone flips", [t for t in hl if t["n_zones_flipped"] == 1]),
    ]:
        s = basic_stats([t["pnl_points"] for t in sub])
        L.append(f"| {label} | {s['n']} | {fmt(s['win_rate'])} | {fmt(s['pf'])} "
                 f"| {fmt(s['expectancy'])} |")
    # per-year
    L.append("")
    L.append("| Year | n | Win% | PF | Expectancy (pts) |")
    L.append("|---|---:|---:|---:|---:|")
    years = sorted({t["entry_ts"][:4] for t in hl})
    for y in years:
        s = basic_stats([t["pnl_points"] for t in hl
                         if t["entry_ts"].startswith(y)])
        L.append(f"| {y} | {s['n']} | {fmt(s['win_rate'])} | {fmt(s['pf'])} "
                 f"| {fmt(s['expectancy'])} |")
    L.append("")

    # pure TP-only cells: the "enter and leave, nothing else" model
    L.append("## TP-only, no stop of any kind (30-day hold horizon)\n")
    L.append("MAE = max adverse excursion: the worst open drawdown a trade "
             "sits through before it exits. TIMEOUT = still open after 30 "
             "days, marked to market at the last bar.\n")
    L.append("| Cell | n | TP hit | TIMEOUT | Win% | PF | Expectancy (pts) | "
             "MAE med | MAE p90 | MAE max | Hold med (h) | Hold p90 (h) |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for key, trades in results.items():
        if not key.endswith("_NOSL"):
            continue
        done = [t for t in trades if t["pnl_points"] is not None]
        s = basic_stats([t["pnl_points"] for t in done])
        n_tp = sum(1 for t in done if t["status"] == "TP")
        n_to = sum(1 for t in done if t["status"] == "TIMEOUT")
        mae = np.array([t.get("mae_points", np.nan) for t in done], float)
        hold = np.array([t.get("hold_hours", np.nan) for t in done], float)
        L.append(f"| {key} | {s['n']} | {n_tp} | {n_to} | "
                 f"{fmt(s['win_rate'])} | {fmt(s['pf'])} | "
                 f"{fmt(s['expectancy'])} | {np.nanmedian(mae):.0f} | "
                 f"{np.nanpercentile(mae, 90):.0f} | {np.nanmax(mae):.0f} | "
                 f"{np.nanmedian(hold):.1f} | {np.nanpercentile(hold, 90):.1f} |")
    L.append("")
    L.append("## Artifacts\n")
    L.append("- `trades_headline.jsonl` — per-trade records, headline cell.")
    L.append("- `grid_summary.json` — full grid stats.")
    L.append("- `run_flip_scalp.py` — the harness.\n")
    (OUT / "flip_scalp_report.md").write_text("\n".join(L) + "\n",
                                              encoding="utf-8")


if __name__ == "__main__":
    main()
