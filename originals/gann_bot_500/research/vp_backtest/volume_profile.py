"""
volume_profile.py — Self-contained Volume Profile calculator for the VP backtest.

This module operates ONLY on pandas DataFrames / plain dicts. It has ZERO
MetaTrader5 (or any live-bot) dependency by design, so it can be unit-tested and
reused outside a running terminal.

A "volume profile" here is a mapping from price bucket -> cumulative volume,
built by spreading each bar's tick_volume uniformly across the bar's high–low
range. From that profile we derive:

  * POC   — Point of Control (highest-volume price bucket)
  * VA    — Value Area (VAH/VAL), the contiguous band around the POC that holds
            `va_pct` of total volume
  * HVN   — High Volume Nodes (top-n buckets by volume)
  * LVN   — Low Volume Nodes (bottom-n buckets by volume)

All functions carry docstrings and defend against empty profiles / out-of-range
prices by returning None (never raising) so callers can branch cleanly.
"""

import math


def build_volume_profile(df, price_bucket_size=0.50):
    """
    Build a volume-by-price profile from OHLCV bars.

    Each bar's tick_volume is distributed UNIFORMLY across the price buckets its
    high–low range spans. Price buckets are snapped to the nearest
    `price_bucket_size` increment so identical levels across bars accumulate.

    Params:
        df: DataFrame (or anything iterable of rows) exposing columns
            ['high', 'low', 'close', 'tick_volume'].
        price_bucket_size (float): width of each price bucket (default 0.50).

    Returns:
        dict: {price_level (float): cumulative_volume (float)}. Empty dict if the
              input has no rows.
    """
    profile = {}
    if df is None or len(df) == 0 or price_bucket_size <= 0:
        return profile

    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    vols = df["tick_volume"].to_numpy()

    for high, low, vol in zip(highs, lows, vols):
        if vol <= 0:
            continue
        lo = min(low, high)
        hi = max(low, high)
        # Snap the band edges to the bucket grid.
        start = _round_to_bucket(lo, price_bucket_size)
        end = _round_to_bucket(hi, price_bucket_size)
        n_buckets = int(round((end - start) / price_bucket_size)) + 1
        if n_buckets <= 1:
            # Whole bar sits inside one bucket.
            profile[start] = profile.get(start, 0.0) + float(vol)
            continue
        vol_per_bucket = float(vol) / n_buckets
        for k in range(n_buckets):
            level = _round_to_bucket(start + k * price_bucket_size, price_bucket_size)
            profile[level] = profile.get(level, 0.0) + vol_per_bucket

    return profile


def _round_to_bucket(price, price_bucket_size):
    """
    Snap a price to the nearest `price_bucket_size` increment.

    Params:
        price (float): raw price.
        price_bucket_size (float): bucket grid spacing.

    Returns:
        float: price rounded to the nearest bucket boundary (2 dp).
    """
    return round(round(price / price_bucket_size) * price_bucket_size, 2)


def get_poc(profile_dict):
    """
    Return the Point of Control — the price bucket with the highest volume.

    Params:
        profile_dict (dict): output of build_volume_profile().

    Returns:
        float or None: POC price level, or None for an empty profile.
    """
    if not profile_dict:
        return None
    return max(profile_dict.items(), key=lambda kv: kv[1])[0]


def get_value_area(profile_dict, va_pct=0.70):
    """
    Compute the Value Area High/Low containing `va_pct` of total volume.

    Standard market-profile expansion: start at the POC bucket, then repeatedly
    step to whichever adjacent side (one bucket above vs one bucket below the
    current band) holds more volume, accumulating until the band's volume reaches
    `va_pct` of the total.

    Params:
        profile_dict (dict): output of build_volume_profile().
        va_pct (float): fraction of total volume the value area must hold
            (default 0.70).

    Returns:
        tuple or None: (VAH, VAL) value-area high/low, or None for empty profile.
    """
    if not profile_dict:
        return None

    levels = sorted(profile_dict.keys())
    total = sum(profile_dict.values())
    if total <= 0:
        return None

    poc = get_poc(profile_dict)
    poc_idx = levels.index(poc)

    lo_idx = hi_idx = poc_idx
    acc = profile_dict[poc]
    target = va_pct * total

    while acc < target and (lo_idx > 0 or hi_idx < len(levels) - 1):
        vol_below = profile_dict[levels[lo_idx - 1]] if lo_idx > 0 else -1.0
        vol_above = profile_dict[levels[hi_idx + 1]] if hi_idx < len(levels) - 1 else -1.0

        if vol_above >= vol_below:
            if hi_idx < len(levels) - 1:
                hi_idx += 1
                acc += profile_dict[levels[hi_idx]]
            elif lo_idx > 0:
                lo_idx -= 1
                acc += profile_dict[levels[lo_idx]]
        else:
            if lo_idx > 0:
                lo_idx -= 1
                acc += profile_dict[levels[lo_idx]]
            elif hi_idx < len(levels) - 1:
                hi_idx += 1
                acc += profile_dict[levels[hi_idx]]

    vah = levels[hi_idx]
    val = levels[lo_idx]
    return (vah, val)


def classify_price_vs_profile(price, poc, vah, val, price_bucket_size=0.50):
    """
    Classify where `price` sits relative to the POC and Value Area.

    Params:
        price (float): the price to classify.
        poc (float): Point of Control.
        vah (float): Value Area High.
        val (float): Value Area Low.
        price_bucket_size (float): used for the "at_poc" tolerance
            (within 0.5 × bucket of the POC).

    Returns:
        str: one of "at_poc", "above_va", "below_va", "inside_va".
             Returns "unknown" if any reference level is None.
    """
    if poc is None or vah is None or val is None:
        return "unknown"
    if abs(price - poc) <= 0.5 * price_bucket_size:
        return "at_poc"
    if price > vah:
        return "above_va"
    if price < val:
        return "below_va"
    return "inside_va"


def get_nearest_hvn(profile_dict, price, n_top=5, direction="above"):
    """
    Return the nearest High Volume Node above or below `price`.

    HVNs are the top-`n_top` buckets by volume. Among those, the nearest one
    strictly above (or below) the current price is returned.

    Params:
        profile_dict (dict): output of build_volume_profile().
        price (float): reference price.
        n_top (int): how many top-volume buckets count as HVNs.
        direction (str): "above" or "below".

    Returns:
        float or None: nearest HVN price in the requested direction, or None if
                       none exists / profile empty.
    """
    if not profile_dict:
        return None
    hvns = [lvl for lvl, _ in sorted(profile_dict.items(),
                                     key=lambda kv: kv[1], reverse=True)[:n_top]]
    return _nearest_in_direction(hvns, price, direction)


def get_nearest_lvn(profile_dict, price, n_bottom=5, direction="above"):
    """
    Return the nearest Low Volume Node above or below `price`.

    LVNs are the bottom-`n_bottom` buckets by volume — thin price areas through
    which price tends to move quickly. Among those, the nearest one strictly
    above (or below) the current price is returned.

    Params:
        profile_dict (dict): output of build_volume_profile().
        price (float): reference price.
        n_bottom (int): how many lowest-volume buckets count as LVNs.
        direction (str): "above" or "below".

    Returns:
        float or None: nearest LVN price in the requested direction, or None if
                       none exists / profile empty.
    """
    if not profile_dict:
        return None
    lvns = [lvl for lvl, _ in sorted(profile_dict.items(),
                                     key=lambda kv: kv[1])[:n_bottom]]
    return _nearest_in_direction(lvns, price, direction)


def _nearest_in_direction(levels, price, direction):
    """
    Pick the level nearest to `price` strictly in the given direction.

    Params:
        levels (list[float]): candidate price levels.
        price (float): reference price.
        direction (str): "above" (levels > price) or "below" (levels < price).

    Returns:
        float or None: nearest qualifying level, or None.
    """
    if direction == "above":
        cands = [l for l in levels if l > price]
        return min(cands) if cands else None
    if direction == "below":
        cands = [l for l in levels if l < price]
        return max(cands) if cands else None
    return None
