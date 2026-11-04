"""
levels.py — Core math engine for gann_bot.

Three independent level calculators plus a zone builder:

  * gann_levels()      — Gann Square of Nine support/resistance levels
  * fibonacci_pivots() — Fibonacci-style daily pivot points
  * fib_retracements() — Fibonacci retracements off an H4 swing
  * build_zones()      — merges all levels into ATR-width price zones

Every calculation is logged to gannbot.log so the daily level map is auditable.
All tunables (degrees, fib ratios, zone width) come from config.py.
"""

import math

import config
from logsetup import get_logger

log = get_logger("levels")


# ── 2A. Gann Square of Nine ───────────────────────────────
def gann_levels(price: float, degrees: list) -> dict:
    """
    Compute Gann Square of Nine support/resistance levels around a price.

    Standard Square of Nine method: take the square root of the (normalized)
    price, then step outward by degree/360 of a full rotation in each direction.

    Params:
        price (float): the anchor price (typically today's Daily open).
        degrees (list): list of angular increments, e.g. [45, 90, ..., 360].

    Returns:
        dict: {"R45": x, "R90": x, ..., "S45": x, "S90": x, ...}
              R* are levels above price, S* are levels below.
    """
    if price <= 0:
        log.error("gann_levels called with non-positive price: %s", price)
        return {}

    # 1-2. Normalize price into [1, 1000) and remember the scale factor.
    scale_factor = 1.0
    norm = float(price)
    while norm > 1000:
        norm /= 10.0
        scale_factor *= 10.0

    root = math.sqrt(norm)
    result = {}

    for deg in degrees:
        increment = deg / 360.0  # one full cycle = 1.0
        up = (root + increment) ** 2 * scale_factor
        dn = (root - increment) ** 2 * scale_factor
        result[f"R{deg}"] = round(up, 2)
        result[f"S{deg}"] = round(dn, 2)

    log.info("Gann levels @ price=%.2f (scale=%.0f): %s", price, scale_factor, result)
    return result


# ── 2B. Pivot Points (Fibonacci style) ────────────────────
def fibonacci_pivots(high: float, low: float, close: float) -> dict:
    """
    Compute Fibonacci-style daily pivot points from prior-day H/L/C.

    Params:
        high (float): previous day's high.
        low (float): previous day's low.
        close (float): previous day's close.

    Returns:
        dict: {"PP", "R1", "R2", "R3", "S1", "S2", "S3"} -> float
    """
    rng = high - low
    pp = (high + low + close) / 3.0

    result = {
        "PP": round(pp, 2),
        "R1": round(pp + 0.382 * rng, 2),
        "R2": round(pp + 0.618 * rng, 2),
        "R3": round(pp + 1.000 * rng, 2),
        "S1": round(pp - 0.382 * rng, 2),
        "S2": round(pp - 0.618 * rng, 2),
        "S3": round(pp - 1.000 * rng, 2),
    }

    log.info("Fibonacci pivots H=%.2f L=%.2f C=%.2f: %s", high, low, close, result)
    return result


# ── 2C. Fibonacci Retracements off H4 Swing ───────────────
def fib_retracements(swing_high: float, swing_low: float, direction: str) -> dict:
    """
    Compute Fibonacci retracement levels off an H4 swing.

    Params:
        swing_high (float): swing high price.
        swing_low (float): swing low price.
        direction (str): "up" (uptrend retracing down from high) or
                         "down" (downtrend retracing up from low).

    Returns:
        dict: {"fib_382": x, "fib_500": x, "fib_618": x, "fib_786": x}
    """
    rng = swing_high - swing_low
    ratios = config.FIB_LEVELS  # [0.382, 0.500, 0.618, 0.786]
    keys = ["fib_382", "fib_500", "fib_618", "fib_786"]
    result = {}

    for key, ratio in zip(keys, ratios):
        if direction == "up":
            # Retrace down from the swing high.
            result[key] = round(swing_high - ratio * rng, 2)
        else:
            # Retrace up from the swing low.
            result[key] = round(swing_low + ratio * rng, 2)

    log.info(
        "Fib retracements swing_h=%.2f swing_l=%.2f dir=%s: %s",
        swing_high, swing_low, direction, result,
    )
    return result


# ── 2D. Zone builder ──────────────────────────────────────
def _zone_kind(source: str) -> str:
    """
    Classify a zone source label as "resistance", "support", or "neutral".

    Pure labelling used by the dashboard/state file (does not affect signal
    logic, which classifies independently). Mapping:
        R*/_R*, fib_382, fib_500 -> resistance
        S*/_S*, fib_618, fib_786 -> support
        PP and anything else     -> neutral

    Params:
        source (str): zone source label, e.g. "R90", "S1", "fib_618", "PP".

    Returns:
        str: "resistance", "support", or "neutral".
    """
    s = source.upper()
    if s == "PP":
        return "neutral"
    if s.startswith("R") or "_R" in s:
        return "resistance"
    if s.startswith("S") or "_S" in s:
        return "support"
    if "FIB_618" in s or "FIB_786" in s:
        return "support"
    if "FIB_382" in s or "FIB_500" in s:
        return "resistance"
    return "neutral"


def build_zones(all_levels: dict, atr: float, zone_mult: float,
                current_price: float, fib_swing_dir: str = None) -> list:
    """
    Convert a merged level dict into a list of ATR-width price zones.

    Each zone spans level ± (atr × zone_mult) and carries its source label and a
    "kind" classification so downstream logic and the dashboard can show what
    produced it. Zones whose level is more than 10 × ATR away from the current
    price are dropped as irrelevant (they cannot be reached intraday).

    Params:
        all_levels (dict): merged {source_name: price} from all calculators.
        atr (float): current ATR (typically H1) used to size the zone.
        zone_mult (float): half-width multiplier (config.ATR_ZONE_WIDTH_MULT).
        current_price (float): current price, used to filter distant zones.
        fib_swing_dir (str): "up" or "down" — the H4 swing direction the fib
            retracements were computed off (structure.find_swing). Stamped as
            "swing_dir" on fib_* zones so signals._classify_zone can classify
            them direction-aware; Gann/pivot zones get swing_dir=None. Optional
            (default None) so legacy callers keep the old static behaviour.

    Returns:
        list: zone dicts {"level", "low", "high", "source", "kind", "swing_dir"}
              sorted by price desc.
    """
    half = atr * zone_mult
    max_dist = 10.0 * atr
    zones = []
    filtered = 0

    for source, level in all_levels.items():
        if level is None:
            continue
        # Drop zones too far from price to matter (only when ATR is known).
        if atr > 0 and abs(float(level) - current_price) > max_dist:
            filtered += 1
            continue
        zones.append({
            "level": round(float(level), 2),
            "low": round(float(level) - half, 2),
            "high": round(float(level) + half, 2),
            "source": source,
            "kind": _zone_kind(source),
            # Direction context for fib retracement zones only (None otherwise).
            "swing_dir": (fib_swing_dir
                          if source.lower().startswith("fib_") else None),
        })

    zones.sort(key=lambda z: z["level"], reverse=True)
    log.info("Built %d zones (atr=%.2f, half-width=%.2f); filtered %d distant "
             "(>10xATR=%.2f from price=%.2f)",
             len(zones), atr, half, filtered, max_dist, current_price)
    return zones
