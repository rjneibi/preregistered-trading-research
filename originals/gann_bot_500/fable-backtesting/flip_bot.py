"""
flip_bot.py v1.2 — CONVICTION dual-arm R3/S3 flip bot. DEMO-ONLY. MAGIC 20260703.

DIRECTION NOTE (do not "fix"): this is a validated BREAKOUT/momentum system —
BUY when price closes ABOVE R3, SELL when it closes BELOW S3. Rounds 2-16
(fable-backtesting/optimization_report.md, MASTER_SUMMARY.md) proved the
continuation edge; fading these levels was tested and rejected. "Flip" refers
to support/resistance polarity flipping, not mean-reversion.

Spec: R3/S3 from the PREVIOUS UTC DAY's H/L/C (backtest parity — NOT broker
day). Two arms: H1 closes 12:00-20:00 UTC; closes at 12/16/20 UTC also count
as the H4 arm (an H4-UTC candle's close price == the H1 close at that hour).
ENTER ONLY ON CONVICTION: both arms fired same direction today. No Mondays.
Max 1 trade/direction/day. Exits: server TP +0.8xATR / SL -2.4xATR + managed
hivol half-out at -1.2xATR, lovol bail -1.0xATR after 8h, hard close 24h.
Sizing: 1% equity risk (0.5% while <95% of peak) x0.5 if D1 ADX<=22 x1.5 on
news days x0.5 in low-vol regime. Daily breaker at -1.5% equity.
v1.1: UTC alignment layer, exact backtest ATR-regime, fill-mode autodetect,
journal CSV with MAE, telegram notify.
v1.2 (2026-08-24): fixed the UTC-midnight state wipe. main() rebound `st` at
the day rollover, destroying st["open"], so every position held overnight lost
derisk/bail8h/ts24h, its server-side exit went unjournalled (MAE lost), and the
bot could open a second position on top of it. Also: managed exits no longer
double-journal, a rejected close no longer drops manager state, and a live
position with no state is ADOPTED instead of silently left unmanaged.
v1.3 (2026-08-24): lot sizing no longer hardcodes the contract size. The old
`/100.0` was right only for a 100oz XAUUSD contract on a USD account; sizing is
now DERIVED from trade_tick_value/trade_tick_size (account currency, so XAGUSD,
mini-gold symbols and non-USD accounts all size correctly), floors to the volume
step instead of rounding to nearest, respects broker volume_max, REFUSES to size
when the contract cannot be priced, and journals requested-vs-realised risk.
v1.4 (2026-08-24): value_per_price_unit() now uses order_calc_profit() as the
arbiter. The v1.3 tick_value derivation MEASURED WRONG by 10x on broker demo feed
(tick_value is quoted per 0.1 lot there), which sized 10x TOO LARGE -- a 1% risk
became 9.1% of the account. See the function docstring.
v1.5 (2026-08-24): FORWARD-TEST BUILD. Three changes, all for measurement:
  (a) $2,000 NOTIONAL ACCOUNT. The demo holds $5,000 but the operator will trade
      $2,000, so sizing must be the $2,000 sizing or the test measures the wrong
      bot. Risk budgets come from notional equity = 2000 + (equity - start),
      which tracks real P/L exactly because the lots are the $2,000 lots. Peak,
      drawdown and the daily breaker all run on notional. Real equity is still
      the DEMO guard and is journalled alongside.
  (b) STOP CAPPED AT $20/oz (door 3). A $2,000 account at volume_min 0.01
      constrains risk-per-trade to <= $20 = 0.01 x 20.0 x 100. So the stop is
      min(2.4xATR, $20). NOTE this is NOT the arm measured in cycle 8: that arm
      used a FLAT $20, which on 91.3% of the sample was WIDER than 2.4xATR and
      measurably WORSE there (net -14.33 -> -27.50). min() applies the flat cap
      only on the 8.7% where it binds -- the subset where door 3 measured better
      -- and leaves 2.4xATR everywhere else. No new free parameter: the cap is
      derived from the account, the multiplier is the pre-existing spec.
  (c) SLIPPAGE IS NOW OBSERVED. The journal records intended price, actual fill
      price, their difference, and the spread at entry. Slippage has been
      modelled end-to-end for this entire program and never measured; cycle 9
      showed the full-sample result sits inside its error bar. This is the
      single highest-value number the forward test can produce.
  Also logs an ATR>=24 warning: the $20 cap starts costing winners near there
  (worst backtest winner MAE $17.60 / ATR 21.09 = 0.835). Warn only, no block.
Covered by test_flip_bot_state.py (offline, stubs MetaTrader5).
Run: py -3.11 flip_bot.py [--check]
"""
import csv
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import MetaTrader5 as mt5

sys.path.insert(0, r"@GANN_ROOT@")
sys.path.insert(0, str(Path(__file__).parent))
from news_calendar import news_weight                       # noqa: E402
try:
    import config as _cfg
    import requests as _rq
except Exception:
    _cfg = _rq = None

# DEMO terminal. Overridable so the path is not a machine-specific hardcode:
#   set FLIP_BOT_TERMINAL to point at another install.
# The account-level DEMO guard in boot() is what actually protects us, not this.
TERMINAL = os.environ.get(
    "FLIP_BOT_TERMINAL", "<mt5-terminal-path>")
SYMBOL = "XAUUSD"
MAGIC = 20260703
HERE = Path(__file__).parent
STATE = HERE / "flip_bot_state.json"
JOURNAL = HERE / "flip_bot_journal.csv"
SESSION_H = range(12, 21)
OFFSET_H = 0                       # broker-minus-UTC hours, set at boot
FILL = None
MAX_LOT = 5.0                      # absolute cap, independent of broker limits

# --- v1.5 forward-test parameters (see module docstring) -------------------
# The operator trades $2,000. The demo holds more. Size the $2,000 account.
NOTIONAL_EQUITY = float(os.environ.get("FLIP_BOT_NOTIONAL", "2000"))
# DERIVED, not chosen: 1% of $2,000 / (volume_min 0.01 x $100 per price unit).
# Recomputed at runtime from the broker's own numbers; this is the fallback.
SL_CAP_USD = 20.0
# The cap starts costing winners near here: worst backtest winner MAE was
# $17.60 at ATR 21.09 -> 0.835 x ATR. Warn, do not block (operator's call).
ATR_WARN = SL_CAP_USD / 0.835      # ~= 23.95


def utcnow():
    return datetime.now(timezone.utc)


def notify(text):
    if not (_cfg and _rq):
        return
    try:
        _rq.post(f"https://api.telegram.org/bot{_cfg.TELEGRAM_TOKEN}"
                 "/sendMessage",
                 json={"chat_id": _cfg.TELEGRAM_CHAT_ID,
                       "text": f"[flip_bot] {text}"}, timeout=3)
    except Exception:
        pass


JOURNAL_COLS = ["ts", "event", "dir", "lot", "px", "sl", "tp", "atr",
                "hivol", "adx", "news_w", "mae", "note",
                # v1.5 measurement columns, appended so existing 13-wide rows
                # keep working unchanged and simply leave these blank.
                "fill_px", "slip", "spread", "notional_eq", "real_eq"]


def journal(row):
    """Append a row, padded to the full column set.

    v1.5 widened the header. Rows are padded rather than every call site
    rewritten, so a short row from an older path is still well-formed CSV
    instead of a ragged line that breaks the analysis read."""
    new = not JOURNAL.exists()
    row = list(row)[:len(JOURNAL_COLS)]
    row += [""] * (len(JOURNAL_COLS) - len(row))
    with open(JOURNAL, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(JOURNAL_COLS)
        w.writerow(row)


def detect_offset():
    global OFFSET_H
    tick = mt5.symbol_info_tick(SYMBOL)
    OFFSET_H = round((tick.time - time.time()) / 3600)
    return OFFSET_H


def detect_fill():
    global FILL
    fm = mt5.symbol_info(SYMBOL).filling_mode
    FILL = (mt5.ORDER_FILLING_FOK if fm & 1 else mt5.ORDER_FILLING_IOC)
    return FILL


def h1_utc(n=2300):
    rs = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 1, n)
    if rs is None:
        return []
    off = OFFSET_H * 3600
    return [{"t": int(b["time"]) - off, "o": float(b["open"]),
             "h": float(b["high"]), "l": float(b["low"]),
             "c": float(b["close"])} for b in rs]


def wilder_series(bars_, period=14):
    trs, out = [], []
    for i in range(1, len(bars_)):
        b, pc = bars_[i], bars_[i - 1]["c"]
        trs.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
    if len(trs) < period:
        return []
    a = sum(trs[:period]) / period
    out = [a]
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
        out.append(a)
    return out


def adx_from_days(days, period=14):
    if len(days) < 2 * period + 2:
        return None
    tr, pdm, ndm = [], [], []
    for i in range(1, len(days)):
        d, p = days[i], days[i - 1]
        tr.append(max(d["h"] - d["l"], abs(d["h"] - p["c"]),
                      abs(d["l"] - p["c"])))
        up, dn = d["h"] - p["h"], p["l"] - d["l"]
        pdm.append(up if up > dn and up > 0 else 0.0)
        ndm.append(dn if dn > up and dn > 0 else 0.0)

    def smooth(x):
        s = [sum(x[:period]) / period]
        for v in x[period:]:
            s.append((s[-1] * (period - 1) + v) / period)
        return s
    atr, sp, sn = smooth(tr), smooth(pdm), smooth(ndm)
    dx = [100 * abs(p - n) / (p + n) if (p + n) > 0 else 0
          for a, p, n in zip(atr, sp, sn)
          for p, n in [(100 * p / a if a > 0 else 0,
                        100 * n / a if a > 0 else 0)]]
    adx = sum(dx[:period]) / period
    for v in dx[period:]:
        adx = (adx * (period - 1) + v) / period
    return adx


def build_day():
    """All structures from UTC-aligned H1: prev-UTC-day pivots, ATR regime,
    UTC-H4 dead baseline, D1 ADX."""
    h1 = h1_utc()
    if len(h1) < 400:
        return None
    days = {}
    for b in h1:
        days.setdefault(b["t"] // 86400, []).append(b)
    today_key = int(utcnow().timestamp()) // 86400
    done = sorted(k for k, v in days.items() if k < today_key and len(v) >= 12)
    if not done:
        return None
    prev = days[done[-1]]
    h = max(b["h"] for b in prev)
    l = min(b["l"] for b in prev)
    c = prev[-1]["c"]
    pp = (h + l + c) / 3.0
    r3, s3 = round(pp + (h - l), 2), round(pp - (h - l), 2)

    atr_s = wilder_series(h1)
    if not atr_s:
        return None
    atr = atr_s[-1]
    med = statistics.median(atr_s[-90 * 24:])

    h4b = {}
    now_ts = int(utcnow().timestamp())
    for b in h1:
        k = b["t"] // 14400
        if (k + 1) * 14400 <= now_ts:
            h4b[k] = b["c"]
    h4c = [h4b[k] for k in sorted(h4b)[-10:]]

    d1 = [{"h": max(b["h"] for b in v), "l": min(b["l"] for b in v),
           "c": v[-1]["c"]} for k, v in sorted(days.items())
          if k < today_key and len(v) >= 12]
    adx = adx_from_days(d1[-60:])

    return {"r3": r3, "s3": s3, "atr": atr, "hivol": atr > med, "adx": adx,
            "r3_dead": any(x > r3 for x in h4c),
            "s3_dead": any(x < s3 for x in h4c)}


def value_per_price_unit(info, price=None):
    """Account-currency P/L for 1.00 lot per 1.0 of PRICE movement.

    v1.3 hardcoded this as 100.0 inside lot_for() -- right ONLY for a 100oz
    XAUUSD contract on a USD account, and wrong for XAGUSD (5,000oz/lot), for
    the 10oz/1oz "mini" gold symbols, and for any non-quote-currency account.

    v1.3 replaced it with trade_tick_value/trade_tick_size. MEASURED AGAINST A
    REAL SERVER (broker demo feed, 2026-08-24) THAT DERIVATION IS WRONG. This
    broker quotes trade_tick_value per 0.1 lot, so it came out 10x LOW on both
    metals:

        XAUUSD  contract_size 100    tick_value 0.1/0.01 -> 10     (10x low)
        XAGUSD  contract_size 5000   tick_value 0.5/0.001 -> 500   (10x low)

    A low value-per-unit sizes the position 10x TOO LARGE: a 1% risk became
    9.1% of the account. order_calc_profit() is the broker's own P/L engine,
    is denominated in the ACCOUNT currency, and agreed with trade_contract_size
    at every volume tested -- so it is the arbiter, not tick_value.

    Returns None when neither authoritative source answers. The caller must
    then refuse to size rather than fall back to a guess, which is exactly what
    the old hardcode silently did.
    """
    sym = getattr(info, "name", None) or SYMBOL

    # 1. AUTHORITATIVE: ask the broker what 1.00 lot earns on a 1.0 price move.
    #    Handles contract size, symbol variant and account currency at once.
    if not price or price <= 0:
        tk = mt5.symbol_info_tick(sym)
        price = getattr(tk, "bid", 0) or 0
    if price > 0:
        try:
            p = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, sym, 1.0,
                                      price, price + 1.0)
        except Exception:
            p = None
        if p and p > 0:
            return float(p)

    # 2. FALLBACK: contract size, valid only when the contract already settles
    #    in the account currency. Anything else needs a conversion we cannot do
    #    here, so we refuse instead of approximating it.
    acc = mt5.account_info()
    cs = getattr(info, "trade_contract_size", 0) or 0
    if cs > 0 and acc and getattr(info, "currency_profit", None) == acc.currency:
        return float(cs)

    # 3. There is deliberately NO tick_value fallback: it was measured wrong by
    #    10x on a live server, and this number sizes the trade.
    return None


def lot_for(risk_usd, sl_dist, price=None):
    """(lot, realised_risk_usd) for `risk_usd` at a stop `sl_dist` price units
    away, or (None, None) if the contract cannot be priced.

    realised_risk is returned because it is NOT always the risk asked for: a
    budget below the broker's volume_min gets sized UP to volume_min, which can
    exceed the intended 1% materially on a small account. That was silent
    before; the caller now journals it.
    """
    info = mt5.symbol_info(SYMBOL)
    vpu = value_per_price_unit(info, price)
    if vpu is None or sl_dist <= 0 or risk_usd <= 0:
        return None, None
    step = getattr(info, "volume_step", 0) or 0.01
    vmin = getattr(info, "volume_min", 0) or 0.01
    vmax = min(getattr(info, "volume_max", 0) or MAX_LOT, MAX_LOT)
    # FLOOR to the step grid. The old code rounded to NEAREST, which sizes
    # ABOVE the risk budget whenever the remainder is more than half a step.
    lot = math.floor(risk_usd / (sl_dist * vpu) / step + 1e-9) * step
    lot = round(max(vmin, min(lot, vmax)),
                max(0, min(8, -int(math.floor(math.log10(step))))))
    return lot, lot * sl_dist * vpu


def send_order(req):
    r = mt5.order_send(req)
    if r and r.retcode == 10030:                 # invalid fill: retry other
        req["type_filling"] = (mt5.ORDER_FILLING_IOC
                               if req["type_filling"] == mt5.ORDER_FILLING_FOK
                               else mt5.ORDER_FILLING_FOK)
        r = mt5.order_send(req)
    return r


def open_trade(direction, day, st, eq, peak):
    tick = mt5.symbol_info_tick(SYMBOL)
    if (tick.ask - tick.bid) / mt5.symbol_info(SYMBOL).point > 60:
        print("spread guard: skip")
        return
    atr = day["atr"]
    px = tick.ask if direction == "BUY" else tick.bid
    sign = 1 if direction == "BUY" else -1
    spread = tick.ask - tick.bid

    # v1.5 door-3 cap. DERIVED from the broker at runtime rather than trusting
    # the SL_CAP_USD constant: the smallest trade this broker will accept is
    # volume_min lots, so a 1% budget on the notional account buys exactly
    # this many price units of stop. Falls back to the constant only if the
    # contract cannot be priced (in which case lot_for() refuses anyway).
    info = mt5.symbol_info(SYMBOL)
    vpu = value_per_price_unit(info, px)
    vmin = getattr(info, "volume_min", 0) or 0.01
    cap = ((0.01 * eq) / (vmin * vpu)) if vpu else SL_CAP_USD
    sl_dist = min(2.4 * atr, cap)
    capped = sl_dist < 2.4 * atr - 1e-9
    if capped:
        print(f"door3 cap: stop {2.4 * atr:.2f} -> {sl_dist:.2f} "
              f"(1% of ${eq:,.2f} notional at {vmin} lot)")
    if atr >= ATR_WARN:
        # not a block: the operator declined the guard. But this is the regime
        # where the backtest says the cap begins costing winners, so it must
        # be visible in the journal when it happens rather than reconstructed.
        print(f"*** ATR WARNING: {atr:.2f} >= {ATR_WARN:.2f} — the ${cap:.2f} "
              f"cap is at {cap / atr:.3f}xATR; backtest worst winner MAE was "
              f"0.835xATR. Winner-kill risk is now live.")
        notify(f"ATR {atr:.1f} >= {ATR_WARN:.1f}: ${cap:.0f} stop is "
               f"{cap / atr:.2f}xATR, worst backtest winner needed 0.835xATR")
        journal([utcnow().isoformat(), "ATR_WARN", direction, "", px, "", "",
                 round(atr, 2), day["hivol"], "", "", 0,
                 f"cap={cap:.2f} = {cap / atr:.3f}xATR"])

    sl, tp = px - sign * sl_dist, px + sign * 0.8 * atr
    risk = eq * (0.01 if eq >= 0.95 * peak else 0.005)
    if day["adx"] is not None and day["adx"] <= 22:
        risk *= 0.5
    # news 1.5x multiplier REMOVED 2026-07-07: H-N confirmation FAIL at
    # full-coverage costs (news PF 1.44 < 1.50 gate; DECISIONS.log; operator
    # confirmed). news_weight() remains in --check output for observability.
    nw = 1.0
    if not day["hivol"]:
        risk *= 0.5
    lot, risk_act = lot_for(risk, abs(px - sl), px)
    if lot is None:
        # v1.3: refuse rather than guess. The old /100.0 hardcode meant a broker
        # that reports nothing usable still got a plausible-looking XAUUSD lot.
        print(f"SIZING REFUSED: {SYMBOL} contract value not resolvable from "
              f"symbol_info — no order sent")
        journal([utcnow().isoformat(), "SIZE_FAIL", direction, "", px,
                 round(sl, 2), round(tp, 2), round(atr, 2), day["hivol"],
                 day["adx"] and round(day["adx"], 1), nw, 0,
                 "value_per_price_unit() returned None"])
        notify(f"SIZING REFUSED {direction}: cannot price {SYMBOL} contract")
        return
    over = risk_act / risk if risk > 0 else 1.0
    risk_note = f"risk_req=${risk:.2f} risk_act=${risk_act:.2f} ({over:.2f}x)"
    if over > 1.10:                    # volume_min floor, not a sizing error
        print(f"OVER-RISK: {risk_note} — broker volume_min forces size above "
              f"the {100 * risk / eq:.2f}% budget")
    r = send_order({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL,
                    "volume": lot,
                    "type": (mt5.ORDER_TYPE_BUY if direction == "BUY"
                             else mt5.ORDER_TYPE_SELL),
                    "price": px, "sl": round(sl, 2), "tp": round(tp, 2),
                    "magic": MAGIC, "comment": "flipbot-conviction",
                    "type_filling": FILL})
    rc = getattr(r, "retcode", None)
    # v1.5 THE MEASUREMENT. Slippage has been a modelled constant for this
    # entire program; cycle 9 showed the backtest verdict sits inside its
    # error bar. `r.price` is the price the broker actually filled at.
    # Positive slip = ADVERSE (worse than intended) for both directions.
    fill_px = float(getattr(r, "price", 0) or 0) or None
    slip = (sign * (fill_px - px)) if fill_px else None
    real_eq = getattr(mt5.account_info(), "equity", None)
    print(f"ENTRY {direction} {lot} @ {px} sl={sl:.2f} tp={tp:.2f} ret={rc} "
          f"{risk_note}")
    if slip is not None:
        print(f"  FILL {fill_px} | slip {slip:+.3f}/oz "
              f"({slip / atr:+.4f} xATR) | spread {spread:.3f}")
    journal([utcnow().isoformat(), "ENTRY", direction, lot, px,
             round(sl, 2), round(tp, 2), round(atr, 2), day["hivol"],
             day["adx"] and round(day["adx"], 1), nw, 0,
             f"{rc} {risk_note} cap={cap:.2f} capped={capped}",
             fill_px, None if slip is None else round(slip, 3),
             round(spread, 3), round(eq, 2), real_eq])
    if rc == mt5.TRADE_RETCODE_DONE:
        notify(f"ENTRY {direction} {lot} @ {px:.2f} (atr {atr:.1f}, "
               f"hivol={day['hivol']}, slip "
               f"{'n/a' if slip is None else f'{slip:+.3f}'})")
        st["open"] = {"dir": direction, "px": px, "atr": atr,
                      "hivol": day["hivol"], "t": utcnow().isoformat(),
                      "derisked": False, "mae": 0.0,
                      # v1.5: the barrier levels are kept so a server-side
                      # exit can be attributed to TP or SL and its fill
                      # compared against the level that was meant to hold.
                      "sl": round(sl, 2), "tp": round(tp, 2),
                      "capped": capped, "cap": round(cap, 2),
                      "entry_fill": fill_px,
                      "entry_slip": None if slip is None else round(slip, 3)}


def close_frac(p, frac, px, sign, why):
    """Close `frac` of the position. Returns (ok, fill_px, slip).

    v1.2: ok is True ONLY on broker confirmation — the caller must not drop
    manager state for a close that never filled.
    v1.5: also returns the realised fill and its adverse slippage. Exit
    slippage is the expensive kind (it is worst on stops, in fast markets)
    and was previously not recorded at all."""
    vol = round(max(p.volume * frac, 0.01), 2)
    r = send_order({"action": mt5.TRADE_ACTION_DEAL, "symbol": SYMBOL,
                    "volume": vol, "position": p.ticket,
                    "type": (mt5.ORDER_TYPE_SELL if sign > 0
                             else mt5.ORDER_TYPE_BUY),
                    "price": px, "magic": MAGIC, "comment": why,
                    "type_filling": FILL})
    rc = getattr(r, "retcode", None)
    ok = rc == mt5.TRADE_RETCODE_DONE
    fill_px = float(getattr(r, "price", 0) or 0) or None
    # closing a long SELLS: a fill BELOW the intended price is adverse.
    slip = (sign * (px - fill_px)) if fill_px else None
    print(f"EXIT {why} {vol} @ {px} ret={rc}{'' if ok else '  *** FAILED ***'}"
          + (f" | fill {fill_px} slip {slip:+.3f}" if slip is not None else ""))
    return ok, fill_px, slip


def adopt(p):
    """v1.2: rebuild manager state for a live MAGIC position that has none.

    Reachable whenever the state file is lost, corrupt, or predates the
    position (crash, restart mid-trade, manual delete). Before this, such a
    position fell through `if not o: return` and had NO manager for its whole
    life — derisk / bail8h / ts24h never fired. Entry ATR and the vol regime
    are not recoverable from the position, so take them from the last ENTRY
    journal row and fall back to recomputing them; the journal row records
    which source was used so an adopted trade is never mistaken for a clean one.
    """
    row = None
    if JOURNAL.exists():
        try:
            with open(JOURNAL, newline="") as f:
                for r in csv.DictReader(f):
                    if r.get("event") == "ENTRY":
                        row = r
        except OSError:
            row = None
    atr = hivol = None
    if row:
        try:
            atr, hivol = float(row["atr"]), row["hivol"] == "True"
        except (KeyError, TypeError, ValueError):
            atr = None
    if atr is None or atr <= 0:                    # journal unusable
        s = wilder_series(h1_utc())
        atr = s[-1] if s else 1.0
        hivol = bool(s) and atr > statistics.median(s[-90 * 24:])
    # p.time is BROKER time like every other timestamp here — de-offset it,
    # or age_h is wrong by the broker offset and ts24h fires hours early/late.
    t0 = datetime.fromtimestamp(int(p.time) - OFFSET_H * 3600, timezone.utc)
    o = {"dir": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
         "px": float(p.price_open), "atr": float(atr), "hivol": bool(hivol),
         "t": t0.isoformat(), "derisked": False, "mae": 0.0, "adopted": True}
    journal([utcnow().isoformat(), "ADOPT", o["dir"], p.volume, o["px"], "", "",
             round(o["atr"], 2), o["hivol"], "", "", 0,
             f"orphan ticket {p.ticket}; atr from "
             f"{'journal' if row else 'recompute'}"])
    notify(f"ADOPTED orphan {o['dir']} ticket {p.ticket} (no manager state)")
    return o


def last_exit_deal():
    """Most recent closing deal on our MAGIC, or None.

    v1.5: a server-side TP/SL exit never passes through close_frac, so its
    fill price was previously invisible -- and stop fills are exactly where
    slippage is worst. Recover it from deal history instead of guessing."""
    try:
        deals = mt5.history_deals_get(
            datetime.fromtimestamp(time.time() - 172800, timezone.utc),
            datetime.fromtimestamp(time.time() + 3600, timezone.utc))
    except Exception:
        return None
    outs = [d for d in (deals or [])
            if getattr(d, "magic", None) == MAGIC
            and getattr(d, "symbol", None) == SYMBOL
            and getattr(d, "entry", None) == mt5.DEAL_ENTRY_OUT]
    return max(outs, key=lambda d: d.time) if outs else None


def manage(st):
    pos = [p for p in (mt5.positions_get(symbol=SYMBOL) or [])
           if p.magic == MAGIC]
    o = st.get("open")
    if not pos:
        if o:                                   # closed server-side (TP/SL)
            d = last_exit_deal()
            fill = float(getattr(d, "price", 0) or 0) or None if d else None
            # which barrier did it hit? compare the fill to the levels we set.
            note = "server_tp_sl_or_manual"
            if fill and o.get("sl") and o.get("tp"):
                sign = 1 if o["dir"] == "BUY" else -1
                d_tp, d_sl = abs(fill - o["tp"]), abs(fill - o["sl"])
                note = ("server_TP" if d_tp < d_sl else "server_SL")
                # adverse slippage vs the level the broker was meant to honour
                lvl = o["tp"] if d_tp < d_sl else o["sl"]
                slip = sign * (lvl - fill)
                note += f" vs {lvl:.2f}"
            else:
                slip = None
            journal([utcnow().isoformat(), "EXIT", o["dir"],
                     getattr(d, "volume", "") if d else "", "", "", "",
                     round(o["atr"], 2), o["hivol"], "", "",
                     round(o.get("mae", 0), 2),
                     f"{note} profit={getattr(d, 'profit', '?')}",
                     fill, None if slip is None else round(slip, 3), "",
                     "", getattr(mt5.account_info(), "equity", None)])
            notify(f"EXIT {o['dir']} ({note}) mae={o.get('mae', 0):.2f}"
                   + (f" slip {slip:+.3f}" if slip is not None else ""))
            st.pop("open", None)
        return
    p = pos[0]
    if not o:
        o = adopt(p)                            # v1.2: was `return` — see adopt()
        st["open"] = o
    sign = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
    tick = mt5.symbol_info_tick(SYMBOL)
    px = tick.bid if sign > 0 else tick.ask
    adverse = sign * (o["px"] - px)
    o["mae"] = max(o.get("mae", 0.0), adverse)
    age_h = (utcnow() - datetime.fromisoformat(o["t"])).total_seconds() / 3600
    atr = o["atr"]
    why, xfill, xslip = None, None, None
    if age_h >= 24:
        ok, xfill, xslip = close_frac(p, 1.0, px, sign, "ts24h")
        why = "ts24h" if ok else "ts24h_FAILED"
    elif o["hivol"] and not o["derisked"] and adverse >= 1.2 * atr:
        ok, xfill, xslip = close_frac(p, 0.5, px, sign, "derisk")
        if ok:
            o["derisked"] = True
    elif not o["hivol"] and age_h >= 8 and adverse >= 1.0 * atr:
        ok, xfill, xslip = close_frac(p, 1.0, px, sign, "bail8h")
        why = "bail8h" if ok else "bail8h_FAILED"
    if why and why.endswith("_FAILED"):
        # retry next tick; journal/notify once so a stuck close is visible
        # without writing a row every 20s for as long as it keeps failing.
        o["fail"] = o.get("fail", 0) + 1
        if o["fail"] == 1:
            journal([utcnow().isoformat(), "EXIT_FAIL", o["dir"], p.volume, px,
                     "", "", round(atr, 2), o["hivol"], "", "",
                     round(o["mae"], 2), why])
            notify(f"CLOSE FAILED {o['dir']} {why} @ {px:.2f} — retrying")
    elif why:
        journal([utcnow().isoformat(), "EXIT", o["dir"], p.volume, px, "",
                 "", round(atr, 2), o["hivol"], "", "",
                 round(o["mae"], 2), why, xfill,
                 None if xslip is None else round(xslip, 3),
                 round(tick.ask - tick.bid, 3), "",
                 getattr(mt5.account_info(), "equity", None)])
        notify(f"EXIT {o['dir']} {why} @ {px:.2f} mae={o['mae']:.2f}")
        # v1.2: drop the entry NOW. Leaving it set made the next tick see an
        # empty position list with `o` still live and journal a SECOND EXIT row
        # as "server_tp_sl_or_manual" — every managed exit was double-counted,
        # corrupting the winner-MAE the forward test is judged on.
        st.pop("open", None)
        return
    st["open"] = o


def boot():
    if not mt5.initialize(path=TERMINAL):
        raise SystemExit(f"mt5 init failed: {mt5.last_error()}")
    acc = mt5.account_info()
    if acc.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise SystemExit("HARD GUARD: not a demo account — refusing to run")
    # v1.5 LAUNCH BUG, 2026-08-25. A symbol that is not in the terminal's
    # Market Watch has symbol_info() but symbol_info_tick() returns None with
    # last_error (-4, 'Terminal: Not found'), and detect_offset() died on it.
    # The earlier --check only worked because the symbol happened to be
    # selected then. Select it explicitly and prove a tick arrives.
    info = mt5.symbol_info(SYMBOL)
    if info is None:
        raise SystemExit(f"{SYMBOL} not offered by this broker")
    if not getattr(info, "visible", False) and not mt5.symbol_select(SYMBOL, True):
        raise SystemExit(f"cannot add {SYMBOL} to Market Watch: "
                         f"{mt5.last_error()}")
    for _ in range(20):                       # the terminal fills it in async
        if mt5.symbol_info_tick(SYMBOL) is not None:
            break
        time.sleep(0.5)
    else:
        raise SystemExit(f"no tick for {SYMBOL} after 10s: {mt5.last_error()}")
    off, fill = detect_offset(), detect_fill()
    print(f"flip_bot v1.5 DEMO {acc.login} eq={acc.equity} "
          f"broker_offset=UTC{off:+d}h fill={fill}")
    return acc


def check():
    acc = boot()
    day = build_day()
    print(json.dumps({**day, "news_w": news_weight(),
                      "offset_h": OFFSET_H, "fill": FILL}, indent=1,
                     default=str))
    # v1.4: sizing is DERIVED from the broker, so show the derivation AND the
    # sources that disagree. Eyeball this before letting it trade.
    info = mt5.symbol_info(SYMBOL)
    tick = mt5.symbol_info_tick(SYMBOL)
    px = getattr(tick, "bid", 0) or 0
    vpu = value_per_price_unit(info, px)
    print(f"\nsizing basis for {SYMBOL}:")
    for a in ("trade_contract_size", "trade_tick_size", "trade_tick_value",
              "trade_tick_value_loss", "currency_profit", "volume_min",
              "volume_step", "volume_max"):
        print(f"  {a:<24} {getattr(info, a, '<absent>')}")

    # the three candidate answers, side by side. On broker demo feed the
    # tick_value route is 10x LOW because tick_value is quoted per 0.1 lot,
    # which is why v1.4 no longer trusts it.
    calc = (mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, SYMBOL, 1.0, px, px + 1.0)
            if px > 0 else None)
    cs = getattr(info, "trade_contract_size", 0) or 0
    ts = getattr(info, "trade_tick_size", 0) or 0
    tv = getattr(info, "trade_tick_value", 0) or 0
    tickroute = (tv / ts) if ts > 0 and tv > 0 else None
    print(f"  order_calc_profit        {calc}   <- AUTHORITATIVE")
    print(f"  contract_size            {cs}")
    print(f"  tick_value/tick_size     {tickroute}   <- NOT USED (see v1.4 note)")
    if calc and tickroute and abs(calc - tickroute) > 1e-6:
        print(f"  !! tick_value route disagrees with the broker by "
              f"{tickroute / calc:.3g}x — sizing from it would be "
              f"{calc / tickroute:.3g}x wrong in LOT terms")

    if vpu is None:
        print("  value/price-unit         UNRESOLVABLE — bot will REFUSE to size")
        return
    print(f"  value/price-unit         {vpu:,.4f} {acc.currency}/lot per 1.0 price")
    if day:
        # v1.5: show the NOTIONAL account the forward test actually sizes, and
        # the door-3 cap that a $2,000 account at volume_min forces.
        vmin = getattr(info, "volume_min", 0) or 0.01
        cap = (0.01 * NOTIONAL_EQUITY) / (vmin * vpu)
        raw = 2.4 * day["atr"]
        sl_dist = min(raw, cap)
        print(f"\n  notional equity        ${NOTIONAL_EQUITY:,.2f} "
              f"(real ${acc.equity:,.2f})")
        print(f"  door3 cap              ${cap:.2f}/oz "
              f"= 1% of ${NOTIONAL_EQUITY:,.0f} at {vmin} lot")
        print(f"  2.4xATR                ${raw:.2f}/oz  ->  stop used "
              f"${sl_dist:.2f} ({'CAPPED' if sl_dist < raw else 'uncapped'})")
        if day["atr"] >= ATR_WARN:
            print(f"  *** ATR {day['atr']:.2f} >= {ATR_WARN:.2f}: cap is "
                  f"{cap / day['atr']:.3f}xATR, backtest worst winner needed "
                  f"0.835xATR — winner-kill risk is LIVE")
        for lbl, r in (("full 1.0%", 0.01), ("derisked 0.5%", 0.005),
                       ("0.25% (adx+lovol)", 0.0025)):
            lot, act = lot_for(NOTIONAL_EQUITY * r, sl_dist, px)
            budget = NOTIONAL_EQUITY * r
            flag = ""
            if lot is not None and act is not None and act > budget * 1.10:
                flag = (f"  <-- {act / budget:.2f}x the ${budget:,.2f} budget "
                        f"(volume_min floor)")
            print(f"  {lbl:<20} sl={sl_dist:7.2f}  lot={lot}  "
                  f"realised risk ${act:,.2f} "
                  f"({100 * act / NOTIONAL_EQUITY:.2f}% of notional){flag}")


def main():
    acc = boot()
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    # v1.5: the notional $2,000 account. real_start is pinned on first run and
    # persisted, so a restart does not silently rebase the notional equity and
    # wipe whatever drawdown the test had accumulated.
    if "real_start" not in st:
        st["real_start"] = acc.equity
    real_start = st["real_start"]

    def notional(eq):
        return NOTIONAL_EQUITY + (eq - real_start)

    print(f"NOTIONAL ACCOUNT ${NOTIONAL_EQUITY:,.2f} "
          f"(real ${acc.equity:,.2f}, baseline ${real_start:,.2f}) "
          f"-> sizing equity ${notional(acc.equity):,.2f}")
    notify(f"started v1.5 notional ${NOTIONAL_EQUITY:,.0f} "
           f"(real {acc.equity}, offset UTC{OFFSET_H:+d}h)")
    peak = st.get("peak", notional(acc.equity))
    last_bar, day, day_built = None, None, None
    while True:
        now = utcnow()
        acc = mt5.account_info()
        neq = notional(acc.equity)
        peak = max(peak, neq)
        dk = now.date().isoformat()
        if st.get("day") != dk:
            # v1.2 FIX (the state wipe): this REBOUND st, destroying every key
            # not in the literal — above all st["open"]. At each UTC midnight a
            # live position lost its manager (derisk/bail8h/ts24h dead for its
            # whole remaining life), a server-side exit went unjournalled so its
            # MAE was lost, and `not st.get("open")` went true so the bot could
            # stack a second position on the first. ~27% of trades hold >=1
            # night, so this fired on about a quarter of all trades.
            # Mutate in place: reset ONLY the day-scoped keys.
            st.update({"day": dk, "signals": {}, "done": [],
                       "day_start_eq": neq, "peak": peak})
            detect_offset()                       # DST recheck
            day = None
        manage(st)
        h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 1, 1)
        bt = int(h1[0]["time"]) if h1 is not None and len(h1) else None
        if bt and bt != last_bar and now.weekday() != 0 \
                and now.hour in SESSION_H:
            last_bar = bt
            if day_built != dk:
                day = build_day()
                day_built = dk if day else None
            if day:
                close_px = float(h1[0]["close"])
                sigs = st["signals"]
                for direc, lvl, dead in (("BUY", day["r3"], day["r3_dead"]),
                                         ("SELL", day["s3"], day["s3_dead"])):
                    hit = (close_px > lvl) if direc == "BUY" \
                        else (close_px < lvl)
                    if dead or not hit:
                        continue
                    # a 12/16/20 UTC close is BOTH an H1 close and the
                    # UTC-H4 candle close -> both arms fire (round-16 ties)
                    arms = (["h4", "h1"] if now.hour in (12, 16, 20)
                            else ["h1"])
                    sigs.setdefault(direc, [])
                    for arm in arms:
                        if arm not in sigs[direc]:
                            sigs[direc].append(arm)
                    breaker = (neq - st["day_start_eq"]
                               <= -0.015 * st["day_start_eq"])
                    if len(sigs[direc]) == 2 and direc not in st["done"] \
                            and not st.get("open") and not breaker:
                        open_trade(direc, day, st, neq, peak)
                        st["done"].append(direc)
        st["peak"], st["hb"] = peak, now.isoformat()
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, default=str))
        tmp.replace(STATE)
        time.sleep(20)


if __name__ == "__main__":
    (check if "--check" in sys.argv else main)()
