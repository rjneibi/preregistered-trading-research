"""
STATUS: RESEARCH-ONLY (2026-07-02).

Tuning loop for the R3+S3 zone-flip scalp (no-Monday), aimed at raising win
rate / profit WITHOUT overfitting:

  * All variants are scored on the TRAIN split only = first 70% of no-Monday
    R3/S3 trades (2021-2026 window).
  * The top variants (chosen on TRAIN) are then scored once on TEST (last 30%).
  * Finalists get a VIRGIN holdout: 2015-2021 events (never examined before).

Variant axes (web-research + mechanism motivated):
  * entry: market at H4 close | retest limit at the broken level |
           retest limit at midpoint(close, level); wait 24h, else MISSED
  * exits: fixed-$ TP/SL grid, ATR-scaled TP/SL grid,
           breakeven move, time stop
Costs 20 pts/trade throughout. Same-bar ambiguity resolved as SL. On a
retest fill bar TP is NOT granted (could have printed pre-fill) — pessimistic.
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

import run_flip_scalp as rfs                                 # noqa: E402
from research.dr_backtest.data_prep import (                 # noqa: E402
    load_m1, resample_ohlc, resample_d1_utc, wilder_atr,
)
from research.dr_backtest.metrics import basic_stats          # noqa: E402

OUT = REPO / "research" / "flip_scalp"
LOT = 100.0
COST = 20.0          # points
WAIT_H = 24          # retest limit wait
HORIZON_H = 120


# ─────────────────────────────────────────────────────────────────────────
class Sim:
    def __init__(self, m1: pd.DataFrame):
        self.t = m1.index.values
        self.o = m1["open"].to_numpy(float)
        self.h = m1["high"].to_numpy(float)
        self.l = m1["low"].to_numpy(float)
        self.c = m1["close"].to_numpy(float)

    def run(self, e: dict, *, entry: str, tp_usd=None, sl_usd=None,
            tp_atr=None, sl_atr=None, be_at_usd=None, time_stop_h=None):
        sign = 1 if e["direction"] == "BUY" else -1
        atr = float(e["atr_at_build"])
        tp_d = tp_usd if tp_usd is not None else tp_atr * atr
        sl_d = sl_usd if sl_usd is not None else sl_atr * atr
        t0 = np.datetime64(pd.Timestamp(e["entry_ts"]))
        i0 = self.t.searchsorted(t0)
        if i0 >= len(self.t):
            return {"status": "NO_DATA", "pnl": None}

        # --- fill ---------------------------------------------------------
        if entry == "market":
            fi, fill = i0, self.o[i0]
        else:
            # retest limit below (BUY) / above (SELL) the H4 close
            srcs = e["zone_sources"]
            lv = [l for s, l in zip(srcs, e["zone_levels"]) if s in ("R3", "S3")]
            level = lv[0] if lv else e["zone_levels"][0]
            close = e["h4_close"]
            limit = level if entry == "retest_level" else (level + close) / 2.0
            iw = self.t.searchsorted(t0 + np.timedelta64(WAIT_H, "h"))
            fi = None
            for i in range(i0, min(iw, len(self.t))):
                touched = (self.l[i] <= limit) if sign > 0 else (self.h[i] >= limit)
                if touched:
                    fi = i
                    fill = (min(self.o[i], limit) if sign > 0
                            else max(self.o[i], limit))
                    break
            if fi is None:
                return {"status": "MISSED", "pnl": None}

        tp_px = fill + sign * tp_d
        sl_px = fill - sign * sl_d
        stop = sl_px
        be_armed = False
        i_end = self.t.searchsorted(t0 + np.timedelta64(HORIZON_H, "h"))
        i_ts = (self.t.searchsorted(self.t[fi] + np.timedelta64(time_stop_h, "h"))
                if time_stop_h else i_end)
        i_end = min(max(i_end, fi + 1), len(self.t))

        for i in range(fi, i_end):
            hi, lo = self.h[i], self.l[i]
            hit_tp = (hi >= tp_px) if sign > 0 else (lo <= tp_px)
            if i == fi and entry != "market":
                hit_tp = False                      # pessimistic on fill bar
            hit_sl = (lo <= stop) if sign > 0 else (hi >= stop)
            if hit_tp and hit_sl:
                return self._done("SL", sign, stop, fill)
            if hit_sl:
                return self._done("SL", sign, stop, fill)
            if hit_tp:
                return self._done("TP", sign, tp_px, fill)
            if be_at_usd and not be_armed:
                trig = fill + sign * be_at_usd
                if (hi >= trig) if sign > 0 else (lo <= trig):
                    be_armed = True
                    stop = fill                      # BE (costs still charged)
            if i >= i_ts:
                return self._done("TIME", sign, self.c[i], fill)
        return self._done("TIMEOUT", sign, self.c[i_end - 1], fill)

    @staticmethod
    def _done(status, sign, px, fill):
        return {"status": status,
                "pnl": sign * (px - fill) * 100.0 - COST}


# ─────────────────────────────────────────────────────────────────────────
def stats_row(name, res):
    filled = [r["pnl"] for r in res if r["pnl"] is not None]
    missed = sum(1 for r in res if r["status"] == "MISSED")
    if not filled:
        return {"variant": name, "n": 0}
    s = basic_stats(filled)
    return {"variant": name, "n": s["n"], "missed": missed,
            "wr": s["win_rate"], "pf": s["pf"],
            "exp_usd": round(s["expectancy"] / 100 * LOT, 0),
            "net_usd": round(sum(filled) / 100 * LOT, 0)}


def load_events(path):
    ev = [json.loads(l) for l in Path(path).read_text().splitlines()]
    ev.sort(key=lambda x: x["entry_ts"])
    ev = [e for e in ev if {"R3", "S3"} & set(e["zone_sources"])]
    ev = [e for e in ev if pd.Timestamp(e["entry_ts"]).strftime("%a") != "Mon"]
    return ev


VARIANTS = {}
for tp, sl in [(10, 10), (8, 12), (12, 8), (10, 15), (15, 10),
               (8, 8), (12, 12), (15, 15)]:
    VARIANTS[f"mkt_TP{tp}_SL{sl}"] = dict(entry="market",
                                          tp_usd=float(tp), sl_usd=float(sl))
for tpm, slm in [(1.0, 1.0), (1.5, 1.5), (1.0, 1.5), (1.5, 1.0),
                 (2.0, 2.0), (2.0, 1.5)]:
    VARIANTS[f"mkt_aTP{tpm}_aSL{slm}"] = dict(entry="market",
                                              tp_atr=tpm, sl_atr=slm)
VARIANTS["retest_lvl_TP10_SL10"] = dict(entry="retest_level",
                                        tp_usd=10.0, sl_usd=10.0)
VARIANTS["retest_mid_TP10_SL10"] = dict(entry="retest_mid",
                                        tp_usd=10.0, sl_usd=10.0)
VARIANTS["retest_lvl_aTP1.5_aSL1.5"] = dict(entry="retest_level",
                                            tp_atr=1.5, sl_atr=1.5)
VARIANTS["retest_mid_aTP1.5_aSL1.5"] = dict(entry="retest_mid",
                                            tp_atr=1.5, sl_atr=1.5)
VARIANTS["mkt_TP10_SL10_BE5"] = dict(entry="market", tp_usd=10.0,
                                     sl_usd=10.0, be_at_usd=5.0)
VARIANTS["mkt_TP10_SL10_ts12h"] = dict(entry="market", tp_usd=10.0,
                                       sl_usd=10.0, time_stop_h=12)
VARIANTS["mkt_TP10_SL10_ts24h"] = dict(entry="market", tp_usd=10.0,
                                       sl_usd=10.0, time_stop_h=24)
VARIANTS["retest_mid_TP10_SL10_BE5"] = dict(entry="retest_mid", tp_usd=10.0,
                                            sl_usd=10.0, be_at_usd=5.0)


def main():
    rfs.apply_config()
    m1 = load_m1(rfs.BT_START - pd.Timedelta(days=rfs.LOAD_BUFFER_DAYS),
                 rfs.BT_END)
    sim = Sim(m1)
    ev = load_events(OUT / "events.jsonl")
    cut = int(round(len(ev) * 0.7))
    train, test = ev[:cut], ev[cut:]
    print(f"no-Monday R3/S3 events: {len(ev)}  train={len(train)} "
          f"test={len(test)}", flush=True)

    rows = []
    for name, kw in VARIANTS.items():
        res = [sim.run(e, **kw) for e in train]
        rows.append(stats_row(name, res))
    df = pd.DataFrame(rows).sort_values("pf", ascending=False)
    print("\n=== TRAIN (first 70%) — sorted by PF ===")
    print(df.to_string(index=False))
    df.to_csv(OUT / "tune_train_results.csv", index=False)

    # top-5 by PF with n>=80 go to TEST
    finalists = [r["variant"] for _, r in df.iterrows()
                 if r["n"] >= 80][:5]
    print(f"\n=== TEST (last 30%) — finalists only: {finalists} ===")
    rows_t = []
    for name in finalists + ["mkt_TP10_SL10"]:
        res = [sim.run(e, **VARIANTS[name]) for e in test]
        rows_t.append(stats_row(name, res))
    dft = pd.DataFrame(rows_t)
    print(dft.to_string(index=False))
    dft.to_csv(OUT / "tune_test_results.csv", index=False)


if __name__ == "__main__":
    main()
