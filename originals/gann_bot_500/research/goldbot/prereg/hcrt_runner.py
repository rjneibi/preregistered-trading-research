"""HCRT verdict run — CRT sweep-and-reject on D1 (frozen prereg, verbatim).

Implements HCRT_PREREGISTRATION.md (freeze c5e042d). Implementation pins made
at RUNNER-BUILD time, before any result was seen (disclosed here, not in the
frozen doc):
  * Trading-day hygiene: D1 rows with < 300 M1 bars (Sunday/holiday partials)
    are NOT trading days — dropped from the C1/C2/T sequence, count disclosed.
  * Gate-3 inversion check + gate-2 mechanism control both compare arms under
    the E2 exit family (exit set held constant; E1's pattern-native barriers
    have no defined mirror).
  * EMA200 warmup: signals require >= 200 completed trading days of history.
  * E1 degenerate events (entry gaps at/through a barrier: tp or sl distance
    <= 0) are skipped and counted — a live order could not have been placed.
  * Cost stress regime is the matrix 'worst' (p95) — STRICTER than the frozen
    p90 wording; a p95 PASS is a-fortiori a p90 pass. If gate 6 is the SOLE
    failing gate, a p90 interpolation sensitivity must be run before verdict.
  * PBO rows are DAILY net-$ sums (zero on non-trade days) per trial column,
    S=8, embargo 24h; DSR on per-trade net returns, trial_srs = [E1, E2].

Run:  .venv/Scripts/python prereg/hcrt_runner.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT))

from goldbot.backtest import net_trades  # noqa: E402
from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.costs import CostModel  # noqa: E402
from goldbot.data import load_ohlc, resample_d1_utc, wilder_atr  # noqa: E402
from goldbot.dsr import dsr, pbo_cscv, sharpe  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402

ERA_SPLIT = pd.Timestamp("2021-06-19T00:00:00Z")
MIN_D1_BARS = 300
EMA_WARMUP = 200
K_TP, K_SL, TIME_STOP_H = 0.8, 2.4, 24


def pf(x) -> float:
    x = np.asarray(x, float)
    if len(x) == 0:
        return 0.0                      # empty set must never look like a pass
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else (float("inf") if w > 0 else 0.0)


def build_days(m1: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    d1 = resample_d1_utc(m1)
    counts = m1.resample("1D", label="left", closed="left").size()
    counts = counts.reindex(d1.index).fillna(0)
    keep = counts >= MIN_D1_BARS
    return d1[keep], int((~keep).sum())


def find_signals(d1: pd.DataFrame, filtered: bool) -> pd.DataFrame:
    """One-sided D1 sweep + close-back-inside; reversion direction.
    filtered=True applies the pinned EMA200 HTF gate."""
    ema = d1["close"].ewm(span=200, adjust=False).mean()
    atr = wilder_atr(d1, 14)
    atr_pct = (atr / d1["close"])
    h, l, c = (d1[k].to_numpy(float) for k in ("high", "low", "close"))
    idx = d1.index
    rows = []
    for i in range(2, len(d1)):
        if i - 1 < EMA_WARMUP or np.isnan(atr.iloc[i - 1]):
            continue
        crh, crl = h[i - 2], l[i - 2]                     # C1 range
        c2h, c2l, c2c = h[i - 1], l[i - 1], c[i - 1]      # C2 manipulation
        inside = crl <= c2c <= crh
        long_sig = (c2l < crl) and inside and (c2h <= crh)
        short_sig = (c2h > crh) and inside and (c2l >= crl)
        if not (long_sig or short_sig):
            continue
        side = 1 if long_sig else -1
        bias_up = c2c > ema.iloc[i - 1]
        if filtered and ((side > 0) != bias_up):
            continue
        rows.append({
            "event_ts": idx[i], "side": side, "atr": float(atr.iloc[i - 1]),
            "hivol": bool(atr_pct.iloc[i - 1] > 0),       # placeholder, set below
            "atr_pct": float(atr_pct.iloc[i - 1]),
            "crh": crh, "crl": crl, "sweep_px": c2l if long_sig else c2h,
        })
    return pd.DataFrame(rows)


def bias_days(d1: pd.DataFrame) -> pd.DataFrame:
    """Bias-only baseline: EVERY eligible day-T open in the EMA200 direction."""
    ema = d1["close"].ewm(span=200, adjust=False).mean()
    atr = wilder_atr(d1, 14)
    atr_pct = atr / d1["close"]
    rows = []
    for i in range(2, len(d1)):
        if i - 1 < EMA_WARMUP or np.isnan(atr.iloc[i - 1]):
            continue
        diff = d1["close"].iloc[i - 1] - ema.iloc[i - 1]
        if diff == 0:
            continue
        rows.append({"event_ts": d1.index[i], "side": 1 if diff > 0 else -1,
                     "atr": float(atr.iloc[i - 1]), "hivol": False,
                     "atr_pct": float(atr_pct.iloc[i - 1])})
    return pd.DataFrame(rows)


def run_e1(m1: pd.DataFrame, sigs: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Pattern-native exits: TP = opposite boundary, SL = sweep extreme,
    per-event absolute barriers via per-event fixed-$ distances."""
    out, degenerate = [], 0
    t = m1.index
    for ev in sigs.itertuples(index=False):
        j0 = t.searchsorted(ev.event_ts)
        if j0 >= len(t):
            continue
        win = m1.iloc[j0:t.searchsorted(ev.event_ts + pd.Timedelta(hours=26))]
        entry = float(win["open"].iloc[0])
        tp_d = (ev.crh - entry) if ev.side > 0 else (entry - ev.crl)
        sl_d = (entry - ev.sweep_px) if ev.side > 0 else (ev.sweep_px - entry)
        if tp_d <= 0 or sl_d <= 0:
            degenerate += 1
            continue
        tr = run_exits(win, pd.DataFrame([ev._asdict()]), tp_usd=tp_d,
                       sl_usd=sl_d, time_stop_h=TIME_STOP_H,
                       fill_mode="gap_open", bail_enabled=False)
        if len(tr):
            tr["atr_pct"] = ev.atr_pct
            out.append(tr)
    return (pd.concat(out, ignore_index=True) if out else pd.DataFrame(),
            degenerate)


def run_e2(m1: pd.DataFrame, sigs: pd.DataFrame) -> pd.DataFrame:
    tr = run_exits(m1, sigs, k_tp_atr=K_TP, k_sl_atr=K_SL,
                   time_stop_h=TIME_STOP_H, fill_mode="gap_open",
                   bail_enabled=False)
    return tr.merge(sigs[["event_ts", "atr_pct"]], on="event_ts", how="left")


def tag(trades: pd.DataFrame, vol_median: float, cm: CostModel) -> pd.DataFrame:
    if not len(trades):
        return trades
    t = net_trades(trades, cm, "realistic").rename(columns={
        "net_usd": "net_real", "cost_usd": "cost_real"})
    t2 = net_trades(trades, cm, "worst")
    t["net_p95"] = t2["net_usd"].to_numpy()
    t["era"] = np.where(t.event_ts < ERA_SPLIT, "old", "new")
    t["hivol_cell"] = t.atr_pct > vol_median
    return t


def daily_series(trades: pd.DataFrame, all_days: pd.DatetimeIndex) -> np.ndarray:
    if not len(trades):
        return np.zeros(len(all_days))
    s = trades.groupby(trades.event_ts.dt.normalize())["net_real"].sum()
    return s.reindex(all_days).fillna(0.0).to_numpy()


def main() -> int:
    cfg = load_config(ROOT / "config.yaml")
    cm = CostModel(cfg)
    print(cm.describe())
    m1_path = resolve_path(cfg, cfg.data.m1_path)
    print(f"\nloading {m1_path.name} ...", flush=True)
    m1 = load_ohlc(m1_path, data_tz=cfg.data.data_tz)
    d1, n_partial = build_days(m1)
    print(f"M1 {m1.index[0]} .. {m1.index[-1]}  ({len(m1):,} bars); "
          f"D1 trading days: {len(d1):,} (dropped {n_partial} partial days "
          f"< {MIN_D1_BARS} bars)")

    atr_pct_series = (wilder_atr(d1, 14) / d1["close"]).dropna()
    VOL_MEDIAN = float(atr_pct_series.median())
    print(f"D1 ATR% full-sample median (parameter-free vol axis): "
          f"{VOL_MEDIAN*100:.4f}%")

    sig_f = find_signals(d1, filtered=True)
    sig_r = find_signals(d1, filtered=False)
    print(f"\nsignals: raw={len(sig_r)}  filtered={len(sig_f)} "
          f"(long={int((sig_f.side > 0).sum()) if len(sig_f) else 0}, "
          f"short={int((sig_f.side < 0).sum()) if len(sig_f) else 0})")
    if len(sig_f) == 0:
        print("\n== HCRT INSUFFICIENT POWER: zero filtered signals ==")
        return 1

    # ── arms ────────────────────────────────────────────────────────────
    e1_f, dg_f = run_e1(m1, sig_f)
    e2_f = run_e2(m1, sig_f)
    e1_r, dg_r = run_e1(m1, sig_r)
    e2_r = run_e2(m1, sig_r)
    mirror = sig_f.assign(side=-sig_f.side)
    e2_m = run_e2(m1, mirror)
    bias = run_e2(m1, bias_days(d1))
    print(f"E1 degenerate skips: filtered={dg_f} raw={dg_r}")

    arms = {}
    for name, tr in (("E1_filtered", e1_f), ("E2_filtered", e2_f),
                     ("E1_raw", e1_r), ("E2_raw", e2_r),
                     ("mirror_E2", e2_m), ("bias_only_E2", bias)):
        arms[name] = tag(tr, VOL_MEDIAN, cm)

    p = arms["E1_filtered"]
    e2 = arms["E2_filtered"]
    mir = arms["mirror_E2"]
    bo = arms["bias_only_E2"]

    # ── 2x2 era table ───────────────────────────────────────────────────
    print("\n== 2x2 era table (net realistic PF | n), reversion vs mirror ==")
    table = {}
    for era in ("old", "new"):
        for hv in (False, True):
            cell = f"{era}/{'HIvol' if hv else 'LOvol'}"
            sel = lambda t: t[(t.era == era) & (t.hivol_cell == hv)] if len(t) else t
            c_p, c_e2, c_m = sel(p), sel(e2), sel(mir)
            table[cell] = {
                "n": int(len(c_p)),
                "pf_E1": pf(c_p.net_real) if len(c_p) else None,
                "pf_E2": pf(c_e2.net_real) if len(c_e2) else None,
                "pf_mirror_E2": pf(c_m.net_real) if len(c_m) else None,
            }
            print(f"  {cell:10s} n={table[cell]['n']:3d}  "
                  f"E1={table[cell]['pf_E1']}  E2={table[cell]['pf_E2']}  "
                  f"mirror={table[cell]['pf_mirror_E2']}")

    # ── gates ───────────────────────────────────────────────────────────
    def era_pf(t, era):
        s = t[t.era == era]
        return pf(s.net_real) if len(s) else float("nan")

    def all_gates(primary: pd.DataFrame, label: str) -> dict:
        d = dsr(primary.net_real.to_numpy(),
                trial_srs=[sharpe(p.net_real), sharpe(e2.net_real)])
        g = {
            "g0_power_n_ge_100": len(primary) >= 100,
            "g1_pf_ge_1.30": pf(primary.net_real) >= 1.30,
            "g2_uplift_ge_0.10": (pf(e2.net_real) - pf(bo.net_real)) >= 0.10,
            "g3_era_ge_1.00_both": (era_pf(primary, "old") >= 1.0
                                    and era_pf(primary, "new") >= 1.0),
            "g3_no_mirror_inversion": pf(mir.net_real) <= pf(e2.net_real),
            "g4_dsr_ge_0.95": d["dsr"] >= 0.95,
            "g6_p95_stress_pf_ge_1.15": pf(primary.net_p95) >= 1.15,
        }
        return g, d

    # PBO over the pinned 4-column matrix (daily net-$, zero-filled)
    all_days = pd.date_range(d1.index[EMA_WARMUP], d1.index[-1], freq="D")
    mat = np.column_stack([daily_series(arms[k], all_days) for k in
                           ("E1_filtered", "E2_filtered", "E1_raw", "E2_raw")])
    times = (all_days.view("int64") // 3_600_000_000_000).astype(float)
    pbo = pbo_cscv(mat, s=8, times=times, embargo_h=24.0)
    print(f"\nPBO (S=8, C(8,4)=70, embargo 24h): {pbo['pbo']:.3f} "
          f"(lambda_mean {pbo['lambda_mean']:+.2f})")

    g1, d1s = all_gates(p, "E1")
    g1["g5_pbo_lt_0.50"] = pbo["pbo"] < 0.50
    print(f"\n== gates (primary E1) ==")
    for k, v in g1.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  DSR detail: SR={d1s['sr']:+.4f} SR0={d1s['sr0']:+.4f} "
          f"skew={d1s['skew']:+.2f} kurt={d1s['kurt_raw']:.1f} "
          f"n={d1s['n_obs']} -> DSR={d1s['dsr']:.4f}")

    # displacement: E2 replaces E1 only if E2 clears EVERY gate AND beats
    # E1's gate-1 PF by >= +0.05 in both eras
    g2s, d2s = all_gates(e2, "E2")
    g2s["g5_pbo_lt_0.50"] = pbo["pbo"] < 0.50
    displace = (all(g2s.values())
                and era_pf(e2, "old") >= era_pf(p, "old") + 0.05
                and era_pf(e2, "new") >= era_pf(p, "new") + 0.05)
    print(f"\nE2 gates: { {k: bool(v) for k, v in g2s.items()} } "
          f"-> displaces E1: {displace}")

    if len(p) < 100 and not displace:
        verdict = (f"HCRT INSUFFICIENT POWER: n={len(p)} < 100 — line closed "
                   f"without edge claim (gate 0); reopen needs >=3y more D1")
    elif all(g1.values()) or displace:
        verdict = "HCRT PASS: proceed ONLY to a Phase-2 DEMO ops prereg"
    else:
        verdict = ("HCRT FAIL: ICT/CRT line on XAUUSD D1 CLOSED — no "
                   "threshold shopping, no timeframe migration; FVG/QT/SMT "
                   "inherit the negative prior")
    print(f"\n== {verdict} ==")

    def summ(t):
        return {"n": int(len(t)), "pf_real": pf(t.net_real) if len(t) else None,
                "pf_p95": pf(t.net_p95) if len(t) else None,
                "net_usd": float(t.net_real.sum()) if len(t) else 0.0,
                "pf_old": era_pf(t, "old") if len(t) else None,
                "pf_new": era_pf(t, "new") if len(t) else None}

    out = {"freeze": "c5e042d", "vol_median_atr_pct": VOL_MEDIAN,
           "n_partial_days_dropped": n_partial,
           "degenerate_e1": {"filtered": dg_f, "raw": dg_r},
           "arms": {k: summ(v) for k, v in arms.items()},
           "table_2x2": table, "gates_E1": {k: bool(v) for k, v in g1.items()},
           "gates_E2": {k: bool(v) for k, v in g2s.items()},
           "displace": bool(displace), "dsr_E1": d1s, "dsr_E2": d2s,
           "pbo": pbo, "verdict": verdict}
    (RESULTS / "HCRT_run.json").write_text(json.dumps(out, indent=1,
                                                      default=str))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  HCRT VERDICT (frozen prereg "
                f"c5e042d): {verdict}\n")
        for k, v in g1.items():
            f.write(f"            HCRT gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            E1 {summ(p)}; mirror {summ(mir)}; "
                f"bias {summ(bo)}; predictions (blind) Rashed FAIL-0.85, "
                f"Claude FAIL-0.80\n")
    print(f"\nresults -> {RESULTS / 'HCRT_run.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
