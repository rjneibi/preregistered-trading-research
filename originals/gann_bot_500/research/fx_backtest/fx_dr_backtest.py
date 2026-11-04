"""
fx_dr_backtest.py — Profile D / Profile R transfer test on EURUSD/GBPUSD/AUDUSD.

REUSES the live six-gate decision logic UNCHANGED by importing research/backtest.py
and feeding it FX bars. Nothing in the gate evaluation, zone construction, EMA/ATR,
polarity, or ADX handling is re-implemented — the whole point is to test whether the
EXISTING validated Profile D/R logic transfers to FX, not to build new logic.

Per profile the only differences from the gold engine are the (already validated)
locked exits and the polarity switch, applied exactly as config/profile defines them:
  Profile D — "Core + Polarity": polarity ON,  TP 3.0xATR / SL 1.0xATR.
  Profile R — "Pure Core":       polarity OFF, TP 2.5xATR / SL 1.5xATR.
NO per-pair re-optimisation of any gate parameter (all ATR-relative params identical).

Costs (realistic): per-symbol spread (fx_common.SYMCFG) + $7/lot round-trip
commission, charged once per trade, in price. Metrics in R (net of costs).
Walk-forward: 70/30 chronological IS/OOS split (same methodology as gold).

Outputs per run: console block, results/trades_{PROFILE}_{SYMBOL}.csv (daily_log
format + outcome columns), and results/summary_{PROFILE}_{SYMBOL}.json for the
report builder.

Run:  py -3.11 research/fx_backtest/fx_dr_backtest.py
"""
import json
import os
import sys
from datetime import datetime, timezone

# Make project root + research/ importable, and pick Profile D config (the engine
# reproduces D natively; R is realised by toggling polarity + exits below).
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
os.environ.setdefault("GANNBOT_PROFILE", "D")

import config            # noqa: E402
import backtest as bt    # noqa: E402  (research/backtest.py)
import fx_common as fx   # noqa: E402

PROFILE_PARAMS = {
    "D": {"polarity": True,  "tp": 3.0, "sl": 1.0},
    "R": {"polarity": False, "tp": 2.5, "sl": 1.5},
}


def _utc_date(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def score_trades(candidates, h1, point, tp, sl, spread_pts, V, split_iso, scale):
    """Per-trade scoring with full costs, on SCALED bars. Returns trade dicts with
    outcome, realized R (net of spread+commission, scale-invariant), and all
    reasoning fields. Price/ATR fields are un-scaled back to native FX for the CSV;
    R is computed in scaled space (identical either way)."""
    spread_price = spread_pts * point          # `point` is already the scaled point
    comm_price = (fx.COMMISSION_USD / V) * point
    trades = []
    for c in candidates:
        outcome, dur, gross, net_after_spread, slp, tpp = bt.simulate_trade(
            h1, c["entry_idx"], c["direction"], c["entry_price"], c["atr_h1"],
            tp, sl, spread_price)
        net = net_after_spread - comm_price        # charge commission once
        risk_price = sl * c["atr_h1"]
        r = net / risk_price if risk_price else 0.0
        entry_date = c["entry_time"][:10]
        trades.append({
            "entry_time": c["entry_time"],
            "in_sample": entry_date < split_iso,
            "direction": c["direction"],
            "zone_source": c["zone_source"],
            "confluence": c["confluence"],
            "entry_price": c["entry_price"] / scale,
            "sl_price": slp / scale, "tp_price": tpp / scale,
            "atr_h1": c["atr_h1"] / scale, "adx": c["adx"],
            "polarity_flipped": c["polarity_flipped"],
            "h4_bias": c["h4_bias"],
            "outcome": outcome, "duration_bars": dur,
            "net_price": net / scale, "r_multiple": r,
        })
    return trades


def metric_block(trades):
    """Metrics over a list of scored trades. PF + expectancy in R; win rate over
    resolved (TP/SL) trades; MaxDD% on the chronological R series."""
    n = len(trades)
    if n == 0:
        return {"n": 0, "win_rate": 0.0, "pf": 0.0, "exp_R": 0.0, "maxdd": 0.0,
                "resolved": 0, "wins": 0, "losses": 0, "opens": 0,
                "longs": 0, "shorts": 0, "avg_win_R": 0.0, "avg_loss_R": 0.0}
    rs = [t["r_multiple"] for t in trades]
    tp_n = sum(1 for t in trades if t["outcome"] == "TP")
    sl_n = sum(1 for t in trades if t["outcome"] == "SL")
    op_n = sum(1 for t in trades if t["outcome"] == "OPEN")
    resolved = tp_n + sl_n
    pos = sum(r for r in rs if r > 0)
    neg = -sum(r for r in rs if r < 0)
    win_r = [r for r in rs if r > 0]
    loss_r = [r for r in rs if r < 0]
    return {
        "n": n,
        "win_rate": (100.0 * tp_n / resolved) if resolved else 0.0,
        "pf": (pos / neg) if neg > 0 else (float("inf") if pos > 0 else 0.0),
        "exp_R": sum(rs) / n,
        "maxdd": fx.max_drawdown_pct(rs),
        "resolved": resolved, "wins": tp_n, "losses": sl_n, "opens": op_n,
        "longs": sum(1 for t in trades if t["direction"] == "BUY"),
        "shorts": sum(1 for t in trades if t["direction"] == "SELL"),
        "avg_win_R": (sum(win_r) / len(win_r)) if win_r else 0.0,
        "avg_loss_R": (sum(loss_r) / len(loss_r)) if loss_r else 0.0,
    }


def polarity_split(trades):
    """Win rate of trades where the polarity gate flipped vs didn't (resolved
    trades only). Mirrors the live adx/polarity_flipped CSV columns."""
    def wr(sub):
        res = [t for t in sub if t["outcome"] in ("TP", "SL")]
        w = sum(1 for t in res if t["outcome"] == "TP")
        return (100.0 * w / len(res)) if res else 0.0, len(res), w
    flip = [t for t in trades if t["polarity_flipped"] == "yes"]
    noflip = [t for t in trades if t["polarity_flipped"] != "yes"]
    fwr, fn, fw = wr(flip)
    nwr, nn, nw = wr(noflip)
    return {"flip_wr": fwr, "flip_n": fn, "flip_w": fw,
            "noflip_wr": nwr, "noflip_n": nn, "noflip_w": nw}


CSV_HEADER = ["timestamp", "profile", "ticket", "direction", "zone_name",
              "confluence", "entry_price", "sl_price", "tp_price", "lots", "atr",
              "adx", "polarity_flipped", "h4_bias", "floating_pnl_at_open",
              # backtest reasoning extension:
              "in_sample", "outcome", "duration_bars", "net_price", "r_multiple"]


def write_csv(path, profile, trades):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        w.writeheader()
        for t in trades:
            w.writerow({
                "timestamp": t["entry_time"], "profile": profile, "ticket": "",
                "direction": t["direction"], "zone_name": t["zone_source"],
                "confluence": t["confluence"],
                "entry_price": round(t["entry_price"], 5),
                "sl_price": round(t["sl_price"], 5),
                "tp_price": round(t["tp_price"], 5), "lots": "",
                "atr": round(t["atr_h1"], 5), "adx": t["adx"],
                "polarity_flipped": t["polarity_flipped"], "h4_bias": t["h4_bias"],
                "floating_pnl_at_open": "",
                "in_sample": t["in_sample"], "outcome": t["outcome"],
                "duration_bars": t["duration_bars"],
                "net_price": round(t["net_price"], 6),
                "r_multiple": round(t["r_multiple"], 4),
            })


def run_symbol_profile(symbol, profile, h1, h4, d1, point, V, split_iso, scale):
    """Configure the engine for (symbol, profile), collect candidates with the
    production gate logic, score with locked exits + costs, return a summary dict.
    h1/h4/d1 are SCALED bars; `point` is the scaled point (1e-5*scale)."""
    p = PROFILE_PARAMS[profile]
    # Toggle the engine exactly as the profile defines (no other changes).
    bt.R_POLARITY = p["polarity"]
    config.ATR_TP_MULT = p["tp"]
    config.ATR_SL_MULT = p["sl"]

    candidates, bottleneck, evaluated, in_zone, _ha = bt.collect_candidates(h1, h4, d1)
    spread_pts = fx.SYMCFG[symbol]["spread_pts"]
    trades = score_trades(candidates, h1, point, p["tp"], p["sl"],
                          spread_pts, V, split_iso, scale)

    full = metric_block(trades)
    is_t = [t for t in trades if t["in_sample"]]
    oos_t = [t for t in trades if not t["in_sample"]]
    m_is = metric_block(is_t)
    m_oos = metric_block(oos_t)
    pol_full = polarity_split(trades)
    pol_oos = polarity_split(oos_t)

    os.makedirs(fx.RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(fx.RESULTS_DIR, f"trades_{profile}_{symbol}.csv")
    write_csv(csv_path, profile, trades)

    summary = {
        "profile": profile, "symbol": symbol, "logic": "D/R",
        "tp": p["tp"], "sl": p["sl"], "polarity": p["polarity"],
        "spread_pts": spread_pts, "commission_usd": fx.COMMISSION_USD,
        "evaluated_bars": evaluated, "in_zone_bars": in_zone,
        "split_date": split_iso,
        "full": full, "is": m_is, "oos": m_oos,
        "polarity_full": pol_full, "polarity_oos": pol_oos,
        "csv": csv_path,
    }
    js_path = os.path.join(fx.RESULTS_DIR, f"summary_{profile}_{symbol}.json")
    with open(js_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    pf = "inf" if full["pf"] == float("inf") else f"{full['pf']:.2f}"
    pf_o = "inf" if m_oos["pf"] == float("inf") else f"{m_oos['pf']:.2f}"
    print(f"\n--- Profile {profile} / {symbol} "
          f"(TP {p['tp']} / SL {p['sl']}, polarity {'ON' if p['polarity'] else 'OFF'}) ---")
    print(f"  FULL: n={full['n']} win={full['win_rate']:.1f}% PF={pf} "
          f"exp={full['exp_R']:+.3f}R MaxDD={full['maxdd']:.1f}% "
          f"L/S={full['longs']}/{full['shorts']}")
    print(f"  OOS : n={m_oos['n']} win={m_oos['win_rate']:.1f}% PF={pf_o} "
          f"exp={m_oos['exp_R']:+.3f}R MaxDD={m_oos['maxdd']:.1f}%")
    print(f"  polarity flip (FULL): flip {pol_full['flip_w']}/{pol_full['flip_n']} "
          f"={pol_full['flip_wr']:.1f}%  no-flip {pol_full['noflip_w']}/"
          f"{pol_full['noflip_n']}={pol_full['noflip_wr']:.1f}%")
    print(f"  CSV: {csv_path}")
    return summary


def main():
    fx.connect()
    start, end = fx.window()
    print("=" * 72)
    print("FX TRANSFER TEST — PROFILE D & R  (production six-gate logic reused)")
    print(f"window {start.date()} -> {end.date()} ({fx.YEARS_BACK}y) | "
          f"IS/OOS {int(fx.IN_SAMPLE_PCT*100)}/{int((1-fx.IN_SAMPLE_PCT)*100)}")
    print("=" * 72)

    import MetaTrader5 as mt5
    scale = fx.DR_SCALE
    all_summaries = []
    for symbol in fx.SYMBOLS:
        point = fx.SYMCFG[symbol]["point"] * scale   # scaled point (0.1)
        V = fx.SYMCFG[symbol]["V"]
        h1 = fx.scale_bars(fx.rates_to_bars(fx.fetch_rates(symbol, mt5.TIMEFRAME_H1, start, end)), scale)
        h4 = fx.scale_bars(fx.rates_to_bars(fx.fetch_rates(symbol, mt5.TIMEFRAME_H4, start, end)), scale)
        d1 = fx.scale_bars(fx.rates_to_bars(fx.fetch_rates(symbol, mt5.TIMEFRAME_D1, start, end)), scale)
        sd = fx.split_date(h1)
        split_iso = sd.strftime("%Y-%m-%d")
        t0, t1, yrs = fx.coverage(h1)
        print(f"\n### {symbol}: H1={len(h1)} H4={len(h4)} D1={len(d1)} | "
              f"{t0.date()}->{t1.date()} ({yrs:.2f}y) | IS<{split_iso}<=OOS | scale x{int(scale)}")
        for profile in ("D", "R"):
            all_summaries.append(
                run_symbol_profile(symbol, profile, h1, h4, d1, point, V, split_iso, scale))

    mt5.shutdown()
    out = os.path.join(fx.RESULTS_DIR, "summaries_DR.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(all_summaries, f, indent=2)
    print(f"\nAll D/R summaries -> {out}")


if __name__ == "__main__":
    main()
