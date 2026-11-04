"""Faithful replay of gann_bot Profile D ("Core + Polarity") on M1 bars, 2010-2026.

Mirrors the live code paths (bot.py main loop, signals.evaluate_signal, levels.*,
structure.*, risk.*) as they ran on demo 2026-06..07:
  * zones recomputed at the first loop tick of each new UTC day: Gann Sq9 from the broker
    D1 open, Fibonacci pivots from the previous broker D1 bar, H4 fib retracement off the
    last 50 H4 bars (incl. the forming one); zone = level +- 0.3 x ATR(H1,14), levels more
    than 10 x ATR from price dropped. ATR = Wilder over 43 H1 bars incl. the forming one.
  * H4 bias = last close vs EMA50 over 200 H4 bars (SMA seed), recomputed at each new H4
    bar (forming bar close = its open at that instant).
  * signals evaluated ONLY at the first tick of each new H1 bar: price inside a zone,
    polarity re-evaluated from the last 10 closed H4 closes, bias must agree with the
    zone side, last closed H1 body must straddle the level.
  * 1 open position max; 1 trade per zone per UTC day; weekend (UTC Sat/Sun) idle.
  * Option C pullback entry: pullback band = [zone mid, H1 close]; up to 15 M1 bars;
    runaway at 1.5 x ATR beyond the zone mid.  entry="bug" reproduces the live check
    (the FORMING M1 bar's close vs open at its first tick -> effectively a coin flip with
    probability P_FIRST_TICK when the bar opens inside the band); entry="intended" uses
    the closed M1 bar and enters at the next open; entry="immediate" enters at the H1 open.
  * exits: SL = 1 x ATR, TP = $9 fixed (from the trigger price); partial 50% at +1 ATR ->
    SL to entry; BE at max(ATR, $15); trail max(ATR, $15). Intrabar: stop first.
Prices are bid bars; ask = bid + SPREAD. Results in R (risk = initial stop distance).
"""
import argparse
import datetime as dt
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import data  # noqa: E402

GANN_DEGREES = [45, 90, 135, 180, 225, 270, 315, 360]
FIBS = [0.382, 0.500, 0.618, 0.786]
FIB_KEYS = ["fib_382", "fib_500", "fib_618", "fib_786"]


# ----------------------------------------------------------------- clocks
def _us_dst(year):
    """US DST window in UTC seconds (2nd Sun Mar 07:00 UTC .. 1st Sun Nov 06:00 UTC)."""
    m = dt.datetime(year, 3, 8, tzinfo=dt.timezone.utc)
    m += dt.timedelta(days=(6 - m.weekday()) % 7)
    n = dt.datetime(year, 11, 1, tzinfo=dt.timezone.utc)
    n += dt.timedelta(days=(6 - n.weekday()) % 7)
    return m.timestamp() + 7 * 3600, n.timestamp() + 6 * 3600


_DST = {y: _us_dst(y) for y in range(2009, 2028)}


def broker_to_utc(tb):
    y = dt.datetime.fromtimestamp(tb, dt.timezone.utc).year
    a, b = _DST[y]
    u = tb - 3 * 3600
    return u if a <= u < b else tb - 2 * 3600


# ----------------------------------------------------------------- bars
class Bars:
    """Bucket M1 bars into H1/H4/D1 (broker time)."""

    def __init__(self, d, sec):
        t = d["t"]
        key = t // sec
        starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
        ends = np.r_[starts[1:], len(t)]
        self.s, self.e = starts, ends
        self.t = key[starts] * sec
        self.o = d["o"][starts]
        self.c = d["c"][ends - 1]
        self.h = np.maximum.reduceat(d["h"], starts)
        self.l = np.minimum.reduceat(d["l"], starts)


def wilder_atr(h, l, c, period=14):
    trs = [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(h))]
    a = sum(trs[:period]) / period
    for tr in trs[period:]:
        a = (a * (period - 1) + tr) / period
    return round(a, 2)


def ema_sma_seed(vals, period=50):
    if len(vals) < period:
        return sum(vals) / len(vals)
    k = 2.0 / (period + 1.0)
    e = sum(vals[:period]) / period
    for v in vals[period:]:
        e = v * k + e * (1.0 - k)
    return e


# ----------------------------------------------------------------- levels (levels.py)
def gann_levels(price):
    sf, norm = 1.0, float(price)
    while norm > 1000:
        norm /= 10.0
        sf *= 10.0
    r = math.sqrt(norm)
    out = {}
    for deg in GANN_DEGREES:
        inc = deg / 360.0
        out[f"R{deg}"] = round((r + inc) ** 2 * sf, 2)
        out[f"S{deg}"] = round((r - inc) ** 2 * sf, 2)
    return out


def fib_pivots(h, l, c):
    rng, pp = h - l, (h + l + c) / 3.0
    return {"PP": round(pp, 2), "R1": round(pp + .382 * rng, 2), "R2": round(pp + .618 * rng, 2),
            "R3": round(pp + rng, 2), "S1": round(pp - .382 * rng, 2),
            "S2": round(pp - .618 * rng, 2), "S3": round(pp - rng, 2)}


def fib_retr(sh, sl, d):
    rng = sh - sl
    return {k: round(sh - r * rng if d == "up" else sl + r * rng, 2) for k, r in zip(FIB_KEYS, FIBS)}


def build_zones(levels, atr, price, sdir, mult=0.3):
    half = atr * mult
    zs = []
    for src, lv in levels.items():
        if atr > 0 and abs(lv - price) > 10 * atr:
            continue
        zs.append({"level": lv, "low": round(lv - half, 2), "high": round(lv + half, 2),
                   "source": src, "swing_dir": sdir if src.startswith("fib_") else None})
    zs.sort(key=lambda z: z["level"], reverse=True)
    return zs


def classify(src, swing_dir):
    s = src.upper()
    if s.startswith("R") or "_R" in s:
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


# ----------------------------------------------------------------- engine
def run(a, d=None, H1=None, H4=None, D1=None, seed=7, verbose=False):
    d = d or data.load()
    H1 = H1 or Bars(d, 3600)
    H4 = H4 or Bars(d, 14400)
    D1 = D1 or Bars(d, 86400)
    T, O, Hh, Ll, C = d["t"], d["o"], d["h"], d["l"], d["c"]
    SP = a.spread
    rng = np.random.default_rng(seed)
    t0 = dt.datetime.fromisoformat(a.start).replace(tzinfo=dt.timezone.utc).timestamp()
    t1 = dt.datetime.fromisoformat(a.end).replace(tzinfo=dt.timezone.utc).timestamp()

    h4_idx_of = np.searchsorted(H4.t, H1.t, side="right") - 1      # H4 bar containing H1 bar
    d1_idx_of = np.searchsorted(D1.t, H1.t, side="right") - 1

    trades = []
    zones, cached_date = [], None
    ledger = {}                    # zone source -> closed count (this UTC day)
    bias, bias_h4 = None, None
    pos = None                     # open position
    pend = None                    # option C pending
    last_mgmt = None               # last M1 index managed

    def manage(j_from, j_to):
        """Walk the open position bar by bar over M1 [j_from, j_to). Returns closed or not."""
        nonlocal pos
        for j in range(j_from, j_to):
            p = pos
            sgn = p["sgn"]
            o, h, l = O[j], Hh[j], Ll[j]
            # the side that closes the position: buy closes on bid, sell on ask
            if sgn == 1:
                adv, fav, op = l, h, o
            else:
                adv, fav, op = h + SP, l + SP, o + SP
            # stop first (gap through -> open)
            if sgn * (adv - p["sl"]) <= 0:
                px = op if sgn * (op - p["sl"]) <= 0 else p["sl"]
                close(px, j, "sl" if not p["moved"] else "be/trail")
                return True
            # partial at +1 ATR (mid), then SL -> entry
            mid_fav = fav + (-SP / 2 if sgn == -1 else SP / 2)
            if a.partial and not p["partial"] and sgn * (mid_fav - p["fill"]) >= p["atr"]:
                ppx = p["fill"] + sgn * p["atr"] - SP / 2 * sgn   # half closed at market
                p["realised"] += 0.5 * sgn * (ppx - p["fill"])
                p["frac"] = 0.5
                p["partial"] = True
                if sgn * (p["fill"] - p["sl"]) > 0:
                    p["sl"], p["moved"] = p["fill"], True
            # take profit
            if p["tp"] is not None and sgn * (fav - p["tp"]) >= 0:
                close(p["tp"], j, "tp")
                return True
            # BE / trail on mid (ATR of the current H1)
            atr_now = p["atr_now"]
            if a.be_trail:
                dist = max(atr_now, a.trail_floor)
                if sgn * (mid_fav - p["fill"]) >= max(atr_now, a.be_floor):
                    if sgn * (p["fill"] - p["sl"]) > 0:
                        p["sl"], p["moved"] = p["fill"], True
                cand = mid_fav - sgn * dist
                if sgn * (cand - p["sl"]) > 0:
                    p["sl"], p["moved"] = round(cand, 2), True
            if a.runner_be is not None:            # runner: BE at +x, trail y
                best = p.setdefault("best", p["fill"])
                best = max(best, mid_fav) if sgn == 1 else min(best, mid_fav)
                p["best"] = best
                u = p["atr"] if a.runner_atr else 1.0       # runner distances in ATR or $
                if sgn * (best - p["fill"]) >= a.runner_be * u:
                    tr_ = a.runner_trail * u
                    cand = max(p["fill"], best - tr_) if sgn == 1 else min(p["fill"], best + tr_)
                    if sgn * (cand - p["sl"]) > 0:
                        p["sl"], p["moved"] = cand, True
            if a.max_hold and j - p["j"] >= a.max_hold:
                close(O[j + 1] + (SP if sgn == -1 else 0), j, "time")
                return True
        return False

    def close(px, j, why):
        nonlocal pos
        p = pos
        pnl = p["realised"] + p["frac"] * p["sgn"] * (px - p["fill"])
        r = pnl / p["risk"]
        trades.append(dict(t=int(T[p["j"]]), t_exit=int(T[j]), dir=p["dir"], zone=p["zone"],
                           fill=round(p["fill"], 2), exit=round(px, 2), why=why, pnl=round(pnl, 2),
                           r=round(r, 3), atr=p["atr"], partial=p["partial"], pol=p["pol"],
                           bias=p["bias"], wait=p["wait"], level=p["level"], j=p["j"]))
        ledger[p["zone"]] = ledger.get(p["zone"], 0) + 1
        pos = None

    def open_pos(j, trig_px, sgn, info):
        nonlocal pos
        fill = O[j] + (SP if sgn == 1 else 0)
        atr = info["atr"]
        sl = trig_px - sgn * a.sl_mult * atr
        if a.tp_mode == "fixed":
            tp = trig_px + sgn * a.tp_usd
        elif a.tp_mode == "atr":
            tp = trig_px + sgn * a.tp_atr * atr
        else:
            tp = None
        risk = abs(fill - sl)
        if risk <= 0 or sgn * (fill - sl) <= 0:
            return
        pos = dict(j=j, sgn=sgn, dir="BUY" if sgn == 1 else "SELL", fill=fill, sl=sl, tp=tp,
                   atr=atr, atr_now=atr, risk=risk, realised=0.0, frac=1.0, partial=False,
                   moved=False, zone=info["zone"], pol=info["pol"], bias=info["bias"], level=info["level"],
                   wait=j - info["j0"])

    k_first = int(np.searchsorted(H1.t, t0))
    k_last = int(np.searchsorted(H1.t, t1))
    for k in range(max(k_first, 210 * 4), k_last):
        i0 = int(H1.s[k])
        i_next = int(H1.s[k + 1]) if k + 1 < len(H1.s) else len(T)
        now_b = int(T[i0])
        now_u = broker_to_utc(now_b)
        udate = dt.datetime.fromtimestamp(now_u, dt.timezone.utc)
        weekend = udate.weekday() >= 5
        bid = O[i0]
        price = bid + SP / 2

        # ATR(H1) over 42 closed + the forming bar (= its first tick)
        hs = list(H1.h[k - 42:k]) + [bid]
        ls = list(H1.l[k - 42:k]) + [bid]
        cs = list(H1.c[k - 42:k]) + [bid]
        atr = wilder_atr(hs, ls, cs)
        if pos is not None:
            pos["atr_now"] = atr

        g = int(h4_idx_of[k])        # forming H4 bar
        if not weekend:
            # zones once per UTC day
            day = udate.date()
            if day != cached_date:
                di = int(d1_idx_of[k])
                daily_open = D1.o[di]
                prev = di - 1
                gann = gann_levels(daily_open)
                piv = fib_pivots(D1.h[prev], D1.l[prev], D1.c[prev])
                s4 = int(H4.s[g])
                fh = max(Hh[s4:i0].max(), bid) if i0 > s4 else bid
                fl = min(Ll[s4:i0].min(), bid) if i0 > s4 else bid
                wh = list(H4.h[g - 49:g]) + [fh]
                wl = list(H4.l[g - 49:g]) + [fl]
                sh, sl_ = max(wh), min(wl)
                sdir = "up" if bid > (sh + sl_) / 2 else "down"
                levels = {**gann, **piv, **fib_retr(sh, sl_, sdir)}
                zones = build_zones(levels, atr, price, sdir, a.zone_mult)
                cached_date = day
                ledger = {}
            # H4 bias at each new H4 bar (forming close = its open)
            if bias_h4 != g:
                closes = list(H4.c[g - 199:g]) + [H4.o[g] if int(H4.s[g]) == i0 else bid]
                bias = "bullish" if closes[-1] > ema_sma_seed(closes, a.ema) else "bearish"
                bias_h4 = g

            # ---- evaluate_signal at the H1 open
            sig = None
            if zones and pos is None:
                z = next((z for z in zones if z["low"] <= price <= z["high"]), None)
                if z is not None:
                    kind = classify(z["source"], z["swing_dir"])
                    if z["source"] == "PP":
                        kind = "resistance" if price < z["level"] else ("support" if price > z["level"] else kind)
                    orig = kind
                    if a.polarity:
                        closes10 = H4.c[g - 10:g]
                        if kind == "support" and (closes10 < z["level"]).any():
                            kind = "resistance"
                        elif kind == "resistance" and (closes10 > z["level"]).any():
                            kind = "support"
                    b = bias if a.bias else ("bullish" if kind == "support" else "bearish")
                    direction = None
                    if b == "bullish" and kind == "support":
                        direction, cdir = 1, "above"
                    elif b == "bearish" and kind == "resistance":
                        direction, cdir = -1, "below"
                    if direction is not None:
                        ho, hc = H1.o[k - 1], H1.c[k - 1]
                        ok = (hc > z["level"] and ho < z["level"]) if cdir == "above" else \
                             (hc < z["level"] and ho > z["level"])
                        if ok or not a.confirm:
                            sig = dict(sgn=direction, zone=z["source"], level=z["level"],
                                       zmid=(z["high"] + z["low"]) / 2, h1c=hc, atr=atr,
                                       pol="yes" if kind != orig else "no", bias=bias, j0=i0)
            if sig is not None and ledger.get(sig["zone"], 0) < a.zone_per_day:
                if a.invert:
                    sig["sgn"] = -sig["sgn"]
                if a.random_dir:
                    sig["sgn"] = 1 if rng.random() < 0.5 else -1
                if a.entry == "immediate":
                    open_pos(i0, bid, sig["sgn"], sig)
                elif pend is None or pend["zone"] != sig["zone"]:
                    pend = dict(sig, lo=min(sig["zmid"], sig["h1c"]), hi=max(sig["zmid"], sig["h1c"]),
                                waited=0)

        # ---- walk this hour's M1 bars: option C pending, then management
        j = i0
        while j < i_next:
            if pend is not None and pos is None and j >= pend["j0"]:
                pend["waited"] += 1
                sgn = pend["sgn"]
                if pend["waited"] >= a.c_bars:
                    pend = None
                else:
                    cur = O[j] + (SP if sgn == -1 else 0)
                    if sgn * (cur - pend["zmid"]) > a.c_runaway * pend["atr"]:
                        pend = None
                    elif a.entry == "bug":
                        if pend["lo"] <= O[j] <= pend["hi"] and rng.random() < a.p_first_tick:
                            info, pend = pend, None
                            open_pos(j, O[j], sgn, info)
                    else:   # intended: closed M1 bar j in direction inside the band -> next open
                        ok = (C[j] > O[j]) if sgn == 1 else (C[j] < O[j])
                        if ok and pend["lo"] <= C[j] <= pend["hi"] and j + 1 < len(T):
                            info, pend = pend, None
                            open_pos(j + 1, C[j], sgn, info)
                            if pos is not None:
                                j += 1
                                continue
            if pos is not None:
                if manage(j, j + 1):
                    pass
            j += 1
        if pend is not None and pos is not None:
            pend = None
    return trades


def summary(tr, label=""):
    if not tr:
        print(f"{label:34s} n=0")
        return {}
    r = np.array([x["r"] for x in tr])
    gw, gl = r[r > 0].sum(), -r[r < 0].sum()
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    out = dict(n=len(r), win=float((r > 0).mean()), pf=gw / gl if gl else float("inf"),
               net=float(r.sum()), avg=float(r.mean()), dd=float(dd))
    print(f"{label:34s} n={out['n']:5d} win={out['win']:.0%} PF={out['pf']:.2f} "
          f"net={out['net']:+7.1f}R avg={out['avg']:+.3f}R maxDD={out['dd']:.1f}R")
    return out


def by_year(tr):
    ys = {}
    for x in tr:
        ys.setdefault(dt.datetime.fromtimestamp(x["t"], dt.timezone.utc).year, []).append(x["r"])
    print("   year   n   win    PF    netR")
    for y in sorted(ys):
        r = np.array(ys[y])
        gl = -r[r < 0].sum()
        print(f"   {y} {len(r):4d} {np.mean(r > 0):4.0%} {r[r > 0].sum() / gl if gl else 99:5.2f} {r.sum():+7.1f}")


def args(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2010-03-01")
    p.add_argument("--end", default="2026-10-13")
    p.add_argument("--spread", type=float, default=0.35)
    p.add_argument("--entry", default="bug", choices=["bug", "intended", "immediate"])
    p.add_argument("--p-first-tick", type=float, default=0.4)
    p.add_argument("--c-bars", type=int, default=15)
    p.add_argument("--c-runaway", type=float, default=1.5)
    p.add_argument("--sl-mult", type=float, default=1.0)
    p.add_argument("--tp-mode", default="fixed", choices=["fixed", "atr", "none"])
    p.add_argument("--tp-usd", type=float, default=9.0)
    p.add_argument("--tp-atr", type=float, default=1.0)
    p.add_argument("--partial", type=int, default=1)
    p.add_argument("--be-trail", type=int, default=1)
    p.add_argument("--be-floor", type=float, default=15.0)
    p.add_argument("--trail-floor", type=float, default=15.0)
    p.add_argument("--runner-be", type=float, default=None)
    p.add_argument("--runner-trail", type=float, default=12.0)
    p.add_argument("--runner-atr", type=int, default=0)
    p.add_argument("--max-hold", type=int, default=0)
    p.add_argument("--polarity", type=int, default=1)
    p.add_argument("--bias", type=int, default=1)
    p.add_argument("--confirm", type=int, default=1)
    p.add_argument("--ema", type=int, default=50)
    p.add_argument("--zone-mult", type=float, default=0.3)
    p.add_argument("--zone-per-day", type=int, default=1)
    p.add_argument("--invert", type=int, default=0)
    p.add_argument("--random-dir", type=int, default=0)
    return p.parse_args(argv)


if __name__ == "__main__":
    A = args()
    tr = run(A)
    summary(tr, "D faithful")
    by_year(tr)
