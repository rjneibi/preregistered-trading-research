"""DOOR 3 — does the R3/S3 spec survive a stop pinned in dollars by a $2,000
account on a 0.01-lot broker?

Prereg: prereg/door3_fixed_dollar_stop.md  SHA256 77A50FB478963E71C7A25CF31E4
C40F82F1652DBCC54D0B114587B18FC939036, sealed 2026-08-24 19:08:16 UTC.

Both arms run on the SAME events, the SAME data, the SAME cost basis. Exactly
one thing differs: k_sl_atr=2.4 becomes sl_usd=20.00 (derived, not chosen —
see the prereg). No sweep.

    python run_door3.py            # uses config.yaml's m1_path
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from goldbot.config import load_config, resolve_path            # noqa: E402
from goldbot.data import (load_ohlc, resample_d1_utc,            # noqa: E402
                          resample_ohlc, wilder_atr)
from goldbot.events import generate_events_final                 # noqa: E402
from goldbot.triple_barrier import run_exits                     # noqa: E402

ERAS = {"old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                pd.Timestamp("2021-06-18T23:59:00Z")),
        "new": (pd.Timestamp("2021-06-19T00:00:00Z"), None)}
WARMUP = pd.Timedelta(days=100)

EQUITY, RISK_PCT, MIN_LOT, USD_PER_UNIT = 2000.0, 0.01, 0.01, 100.0
SL_USD = (RISK_PCT * EQUITY) / (MIN_LOT * USD_PER_UNIT)      # = 20.00, derived

# MEASURED on broker demo feed 2026-08-24 (swap_mode=1 POINTS, rollover3days=3)
SWAP_LONG_PTS, SWAP_SHORT_PTS = -12.6, -4.6
COMMISSION_RT = 7.0                                          # $/lot round trip
MATRIX = ROOT / "results" / "cost_matrix.json"

WINDOWS = {"FULL 2015-2026": pd.Timestamp("2000-01-01", tz="UTC"),
           "MODERN 2021-06+": pd.Timestamp("2021-06-19", tz="UTC"),
           "RECENT 2023-01+": pd.Timestamp("2023-01-01", tz="UTC")}


def spread_p90(mx, ts):
    """p90 spread $/oz for a trade's entry year x machine-UTC hour."""
    y, h = str(ts.year), str(ts.hour)
    cell = mx.get("years", {}).get(y, {}).get(h)
    if cell and "p90" in cell:
        return cell["p90"]
    fb = mx.get("fallback", {})
    return (fb.get(y) or fb.get("_global", {})).get("p90", 0.64)


def add_costs(t, mx):
    """Cost basis identical to cycles 6-7: spread + slippage(0.5x spread per
    side, i.e. 1x spread round trip) => 2x spread, x100/lot, + $7 commission.
    Swap uses the MEASURED points, with Wednesday charged triple exactly rather
    than via the 1.4x average blend."""
    t = t.copy()
    t["entry_ts"] = pd.to_datetime(t.entry_ts, utc=True)
    t["exit_ts"] = pd.to_datetime(t.exit_ts, utc=True)
    t["cost_usd"] = [spread_p90(mx, ts) * 100.0 * 2.0 + COMMISSION_RT
                     for ts in t.entry_ts]
    swaps = []
    for r in t.itertuples():
        pts = SWAP_LONG_PTS if r.side > 0 else SWAP_SHORT_PTS
        tot = 0.0
        for p in pd.date_range(r.entry_ts.normalize() + pd.Timedelta(hours=21),
                               r.exit_ts, freq="D"):
            if p > r.entry_ts:                       # broker rollover 21:00 UTC
                tot += pts * (3.0 if p.weekday() == 2 else 1.0)
        swaps.append(tot)
    t["swap_usd"] = swaps                            # 1 pt = $1 per lot
    t["net_usd"] = t.gross_usd - t.cost_usd + t.swap_usd
    return t


def summarise(t, label):
    rows = []
    for nm, cut in WINDOWS.items():
        s = t[t.exit_ts >= cut]
        if not len(s):
            continue
        win = (s.gross_usd > 0).mean()
        rows.append({"arm": label, "window": nm, "n": len(s), "wr": win,
                     "gross": s.gross_usd.mean(), "cost": -s.cost_usd.mean(),
                     "swap": s.swap_usd.mean(), "net": s.net_usd.mean(),
                     "net_total": s.net_usd.sum()})
    return rows


def main() -> int:
    cfg = load_config(str(ROOT / "config.yaml"))
    m1_path = resolve_path(cfg, cfg.data.m1_path)
    e = cfg.exits.final
    print(f"DOOR 3 | account ${EQUITY:,.0f} | min lot {MIN_LOT} | "
          f"derived stop ${SL_USD:.2f}/oz")
    print(f"  baseline arm: k_tp_atr={e.k_tp_atr} k_sl_atr={e.k_sl_atr}")
    print(f"  door-3   arm: k_tp_atr={e.k_tp_atr} sl_usd={SL_USD:.2f}  "
          f"(ONE change)")
    print(f"loading {m1_path.name} ...", flush=True)
    m1_full = load_ohlc(m1_path, data_tz=cfg.data.data_tz)
    data_end = m1_full.index[-1]
    print(f"  {len(m1_full):,} M1 bars, {m1_full.index[0]} -> {data_end}")

    base, door3, ev_all = [], [], []
    for era, (start, end) in ERAS.items():
        end = end or data_end
        if start > data_end:
            continue
        m1 = m1_full[(m1_full.index >= start - WARMUP) & (m1_full.index <= end)]
        h1 = resample_ohlc(m1, "1h")
        h4 = resample_ohlc(m1, "4h")
        d1 = resample_d1_utc(m1)
        atr_h1 = wilder_atr(h1, e.atr.period)
        events = generate_events_final(h1, h4, d1, atr_h1, cfg, start, end)
        ev_all.append(events)
        common = dict(time_stop_h=e.time_stop_h, fill_mode=cfg.exits.fill_mode,
                      bail_enabled=e.bail.enabled,
                      hivol_half_x=e.bail.hivol_half_x,
                      lovol_bail_h=e.bail.lovol_bail_h,
                      lovol_bail_x=e.bail.lovol_bail_x)
        a = run_exits(m1, events, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr,
                      **common)
        b = run_exits(m1, events, k_tp_atr=e.k_tp_atr, sl_usd=SL_USD, **common)
        a["era"] = b["era"] = era
        base.append(a)
        door3.append(b)
        print(f"  [{era}] {len(events)} events -> baseline {len(a)}, "
              f"door3 {len(b)} trades")

    mx = json.loads(MATRIX.read_text(encoding="utf-8"))
    A = add_costs(pd.concat(base, ignore_index=True), mx)
    B = add_costs(pd.concat(door3, ignore_index=True), mx)
    events = pd.concat(ev_all, ignore_index=True)

    print("\n" + "=" * 96)
    print("RESULTS — identical entries, identical costs, one changed barrier")
    print("=" * 96)
    rows = summarise(A, "baseline 2.4xATR") + summarise(B, f"door3 ${SL_USD:.0f}")
    df = pd.DataFrame(rows)
    print(f"{'arm':<20}{'window':<18}{'n':>5}{'win%':>8}{'gross':>10}"
          f"{'cost':>10}{'swap':>8}{'net/trade':>11}{'net total':>12}")
    for r in df.itertuples():
        print(f"{r.arm:<20}{r.window:<18}{r.n:>5}{r.wr*100:>7.1f}%"
              f"{r.gross:>10.2f}{r.cost:>10.2f}{r.swap:>8.2f}"
              f"{r.net:>11.2f}{r.net_total:>12,.0f}")

    print("\n" + "=" * 96)
    print("RESOLUTION MIX")
    print("=" * 96)
    for nm, t in (("baseline", A), ("door3", B)):
        mix = t.resolution.value_counts(normalize=True).mul(100).round(1)
        print(f"  {nm:<9} " + "  ".join(f"{k}={v}%" for k, v in mix.items())
              + f"   derisked={t.derisked.mean()*100:.1f}%"
              + f"   ambiguous={t.ambiguous.mean()*100:.1f}%")

    print("\n" + "=" * 96)
    print("PREDICTION CHECK  (prereg SHA256 77A50FB4..., sealed before running)")
    print("=" * 96)
    wa = (A.gross_usd > 0).mean()
    wb = (B.gross_usd > 0).mean()
    d = (wa - wb) * 100
    p1 = d >= 15.0
    print(f"  P1 win rate falls >=15pp      : baseline {wa*100:.1f}% -> "
          f"door3 {wb*100:.1f}%  (drop {d:.1f}pp)   "
          f"{'CONFIRMED' if p1 else 'REFUTED'}")

    rb = B[B.exit_ts >= WINDOWS["RECENT 2023-01+"]].net_usd.mean()
    ra = A[A.exit_ts >= WINDOWS["RECENT 2023-01+"]].net_usd.mean()
    p2 = rb < 0
    print(f"  P2 RECENT net/trade negative  : baseline ${ra:+.2f} -> "
          f"door3 ${rb:+.2f}   {'CONFIRMED' if p2 else 'REFUTED'}")

    lost = (B.atr > SL_USD).mean()
    p3 = lost >= 0.60
    print(f"  P3 >=60% lose the bail overlay: {lost*100:.1f}% of trades have "
          f"ATR > ${SL_USD:.0f}   {'CONFIRMED' if p3 else 'REFUTED'}")
    print(f"     (baseline derisked {A.derisked.mean()*100:.1f}% of trades, "
          f"door3 {B.derisked.mean()*100:.1f}%)")

    p4 = B.gross_usd.mean() < A.gross_usd.mean()
    print(f"  P4 full-sample gross lower    : baseline ${A.gross_usd.mean():+.2f} "
          f"-> door3 ${B.gross_usd.mean():+.2f}   "
          f"{'CONFIRMED' if p4 else 'REFUTED'}")

    hits = sum((p1, p2, p3, p4))
    print(f"\n  {hits}/4 predictions confirmed")
    verdict = ("DOOR 3 IS DEAD — as predicted." if p2 else
               "DOOR 3 SURVIVED the kill shot — needs Sidak + forward test "
               "before it means anything.")
    print(f"  VERDICT: {verdict}")

    out = ROOT / "results"
    A.to_csv(out / "door3_baseline_trades.csv", index=False)
    B.to_csv(out / "door3_fixed20_trades.csv", index=False)
    print(f"\nwrote {out / 'door3_baseline_trades.csv'} and "
          f"{out / 'door3_fixed20_trades.csv'}  ({len(events)} events)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
