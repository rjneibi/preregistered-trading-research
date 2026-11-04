"""
backtest_vp.py — Bar-by-bar backtest of Profile D & R, with/without a Volume
Profile confluence filter.

Four configurations are simulated on the saved CSV history:

    1. Profile_D_Baseline — D 6-gate logic, no VP filter
    2. Profile_D_VP       — D 6-gate logic + VP filter
    3. Profile_R_Baseline — R 5-gate logic, no VP filter
    4. Profile_R_VP       — R 5-gate logic + VP filter

Gate stack (reconstructed in signal_engine, NOT imported from the live bot):
    confluence zone hit -> H4 EMA50 bias -> H4 fib structure -> ADX>25 ->
    [polarity flip — D only] -> H1 body-close confirmation.

VP filter (applied only in the *_VP configs; a signal must pass ALL THREE):
    * POC proximity : zone within 1.0 × ATR of the 20-session POC
    * VA context    : price must NOT sit inside the Value Area (range = skip)
    * LVN path      : an LVN must lie between entry and the TP target

Outputs, written to research/vp_backtest/results/:
    <Config>.csv           — taken trades (one row per trade) for all 4 configs
    <Config>_filtered.csv  — VP configs only: ADX-passed signals VP rejected,
                             with their hypothetical outcome (for filter analysis)
    <Config>_summary.csv   — one-row headline metrics per config
    all_summaries.csv      — the 4 summary rows combined

No live bot files are imported or modified.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Local engines (pure-DataFrame; zero live-bot imports).
_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parent))
import signal_engine as se          # noqa: E402
import volume_profile as vp         # noqa: E402

_DATA_DIR = _THIS.parent / "data"
_RESULTS_DIR = _THIS.parent / "results"

# ── Constants (mirrored from config.py; NOT imported) ─────
SYMBOL = "XAUUSD"
POINT = 0.01                 # XAUUSD point size (price units per point)
MAX_SPREAD_POINTS = 40       # spread cost deducted from every entry
LOT = 0.01                   # fixed lot for comparability
ADX_THRESHOLD = 25           # spec: ADX > 25 gate for BOTH profiles
ATR_ZONE_WIDTH_MULT = 0.3    # zone half-width = 0.3 × ATR (config.ATR_ZONE_WIDTH_MULT)
CONFLUENCE_ATR_MULT = 0.5    # confluence clustering radius (config.CONFLUENCE_ATR_MULT)
SWING_LOOKBACK_H4 = 50
VP_LOOKBACK_SESSIONS = 20    # rolling D1 sessions for the volume profile window
VP_POC_PROX_ATR = 1.0        # POC must be within 1.0 × ATR of the zone
PRICE_BUCKET = 0.50          # VP price bucket size

# Per-profile SL/TP ATR multiples.
PROFILE_PARAMS = {
    "D": {"sl_mult": 1.0, "tp_mult": 3.0, "use_polarity": True},
    "R": {"sl_mult": 1.5, "tp_mult": 2.5, "use_polarity": False},
}

# Timeframe lengths in seconds (MT5 bar `time` is the bar OPEN epoch).
_TF_SECONDS = {"H1": 3600, "H4": 4 * 3600, "D1": 24 * 3600}

_PROGRESS_EVERY = 500


# ── Data loading ──────────────────────────────────────────
def _load_csv(name):
    """
    Load one saved timeframe CSV into a DataFrame indexed 0..n-1, oldest first.

    Params:
        name (str): file name under data/ (e.g. "xauusd_h1.csv").

    Returns:
        DataFrame: with an added integer 'ts' (epoch seconds) column.
    """
    path = _DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run fetch_data.py first.")
    df = pd.read_csv(path)
    df["ts"] = df["time"].astype(np.int64)
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def _asof_index(ts_array, tf_seconds, decision_close_ts):
    """
    Index of the most recent bar fully CLOSED at `decision_close_ts` (no lookahead).

    A bar with open-epoch T closes at T + tf_seconds. We want the largest index
    whose close epoch <= decision_close_ts.

    Params:
        ts_array (np.ndarray): bar open epochs, ascending.
        tf_seconds (int): timeframe length in seconds.
        decision_close_ts (int): the decision instant (an H1 bar's close epoch).

    Returns:
        int: index into ts_array, or -1 if no bar has closed yet.
    """
    close_ts = ts_array + tf_seconds
    return int(np.searchsorted(close_ts, decision_close_ts, side="right") - 1)


# ── Trade simulation ──────────────────────────────────────
def _simulate_trade(h1, entry_idx, direction, entry_price, sl, tp):
    """
    Walk H1 bars forward from `entry_idx` until SL or TP is touched.

    Conservative tie-break: if a single bar's range spans both SL and TP, the SL
    is assumed hit first.

    Params:
        h1 (DataFrame): H1 bars with ['high','low','close','ts'].
        entry_idx (int): index of the entry bar (entry filled at its open).
        direction (str): "BUY" or "SELL".
        entry_price (float): spread-adjusted fill price.
        sl (float): stop-loss price.
        tp (float): take-profit price.

    Returns:
        dict: {exit_price, exit_ts, pnl_points, hit} where hit in {"tp","sl","eod"}.
    """
    highs = h1["high"].to_numpy(dtype=float)
    lows = h1["low"].to_numpy(dtype=float)
    ts = h1["ts"].to_numpy(np.int64)
    n = len(h1)

    for i in range(entry_idx, n):
        hi, lo = highs[i], lows[i]
        if direction == "BUY":
            hit_sl = lo <= sl
            hit_tp = hi >= tp
            if hit_sl and hit_tp:
                exit_price, hit = sl, "sl"
            elif hit_tp:
                exit_price, hit = tp, "tp"
            elif hit_sl:
                exit_price, hit = sl, "sl"
            else:
                continue
            pnl = (exit_price - entry_price) / POINT
        else:  # SELL
            hit_sl = hi >= sl
            hit_tp = lo <= tp
            if hit_sl and hit_tp:
                exit_price, hit = sl, "sl"
            elif hit_tp:
                exit_price, hit = tp, "tp"
            elif hit_sl:
                exit_price, hit = sl, "sl"
            else:
                continue
            pnl = (entry_price - exit_price) / POINT
        return {"exit_price": round(exit_price, 2), "exit_ts": int(ts[i]),
                "pnl_points": round(pnl, 1), "hit": hit, "exit_idx": i}

    # Never hit a level — close at the last available close.
    last_close = float(h1["close"].iloc[-1])
    pnl = ((last_close - entry_price) if direction == "BUY"
           else (entry_price - last_close)) / POINT
    return {"exit_price": round(last_close, 2), "exit_ts": int(ts[-1]),
            "pnl_points": round(pnl, 1), "hit": "eod", "exit_idx": n - 1}


def _apply_spread(direction, raw_entry):
    """
    Worsen the entry price by the full MAX_SPREAD_POINTS spread cost.

    Params:
        direction (str): "BUY" or "SELL".
        raw_entry (float): next-bar open price.

    Returns:
        float: spread-adjusted entry (BUY pays up, SELL sells down).
    """
    cost = MAX_SPREAD_POINTS * POINT
    return raw_entry + cost if direction == "BUY" else raw_entry - cost


# ── VP filter ─────────────────────────────────────────────
def _vp_filter(h1, decision_idx, d1_asof, atr, zone_price, current_price,
               direction, tp_price):
    """
    Evaluate the three VP sub-filters for a candidate signal.

    Builds a volume profile from the H1 bars spanning the last
    VP_LOOKBACK_SESSIONS D1 sessions (the "20-session lookback window"), then:
      * POC proximity : |zone_price - POC| <= VP_POC_PROX_ATR × ATR
      * VA context    : price classification must NOT be "inside_va"
      * LVN path      : nearest LVN toward the trade direction lies strictly
                        between current_price and tp_price

    Params:
        h1 (DataFrame): full H1 frame.
        decision_idx (int): index of the decision (just-closed) H1 bar.
        d1_asof (int): index of the current D1 session in the D1 frame.
        atr (float): current H4 ATR.
        zone_price (float): the signal zone's price.
        current_price (float): price at signal time.
        direction (str): "BUY" or "SELL".
        tp_price (float): the trade's take-profit price.

    Returns:
        dict: {poc, vah, val, poc_distance_atr, inside_va, lvn_path_clear,
               poc_ok, va_ok, lvn_ok, passed}.
    """
    # Window = H1 bars within the last VP_LOOKBACK_SESSIONS * 24h before decision.
    decision_close_ts = int(h1["ts"].iloc[decision_idx]) + _TF_SECONDS["H1"]
    window_start_ts = decision_close_ts - VP_LOOKBACK_SESSIONS * _TF_SECONDS["D1"]
    h1_ts = h1["ts"].to_numpy(np.int64)
    lo = int(np.searchsorted(h1_ts, window_start_ts, side="left"))
    win = h1.iloc[lo:decision_idx + 1]

    profile = vp.build_volume_profile(win, price_bucket_size=PRICE_BUCKET)
    poc = vp.get_poc(profile)
    va = vp.get_value_area(profile, va_pct=0.70)
    vah, val = (va if va is not None else (None, None))

    if poc is None or vah is None:
        # No profile -> cannot confirm any sub-filter; reject in VP variants.
        return {"poc": None, "vah": None, "val": None,
                "poc_distance_atr": None, "inside_va": None,
                "lvn_path_clear": None, "poc_ok": False, "va_ok": False,
                "lvn_ok": False, "passed": False}

    poc_dist_atr = abs(zone_price - poc) / atr if atr > 0 else None
    poc_ok = poc_dist_atr is not None and poc_dist_atr <= VP_POC_PROX_ATR

    cls = vp.classify_price_vs_profile(current_price, poc, vah, val, PRICE_BUCKET)
    inside_va = (cls == "inside_va")
    va_ok = not inside_va

    lvn_dir = "above" if direction == "BUY" else "below"
    lvn = vp.get_nearest_lvn(profile, current_price, n_bottom=5, direction=lvn_dir)
    if lvn is None:
        lvn_path_clear = False
    elif direction == "BUY":
        lvn_path_clear = current_price < lvn < tp_price
    else:
        lvn_path_clear = tp_price < lvn < current_price
    lvn_ok = bool(lvn_path_clear)

    return {"poc": poc, "vah": vah, "val": val,
            "poc_distance_atr": (round(poc_dist_atr, 3)
                                 if poc_dist_atr is not None else None),
            "inside_va": inside_va, "lvn_path_clear": lvn_ok,
            "poc_ok": poc_ok, "va_ok": va_ok, "lvn_ok": lvn_ok,
            "passed": bool(poc_ok and va_ok and lvn_ok)}


# ── Core per-config backtest ──────────────────────────────
def run_config(profile_key, use_vp, h1, h4, d1, atr_h4, ema_h4, adx_h4):
    """
    Run one of the four configurations over the full H1 history.

    Params:
        profile_key (str): "D" or "R".
        use_vp (bool): apply the VP filter when True.
        h1, h4, d1 (DataFrame): the three timeframe frames.
        atr_h4, ema_h4 (Series): precomputed H4 ATR / EMA50.
        adx_h4 (Series): precomputed H4 ADX.

    Returns:
        tuple(list[dict], list[dict], dict):
            (taken_trades, filtered_signals, counters)
    """
    params = PROFILE_PARAMS[profile_key]
    use_polarity = params["use_polarity"]
    sl_mult, tp_mult = params["sl_mult"], params["tp_mult"]
    config_name = f"Profile_{profile_key}_{'VP' if use_vp else 'Baseline'}"
    print(f"\n=== Running {config_name} ===")

    h1_ts = h1["ts"].to_numpy(np.int64)
    h4_ts = h4["ts"].to_numpy(np.int64)
    d1_ts = d1["ts"].to_numpy(np.int64)
    h1_open = h1["open"].to_numpy(dtype=float)
    h1_close = h1["close"].to_numpy(dtype=float)

    taken = []
    filtered = []
    counters = {"raw_signals": 0, "adx_passed": 0, "vp_eligible": 0,
                "vp_passed": 0, "bars": 0}

    # Per-day zone cache (recomputed when the calendar day changes, like live).
    cached_day = None
    cached_zones = []
    cached_fib = None
    fired_zones = set()       # (round(zone_price,1), day) taken this calendar day
    fired_day = None

    open_until_idx = -1       # index through which a trade occupies the slot
    n = len(h1)
    start_idx = 0

    for i in range(n):
        counters["bars"] += 1
        if i % _PROGRESS_EVERY == 0:
            print(f"  {config_name}: bar {i}/{n} "
                  f"(taken={len(taken)}, filtered={len(filtered)})")

        # Need a NEXT bar to fill an entry at its open.
        if i + 1 >= n:
            break
        # Skip bars while a trade holds the single slot.
        if i <= open_until_idx:
            continue

        decision_close_ts = int(h1_ts[i]) + _TF_SECONDS["H1"]

        # As-of slices (no lookahead): last fully closed H4 / D1.
        h4_idx = _asof_index(h4_ts, _TF_SECONDS["H4"], decision_close_ts)
        # D1 "current session" = the day containing this H1 bar (its open is known
        # at day start, so using it as the Gann anchor is not lookahead).
        d1_cur = int(np.searchsorted(d1_ts, int(h1_ts[i]), side="right") - 1)
        if h4_idx < SWING_LOOKBACK_H4 or d1_cur < 1:
            continue
        atr = float(atr_h4.iloc[h4_idx])
        if not np.isfinite(atr) or atr <= 0:
            continue

        # Day boundary -> recompute the day's confluence zones + fib structure.
        day = pd.to_datetime(int(h1_ts[i]), unit="s", utc=True).date()
        if day != cached_day:
            h4_slice = h4.iloc[:h4_idx + 1]
            d1_slice = d1.iloc[:d1_cur + 1]
            cached_fib = se.get_h4_fib_structure(h4_slice, SWING_LOOKBACK_H4)
            cached_zones = se.get_confluence_zones(
                h4_slice, d1_slice, atr, atr_mult=CONFLUENCE_ATR_MULT,
                fib_struct=cached_fib)
            cached_day = day
            if fired_day != day:
                fired_zones = set()
                fired_day = day

        if not cached_zones:
            continue

        price = h1_close[i]   # decision uses the just-closed H1 bar's close

        # ── Gate 1: confluence zone hit (price inside a zone band) ──
        zone = None
        for z in cached_zones:
            if z["low"] <= price <= z["high"]:
                zone = z
                break
        if zone is None:
            continue

        # Skip a zone already traded today (live _fired_zones rule).
        zkey = (round(zone["price"], 1), day)
        if zkey in fired_zones:
            continue

        # ── Gate 2/5: bias + zone side (+ polarity flip for D) ──
        h4_slice = h4.iloc[:h4_idx + 1]
        bias = se.get_h4_bias(h4_slice, ema_series=ema_h4.iloc[:h4_idx + 1])
        kind, polarity_flipped = se.classify_zone_for_signal(
            zone, price, use_polarity, h4_slice)

        if bias == "bullish" and kind == "support":
            direction, confirm_dir = "BUY", "buy"
        elif bias == "bearish" and kind == "resistance":
            direction, confirm_dir = "SELL", "sell"
        else:
            continue

        # ── Gate 3: H4 fib structure confluence ──
        # The zone must align with an H4 fib retracement level (within the
        # confluence radius) OR price must sit within the active swing range and
        # the zone itself was built including a fib_* source.
        fib_ok = _fib_structure_ok(zone, cached_fib, atr)
        if not fib_ok:
            continue

        # ── Gate 6: H1 body-close confirmation ──
        h1_slice = h1.iloc[:i + 1]   # last row = just-closed decision bar
        if not se.check_h1_body_close(h1_slice, zone["price"], confirm_dir):
            continue

        # Reaching here = a RAW signal (all core gates except ADX/VP passed).
        counters["raw_signals"] += 1

        # ── Gate 4: ADX > threshold ──
        adx_val = float(adx_h4.iloc[h4_idx]) if np.isfinite(adx_h4.iloc[h4_idx]) else np.nan
        adx_pass = np.isfinite(adx_val) and adx_val > ADX_THRESHOLD
        if not adx_pass:
            continue
        counters["adx_passed"] += 1

        # Build the prospective trade (entry next bar open + spread).
        raw_entry = h1_open[i + 1]
        entry = _apply_spread(direction, raw_entry)
        sl_dist = sl_mult * atr
        tp_dist = tp_mult * atr
        if direction == "BUY":
            sl = round(entry - sl_dist, 2)
            tp = round(entry + tp_dist, 2)
        else:
            sl = round(entry + sl_dist, 2)
            tp = round(entry - tp_dist, 2)

        # ── VP filter (VP configs only) ──
        vp_info = None
        if use_vp:
            counters["vp_eligible"] += 1
            vp_info = _vp_filter(h1, i, d1_cur, atr, zone["price"], price,
                                 direction, tp)

        gate_checklist = {
            "confluence_zone": True, "h4_ema50_bias": True,
            "h4_fib_structure": True, "adx": True,
            "polarity": (polarity_flipped if use_polarity else None),
            "h1_body_close": True,
        }

        # Simulate the outcome regardless (needed for filtered-out analysis).
        sim = _simulate_trade(h1, i + 1, direction, entry, sl, tp)

        record = {
            "config": config_name,
            "entry_time": pd.to_datetime(int(h1_ts[i + 1]), unit="s", utc=True),
            "direction": direction,
            "entry_price": round(entry, 2),
            "sl": sl, "tp": tp,
            "exit_price": sim["exit_price"],
            "exit_time": pd.to_datetime(sim["exit_ts"], unit="s", utc=True),
            "pnl_points": sim["pnl_points"],
            "hit": sim["hit"],
            "risk_points": round(sl_dist / POINT, 1),
            "rr_achieved": round(sim["pnl_points"] / (sl_dist / POINT), 3),
            "zone_price": zone["price"],
            "zone_type": kind,
            "adx_value": round(adx_val, 2),
            "polarity_flipped": (polarity_flipped if use_polarity else None),
            "gate_checklist": gate_checklist,
            "poc_distance_atr": (vp_info["poc_distance_atr"] if vp_info else None),
            "inside_va": (vp_info["inside_va"] if vp_info else None),
            "lvn_path_clear": (vp_info["lvn_path_clear"] if vp_info else None),
        }

        if use_vp and not vp_info["passed"]:
            # Filtered OUT: record which sub-filter(s) failed; do NOT take trade,
            # do NOT occupy the slot, do NOT mark the zone fired.
            record["fail_poc"] = not vp_info["poc_ok"]
            record["fail_va"] = not vp_info["va_ok"]
            record["fail_lvn"] = not vp_info["lvn_ok"]
            filtered.append(record)
            continue

        # TAKEN trade.
        if use_vp:
            counters["vp_passed"] += 1
        taken.append(record)
        fired_zones.add(zkey)
        open_until_idx = sim["exit_idx"]   # hold the slot until the trade exits

    print(f"  {config_name}: DONE — {len(taken)} trades, "
          f"{len(filtered)} filtered, {counters['raw_signals']} raw signals")
    return taken, filtered, counters


def _fib_structure_ok(zone, fib_struct, atr):
    """
    H4 fib-structure gate: the zone must be supported by the H4 fib retracements.

    Passes if EITHER the zone was built from a fib_* source, OR the zone price is
    within CONFLUENCE_ATR_MULT × ATR of any of the 0.382/0.5/0.618 retracement
    levels — i.e. the zone coincides with the active H4 fib structure.

    Params:
        zone (dict): the candidate confluence zone.
        fib_struct (dict): get_h4_fib_structure() result.
        atr (float): current H4 ATR.

    Returns:
        bool: True if the fib-structure confluence holds.
    """
    if any(str(s).lower().startswith("fib_") for s in zone.get("sources", [])):
        return True
    tol = CONFLUENCE_ATR_MULT * atr
    for k in ("fib_382", "fib_500", "fib_618"):
        lvl = fib_struct.get(k)
        if lvl is not None and abs(zone["price"] - lvl) <= tol:
            return True
    return False


# ── Metrics + persistence ─────────────────────────────────
def _summarize(config_name, trades, counters, use_vp):
    """
    Compute headline metrics for one configuration.

    Params:
        config_name (str): e.g. "Profile_D_VP".
        trades (list[dict]): taken trades.
        counters (dict): raw/adx/vp counters from run_config.
        use_vp (bool): whether this is a VP config.

    Returns:
        dict: headline metric row.
    """
    n = len(trades)
    pnls = np.array([t["pnl_points"] for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    win_rate = (len(wins) / n * 100.0) if n else 0.0
    gross_win = wins.sum()
    gross_loss = abs(losses.sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
    expectancy = pnls.mean() if n else 0.0
    avg_rr = np.mean([t["rr_achieved"] for t in trades]) if n else 0.0

    # Max drawdown on the cumulative-points equity curve.
    if n:
        equity = np.cumsum(pnls)
        peak = np.maximum.accumulate(equity)
        max_dd = float((peak - equity).max())
    else:
        max_dd = 0.0

    raw = counters["raw_signals"]
    adx_pass_rate = (counters["adx_passed"] / raw * 100.0) if raw else 0.0
    if use_vp and counters["vp_eligible"]:
        vp_pass_rate = counters["vp_passed"] / counters["vp_eligible"] * 100.0
    else:
        vp_pass_rate = float("nan")

    return {
        "Config": config_name,
        "Trades": n,
        "WinRate%": round(win_rate, 2),
        "PF": round(pf, 3) if np.isfinite(pf) else pf,
        "AvgRR": round(float(avg_rr), 3),
        "Expectancy": round(float(expectancy), 2),
        "MaxDD_pts": round(max_dd, 1),
        "ADX_PassRate%": round(adx_pass_rate, 2),
        "VP_PassRate%": (round(vp_pass_rate, 2) if np.isfinite(vp_pass_rate) else ""),
        "RawSignals": raw,
        "ADXPassed": counters["adx_passed"],
        "VPEligible": counters["vp_eligible"],
        "VPPassed": counters["vp_passed"],
    }


def _trades_to_frame(trades):
    """Flatten a list of trade dicts (gate_checklist -> JSON string) to a DataFrame."""
    import json
    rows = []
    for t in trades:
        r = dict(t)
        r["gate_checklist"] = json.dumps(r.get("gate_checklist", {}))
        rows.append(r)
    return pd.DataFrame(rows)


def main():
    """
    Load data, precompute H4 indicators once, run all four configs, persist
    per-config trade/filter/summary CSVs and a combined summary.

    Returns:
        int: 0 on success.
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("[backtest_vp] Loading CSV data ...")
    h1 = _load_csv("xauusd_h1.csv")
    h4 = _load_csv("xauusd_h4.csv")
    d1 = _load_csv("xauusd_d1.csv")
    print(f"[backtest_vp] H1={len(h1)} H4={len(h4)} D1={len(d1)} bars")

    print("[backtest_vp] Precomputing H4 indicators (ATR/EMA50/ADX) ...")
    atr_h4 = se.get_atr(h4, period=14)
    ema_h4 = se.get_ema(h4, period=50)
    adx_h4, _ = se.get_adx(h4, period=14, threshold=ADX_THRESHOLD)

    configs = [("D", False), ("D", True), ("R", False), ("R", True)]
    summaries = []
    for profile_key, use_vp in configs:
        taken, filtered, counters = run_config(
            profile_key, use_vp, h1, h4, d1, atr_h4, ema_h4, adx_h4)
        config_name = f"Profile_{profile_key}_{'VP' if use_vp else 'Baseline'}"

        _trades_to_frame(taken).to_csv(_RESULTS_DIR / f"{config_name}.csv",
                                       index=False)
        if use_vp:
            _trades_to_frame(filtered).to_csv(
                _RESULTS_DIR / f"{config_name}_filtered.csv", index=False)

        summ = _summarize(config_name, taken, counters, use_vp)
        pd.DataFrame([summ]).to_csv(
            _RESULTS_DIR / f"{config_name}_summary.csv", index=False)
        summaries.append(summ)
        print(f"[backtest_vp] {config_name}: trades={summ['Trades']} "
              f"win%={summ['WinRate%']} PF={summ['PF']} "
              f"exp={summ['Expectancy']} maxDD={summ['MaxDD_pts']}")

    pd.DataFrame(summaries).to_csv(_RESULTS_DIR / "all_summaries.csv", index=False)
    print(f"\n[backtest_vp] All 4 configs complete. Results in {_RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
