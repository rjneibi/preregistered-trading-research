"""
STATUS: RESEARCH-ONLY (2026-07-02). Round 2 of the optimization loop —
structural innovations on the R3/S3 flip scalp (no-Monday base):

  A. Trailing stops (let winners run past $8)
  B. End-of-day exit (range-expansion days close near extremes)
  C. Pyramid add-on at +$4
  D. Re-entry once after SL if the zone is still flipped on a later H4 close
  E. Overshoot (break-candle quality) filter diagnostic
  F. Far-Gann flip stream (R90+/S90+ degrees) as extra entries, both eras

Protocol: tune on TRAIN (first 70% of 2021-26), validate on TEST (last 30%).
The 2015-21 virgin holdout is spent ONCE at the end on the composite winner
(run separately). Costs 20 pts/trade (pyramid legs each pay costs).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs                                  # noqa: E402
from research.dr_backtest.data_prep import load_m1, resample_ohlc  # noqa: E402
from research.dr_backtest.metrics import basic_stats           # noqa: E402

OUT = REPO / "research" / "flip_scalp"
LOT = 100.0
COST = 20.0
HORIZON_H = 120


class SimX:
    """Extended M1 simulator: trailing, EOD exit, pyramid, re-entry."""

    def __init__(self, m1: pd.DataFrame, h4: pd.DataFrame):
        self.t = m1.index.values
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)
        self.h4_open = h4.index.values
        self.h4_close = h4["close"].to_numpy(float)

    # ------------------------------------------------------------------
    def _leg(self, sign, fi, fill, *, tp=None, sl=12.0, ts_h=24,
             trail_arm=None, trail_dist=None, eod=False):
        """One position leg from bar fi at price fill. Returns (pnl$, exit_i).
        tp None => no fixed TP (trail or eod governs)."""
        tp_px = fill + sign * tp if tp is not None else None
        stop = fill - sign * sl
        t_fill = self.t[fi]
        i_end = self.t.searchsorted(t_fill + np.timedelta64(HORIZON_H, "h"))
        i_ts = (self.t.searchsorted(t_fill + np.timedelta64(ts_h, "h"))
                if ts_h else i_end)
        if eod:
            day = t_fill.astype("datetime64[D]")
            i_ts = self.t.searchsorted(day + np.timedelta64(1, "D"))
            if i_ts <= fi:
                i_ts = self.t.searchsorted(day + np.timedelta64(2, "D"))
        i_end = min(max(i_end, fi + 1), len(self.t))
        best = fill
        for i in range(fi, i_end):
            hi, lo = self.h[i], self.l[i]
            if sign > 0:
                best = max(best, hi)
            else:
                best = min(best, lo)
            if trail_arm is not None and abs(best - fill) >= trail_arm:
                new_stop = best - sign * trail_dist
                if sign * (new_stop - stop) > 0:
                    stop = new_stop
            hit_sl = (lo <= stop) if sign > 0 else (hi >= stop)
            hit_tp = (tp_px is not None and
                      ((hi >= tp_px) if sign > 0 else (lo <= tp_px)))
            if hit_sl:                       # conservative: stop first
                return sign * (stop - fill) * 100 - COST, i
            if hit_tp:
                return sign * (tp_px - fill) * 100 - COST, i
            if i >= i_ts:
                return sign * (self.c[i] - fill) * 100 - COST, i
        return sign * (self.c[i_end - 1] - fill) * 100 - COST, i_end - 1

    # ------------------------------------------------------------------
    def run(self, e, *, tp=8.0, sl=12.0, ts_h=24, trail_arm=None,
            trail_dist=None, eod=False, pyramid_at=None,
            reenter=False, level=None):
        sign = 1 if e["direction"] == "BUY" else -1
        t0 = np.datetime64(pd.Timestamp(e["entry_ts"]))
        i0 = self.t.searchsorted(t0)
        if i0 >= len(self.t):
            return None
        fill = self.o[i0]
        pnl, exit_i = self._leg(sign, i0, fill, tp=tp, sl=sl, ts_h=ts_h,
                                trail_arm=trail_arm, trail_dist=trail_dist,
                                eod=eod)
        # pyramid: add a unit if price reaches fill + pyramid_at before exit
        if pyramid_at is not None:
            add_px = fill + sign * pyramid_at
            for i in range(i0, exit_i + 1):
                touched = (self.h[i] >= add_px) if sign > 0 else (self.l[i] <= add_px)
                if touched:
                    p2, _ = self._leg(sign, i, add_px, tp=tp, sl=sl,
                                      ts_h=ts_h, trail_arm=trail_arm,
                                      trail_dist=trail_dist, eod=eod)
                    pnl += p2
                    break
        # re-entry: if first leg lost, and a later H4 close (within 24h)
        # is still beyond the level, take one more identical trade
        if reenter and pnl < 0 and level is not None:
            t_exit = self.t[exit_i]
            k0 = self.h4_open.searchsorted(t_exit)
            for k in range(k0, min(k0 + 6, len(self.h4_open))):
                h4_close_t = self.h4_open[k] + np.timedelta64(4, "h")
                if h4_close_t > t_exit + np.timedelta64(24, "h"):
                    break
                still = (self.h4_close[k] < level if sign < 0
                         else self.h4_close[k] > level)
                if still:
                    j = self.t.searchsorted(h4_close_t)
                    if j < len(self.t):
                        p2, _ = self._leg(sign, j, self.o[j], tp=tp, sl=sl,
                                          ts_h=ts_h)
                        pnl += p2
                    break
        return pnl


# ─────────────────────────────────────────────────────────────────────────
def r3s3_level(e):
    lv = [l for s, l in zip(e["zone_sources"], e["zone_levels"])
          if s in ("R3", "S3")]
    return lv[0] if lv else e["zone_levels"][0]


def far_gann(e):
    for s in e["zone_sources"]:
        u = s.upper()
        if u[0] in "RS" and u[1:].isdigit() and int(u[1:]) >= 90:
            return True
    return False


def stats(name, pnls):
    p = [x for x in pnls if x is not None]
    if not p:
        return {"variant": name, "n": 0}
    s = basic_stats(p)
    return {"variant": name, "n": s["n"], "wr": s["win_rate"], "pf": s["pf"],
            "exp$": round(s["expectancy"] / 100 * LOT, 0),
            "net$": round(sum(p) / 100 * LOT, 0)}


def main():
    rfs.apply_config()
    m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS),
                 rfs.BT_END)
    h4 = resample_ohlc(m1, "4h")
    sim = SimX(m1, h4)

    ev = [json.loads(l) for l in (OUT / "events.jsonl").read_text().splitlines()]
    ev.sort(key=lambda x: x["entry_ts"])
    base = [e for e in ev if {"R3", "S3"} & set(e["zone_sources"])
            and pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]
    cut = int(round(len(base) * 0.7))
    train, test = base[:cut], base[cut:]
    print(f"base events: {len(base)} train={len(train)} test={len(test)}",
          flush=True)

    V = {
        "FINAL_v1 TP8/SL12/ts24": dict(),
        "trail arm6 dist4 (no TP)": dict(tp=None, trail_arm=6., trail_dist=4.),
        "trail arm8 dist5 (no TP)": dict(tp=None, trail_arm=8., trail_dist=5.),
        "trail arm8 dist6 + TP20": dict(tp=20., trail_arm=8., trail_dist=6.),
        "trail arm4 dist4 (no TP)": dict(tp=None, trail_arm=4., trail_dist=4.),
        "EOD exit (no TP)": dict(tp=None, ts_h=None, eod=True),
        "EOD exit + TP15": dict(tp=15., ts_h=None, eod=True),
        "pyramid +4": dict(pyramid_at=4.),
        "pyramid +4 trail8/5": dict(tp=None, trail_arm=8., trail_dist=5.,
                                    pyramid_at=4.),
        "re-entry after SL": dict(reenter=True),
    }
    for split, evs in [("TRAIN", train), ("TEST-preview-skipped", None)]:
        if evs is None:
            continue
        rows = []
        for name, kw in V.items():
            pnls = [sim.run(e, level=r3s3_level(e), **kw) for e in evs]
            rows.append(stats(name, pnls))
        print(f"\n=== {split} ===")
        print(pd.DataFrame(rows).sort_values("pf", ascending=False)
              .to_string(index=False))

    # E. overshoot diagnostic (train only)
    print("\n=== overshoot terciles (TRAIN, FINAL_v1 exits) ===")
    feats = []
    for e in train:
        ov = abs(e["h4_close"] - r3s3_level(e)) / max(e["atr_at_build"], 1e-9)
        feats.append((ov, sim.run(e, level=r3s3_level(e))))
    feats = [(o, p) for o, p in feats if p is not None]
    feats.sort(key=lambda x: x[0])
    k = len(feats) // 3
    for lbl, part in [("small overshoot", feats[:k]),
                      ("mid", feats[k:2 * k]),
                      ("large overshoot", feats[2 * k:])]:
        print(stats(lbl, [p for _, p in part]),
              f" (overshoot {part[0][0]:.2f}-{part[-1][0]:.2f} ATR)")

    # F. far-Gann stream (train + test shown; tiny n expected)
    fg = [e for e in ev if far_gann(e)
          and not ({"R3", "S3"} & set(e["zone_sources"]))
          and pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]
    print(f"\n=== far-Gann stream (>=90deg, non-R3/S3 bars, no-Mon) "
          f"n={len(fg)} — FINAL_v1 exits, full 2021-26 ===")
    pnls = [sim.run(e, level=e["zone_levels"][0]) for e in fg]
    print(stats("far-gann 2021-26", pnls))


if __name__ == "__main__":
    main()
