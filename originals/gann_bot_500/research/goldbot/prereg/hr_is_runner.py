"""HR IS-only integration run — sizing + ER-regime router wired into the
conviction backtest. NO OOS DATA TOUCHED: everything past the IS cutoff is
dropped at load and never enters a statistic, a calibration, or a print.

Wiring per the integration task:
- ER at H1 bar t uses closes <= t only; the decision made at bar t applies
  to the event whose signal IS that bar's close (existing pivot-entry
  convention: decide on closed bar, fill next M1 open).
- Thresholds via calibrate_thresholds on the IS ER distribution only;
  PLACEHOLDER_THRESHOLDS never used.
- position_size replaces fixed lots; 0.0 -> SKIP (never clamped up).
- Diagnostics: flip_count, % bars per state, trades per state.
Modules are imported by explicit file location so prereg/regime.py (the H2
vol filter, a DIFFERENT module) can never shadow modules/regime.py.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULES = ROOT / "modules"
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT))

from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.data import load_ohlc, resample_ohlc  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"mod_{name}",
                                                  MODULES / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[f"mod_{name}"] = m       # dataclasses resolves __module__ here
    spec.loader.exec_module(m)
    return m


regime = _load("regime")
sizing = _load("sizing")

START = pd.Timestamp("2015-06-19T00:00:00Z")


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def sized_walk(trades: pd.DataFrame, mcfg, spec) -> dict:
    """Chronological equity walk with position_size; 0.0 lots -> skip."""
    eq = float(mcfg.sizing.start_equity)
    rf = float(mcfg.sizing.risk_fraction)
    mult = float(mcfg.sizing.stop_atr_mult)
    skipped = 0
    pnls = []
    for r in trades.sort_values("event_ts").itertuples():
        stop = mult * float(r.atr)
        lots = sizing.position_size(eq, rf, stop, spec)
        if lots == 0.0:
            skipped += 1
            continue
        assert lots * stop * spec.value_per_unit_per_lot <= eq * rf + 1e-6
        pnl = float(r.net_med) * lots            # net scales ~linearly per lot
        pnls.append(pnl)
        eq += pnl
    p = np.array(pnls)
    return {"final_equity": round(eq, 2), "n_taken": len(p),
            "n_skipped_zero_lots": skipped, "sized_pf": pf(p),
            "sized_net": round(float(p.sum()), 2) if len(p) else 0.0}


def main() -> int:
    cfg = load_config(ROOT / "config.yaml")
    mcfg = cfg.modules
    ss = mcfg.sizing.symbol_spec
    spec = sizing.SymbolSpec(tick_size=ss.tick_size, tick_value=ss.tick_value,
                             volume_step=ss.volume_step,
                             volume_min=ss.volume_min, volume_max=ss.volume_max)

    trades = pd.read_csv(RESULTS / "verdict_trades.csv",
                         parse_dates=["event_ts"])
    data_end = trades.event_ts.max()
    cutoff = START + float(mcfg.is_fraction) * (data_end - START)
    is_trades = trades[trades.event_ts <= cutoff].copy()
    n_dropped = len(trades) - len(is_trades)
    del trades                                   # OOS rows leave scope here
    print(f"IS cutoff {cutoff} | IS trades {len(is_trades)} "
          f"(OOS rows dropped unseen: {n_dropped})")

    print("building H1 bars + ER + regime (IS only) ...", flush=True)
    m1 = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                   data_tz=cfg.data.data_tz,
                   start_utc=START - pd.Timedelta(days=10),
                   end_utc=cutoff)               # OOS bars never loaded
    h1 = resample_ohlc(m1, "1h")
    er = regime.efficiency_ratio(h1["close"], int(mcfg.er_window))
    thr = regime.calibrate_thresholds(
        er, mr_enter_q=mcfg.calib_quantiles.mr_enter_q,
        mr_exit_q=mcfg.calib_quantiles.mr_exit_q,
        mom_exit_q=mcfg.calib_quantiles.mom_exit_q,
        mom_enter_q=mcfg.calib_quantiles.mom_enter_q)
    states = regime.classify_series(er, thr, int(mcfg.confirm_bars))
    print(f"calibrated thresholds (IS only): {thr}")

    # decision at bar t (close time = index + 1h) applies to the event whose
    # signal time equals that close — same-bar close, next-M1-open fill.
    close_time = h1.index + pd.Timedelta(hours=1)
    state_at_close = pd.Series(states.values, index=close_time)
    is_trades["regime"] = state_at_close.reindex(is_trades.event_ts).values
    n_unmatched = int(is_trades.regime.isna().sum())
    assert n_unmatched == 0, f"{n_unmatched} events missing a regime bar"

    pct_bars = states.value_counts(normalize=True).round(4).to_dict()
    trades_per_state = is_trades.regime.value_counts().to_dict()
    flips = regime.flip_count(states)
    print(f"diagnostics: flips={flips} | % bars {pct_bars} | "
          f"trades per state {trades_per_state}")

    rows = {}
    variants = {"routing_OFF": None,
                "route_MOMENTUM": ["MOMENTUM"],
                "route_MEAN_REVERSION": ["MEAN_REVERSION"],
                "route_NEUTRAL": ["NEUTRAL"]}
    for name, allowed in variants.items():
        t = is_trades if allowed is None else \
            is_trades[is_trades.regime.isin(allowed)]
        s = sized_walk(t, mcfg, spec)
        rows[name] = {"n": int(len(t)), "pf_1lot": pf(t.net_med),
                      "net_1lot": round(float(t.net_med.sum()), 2), **s}
        print(f"  {name:>22}: n={len(t):>3} PF(1lot)={rows[name]['pf_1lot']:.3f} "
              f"net(1lot)=${rows[name]['net_1lot']:,.0f} | sized: "
              f"PF={s['sized_pf']:.3f} net=${s['sized_net']:,.0f} "
              f"eq ${s['final_equity']:,.0f} skip0={s['n_skipped_zero_lots']}")

    manifest = {
        "is_cutoff": str(cutoff), "is_fraction": float(mcfg.is_fraction),
        "n_is_trades": int(len(is_trades)), "oos_rows_dropped": n_dropped,
        "er_window": int(mcfg.er_window), "confirm_bars": int(mcfg.confirm_bars),
        "calib_quantiles": mcfg.calib_quantiles.raw(),
        "thresholds": {"enter_mr": thr.enter_mr, "exit_mr": thr.exit_mr,
                       "exit_mom": thr.exit_mom, "enter_mom": thr.enter_mom},
        "route_pivot_in": list(mcfg.route_pivot_in),
        "symbol_spec": ss.raw(), "sizing": {
            "risk_fraction": float(mcfg.sizing.risk_fraction),
            "start_equity": float(mcfg.sizing.start_equity),
            "stop_atr_mult": float(mcfg.sizing.stop_atr_mult)},
        "diagnostics": {"flip_count": flips, "pct_bars_per_state": pct_bars,
                        "trades_per_state": {k: int(v) for k, v
                                             in trades_per_state.items()}},
        "comparison_IS_only": rows,
    }
    (RESULTS / "HR_is_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\nmanifest -> {RESULTS / 'HR_is_manifest.json'} "
          f"(NO OOS data touched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
