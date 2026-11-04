"""
fx_s_backtest.py — Profile S (swing) transfer test on EURUSD/GBPUSD/AUDUSD.

REUSES the Profile S engine (backtest_s.py) UNCHANGED — its gates, structural
R:R filter, phase trail, weekend-gap control, BE/trailing and IS/OOS split are all
the committed logic. The engine re-implements its math in raw numpy floats with NO
2-decimal rounding, so it runs natively at FX precision (1e-5) — unlike the D/R
engine, no price scaling is needed.

FX adaptations (instrument config only — no gate re-tuning):
  * point 1e-5, USD_PER_LOT_PER_DOLLAR = 100000 ($1/point/lot, contract 100k),
  * dynamic per-symbol swap rates pulled live from symbol_info,
  * per-trade cost = per-symbol spread + $7/lot commission folded into the
    spread-points column (matches the D/R cost model); nightly swap also charged,
  * a currency-aware NEWS BLACKOUT (added here) on top of the engine's weekend gap.

News blackout (Step 3c): blocks NEW entries (and re-entries) inside high-impact
windows for the pair's currencies. The MetaTrader5 Python API exposes no economic
calendar, so only the *rule-predictable* recurring events are placed precisely:
  USD Non-Farm Payrolls — 1st Friday, 12:00–15:00 UTC (all three pairs)
  AUD RBA cash-rate     — 1st Tuesday, 03:00–06:00 UTC (AUDUSD only)
ECB / BoE / FOMC rate decisions are NOT fixed-date and cannot be reproduced from a
recurrence rule without a historical calendar feed; the framework accepts an
explicit EVENT_DATES list to add them if such a feed is wired in later. Blocked-
entry counts are reported so the filter's impact is transparent (expected small for
a multi-day swing system).

Run:  py -3.11 research/fx_backtest/fx_s_backtest.py
"""
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import MetaTrader5 as mt5

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))

import backtest_s as bs           # noqa: E402  (root Profile S engine)
import backtest_config_s as scfg  # noqa: E402
import backtest_report as rpt     # noqa: E402
import fx_common as fx            # noqa: E402

CURRENCIES = {"EURUSD": ["EUR", "USD"], "GBPUSD": ["GBP", "USD"],
              "AUDUSD": ["AUD", "USD"]}
COMMISSION_PTS = int(fx.COMMISSION_USD)   # $7/lot round trip = 7 points (V=$1/pt)

# Optional explicit high-impact event datetimes (UTC) to extend the blackout for
# the non-recurring central-bank decisions. Empty by default (see module docstring).
EVENT_DATES = []  # e.g. [datetime(2024, 3, 7, 13, 15)]  # ECB decision


def _is_first_weekday(dt, weekday):
    """True if dt falls on the first <weekday> (0=Mon) of its month."""
    return dt.weekday() == weekday and dt.day <= 7


def news_blackout(dt, currencies):
    """True if dt is inside a high-impact news window for any of `currencies`."""
    h = dt.hour
    if "USD" in currencies and _is_first_weekday(dt, 4) and 12 <= h < 15:
        return True   # US Non-Farm Payrolls
    if "AUD" in currencies and _is_first_weekday(dt, 1) and 3 <= h < 6:
        return True   # RBA cash-rate decision
    for ev in EVENT_DATES:
        if abs((dt - ev).total_seconds()) <= 2 * 3600:
            return True
    return False


def install_news_blackout(symbol):
    """Wrap bs.evaluate_setup so a would-be 'ok' setup inside a news window is
    suppressed and counted. Returns (restore_fn, counter_dict)."""
    currencies = CURRENCIES[symbol]
    orig = bs.evaluate_setup
    counter = {"blocked": 0}

    def patched(ind, j, direction_filter=None):
        res = orig(ind, j, direction_filter)
        if res.get("status") == "ok":
            bt = pd.Timestamp(ind.h4_df["time"].values[j]).to_pydatetime()
            if news_blackout(bt, currencies):
                counter["blocked"] += 1
                return {"status": "no_signal"}
        return res

    bs.evaluate_setup = patched
    return (lambda: setattr(bs, "evaluate_setup", orig)), counter


DAILY_LOG_HEADER = ["timestamp", "profile", "ticket", "direction", "zone_name",
                    "confluence", "entry_price", "sl_price", "tp_price", "lots",
                    "atr", "adx", "polarity_flipped", "h4_bias",
                    "floating_pnl_at_open",
                    # backtest reasoning extension:
                    "in_sample", "result", "exit_price", "pnl_usd", "pnl_r",
                    "bars_held", "structural_rr", "reduced_size", "is_reentry",
                    "swap_cost", "spread_cost"]


def write_daily_log_csv(path, trades):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=DAILY_LOG_HEADER)
        w.writeheader()
        for t in sorted(trades, key=lambda x: x.entry_time):
            pnl_r = (t.realized_pnl / t.risk_usd) if t.risk_usd else 0.0
            w.writerow({
                "timestamp": t.entry_time, "profile": "S", "ticket": t.id,
                "direction": t.direction, "zone_name": "polarity_break",
                "confluence": t.confluence_score,
                "entry_price": round(t.entry, 5), "sl_price": round(t.sl_original, 5),
                "tp_price": round(t.tp, 5), "lots": round(t.orig_lot, 2),
                "atr": round(t.daily_atr, 5), "adx": "",
                # Every S trade clears the mandatory break-&-retest polarity gate.
                "polarity_flipped": "yes",
                "h4_bias": "bullish" if t.direction == "BUY" else "bearish",
                "floating_pnl_at_open": "",
                "in_sample": int(t.in_sample), "result": t.result,
                "exit_price": round(t.exit_price, 5),
                "pnl_usd": round(t.realized_pnl, 2), "pnl_r": round(pnl_r, 3),
                "bars_held": t.bars_held, "structural_rr": round(t.structural_rr, 3),
                "reduced_size": int(t.reduced_size), "is_reentry": int(t.is_reentry),
                "swap_cost": round(t.swap_cost_total, 2),
                "spread_cost": round(t.spread_cost, 2),
            })


def metric_summary(m):
    pf = m["profit_factor"]
    return {
        "n": m["trades"], "wins": m["wins"], "losses": m["losses"],
        "be": m["be"], "timeouts": m["timeouts"],
        "win_rate": m["win_rate"] * 100.0,
        "pf": ("inf" if pf == float("inf") else round(pf, 4)),
        "exp_R": round(m["expectancy_r"], 4),
        "exp_usd": round(m["expectancy_usd"], 2),
        "maxdd": round(m["max_dd_pct"], 2),
        "net_profit": round(m["net_profit"], 2),
        "regime_conc": round(m["regime_conc"], 4),
    }


def run_symbol(symbol, start, end):
    print(f"\n### Profile S / {symbol}")
    bs.GOLD_POINT = fx.SYMCFG[symbol]["point"]          # 1e-5
    bs.USD_PER_LOT_PER_DOLLAR = fx.USD_PER_LOT_PER_PRICE  # 100000
    bs.SYMBOL = symbol

    daily_df = bs._rates_to_df(fx.fetch_rates(symbol, mt5.TIMEFRAME_D1, start, end))
    h4_df = bs._rates_to_df(fx.fetch_rates(symbol, mt5.TIMEFRAME_H4, start, end))
    # Force a conservative per-symbol cost: spread + folded commission (points).
    cost_pts = fx.SYMCFG[symbol]["spread_pts"] + COMMISSION_PTS
    h4_df["spread"] = cost_pts

    sinfo = mt5.symbol_info(symbol)
    # MT5 FX swaps are quoted in POINTS. The S engine computes the nightly charge
    # as |swap| * lot * USD_PER_LOT_PER_DOLLAR, which expects swap in PRICE units
    # (gold's convention). Pre-scale by `point` so swap_points -> price, giving
    # |swap_pts| * point * 100000 * lot = |swap_pts| * $1 * lot per night (correct).
    point = fx.SYMCFG[symbol]["point"]
    bs.SWAP_LONG = float(sinfo.swap_long) * point
    bs.SWAP_SHORT = float(sinfo.swap_short) * point
    swap_long_pts = float(sinfo.swap_long)
    swap_short_pts = float(sinfo.swap_short)

    ind = bs.Indicators(daily_df, h4_df)
    n_h4 = len(h4_df)
    split_idx = int(n_h4 * scfg.IN_SAMPLE_PCT)
    split_time = pd.Timestamp(h4_df["time"].values[split_idx]).to_pydatetime()
    is_start = pd.Timestamp(h4_df["time"].values[0]).to_pydatetime()
    oos_end = pd.Timestamp(h4_df["time"].values[-1]).to_pydatetime()

    restore, blk = install_news_blackout(symbol)
    try:
        bs.Trade._next_id = 1
        trades, rejections, equity_points, stats = bs.run_simulation(ind, split_idx)
    finally:
        restore()

    # Make Profile S metrics AFTER-COST and consistent with D/R: the engine tracks
    # spread + swap only on the equity curve, leaving t.realized_pnl gross (price
    # only). Fold both into realized_pnl so PF / expectancy / MaxDD computed below
    # are net of spread + commission (folded into spread_cost) + nightly swap.
    for t in trades:
        t.realized_pnl -= (t.spread_cost + t.swap_cost_total)

    base = scfg.INITIAL_EQUITY
    is_tr = [t for t in trades if t.in_sample]
    oos_tr = [t for t in trades if not t.in_sample]
    is_rej = [r for r in rejections if r["in_sample"]]
    oos_rej = [r for r in rejections if not r["in_sample"]]
    is_m = rpt.compute_metrics(is_tr, is_rej, base)
    oos_base = base + is_m["net_profit"]
    oos_m = rpt.compute_metrics(oos_tr, oos_rej, oos_base)
    full_m = rpt.compute_metrics(trades, rejections, base)

    longs = sum(1 for t in trades if t.direction == "BUY")
    shorts = sum(1 for t in trades if t.direction == "SELL")
    # Polarity gate is mandatory in S → every trade "flipped"; polarity-gate win
    # rate == overall win rate (no no-flip subset exists).
    pol = {"flip_n": full_m["trades"], "flip_wr": full_m["win_rate"] * 100.0,
           "noflip_n": 0, "noflip_wr": 0.0}
    pol_oos = {"flip_n": oos_m["trades"], "flip_wr": oos_m["win_rate"] * 100.0,
               "noflip_n": 0, "noflip_wr": 0.0}

    os.makedirs(fx.RESULTS_DIR, exist_ok=True)
    csv_path = os.path.join(fx.RESULTS_DIR, f"trades_S_{symbol}.csv")
    write_daily_log_csv(csv_path, trades)

    summary = {
        "profile": "S", "symbol": symbol, "logic": "S-swing",
        "cost_pts": cost_pts, "swap_long_pts": swap_long_pts,
        "swap_short_pts": swap_short_pts,
        "news_blocked_entries": blk["blocked"],
        "split_date": split_time.strftime("%Y-%m-%d"),
        "is_period": [is_start.strftime("%Y-%m-%d"), split_time.strftime("%Y-%m-%d")],
        "oos_period": [split_time.strftime("%Y-%m-%d"), oos_end.strftime("%Y-%m-%d")],
        "longs": longs, "shorts": shorts,
        "rejections": len(rejections),
        "full": metric_summary(full_m), "is": metric_summary(is_m),
        "oos": metric_summary(oos_m),
        "polarity_full": pol, "polarity_oos": pol_oos,
        "csv": csv_path,
    }
    js_path = os.path.join(fx.RESULTS_DIR, f"summary_S_{symbol}.json")
    with open(js_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    fpf = summary["full"]["pf"]; opf = summary["oos"]["pf"]
    print(f"  cost={cost_pts}pts swap_pts L/S={swap_long_pts}/{swap_short_pts} "
          f"news_blocked={blk['blocked']} rejections={len(rejections)}")
    print(f"  FULL: n={summary['full']['n']} win={summary['full']['win_rate']:.1f}% "
          f"PF={fpf} exp={summary['full']['exp_R']:+.3f}R "
          f"MaxDD={summary['full']['maxdd']:.1f}% L/S={longs}/{shorts}")
    print(f"  OOS : n={summary['oos']['n']} win={summary['oos']['win_rate']:.1f}% "
          f"PF={opf} exp={summary['oos']['exp_R']:+.3f}R "
          f"MaxDD={summary['oos']['maxdd']:.1f}%")
    print(f"  polarity-gate win rate (FULL): {pol['flip_wr']:.1f}% over "
          f"{pol['flip_n']} trades (gate mandatory — all trades)")
    print(f"  CSV: {csv_path}")
    return summary


def main():
    fx.connect()
    start, end = fx.window()
    print("=" * 72)
    print("FX TRANSFER TEST — PROFILE S (swing engine reused)")
    print(f"window {start.date()} -> {end.date()} ({fx.YEARS_BACK}y) | "
          f"IS/OOS {int(scfg.IN_SAMPLE_PCT*100)}/{int((1-scfg.IN_SAMPLE_PCT)*100)}")
    print("=" * 72)
    summaries = [run_symbol(s, start, end) for s in fx.SYMBOLS]
    mt5.shutdown()
    out = os.path.join(fx.RESULTS_DIR, "summaries_S.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)
    print(f"\nAll S summaries -> {out}")


if __name__ == "__main__":
    main()
