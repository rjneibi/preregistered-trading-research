"""HSW verdict run — intraday sweep-and-reclaim at PDH/PDL (frozen prereg).

Implements HSW_PREREGISTRATION.md (freeze 2f7599a). Implementation pins made
at RUNNER-BUILD time, before any result was seen (disclosed here, not in the
frozen doc):
  * Trading-day hygiene: days with < 300 M1 bars dropped (HCRT convention);
    PDH/PDL come from the previous KEPT trading day.
  * One-sidedness "penetrated earlier in day T" is pinned STRICT: the signal
    is void if the opposite level was penetrated at any bar at-or-before the
    reclaim bar.
  * Level spent after its FIRST penetration episode of the day, whether or
    not that episode produced a valid signal (no second-episode candidates).
  * Depth is measured from penetration-start through the reclaim bar
    inclusive (lows after reclaim do not count).
  * Reclaim window: reclaim-bar OPEN time <= penetration-start OPEN + 60 min.
  * The anti-scalp target guard (mid - entry < 0.5*ATR voids ALL arms) is
    evaluated at the actual entry-bar open; voided events are removed from
    every trial column AND from the mirror arm (entry parity), but NOT from
    the touch-baseline (whose entries do not depend on a reclaim).
  * Gate-2 mechanism control and gate-3 mirror both use the E2 exit family at
    the primary depth d=0.15 (exit family held constant; HCRT convention).
  * Cost stress regime is the matrix 'worst' (p95) — STRICTER than the frozen
    p90 wording; if gate 6 is the SOLE failing gate a p90 interpolation
    sensitivity must be run before verdict.
  * PBO rows are DAILY net-$ sums (zero-filled) over the 6 selectable
    columns, S=8, embargo 24h; DSR on per-trade net returns, trial_srs = all
    6 selectable trials.

Run:  .venv/Scripts/python prereg/hsw_runner.py
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
from goldbot.data import load_ohlc, resample_ohlc, resample_d1_utc, \
    wilder_atr  # noqa: E402
from goldbot.dsr import dsr, pbo_cscv, sharpe  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402

ERA_SPLIT = pd.Timestamp("2021-06-19T00:00:00Z")
MIN_D1_BARS = 300
DEPTHS = (0.05, 0.15, 0.30)          # the ONLY searched parameter
PRIMARY_DEPTH = 0.15
SESSION_H = (7, 19)                  # penetration-start bar-open hour, incl.
RECLAIM_MIN = 60
FLOOR_ATR = 0.5                      # anti-scalp SL floor and target guard
K_TP, K_SL, TIME_STOP_H = 0.8, 2.4, 24


def pf(x) -> float:
    x = np.asarray(x, float)
    if len(x) == 0:
        return 0.0                   # empty set must never look like a pass
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else (float("inf") if w > 0 else 0.0)


def build_days(m1: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    d1 = resample_d1_utc(m1)
    counts = m1.resample("1D", label="left", closed="left").size()
    counts = counts.reindex(d1.index).fillna(0)
    keep = counts >= MIN_D1_BARS
    return d1[keep], int((~keep).sum())


def _first_episode(day: pd.DataFrame, level: float, side: int):
    """First penetration episode of `level` on `day`. side=+1 -> PDL sweep
    (lows below), side=-1 -> PDH sweep (highs above). Returns None or dict
    with i_pen, i_rec (None if no reclaim in window), extreme, times."""
    lo = day["low"].to_numpy(float)
    hi = day["high"].to_numpy(float)
    cl = day["close"].to_numpy(float)
    pen = (lo < level) if side > 0 else (hi > level)
    if not pen.any():
        return None
    i_pen = int(np.argmax(pen))
    t_pen = day.index[i_pen]
    t_lim = t_pen + pd.Timedelta(minutes=RECLAIM_MIN)
    i_rec = None
    for i in range(i_pen, len(day)):
        if day.index[i] > t_lim:
            break
        if (cl[i] > level) if side > 0 else (cl[i] < level):
            i_rec = i
            break
    if i_rec is None:
        return {"i_pen": i_pen, "t_pen": t_pen, "i_rec": None,
                "extreme": None}
    ext = float(lo[i_pen:i_rec + 1].min()) if side > 0 \
        else float(hi[i_pen:i_rec + 1].max())
    return {"i_pen": i_pen, "t_pen": t_pen, "i_rec": i_rec,
            "t_rec": day.index[i_rec], "extreme": ext}


def find_events(m1: pd.DataFrame, d1: pd.DataFrame,
                atr_h1: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Scan every trading day for sweep-reclaim candidates (both sides) and
    touch-baseline events. Depth filtering happens later, per trial.
    Returns (candidates, touch_events, diag_counts)."""
    d1_atr = wilder_atr(d1, 14)
    d1_atr_pct = (d1_atr / d1["close"])
    h1_t = atr_h1.index
    day_idx = d1.index
    m1_naive = m1.index
    cand, touch = [], []
    diag = {"days_scanned": 0, "no_reclaim": 0, "both_sides_void": 0,
            "no_atr": 0, "asia_window": 0}

    day_starts = m1_naive.searchsorted(day_idx)
    day_ends = m1_naive.searchsorted(day_idx + pd.Timedelta(days=1))

    for k in range(1, len(day_idx)):
        pdh = float(d1["high"].iloc[k - 1])
        pdl = float(d1["low"].iloc[k - 1])
        if np.isnan(d1_atr.iloc[k - 1]):
            continue
        day = m1.iloc[day_starts[k]:day_ends[k]]
        if not len(day):
            continue
        diag["days_scanned"] += 1
        atr_pct_t1 = float(d1_atr_pct.iloc[k - 1])

        eps = {s: _first_episode(day, pdl if s > 0 else pdh, s)
               for s in (1, -1)}

        def h1_atr_at(ts) -> float:
            j = h1_t.searchsorted(ts)          # last COMPLETED H1 bar < ts
            if j - 2 < 0:
                return float("nan")
            return float(atr_h1.iloc[j - 2]) if h1_t[j - 1] + \
                pd.Timedelta(hours=1) > ts else float(atr_h1.iloc[j - 1])

        # touch-baseline: first penetration of either level, session-gated,
        # one trade/day, fade direction, no reclaim requirement.
        tb = [(e["t_pen"], s) for s, e in eps.items() if e is not None]
        if tb:
            tb.sort(key=lambda x: x[0])
            t0, s0 = tb[0]
            if SESSION_H[0] <= t0.hour <= SESSION_H[1]:
                a = h1_atr_at(t0)
                if not np.isnan(a):
                    touch.append({"event_ts": t0 + pd.Timedelta(minutes=1),
                                  "side": s0, "atr": a, "hivol": False,
                                  "atr_pct": atr_pct_t1})

        # sweep-reclaim candidates, chronological by reclaim time
        evs = []
        for s, e in eps.items():
            if e is None:
                continue
            if e["i_rec"] is None:
                diag["no_reclaim"] += 1
                continue
            opp = eps[-s]
            if opp is not None and opp["t_pen"] <= e["t_rec"]:
                diag["both_sides_void"] += 1
                continue
            if not (SESSION_H[0] <= e["t_pen"].hour <= SESSION_H[1]):
                diag["asia_window"] += 1
                continue
            a = h1_atr_at(e["t_pen"])
            if np.isnan(a):
                diag["no_atr"] += 1
                continue
            level = pdl if s > 0 else pdh
            evs.append({
                "event_ts": e["t_rec"] + pd.Timedelta(minutes=1),
                "side": s, "atr": a, "hivol": False,
                "atr_pct": atr_pct_t1,
                "depth": (level - e["extreme"]) if s > 0
                         else (e["extreme"] - level),
                "extreme": e["extreme"], "pdh": pdh, "pdl": pdl,
                "mid": (pdh + pdl) / 2.0,
            })
        evs.sort(key=lambda r: r["event_ts"])
        cand.extend(evs)                        # 1/day applied per trial later

    return pd.DataFrame(cand), pd.DataFrame(touch), diag


def entry_guard(m1: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Evaluate the anti-scalp target guard at the actual entry-bar open and
    attach entry px + E1 barrier distances. Voided rows dropped (all arms)."""
    if not len(cand):
        return cand.assign(entry_px=[], tp_d=[], sl_d=[])
    t = m1.index
    o = m1["open"].to_numpy(float)
    rows = []
    for ev in cand.itertuples(index=False):
        j = t.searchsorted(ev.event_ts)
        if j >= len(t):
            continue
        entry = float(o[j])
        tp_d = (ev.mid - entry) if ev.side > 0 else (entry - ev.mid)
        if tp_d < FLOOR_ATR * ev.atr:           # guard: voids ALL arms
            continue
        raw_sl = (entry - ev.extreme) if ev.side > 0 else (ev.extreme - entry)
        sl_d = max(raw_sl, FLOOR_ATR * ev.atr)
        rows.append({**ev._asdict(), "entry_px": entry,
                     "tp_d": tp_d, "sl_d": sl_d})
    return pd.DataFrame(rows)


def one_per_day(evts: pd.DataFrame) -> pd.DataFrame:
    if not len(evts):
        return evts
    d = evts.sort_values("event_ts")
    return d.groupby(d.event_ts.dt.normalize(), as_index=False).first()


def run_e1(m1: pd.DataFrame, sigs: pd.DataFrame) -> pd.DataFrame:
    out = []
    t = m1.index
    for ev in sigs.itertuples(index=False):
        j0 = t.searchsorted(ev.event_ts)
        if j0 >= len(t):
            continue
        win = m1.iloc[j0:t.searchsorted(ev.event_ts + pd.Timedelta(hours=26))]
        tr = run_exits(win, pd.DataFrame([ev._asdict()]), tp_usd=float(ev.tp_d),
                       sl_usd=float(ev.sl_d), time_stop_h=TIME_STOP_H,
                       fill_mode="gap_open", bail_enabled=False)
        if len(tr):
            tr["atr_pct"] = ev.atr_pct
            out.append(tr)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def run_e2(m1: pd.DataFrame, sigs: pd.DataFrame) -> pd.DataFrame:
    if not len(sigs):
        return pd.DataFrame()
    tr = run_exits(m1, sigs, k_tp_atr=K_TP, k_sl_atr=K_SL,
                   time_stop_h=TIME_STOP_H, fill_mode="gap_open",
                   bail_enabled=False)
    if not len(tr):
        return tr
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
    h1 = resample_ohlc(m1, "1h")
    atr_h1 = wilder_atr(h1, 14)
    print(f"M1 {m1.index[0]} .. {m1.index[-1]}  ({len(m1):,} bars); "
          f"D1 trading days: {len(d1):,} (dropped {n_partial} partial)")

    atr_pct_series = (wilder_atr(d1, 14) / d1["close"]).dropna()
    VOL_MEDIAN = float(atr_pct_series.median())
    print(f"D1 ATR% median (vol axis): {VOL_MEDIAN*100:.4f}%")

    cand, touch, diag = find_events(m1, d1, atr_h1)
    print(f"\ncandidates (pre-guard, pre-depth): {len(cand)}  "
          f"touch-baseline events: {len(touch)}  diag: {diag}")
    if not len(cand):
        print("\n== HSW INSUFFICIENT POWER: zero candidates ==")
        return 1
    cand = entry_guard(m1, cand)
    print(f"candidates after anti-scalp guard: {len(cand)}")

    # per-depth selectable signal sets (1/day applied AFTER depth filter)
    sig = {d: one_per_day(cand[cand.depth >= d * cand.atr]) for d in DEPTHS}
    for d in DEPTHS:
        s = sig[d]
        print(f"  d={d:.2f}: n={len(s)} "
              f"(long={int((s.side > 0).sum()) if len(s) else 0}, "
              f"short={int((s.side < 0).sum()) if len(s) else 0})")

    # ── arms ────────────────────────────────────────────────────────────
    arms = {}
    for d in DEPTHS:
        arms[f"E1_d{d:.2f}"] = run_e1(m1, sig[d])
        arms[f"E2_d{d:.2f}"] = run_e2(m1, sig[d])
    mirror = sig[PRIMARY_DEPTH].assign(side=-sig[PRIMARY_DEPTH].side)
    arms["mirror_E2"] = run_e2(m1, mirror)
    arms["touch_baseline_E2"] = run_e2(m1, one_per_day(touch))
    arms = {k: tag(v, VOL_MEDIAN, cm) for k, v in arms.items()}

    p = arms[f"E1_d{PRIMARY_DEPTH:.2f}"]
    e2p = arms[f"E2_d{PRIMARY_DEPTH:.2f}"]
    mir = arms["mirror_E2"]
    tb = arms["touch_baseline_E2"]

    # ── 2x2 era table ───────────────────────────────────────────────────
    print("\n== 2x2 era table (net realistic PF | n), primary vs mirror ==")
    table = {}
    for era in ("old", "new"):
        for hv in (False, True):
            cell = f"{era}/{'HIvol' if hv else 'LOvol'}"
            sel = lambda t: t[(t.era == era) & (t.hivol_cell == hv)] \
                if len(t) else t
            c_p, c_e2, c_m = sel(p), sel(e2p), sel(mir)
            table[cell] = {
                "n": int(len(c_p)),
                "pf_E1": pf(c_p.net_real) if len(c_p) else None,
                "pf_E2": pf(c_e2.net_real) if len(c_e2) else None,
                "pf_mirror_E2": pf(c_m.net_real) if len(c_m) else None,
            }
            print(f"  {cell:10s} n={table[cell]['n']:4d}  "
                  f"E1={table[cell]['pf_E1']}  E2={table[cell]['pf_E2']}  "
                  f"mirror={table[cell]['pf_mirror_E2']}")

    # ── gates ───────────────────────────────────────────────────────────
    def era_pf(t, era):
        s = t[t.era == era] if len(t) else t
        return pf(s.net_real) if len(s) else float("nan")

    sel_keys = [f"{e}_d{d:.2f}" for e in ("E1", "E2") for d in DEPTHS]
    trial_srs = [sharpe(arms[k].net_real) if len(arms[k]) else 0.0
                 for k in sel_keys]

    all_days = pd.date_range(d1.index[0], d1.index[-1], freq="D")
    mat = np.column_stack([daily_series(arms[k], all_days) for k in sel_keys])
    times = (all_days.view("int64") // 3_600_000_000_000).astype(float)
    pbo = pbo_cscv(mat, s=8, times=times, embargo_h=24.0)
    print(f"\nPBO (S=8, C(8,4)=70, embargo 24h): {pbo['pbo']:.3f} "
          f"(lambda_mean {pbo['lambda_mean']:+.2f})")

    def all_gates(primary: pd.DataFrame) -> tuple[dict, dict]:
        d = dsr(primary.net_real.to_numpy(), trial_srs=trial_srs) \
            if len(primary) else {"dsr": 0.0, "sr": 0.0, "sr0": 0.0,
                                  "skew": 0.0, "kurt_raw": 0.0, "n_obs": 0}
        g = {
            "g0_power_n_ge_100": len(primary) >= 100,
            "g1_pf_ge_1.30": pf(primary.net_real) >= 1.30 if len(primary)
            else False,
            "g2_uplift_ge_0.10": (pf(e2p.net_real) - pf(tb.net_real)) >= 0.10
            if len(e2p) and len(tb) else False,
            "g3_era_ge_1.00_both": (era_pf(primary, "old") >= 1.0
                                    and era_pf(primary, "new") >= 1.0),
            "g3_no_mirror_inversion": pf(mir.net_real) <= pf(e2p.net_real)
            if len(mir) and len(e2p) else True,
            "g4_dsr_ge_0.95": d["dsr"] >= 0.95,
            "g5_pbo_lt_0.50": pbo["pbo"] < 0.50,
            "g6_p95_stress_pf_ge_1.15": pf(primary.net_p95) >= 1.15
            if len(primary) else False,
        }
        return g, d

    g1, d1s = all_gates(p)
    print(f"\n== gates (primary E1 d={PRIMARY_DEPTH}) ==")
    for k, v in g1.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    print(f"  DSR detail: SR={d1s['sr']:+.4f} SR0={d1s['sr0']:+.4f} "
          f"skew={d1s['skew']:+.2f} kurt={d1s['kurt_raw']:.1f} "
          f"n={d1s['n_obs']} -> DSR={d1s['dsr']:.4f}")

    # displacement across the other 5 selectable cells
    displace_by, disp_gates = None, {}
    for k in sel_keys:
        if k == f"E1_d{PRIMARY_DEPTH:.2f}":
            continue
        gk, _ = all_gates(arms[k])
        disp_gates[k] = {kk: bool(vv) for kk, vv in gk.items()}
        if (all(gk.values())
                and era_pf(arms[k], "old") >= era_pf(p, "old") + 0.05
                and era_pf(arms[k], "new") >= era_pf(p, "new") + 0.05):
            displace_by = k
            break
    print(f"\ndisplacement: {displace_by or 'none'}")

    if len(p) < 100 and displace_by is None:
        verdict = (f"HSW INSUFFICIENT POWER: n={len(p)} < 100 — line closed "
                   f"without edge claim (gate 0)")
    elif all(g1.values()) or displace_by:
        verdict = "HSW PASS: proceed ONLY to a Phase-2 DEMO ops prereg"
    else:
        verdict = ("HSW FAIL: intraday sweep-reclaim line on XAUUSD CLOSED — "
                   "no depth/session/window shopping, no level-definition "
                   "migration; reversal-at-levels family closed at every "
                   "free-data scale (with HCRT)")
    print(f"\n== {verdict} ==")

    def summ(t):
        return {"n": int(len(t)), "pf_real": pf(t.net_real) if len(t) else None,
                "pf_p95": pf(t.net_p95) if len(t) else None,
                "net_usd": float(t.net_real.sum()) if len(t) else 0.0,
                "pf_old": era_pf(t, "old") if len(t) else None,
                "pf_new": era_pf(t, "new") if len(t) else None}

    out = {"freeze": "2f7599a", "vol_median_atr_pct": VOL_MEDIAN,
           "n_partial_days_dropped": n_partial, "diag": diag,
           "arms": {k: summ(v) for k, v in arms.items()},
           "table_2x2": table,
           "gates_primary": {k: bool(v) for k, v in g1.items()},
           "gates_displacement": disp_gates,
           "displace_by": displace_by, "dsr_primary": d1s,
           "pbo": pbo, "verdict": verdict}
    (RESULTS / "HSW_run.json").write_text(json.dumps(out, indent=1,
                                                     default=str))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  HSW VERDICT (frozen prereg "
                f"2f7599a): {verdict}\n")
        for k, v in g1.items():
            f.write(f"            HSW gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            primary {summ(p)}; mirror {summ(mir)}; "
                f"touch-baseline {summ(tb)}; predictions (blind) Rashed "
                f"PASS-0.80(first), Claude FAIL-0.80 — FIRST DISAGREEMENT\n")
    print(f"\nresults -> {RESULTS / 'HSW_run.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
