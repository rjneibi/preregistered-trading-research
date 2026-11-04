"""
signals.py — Conditional zone logic (the brain) for gann_bot.

Named "signals" (plural), NOT "signal": a module named signal.py would shadow
Python's stdlib `signal` (which `import subprocess` and others pull in),
breaking unrelated imports across the project.

UNIFIED for the two settled logics. evaluate_signal() takes a single
``use_polarity`` flag that selects between them:

  Logic 1 — "Core + Polarity" (Profile D, use_polarity=True)
    Zone hit → H4 EMA50 bias → H4 Fib retracement → Polarity flip →
    H1 body-close confirm
  Logic 2 — "Pure Core" (Profile R, use_polarity=False)
    Zone hit → H4 EMA50 bias → H4 Fib retracement → H1 body-close confirm

The only difference is the polarity-flip re-evaluation (structure.check_zone_
polarity): ON for Logic 1, OFF for Logic 2. Every other gate is identical.

evaluate_signal() decides whether the current price, sitting inside a level
zone, warrants a BUY or SELL. It combines:

  * which zone price is currently inside       (zone hit),
  * H4 EMA50 bias (must agree with direction)  (bias filter),
  * H4 Fib retracement structure               (built into the zones),
  * optional zone polarity flip                 (Logic 1 only),
  * H1 body-close confirmation of the break    (confirmation),
  * the next zone in the trade direction as the target,
  * a confluence list of nearby zones.

Returns a signal dict or None. No orders are placed here — bot.py does that.
"""

import time

import config
import structure
from logsetup import get_logger

log = get_logger("signal")

# Throttle state for the "No trade" log: (zone_source, reason) -> last log ts.
_last_no_trade_log = {}


def _classify_zone(source: str, swing_dir: str = None) -> str:
    """
    Classify a zone source label as "support", "resistance", or "neutral".

    STRATEGY CHANGE 2026-06-12: fib zones are now direction-aware. The old
    static mapping (618/786 = support, 382/500 = resistance) is only meaningful
    for an UP swing; in a DOWN swing levels.fib_retracements places the levels
    as `swing_low + ratio×range` — i.e. retracement CEILINGS above price-action
    lows — so the roles mirror. Re-validate before trusting win-rate statistics.

    Params:
        source (str): zone source, e.g. "R90", "R2", "fib_618", "PP".
        swing_dir (str): "up" / "down" — the H4 swing direction the fib levels
            were computed off (zone["swing_dir"]); None (legacy callers /
            non-fib zones) keeps the original static classification.

    Returns:
        str: "support", "resistance", or "neutral".
    """
    s = source.upper()

    # Pivot / Gann resistance and the upper-leaning fib retracements.
    if s.startswith("R") or "_R" in s:
        return "resistance"
    if s.startswith("S") or "_S" in s:
        return "support"

    # Fibonacci retracements, direction-aware:
    #   up   swing → deep retracements (.618/.786) are support on the pullback,
    #                shallow ones (.382/.500) resistance on a bounce (original).
    #   down swing → mirror: .618/.786 act as resistance, .382/.500 as support.
    if swing_dir == "down":
        if "FIB_618" in s or "FIB_786" in s:
            return "resistance"
        if "FIB_382" in s or "FIB_500" in s:
            return "support"
    if "FIB_618" in s or "FIB_786" in s:
        return "support"
    if "FIB_382" in s or "FIB_500" in s:
        return "resistance"

    return "neutral"  # PP and anything unclassified


def _find_inside_zone(price: float, zones: list):
    """
    Find the zone whose [low, high] band currently contains price.

    Params:
        price (float): current price (mid).
        zones (list): zone dicts sorted by level descending.

    Returns:
        dict or None: the containing zone, or None if price is in open air.
    """
    for z in zones:
        if z["low"] <= price <= z["high"]:
            return z
    return None


def _next_zone(zones: list, current_zone: dict, direction: str):
    """
    Find the next zone in the trade direction to use as a target.

    Params:
        zones (list): zone dicts sorted by level descending.
        current_zone (dict): the zone price is currently inside.
        direction (str): "BUY" (target above) or "SELL" (target below).

    Returns:
        dict or None: the next target zone, or None if none exists.
    """
    level = current_zone["level"]
    if direction == "BUY":
        # nearest zone strictly above the current level
        above = [z for z in zones if z["level"] > level]
        return min(above, key=lambda z: z["level"]) if above else None
    else:
        below = [z for z in zones if z["level"] < level]
        return max(below, key=lambda z: z["level"]) if below else None


def _confluence(zones: list, entry: float, atr: float) -> list:
    """
    List sources of all zones whose level is within CONFLUENCE_ATR_MULT × ATR of entry.

    Params:
        zones (list): all zone dicts.
        entry (float): entry price.
        atr (float): current ATR.

    Returns:
        list: source labels contributing confluence at the entry.
    """
    tol = config.CONFLUENCE_ATR_MULT * atr
    return [z["source"] for z in zones if abs(z["level"] - entry) <= tol]


def _set_reason(reason, stage, detail, zone=None, direction=None):
    """Populate the optional diagnostic `reason` dict (no-op if None) so callers
    can log the EXACT gate that blocked a signal instead of a generic message."""
    if reason is not None:
        reason["stage"] = stage
        reason["detail"] = detail
        reason["zone"] = zone
        reason["direction"] = direction


def evaluate_signal(current_price, zones, h4_bias, h1_bars, atr,
                    use_polarity=True, reason=None):
    """
    Evaluate whether to fire a trade signal given the current market state.

    Params:
        current_price (float): current price (mid).
        zones (list): zone dicts from levels.build_zones().
        h4_bias (str): "bullish" or "bearish".
        h1_bars (list): H1 OHLC bars, most recent last.
        atr (float): current H1 ATR.
        use_polarity (bool): when True (Logic 1 / Profile D) a zone's side is
            re-evaluated from recent H4 closes via structure.check_zone_polarity
            (a support broken to the downside becomes resistance, and vice-versa)
            BEFORE deciding direction. When False (Logic 2 / Profile R) the zone's
            static classification (plus the direction-aware PP case) is used as-is.
        reason (dict, optional): if provided, is filled with the diagnostic
            stage/detail/zone/direction explaining why no signal fired (or that
            one did). Backward compatible — omitting it changes nothing.

    Returns:
        dict or None: signal dict with keys direction, entry_price, zone_hit,
                      target_zone, confluence, polarity_flipped — or None if no
                      trade.
    """
    # Null/zero safety: never evaluate against missing/invalid inputs.
    if not zones:
        _set_reason(reason, "zone", "no valid confluence zones available")
        return None
    if not h1_bars or len(h1_bars) < 2:
        _set_reason(reason, "data", "insufficient H1 bars for confirmation")
        return None
    if atr is None or atr <= 0:
        _set_reason(reason, "data", "ATR unavailable or non-positive")
        return None

    zone = _find_inside_zone(current_price, zones)
    if zone is None:
        _set_reason(reason, "zone", "price not inside any confluence zone")
        return None  # price not in any zone

    # STRATEGY CHANGE 2026-06-12: fib zones now direction-aware (the zone's
    # swing_dir, stamped by levels.build_zones, mirrors the support/resistance
    # roles for a "down" swing). Re-validate before trusting win-rate statistics.
    kind = _classify_zone(zone["source"], zone.get("swing_dir"))
    if zone["source"].lower().startswith("fib_"):
        log.info("Fib zone %s: swing_dir=%s -> classified as %s",
                 zone["source"], zone.get("swing_dir"), kind)

    # PP is direction-aware: approached from below it acts as resistance, from
    # above as support. (Other zones keep their static classification.)
    if zone["source"].upper() == "PP":
        if current_price < zone["level"]:
            kind = "resistance"
        elif current_price > zone["level"]:
            kind = "support"

    # Zone polarity flip (Logic 1 / Profile D only). A support broken to the
    # downside on H4 has become resistance (and vice-versa); re-evaluate the side
    # from recent H4 closes BEFORE deciding direction. The zone dict is not
    # mutated — a shallow copy carries the effective side into the check. Logic 2
    # (Profile R) passes use_polarity=False and skips this entirely.
    original_side = kind
    if use_polarity:
        kind = structure.check_zone_polarity({**zone, "side": kind}, config.SYMBOL)
        polarity_flipped = "yes" if kind != original_side else "no"
        if polarity_flipped == "yes":
            log.info(
                "Zone %s polarity flipped: original=%s current=%s — evaluating as %s",
                zone["source"], original_side, kind,
                "SELL" if kind == "resistance" else "BUY",
            )
    else:
        polarity_flipped = "off"

    # Decide direction from bias + zone type. Conflicts produce no trade.
    if h4_bias == "bullish" and kind == "support":
        direction = "BUY"
        confirm_dir = "above"
    elif h4_bias == "bearish" and kind == "resistance":
        direction = "SELL"
        confirm_dir = "below"
    else:
        # Throttle: at most once per 60s per (zone, reason) combination.
        key = (zone["source"], kind)
        now = time.time()
        if now - _last_no_trade_log.get(key, 0.0) >= 60:
            log.info(
                "No trade: bias=%s zone=%s(%s) conflict/neutral",
                h4_bias, zone["source"], kind,
            )
            _last_no_trade_log[key] = now
        _set_reason(reason, "bias",
                    f"H4 bias {h4_bias} does not agree with zone side {kind}",
                    zone=zone["level"])
        return None

    # Require H1 body-close confirmation of the level break.
    if not structure.h1_close_confirmed(h1_bars, zone["level"], confirm_dir):
        log.info(
            "Signal pending confirmation: %s @ %s (no H1 %s close yet)",
            direction, zone["source"], confirm_dir,
        )
        _set_reason(reason, "h1_confirm",
                    f"awaiting H1 {confirm_dir} body-close of level",
                    zone=zone["level"], direction=direction)
        return None

    target = _next_zone(zones, zone, direction)
    confluence = _confluence(zones, current_price, atr)

    sig = {
        "direction": direction,
        "entry_price": current_price,
        "zone_hit": zone,
        "target_zone": target,
        "confluence": confluence,
        "polarity_flipped": polarity_flipped,  # "yes"/"no" (Logic 1) or "off" (Logic 2)
    }
    _set_reason(reason, "signal", "all gates passed",
                zone=zone["level"], direction=direction)
    log.info(
        "SIGNAL %s @ %.2f zone=%s target=%s confluence=%s",
        direction, current_price, zone["source"],
        target["source"] if target else "none", confluence,
    )
    # NOTE: the early "Filter scan / Result: SIGNAL" Telegram message was removed.
    # It fired here, before bot.py's cooldown / lot-sizing / order gates, so it
    # announced trades that were never placed. There is NO pre-order Telegram
    # message at all: the single truthful trade notification is
    # notify_signal_card(), sent by bot.py only AFTER order_send() confirms a
    # ticket. (notifier.notify_signal_evaluated exists but has no caller.)
    return sig
