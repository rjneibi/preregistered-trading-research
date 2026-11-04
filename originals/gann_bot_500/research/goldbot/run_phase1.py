"""Phase 1 pipeline: pivot edge -> triple-barrier exits -> cost netting ->
CPCV report -> GO/NO-GO.

    python run_phase1.py path/to/xauusd_m1.csv [--variant final|base]
                          [--config config.yaml] [--fill gap_open|barrier_level]

Honesty banner: numbers here are an UPPER BOUND — fills at barrier prices
(or bar opens on gaps), flat slippage estimates, no news spread widening.
The printed cost floor per regime is the minimum your edge must clear.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from goldbot.backtest import (cpcv_report, fmt_stats, go_no_go, net_trades,  # noqa: E402
                              per_year, stats)
from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.costs import REGIMES, CostModel  # noqa: E402
from goldbot.cpcv import CombinatorialPurgedCV  # noqa: E402
from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr  # noqa: E402
from goldbot.events import generate_events_base, generate_events_final  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402

ERAS = {"old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                pd.Timestamp("2021-06-18T23:59:00Z")),
        "new": (pd.Timestamp("2021-06-19T00:00:00Z"), None)}   # None -> data end
WARMUP = pd.Timedelta(days=100)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("m1_path", nargs="?", default=None)
    ap.add_argument("--variant", choices=("final", "base"), default=None)
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--fill", choices=("gap_open", "barrier_level"), default=None)
    args = ap.parse_args()

    cfg = load_config(args.config)
    variant = args.variant or cfg.strategy.variant
    fill_mode = args.fill or cfg.exits.fill_mode
    m1_path = Path(args.m1_path) if args.m1_path else resolve_path(cfg, cfg.data.m1_path)
    assert m1_path.exists(), f"no data at {m1_path}"

    print(f"goldbot phase 1 | variant={variant} fill={fill_mode} "
          f"day_boundary={cfg.pivots.day_boundary}")
    if cfg.pivots.day_boundary != "utc00":
        print("  !! WARNING: non-UTC00 day boundary — pivots will NOT match "
              "any validated historical result")

    cost_model = CostModel(cfg)
    print(cost_model.describe())

    print(f"loading {m1_path} ...", flush=True)
    m1_full = load_ohlc(m1_path, data_tz=cfg.data.data_tz)
    data_end = m1_full.index[-1]
    print(f"  {len(m1_full):,} M1 bars, {m1_full.index[0]} -> {data_end}")

    all_trades = []
    for era, (start, end) in ERAS.items():
        end = end or data_end
        if start > data_end:
            continue
        m1 = m1_full[(m1_full.index >= start - WARMUP) & (m1_full.index <= end)]
        h1 = resample_ohlc(m1, "1h")
        h4 = resample_ohlc(m1, "4h")
        d1 = resample_d1_utc(m1)
        atr_h1 = wilder_atr(h1, cfg.exits.final.atr.period)

        if variant == "final":
            e = cfg.exits.final
            events = generate_events_final(h1, h4, d1, atr_h1, cfg, start, end)
            trades = run_exits(
                m1, events, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr,
                time_stop_h=e.time_stop_h, fill_mode=fill_mode,
                bail_enabled=e.bail.enabled,
                hivol_half_x=e.bail.hivol_half_x,
                lovol_bail_h=e.bail.lovol_bail_h,
                lovol_bail_x=e.bail.lovol_bail_x)
        else:
            e = cfg.exits.base
            events = generate_events_base(h4, d1, atr_h1, h1.index, cfg,
                                          start, end)
            trades = run_exits(
                m1, events, tp_usd=e.tp_usd, sl_usd=e.sl_usd,
                time_stop_h=e.time_stop_h, fill_mode=fill_mode,
                bail_enabled=e.bail.enabled)
        trades["era"] = era
        all_trades.append(trades)
        print(f"  [{era}] {len(events)} events -> {len(trades)} trades "
              f"({int(trades['ambiguous'].sum())} ambiguous bars)")

    trades = pd.concat(all_trades, ignore_index=True)
    n_amb = int(trades["ambiguous"].sum())
    print(f"\ntotal {len(trades)} trades | ambiguous TP+SL bars: {n_amb} "
          f"({n_amb / max(1, len(trades)):.1%}) — resolved as stops")

    # ── cost regimes ────────────────────────────────────────────────────
    era_pf = {}
    netted = {}
    print("\n== era stats per cost regime (per 1.0 lot, pre-leverage) ==")
    for regime in REGIMES:
        t = net_trades(trades, cost_model, regime)
        netted[regime] = t
        print(f"[{regime}] (breakeven ~${cost_model.breakeven_move_usd(regime):.2f}/oz)")
        for era in t["era"].unique():
            s = stats(t[t.era == era]["net_usd"])
            era_pf[(regime, era)] = s["pf"]
            print(f"  {era}: {fmt_stats(s)}")

    print("\n== per-year (realistic regime) ==")
    yr = per_year(netted["realistic"])
    for y, row in yr.iterrows():
        print(f"  {y}: n={row['n']:>3.0f} wr={row['wr']:.1%} "
              f"pf={row['pf']:.2f} net=${row['net_usd']:,.0f}")

    # ── CPCV ─────────────────────────────────────────────────────────────
    ccfg = cfg.cpcv
    lfm = ccfg.l_feature_max_h
    if ccfg.strict_regime_purge:
        lfm = max(lfm, cfg.exits.final.atr.regime_median_bars)
    splitter = CombinatorialPurgedCV(
        n_groups=ccfg.n_groups, k_test=ccfg.k_test, tau_max=ccfg.tau_max_h,
        embargo=ccfg.embargo_h, l_feature_max=lfm)
    print(f"\n== CPCV ({ccfg.n_groups} groups, k={ccfg.k_test} -> 15 splits / "
          f"5 paths; purge tau={ccfg.tau_max_h}h, embargo={ccfg.embargo_h}h, "
          f"lookback={lfm}h) ==")
    cpcv_out = {}
    for regime in ("flat", "realistic"):
        rep = cpcv_report(netted[regime], splitter)
        cpcv_out[regime] = rep
        print(f"[{regime}] positive splits: {rep['positive_splits']}/{rep['n_splits']} | "
              f"split PF median={rep['median_split_pf']:.2f} "
              f"worst={rep['worst_split_pf']:.2f}")
        for p in rep["paths"]:
            print(f"    path {p['path']}: {fmt_stats(p)}")

    # ── GO/NO-GO ─────────────────────────────────────────────────────────
    pf_new = era_pf.get(("realistic", "new"), float("nan"))
    pf_old = era_pf.get(("realistic", "old"), float("nan"))
    ok, verdict = go_no_go(pf_new, pf_old)
    rep = cpcv_out["realistic"]
    majority = rep["positive_splits"] >= (rep["n_splits"] * 2) // 3 + 1
    print(f"\n{verdict}")
    print(f"CPCV gate: {'clear majority' if majority else 'NO majority'} of "
          f"purged splits positive ({rep['positive_splits']}/{rep['n_splits']})"
          f" — {'OK' if majority else 'regime luck risk, stop'}")
    print("REMINDER: cost matrix is a THIN sample; rerun after the full tick "
          "download before acting on this verdict.")

    # ── artifacts ────────────────────────────────────────────────────────
    results = ROOT / "results"
    results.mkdir(exist_ok=True)
    netted["realistic"].to_csv(results / f"trades_{variant}.csv", index=False)
    lines = [f"# goldbot phase 1 — {variant} / {fill_mode}",
             f"generated from {m1_path.name}, data end {data_end}", "",
             f"**{verdict}**",
             f"CPCV positive splits (realistic): "
             f"{rep['positive_splits']}/{rep['n_splits']}, "
             f"median PF {rep['median_split_pf']:.2f}, "
             f"worst {rep['worst_split_pf']:.2f}", "",
             "| regime | era | n | wr | pf | net |", "|---|---|---|---|---|---|"]
    for regime in REGIMES:
        for era in netted[regime]["era"].unique():
            s = stats(netted[regime][netted[regime].era == era]["net_usd"])
            lines.append(f"| {regime} | {era} | {s['n']} | {s['wr']:.1%} | "
                         f"{s['pf']:.2f} | ${s['net_usd']:,.0f} |")
    (results / f"phase1_report_{variant}.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(f"\nwrote {results / f'trades_{variant}.csv'} and "
          f"{results / f'phase1_report_{variant}.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
