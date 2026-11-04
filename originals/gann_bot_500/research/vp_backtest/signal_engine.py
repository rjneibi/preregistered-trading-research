"""
signal_engine.py — Self-contained reconstruction of the gann_bot gate logic.

This module re-implements (does NOT import) the parts of the live bot's
signals.py / structure.py / levels.py needed to backtest Profile D and Profile R
on saved CSV data. Every function below is a clean-room reimplementation working
purely on pandas DataFrames; nothing here imports bot.py, signals.py,
structure.py, broker.py or notifier.py.

Indicators (ATR, EMA, ADX) follow the SAME Wilder-smoothing conventions as the
live structure.py so the reconstructed gates line up with production behaviour.

Timeframe note: the live bot sizes its zones off H1 ATR, but for this research
backtest every ATR-based quantity (zone width, confluence clustering, SL/TP) is
derived from a single H4 ATR series, matching the spec's get_atr(df_h4, ...).
This is a deliberate, self-consistent reconstruction choice and is documented at
each call site.
"""

import numpy as np
import pandas as pd

# Fibonacci retracement ratios (mirrors config.FIB_LEVELS).
_FIB_RATIOS = [0.382, 0.500, 0.618, 0.786]
# Gann angular increments (mirrors config.GANN_DEGREES).
_GANN_DEGREES = [45, 90, 135, 180, 225, 270, 315, 360]


# ── Indicators ────────────────────────────────────────────
def get_atr(df_h4, period=14):
    """
    Wilder-smoothed Average True Range on H4 data.

    Seed = SMA of the first `period` true ranges; thereafter
    ATR = (prev_ATR × (period-1) + TR) / period  (matches broker.get_atr).

    Params:
        df_h4 (DataFrame): H4 bars with ['high', 'low', 'close'], oldest first.
        period (int): ATR period (default 14).

    Returns:
        pandas.Series: ATR aligned to df_h4.index (NaN until warmed up).
    """
    high = df_h4["high"].to_numpy(dtype=float)
    low = df_h4["low"].to_numpy(dtype=float)
    close = df_h4["close"].to_numpy(dtype=float)
    n = len(df_h4)
    atr = np.full(n, np.nan)
    if n < period + 1:
        return pd.Series(atr, index=df_h4.index)

    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                    abs(high[i] - close[i - 1]),
                    abs(low[i] - close[i - 1]))

    # Wilder seed at index `period` = SMA of TR[1..period].
    atr[period] = tr[1:period + 1].mean()
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return pd.Series(atr, index=df_h4.index)


def get_ema(df_h4, period=50):
    """
    Exponential Moving Average of H4 close (SMA-seeded, matching structure._ema).

    Params:
        df_h4 (DataFrame): H4 bars with ['close'], oldest first.
        period (int): EMA period (default 50).

    Returns:
        pandas.Series: EMA50 aligned to df_h4.index (NaN until seeded).
    """
    close = df_h4["close"].to_numpy(dtype=float)
    n = len(close)
    ema = np.full(n, np.nan)
    if n == 0:
        return pd.Series(ema, index=df_h4.index)
    if n < period:
        # Fall back to running mean (live _ema does the same for short series).
        run = np.cumsum(close) / np.arange(1, n + 1)
        return pd.Series(run, index=df_h4.index)

    k = 2.0 / (period + 1.0)
    ema[period - 1] = close[:period].mean()  # SMA seed
    for i in range(period, n):
        ema[i] = close[i] * k + ema[i - 1] * (1.0 - k)
    return pd.Series(ema, index=df_h4.index)


def get_adx(df_h4, period=14, threshold=25):
    """
    Wilder ADX on H4 data, plus a boolean "passes threshold" series.

    Re-implements structure.get_adx's math (Wilder RMA of TR/+DM/-DM, DI, DX,
    then RMA of DX) but vectorised over the whole history.

    Params:
        df_h4 (DataFrame): H4 bars with ['high', 'low', 'close'], oldest first.
        period (int): ADX period (default 14).
        threshold (float): ADX trend-strength cutoff (default 25).

    Returns:
        tuple(pandas.Series, pandas.Series):
            (adx values aligned to index, boolean adx_pass = adx > threshold).
    """
    high = df_h4["high"].to_numpy(dtype=float)
    low = df_h4["low"].to_numpy(dtype=float)
    close = df_h4["close"].to_numpy(dtype=float)
    n = len(df_h4)
    adx = np.full(n, np.nan)
    if n < 2 * period + 1:
        s = pd.Series(adx, index=df_h4.index)
        return s, (s > threshold)

    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        dn = low[i - 1] - low[i]
        plus_dm[i] = up if (up > dn and up > 0) else 0.0
        minus_dm[i] = dn if (dn > up and dn > 0) else 0.0
        tr[i] = max(high[i] - low[i],
                    abs(high[i] - close[i - 1]),
                    abs(low[i] - close[i - 1]))

    def _rma(arr):
        """Wilder running moving average over arr[1:] (arr[0] is the dummy seed)."""
        out = np.full(n, np.nan)
        first = 1 + period  # first index with a full window
        if first > n:
            return out
        out[period] = arr[1:period + 1].sum()  # Wilder sum-seed (kept on scale)
        for i in range(period + 1, n):
            out[i] = out[i - 1] - (out[i - 1] / period) + arr[i]
        return out

    sm_tr = _rma(tr)
    sm_plus = _rma(plus_dm)
    sm_minus = _rma(minus_dm)

    dx = np.full(n, np.nan)
    for i in range(period, n):
        if not np.isfinite(sm_tr[i]) or sm_tr[i] == 0:
            dx[i] = 0.0
            continue
        plus_di = 100.0 * sm_plus[i] / sm_tr[i]
        minus_di = 100.0 * sm_minus[i] / sm_tr[i]
        di_sum = plus_di + minus_di
        dx[i] = 100.0 * abs(plus_di - minus_di) / di_sum if di_sum != 0 else 0.0

    # ADX = Wilder RMA of DX, seeded `period` bars after DX starts.
    dx_start = period
    seed_idx = dx_start + period
    if seed_idx < n:
        adx[seed_idx] = np.nanmean(dx[dx_start:seed_idx + 1])
        for i in range(seed_idx + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    s = pd.Series(adx, index=df_h4.index)
    return s, (s > threshold)


# ── H4 structure ──────────────────────────────────────────
def get_h4_fib_structure(df_h4, lookback=50):
    """
    Identify the H4 swing high/low over `lookback` bars and its fib retracements.

    Swing direction follows structure.find_swing: "up" if the last close sits
    above the midpoint of the swing range, else "down". Retracement levels are
    placed direction-aware (mirrors levels.fib_retracements).

    Params:
        df_h4 (DataFrame): H4 bars with ['high', 'low', 'close'], oldest first.
        lookback (int): bars to scan for the swing (default 50).

    Returns:
        dict: {swing_high, swing_low, swing_dir, fib_382, fib_500, fib_618,
               fib_786}. Values are None if df_h4 is empty.
    """
    if df_h4 is None or len(df_h4) == 0:
        return {"swing_high": None, "swing_low": None, "swing_dir": "down",
                "fib_382": None, "fib_500": None, "fib_618": None,
                "fib_786": None}

    window = df_h4.iloc[-lookback:] if len(df_h4) > lookback else df_h4
    swing_high = float(window["high"].max())
    swing_low = float(window["low"].min())
    rng = swing_high - swing_low
    mid = (swing_high + swing_low) / 2.0
    last_close = float(window["close"].iloc[-1])
    direction = "up" if last_close > mid else "down"

    out = {"swing_high": round(swing_high, 2), "swing_low": round(swing_low, 2),
           "swing_dir": direction}
    keys = ["fib_382", "fib_500", "fib_618", "fib_786"]
    for key, ratio in zip(keys, _FIB_RATIOS):
        if direction == "up":
            out[key] = round(swing_high - ratio * rng, 2)
        else:
            out[key] = round(swing_low + ratio * rng, 2)
    return out


def get_h4_bias(df_h4, ema_series=None, period=50):
    """
    EMA50-based H4 trend bias ("bullish" if last close > EMA50, else "bearish").

    Params:
        df_h4 (DataFrame): H4 bars with ['close'], oldest first.
        ema_series (pandas.Series, optional): precomputed EMA50 to avoid recompute.
        period (int): EMA period if ema_series is not supplied.

    Returns:
        str: "bullish" or "bearish".
    """
    if df_h4 is None or len(df_h4) == 0:
        return "bearish"
    if ema_series is None:
        ema_series = get_ema(df_h4, period)
    ema50 = ema_series.iloc[-1]
    last_close = float(df_h4["close"].iloc[-1])
    if not np.isfinite(ema50):
        return "bearish"
    return "bullish" if last_close > ema50 else "bearish"


def check_zone_polarity(df_h4, zone_price, side, lookback=10):
    """
    Re-evaluate a zone's polarity from the last `lookback` CLOSED H4 closes.

    Mirrors structure.check_zone_polarity: a support that price has CLOSED below
    has flipped to resistance, and a resistance price has CLOSED above has
    flipped to support.

    Params:
        df_h4 (DataFrame): H4 bars with ['close'], oldest first. The caller must
            pass only bars up to (and including) the last CLOSED bar — no
            lookahead.
        zone_price (float): the zone level being tested.
        side (str): the zone's current side, "support" or "resistance".
        lookback (int): number of recent closed H4 closes to inspect (default 10).

    Returns:
        str: the (possibly flipped) side. Non-directional sides are returned
             unchanged.
    """
    if df_h4 is None or len(df_h4) == 0:
        return side
    closes = df_h4["close"].to_numpy(dtype=float)[-lookback:]
    if len(closes) == 0:
        return side
    if side == "support":
        return "resistance" if np.any(closes < zone_price) else "support"
    if side == "resistance":
        return "support" if np.any(closes > zone_price) else "resistance"
    return side


# ── Level math (Gann SQ9 + Fibonacci pivots) ──────────────
def _gann_levels(price, degrees=_GANN_DEGREES):
    """
    Gann Square-of-Nine support/resistance levels around `price`.

    *** APPROXIMATION NOTICE ***
    This is a SIMPLIFIED Square-of-Nine approximation. It normalises the anchor
    price into [1, 1000) (recording the power-of-ten scale), takes the square
    root, steps outward by degree/360 of a full rotation, then squares back and
    re-applies the scale. The normalisation scheme and the choice to treat one
    full 360° rotation as +1.0 on the square-root axis is UNVERIFIED against any
    canonical Gann reference — it merely reproduces the live levels.gann_levels()
    so the reconstructed zones match production. Do not treat these as
    authoritative Gann levels.

    Params:
        price (float): anchor price (the day's open).
        degrees (list[int]): angular increments.

    Returns:
        dict: {"R45":x, ..., "S45":x, ...}; empty if price <= 0.
    """
    if price <= 0:
        return {}
    scale = 1.0
    norm = float(price)
    while norm > 1000:
        norm /= 10.0
        scale *= 10.0
    root = np.sqrt(norm)
    out = {}
    for deg in degrees:
        inc = deg / 360.0
        out[f"R{deg}"] = round((root + inc) ** 2 * scale, 2)
        out[f"S{deg}"] = round((root - inc) ** 2 * scale, 2)
    return out


def _fibonacci_pivots(high, low, close):
    """
    Fibonacci-style daily pivots from prior-day H/L/C (mirrors levels.fibonacci_pivots).

    Params:
        high (float): previous day's high.
        low (float): previous day's low.
        close (float): previous day's close.

    Returns:
        dict: {"PP","R1","R2","R3","S1","S2","S3"} -> float.
    """
    rng = high - low
    pp = (high + low + close) / 3.0
    return {
        "PP": round(pp, 2),
        "R1": round(pp + 0.382 * rng, 2),
        "R2": round(pp + 0.618 * rng, 2),
        "R3": round(pp + 1.000 * rng, 2),
        "S1": round(pp - 0.382 * rng, 2),
        "S2": round(pp - 0.618 * rng, 2),
        "S3": round(pp - 1.000 * rng, 2),
    }


def get_confluence_zones(df_h4, df_d1, atr, n_gann=8, n_fib=6, atr_mult=0.5,
                         daily_open=None, fib_struct=None):
    """
    Build confluence zones by clustering Gann SQ9 + Fibonacci-pivot + fib-retrace
    levels that fall within `atr_mult × ATR` of each other.

    The levels are computed from:
      * Gann Square of Nine around the day's open (see _gann_levels APPROXIMATION
        NOTICE — the normalisation is unverified),
      * Fibonacci daily pivots from the previous D1 bar's H/L/C,
      * H4 fib retracements (so the H4 fib structure participates in confluence).

    Nearby levels are merged into a single zone whose price is the mean of its
    members; its `zone_type` is voted from member sources (resistance/support/
    neutral) and its `width` is `2 × atr_mult × ATR`.

    Params:
        df_h4 (DataFrame): H4 bars up to the decision bar (no lookahead).
        df_d1 (DataFrame): D1 bars up to the decision day (no lookahead). The last
            row is treated as the current (forming) day, the prior row as the last
            completed day for pivots.
        atr (float): current H4 ATR (drives clustering distance + zone width).
        n_gann (int): how many Gann degrees to use (kept for signature parity;
            all configured degrees are used).
        n_fib (int): kept for signature parity.
        atr_mult (float): clustering radius / half-width multiplier (default 0.5,
            mirrors config.CONFLUENCE_ATR_MULT).
        daily_open (float, optional): override for the day's open (Gann anchor).
            Defaults to df_d1's last open.
        fib_struct (dict, optional): precomputed get_h4_fib_structure() result.

    Returns:
        list[dict]: zone dicts {price, zone_type, width, sources, swing_dir}
                    sorted by price descending. Empty if inputs are insufficient.
    """
    if atr is None or atr <= 0 or df_d1 is None or len(df_d1) < 2:
        return []

    if daily_open is None:
        daily_open = float(df_d1["open"].iloc[-1])
    prev = df_d1.iloc[-2]

    if fib_struct is None:
        fib_struct = get_h4_fib_structure(df_h4)

    all_levels = {}
    all_levels.update(_gann_levels(daily_open))
    all_levels.update(_fibonacci_pivots(float(prev["high"]), float(prev["low"]),
                                        float(prev["close"])))
    for k in ("fib_382", "fib_500", "fib_618", "fib_786"):
        if fib_struct.get(k) is not None:
            all_levels[k] = fib_struct[k]

    swing_dir = fib_struct.get("swing_dir")

    # Sort sources by price, then greedily cluster within atr_mult × ATR.
    items = sorted(((float(v), s) for s, v in all_levels.items()
                    if v is not None), key=lambda t: t[0])
    radius = atr_mult * atr
    zones = []
    cluster = []
    for price, src in items:
        if not cluster:
            cluster = [(price, src)]
            continue
        if price - cluster[-1][0] <= radius:
            cluster.append((price, src))
        else:
            zones.append(_finalise_zone(cluster, atr_mult, atr, swing_dir))
            cluster = [(price, src)]
    if cluster:
        zones.append(_finalise_zone(cluster, atr_mult, atr, swing_dir))

    zones.sort(key=lambda z: z["price"], reverse=True)
    return zones


def _finalise_zone(cluster, atr_mult, atr, swing_dir):
    """
    Collapse a cluster of (price, source) members into one zone dict.

    Params:
        cluster (list[tuple]): [(price, source), ...] members of one cluster.
        atr_mult (float): half-width multiplier.
        atr (float): current ATR.
        swing_dir (str): H4 swing direction for direction-aware fib classification.

    Returns:
        dict: {price, zone_type, width, sources, swing_dir, low, high}.
    """
    prices = [p for p, _ in cluster]
    sources = [s for _, s in cluster]
    center = round(sum(prices) / len(prices), 2)
    half = atr_mult * atr

    # Vote zone_type from member classifications.
    votes = {"support": 0, "resistance": 0, "neutral": 0}
    for s in sources:
        votes[_classify_source(s, swing_dir)] += 1
    zone_type = max(votes.items(), key=lambda kv: kv[1])[0]

    return {
        "price": center,
        "zone_type": zone_type,
        "width": round(2 * half, 2),
        "low": round(center - half, 2),
        "high": round(center + half, 2),
        "sources": sources,
        "swing_dir": swing_dir,
    }


def _classify_source(source, swing_dir=None):
    """
    Classify a level source as "support"/"resistance"/"neutral" (mirrors
    signals._classify_zone, including the direction-aware fib handling).

    Params:
        source (str): source label (e.g. "R90", "S2", "fib_618", "PP").
        swing_dir (str): H4 swing direction ("up"/"down") for fib levels.

    Returns:
        str: "support", "resistance", or "neutral".
    """
    s = source.upper()
    if s == "PP":
        return "neutral"
    if s.startswith("R") and not s.startswith("FIB") or "_R" in s:
        return "resistance"
    if s.startswith("S") or "_S" in s:
        return "support"
    if swing_dir == "down":
        if "FIB_618" in s or "FIB_786" in s:
            return "resistance"
        if "FIB_382" in s or "FIB_500" in s:
            return "support"
    if "FIB_618" in s or "FIB_786" in s:
        return "support"
    if "FIB_382" in s or "FIB_500" in s:
        return "resistance"
    return "neutral"


def check_h1_body_close(df_h1, zone_price, direction):
    """
    Body-close confirmation of a level break on the most recent CLOSED H1 bar.

    Mirrors structure.h1_close_confirmed: only the body (open/close) counts —
    wicks are ignored. The caller passes H1 bars sliced so the LAST row is the
    just-closed bar at the decision point (no lookahead).

    Params:
        df_h1 (DataFrame): H1 bars with ['open', 'close'], oldest first, last row
            = last closed bar.
        zone_price (float): the level being tested.
        direction (str): "buy" (expects an upward break) or "sell" (downward).

    Returns:
        bool: True if the last closed H1 body fully crossed the level.
    """
    if df_h1 is None or len(df_h1) < 1:
        return False
    o = float(df_h1["open"].iloc[-1])
    c = float(df_h1["close"].iloc[-1])
    d = direction.lower()
    if d == "buy":
        return c > zone_price and o < zone_price
    if d == "sell":
        return c < zone_price and o > zone_price
    return False


def classify_zone_for_signal(zone, current_price, use_polarity, df_h4_asof):
    """
    Resolve a zone's effective side for signal direction, applying the same rules
    as signals.evaluate_signal (direction-aware fib, PP-by-approach, and the
    optional H4 polarity flip for Profile D).

    Params:
        zone (dict): a confluence zone (must carry 'sources', 'zone_type',
            'swing_dir', 'price').
        current_price (float): current price.
        use_polarity (bool): True for Profile D (apply polarity flip), False for R.
        df_h4_asof (DataFrame): H4 bars up to the decision bar (for polarity).

    Returns:
        tuple(str, bool): (effective_side, polarity_flipped)
            effective_side in {"support","resistance","neutral"}.
    """
    # Start from the zone's voted type; refine PP by approach direction.
    kind = zone["zone_type"]
    if any(s.upper() == "PP" for s in zone.get("sources", [])) and \
            len(zone.get("sources", [])) == 1:
        if current_price < zone["price"]:
            kind = "resistance"
        elif current_price > zone["price"]:
            kind = "support"

    polarity_flipped = False
    if use_polarity and kind in ("support", "resistance"):
        new_kind = check_zone_polarity(df_h4_asof, zone["price"], kind)
        polarity_flipped = (new_kind != kind)
        kind = new_kind
    return kind, polarity_flipped
