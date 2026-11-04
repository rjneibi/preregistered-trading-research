# STATUS: RESEARCH-ONLY — ICT parameter lab; params chosen on the same window (selection bias,
# small OOS leg). Caveated in-file. See AUDIT_REPORT.md section 4-research.
"""
ict_scalper_london.py — London-only ICT scalper variant (CONFIRMATORY re-run).
================================================================================
DERIVED FROM ict_scalper_backtest.py (committed 2bb43b1). This variant:
  * restricts the kill-zone to LONDON ONLY (02:00–05:00 NY); the NY window is dropped.
  * HARD-LOCKS the parameters a priori — sweep_min=50, disp_mult=1.75, TP=fixed_1500,
    carried verbatim from the FULL-MODEL IS optimization. There is NO grid search and
    NO re-optimization on this subset (anti-overfit guardrail).
  * still runs the 70/30 split, but reports it as DESCRIPTIVE ONLY. London-only was
    chosen AFTER observing it outperform in THIS SAME window, so this re-run is
    confirmatory of the existing data, NOT an independent test. The OOS leg is ~2
    trades; real statistical confidence requires FORWARD trades, not this re-run.

Outputs (do NOT overwrite the full-model outputs):
  research/results/ict_london_results.md
  research/results/ict_london_equity.csv
  DB table ict_london_trades (CREATE IF NOT EXISTS; clears only its own rows).

Per-trade ledger is in DOLLARS at a fixed 1.00 lot / 100oz contract (confirmed from
symbol_info), not risk-fractional sizing. The hard order-send guard remains intact;
MAGIC 20260608 is a label only.

Run:  py -3.11 research/ict_scalper_london.py
================================================================================
ORIGINAL HEADER (full model) follows for reference:

ict_scalper_backtest.py — Pure-ICT scalping entry-edge backtest for XAUUSD.
================================================================================
RESEARCH / BACKTEST ONLY. Read-only MT5 connection (copy_rates_* only). No order
function is imported or reachable (hard-guarded below). Touches nothing the live
bot uses — all I/O lives under research/. MAGIC 20260608 is a reserved LABEL only;
it is never attached to an order/position in this phase.

Goal: isolate whether a deterministic, intraday ICT scalp model (sweep -> MSS /
displacement -> FVG/OTE entry, $10-20 / 1000-2000pt targets) has a STANDALONE
entry edge that clears the project go/no-go bar, validated on a 70/30 chronological
walk-forward (optimise 3 free params on IS, lock, evaluate unchanged on OOS).

Gate stack (sequential, theory-locked except the 3 optimised params):
  1 Kill-zone window (NY): London 02:00-05:00, NY 07:00-10:00
  2 Intraday bias (Judas vs NY-midnight open): shorts only on a buy-side sweep
    ABOVE midnight open; longs only on a sell-side sweep BELOW it
  3 Liquidity pools (intraday): prior-session high/low + M1 fractal(N=2) extremes
    (relative-equal clustering within 0.1*ATR)
  4 Sweep: penetrate level >= sweep_min pts, close back on origin side within 3
    bars; penetration <= sweep_max(800) else treated as breakout
  5 Displacement + MSS: M1 body >= disp_mult*ATR(14) in reversal dir AND breaks
    the most recent opposing micro-swing
  6 FVG/OTE: 3-candle imbalance in the displacement leg, sitting in the 62-79%
    retracement band; entry = limit at proximal FVG edge
  7 Stop = beyond sweep extreme + 0.5*ATR; Target = fixed {1000,1500,2000} OR
    nearest opposing pool

Free params (optimised on IS only): sweep_min{50,100,150,200},
disp_mult{1.25,1.5,1.75,2.0}, TP variant{1000,1500,2000,opposing-pool}.

Run:  py -3.11 research/ict_scalper_backtest.py
"""
import os
import sys
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, date
from zoneinfo import ZoneInfo

import numpy as np
import MetaTrader5 as mt5

# ── HARD GUARD: prove no order-sending function is reachable from this script ──
# Any accidental trade call must raise immediately. We do NOT import the live
# trade surface; we additionally neuter the names on the mt5 module object.
for _fn in ("order_send", "order_check", "order_calc_margin", "order_calc_profit",
            "positions_get", "Buy", "Sell"):
    if hasattr(mt5, _fn):
        def _blocked(*_a, _n=_fn, **_k):
            raise RuntimeError(f"GUARD: live trade/position fn '{_n}' is forbidden "
                               f"in this research script")
        setattr(mt5, _fn, _blocked)

# ── Constants ─────────────────────────────────────────────────────────────────
MAGIC_RESERVED = 20260608          # LABEL ONLY — never attached to any order here
TERMINAL_PRIMARY = "<mt5-terminal-path>"
TERMINAL_FALLBACK = "<mt5-terminal-path>"
GOLD_CANDIDATES = ["XAUUSD", "GOLD", "XAUUSD.x", "XAUUSDm", "GOLD.x", "XAUUSD."]
PREFERRED_SYMBOL = "XAUUSD"        # canonical name the live profiles use

MAX_MONTHS = 24
IN_SAMPLE_PCT = 0.70
NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

# Theory-locked params (NOT optimised)
FRACTAL_N = 2
OTE_LO, OTE_HI = 0.62, 0.79
SWEEP_WINDOW = 3                   # bars to close back inside
SWEEP_MAX_PTS = 800                # beyond this = genuine breakout, reject
STOP_BUFFER_ATR = 0.5
FILL_BUFFER_PTS = 1                # limit must be traded THROUGH by 1 pt
ENTRY_CANCEL_BARS = 10
DISP_SEARCH_BARS = 8              # bars after close-back to find displacement
FVG_SEARCH_BARS = 6              # bars after displacement to find/scan FVG
POOL_LOOKBACK_BARS = 240          # 4h of M1 for recent fractal pools
SPREAD_FLOOR_PTS = 25
NEWS_BLACKOUT = (("08:25", "09:00"),)   # NY; v1 proxy for recurring USD release
ATR_PERIOD = 14
RISK_PCT = 0.005                  # 0.5% risk per trade
START_BALANCE = 10000.0

# ── HARD-LOCKED params (a priori; carried from full-model IS optimization) ──────
# NO grid search, NO re-optimization on this subset. The grids below are retained
# only so generate_setups() can use SWEEP_MIN_GRID[0] as its sweep floor; the single
# locked combination is what is actually evaluated.
LOCK_SWEEP_MIN = 50
LOCK_DISP_MULT = 1.75
LOCK_TP = "fixed_1500"
SWEEP_MIN_GRID = [LOCK_SWEEP_MIN]       # floor used inside generate_setups()

# Account sizes for $-drawdown reporting (per task spec)
ACCOUNT_SIZES = [10000.0, 25000.0, 50000.0]
FIXED_LOT = 1.00                        # ledger sizing: fixed 1.00 lot, NOT % risk

# Kill zones in NY local time (start_h, start_m, end_h, end_m, label)
# LONDON ONLY — the NY window is intentionally dropped for this variant.
KILLZONES = [(2, 0, 5, 0, "LONDON")]

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(_HERE, "results")
DB_PATH = os.path.join(_HERE, "trades.db")


# ── EU DST broker-clock model ────────────────────────────────────────────────
def _last_sunday(year, month):
    d = date(year, month, 31)
    while d.month != month:
        d = d - timedelta(days=1)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def eu_dst_active(d):
    """True if EU summer time (EEST) is in effect on naive date/datetime `d`.
    EU DST: last Sun Mar 01:00 UTC -> last Sun Oct 01:00 UTC."""
    y = d.year
    start = _last_sunday(y, 3)
    end = _last_sunday(y, 10)
    dd = d.date() if isinstance(d, datetime) else d
    return start <= dd < end


class ServerClock:
    """Converts MT5 server-wall timestamps to America/New_York with DST.

    MT5 encodes bar/tick time as the broker's wall clock stored as a Unix epoch,
    so utcfromtimestamp() recovers the server wall clock (naive). We detect the
    current server->UTC offset, infer the winter base offset assuming the broker
    observes EU DST (the dominant convention on MetaQuotes/gold feeds — verified
    by the live +3 reading in EU summer), then map each historical bar:
        true_utc = server_wall - broker_offset(date);  ny = true_utc -> NY tz
    Limitation logged in the report: historical broker DST transitions are
    modelled by the EU schedule rather than reconstructed tick-by-tick.
    """
    def __init__(self, offset_now_hours, now_naive_server):
        self.offset_now = offset_now_hours
        self.is_dst_now = eu_dst_active(now_naive_server)
        self.base_winter = offset_now_hours - (1 if self.is_dst_now else 0)
        self.regime = "EU DST (EET/EEST)" if self.base_winter == 2 else \
                      f"fixed/other base UTC+{self.base_winter}"

    def offset_for(self, server_wall):
        return self.base_winter + (1 if eu_dst_active(server_wall) else 0)

    def to_ny(self, epoch):
        sw = datetime.utcfromtimestamp(int(epoch))
        true_utc = sw - timedelta(hours=self.offset_for(sw))
        return true_utc.replace(tzinfo=UTC).astimezone(NY)


# ── Connection / detection ───────────────────────────────────────────────────
def connect():
    for path in (TERMINAL_PRIMARY, TERMINAL_FALLBACK):
        if mt5.initialize(path=path):
            return path
    print("FATAL: mt5.initialize failed on both terminals:", mt5.last_error())
    sys.exit(1)


def detect_symbol():
    selectable = []
    for c in GOLD_CANDIDATES:
        if mt5.symbol_select(c, True):
            info = mt5.symbol_info(c)
            if info is not None:
                selectable.append(c)
    if not selectable:
        print("FATAL: no gold symbol selectable on this terminal."); sys.exit(1)
    # Prefer the canonical XAUUSD used by the live profiles; many brokers expose
    # GOLD as an alias, so multiple matches is normal and not fatal.
    chosen = PREFERRED_SYMBOL if PREFERRED_SYMBOL in selectable else selectable[0]
    return chosen, selectable


def detect_server_clock(symbol, latest_bar_epoch=None):
    """Detect the broker server->UTC offset and build a ServerClock.

    The live-tick method (compare last tick wall-clock to real UTC) is only valid
    when the quote is FRESH. On a weekend/holiday the last tick is stale (e.g. the
    Friday close), so utc_now has advanced hours past it and the naive difference
    yields a garbage offset. We therefore:
      1. take the freshest server timestamp available (max of last tick and the
         latest M1 bar),
      2. accept the detected offset only if it lands in this feed's plausible band
         (EET/EEST => UTC+2/+3; band [-2, +4] gives margin),
      3. otherwise fall back to the EET base (UTC+2) + EU-DST model for "now".
    The detection path is returned for logging."""
    t = mt5.symbol_info_tick(symbol)
    tick_epoch = int(t.time) if t is not None else 0
    ref_epoch = max(tick_epoch, int(latest_bar_epoch or 0))
    server_wall = datetime.utcfromtimestamp(ref_epoch) if ref_epoch else None
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    info = {"tick_epoch": tick_epoch, "bar_epoch": int(latest_bar_epoch or 0)}
    if server_wall is not None:
        off = round((server_wall - utc_now).total_seconds() / 3600.0)
        if -2 <= off <= 4:                    # plausible -> trust the live reading
            info["method"] = "live"; info["raw_off"] = off
            return ServerClock(off, server_wall), info
        info["stale_off"] = off
    # Fallback: stale quote (closed market). Assume EET broker base + EU DST.
    off_model = 2 + (1 if eu_dst_active(utc_now) else 0)
    info["method"] = "EET-DST fallback (stale quote)"; info["raw_off"] = off_model
    return ServerClock(off_model, utc_now), info


# ── Data ─────────────────────────────────────────────────────────────────────
def fetch(symbol, tf, start, end):
    mt5.symbol_select(symbol, True)
    r = mt5.copy_rates_range(symbol, tf, start, end)
    if r is None or len(r) == 0:
        print(f"FATAL: no data tf={tf}: {mt5.last_error()}"); sys.exit(1)
    return r


def fetch_chunked(symbol, tf, start, end, chunk_days=28, label=""):
    """Fetch a timeframe in <=chunk_days windows (walking backward from `end`)
    and stitch the pieces together. A single copy_rates_range over many months of
    M1 silently fails on this terminal ('Invalid params' beyond ~60 days); chunking
    forces the terminal to serve each window, and we keep whatever actually exists.

    - Dedupe by bar epoch (overlapping/adjacent windows are harmless).
    - Stop early when history runs out: two consecutive windows that return <=1 bar
      going backward are treated as 'no more history' and we break.
    - It cannot conjure data the broker does not hold; the real stitched span is
      reported by the caller and governs confidence, not MAX_MONTHS.
    """
    mt5.symbol_select(symbol, True)
    seen = {}                       # epoch -> tuple(row)  (dedup)
    dtype = None
    cur_end = end
    empty_streak = 0
    windows = 0
    while cur_end > start:
        cur_start = max(start, cur_end - timedelta(days=chunk_days))
        r = mt5.copy_rates_range(symbol, tf, cur_start, cur_end)
        windows += 1
        if r is not None and len(r) > 1:
            if dtype is None:
                dtype = r.dtype
            for row in r:
                seen[int(row["time"])] = tuple(row)
            empty_streak = 0
        else:
            empty_streak += 1
            if empty_streak >= 2:   # history exhausted going backward
                break
        cur_end = cur_start
    if not seen:
        print(f"FATAL: no data tf={tf} ({label}) after chunked fetch over "
              f"{windows} windows: {mt5.last_error()}"); sys.exit(1)
    epochs = sorted(seen)           # ascending, deduped
    arr = np.array([seen[e] for e in epochs], dtype=dtype)
    print(f"  chunked fetch {label or tf}: {len(arr)} bars across {windows} "
          f"window(s) of <={chunk_days}d")
    return arr


@dataclass
class M1Data:
    epoch: np.ndarray
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    spread: np.ndarray
    ny: list                       # list[datetime tz-aware NY]
    atr: np.ndarray
    fr_high: np.ndarray            # bool fractal swing high
    fr_low: np.ndarray             # bool fractal swing low
    n: int


def build_m1(rates, clock):
    o = rates["open"].astype(float)
    h = rates["high"].astype(float)
    l = rates["low"].astype(float)
    c = rates["close"].astype(float)
    sp = rates["spread"].astype(float)
    ep = rates["time"].astype(np.int64)
    n = len(ep)
    ny = [clock.to_ny(e) for e in ep]
    # ATR(14) — simple rolling mean of true range (sufficient for gating)
    prev_c = np.empty(n); prev_c[0] = c[0]; prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    atr = np.full(n, np.nan)
    if n >= ATR_PERIOD:
        csum = np.cumsum(tr)
        atr[ATR_PERIOD - 1] = csum[ATR_PERIOD - 1] / ATR_PERIOD
        atr[ATR_PERIOD:] = (csum[ATR_PERIOD:] - csum[:-ATR_PERIOD]) / ATR_PERIOD
    # fractal N=2
    fr_high = np.zeros(n, dtype=bool)
    fr_low = np.zeros(n, dtype=bool)
    for i in range(FRACTAL_N, n - FRACTAL_N):
        hi = h[i]
        if hi > h[i-1] and hi > h[i-2] and hi > h[i+1] and hi > h[i+2]:
            fr_high[i] = True
        lo = l[i]
        if lo < l[i-1] and lo < l[i-2] and lo < l[i+1] and lo < l[i+2]:
            fr_low[i] = True
    return M1Data(ep, o, h, l, c, sp, ny, atr, fr_high, fr_low, n)


# ── Sessions / midnight opens ────────────────────────────────────────────────
def in_killzone(dt):
    hm = dt.hour * 60 + dt.minute
    for sh, sm, eh, em, label in KILLZONES:
        if sh * 60 + sm <= hm < eh * 60 + em:
            return label
    return None


def in_news_blackout(dt):
    hm = dt.hour * 60 + dt.minute
    for a, b in NEWS_BLACKOUT:
        ah, am = map(int, a.split(":")); bh, bm = map(int, b.split(":"))
        if ah * 60 + am <= hm < bh * 60 + bm:
            return True
    return False


def build_day_context(m1):
    """Per NY-date: midnight open + Asian (prev 20:00-02:00) and London
    (02:00-07:00) session high/low. One pass."""
    midnight = {}          # date -> open price of the 00:00 NY M1 bar
    asian = {}             # date -> [hi, lo]  (prev day 20:00 .. this day 02:00)
    london = {}            # date -> [hi, lo]  (this day 02:00 .. 07:00)
    for i in range(m1.n):
        dt = m1.ny[i]
        d = dt.date()
        hm = dt.hour * 60 + dt.minute
        if dt.hour == 0 and dt.minute == 0 and d not in midnight:
            midnight[d] = m1.o[i]
        # London window 02:00-07:00 -> attributed to this date
        if 2 * 60 <= hm < 7 * 60:
            a = london.setdefault(d, [m1.h[i], m1.l[i]])
            a[0] = max(a[0], m1.h[i]); a[1] = min(a[1], m1.l[i])
        # Asian window: 20:00-23:59 belongs to NEXT day's session; 00:00-02:00 to today
        if hm >= 20 * 60:
            nd = d + timedelta(days=1)
            a = asian.setdefault(nd, [m1.h[i], m1.l[i]])
            a[0] = max(a[0], m1.h[i]); a[1] = min(a[1], m1.l[i])
        elif hm < 2 * 60:
            a = asian.setdefault(d, [m1.h[i], m1.l[i]])
            a[0] = max(a[0], m1.h[i]); a[1] = min(a[1], m1.l[i])
    return midnight, asian, london


# ── Data-quality gate ────────────────────────────────────────────────────────
def data_quality(m1):
    """Kill-zone M1 coverage + gap scan. Returns dict."""
    kz_present = 0
    kz_expected = 0
    gaps = 0
    # count expected vs present minute-bars inside killzones; flag >5min gaps in KZ
    last_kz_epoch = None
    last_kz_label = None
    # Build set of kz minutes present per (date,label) is heavy; approximate by
    # walking bars: expected = killzone span in minutes summed over distinct days
    # that have ANY killzone bar (so weekends/holidays don't inflate the denom).
    days_with_kz = {}
    for i in range(m1.n):
        dt = m1.ny[i]
        lbl = in_killzone(dt)
        if lbl is None:
            continue
        kz_present += 1
        days_with_kz.setdefault((dt.date(), lbl), True)
        if last_kz_epoch is not None and last_kz_label == lbl:
            gap_min = (int(m1.epoch[i]) - last_kz_epoch) / 60.0
            if 5 < gap_min:
                gaps += 1
        last_kz_epoch = int(m1.epoch[i]); last_kz_label = lbl
    # expected minutes per killzone label
    span = {lbl: (eh*60+em) - (sh*60+sm) for sh, sm, eh, em, lbl in KILLZONES}
    for (d, lbl) in days_with_kz:
        kz_expected += span[lbl]
    cov = (kz_present / kz_expected) if kz_expected else 0.0
    return {"kz_present": kz_present, "kz_expected": kz_expected,
            "coverage": cov, "kz_gaps_gt5min": gaps,
            "trustworthy": cov >= 0.95}


# ── Setup geometry ───────────────────────────────────────────────────────────
@dataclass
class Setup:
    arm_idx: int                   # bar where displacement confirmed
    direction: str                 # BUY / SELL
    killzone: str
    sweep_extreme: float           # swept high (SELL) / low (BUY)
    penetration_pts: float
    disp_ratio: float              # displacement body / ATR
    limit: float                   # entry limit (proximal FVG edge)
    sl: float
    risk: float                    # |sl - limit|  (price)
    atr_at: float
    opp_pool: float                # nearest opposing pool for opposing_pool TP (or nan)
    fvg_idx: int


def nearest_pools(m1, i, point):
    """Recent buy-side (fractal highs) and sell-side (fractal lows) pools within
    POOL_LOOKBACK_BARS, deduped into relative-equal clusters (<=0.1*ATR)."""
    lo = max(FRACTAL_N, i - POOL_LOOKBACK_BARS)
    atr = m1.atr[i]
    tol = 0.1 * atr if atr == atr else 0.0
    highs = [m1.h[k] for k in range(lo, i) if m1.fr_high[k]]
    lows = [m1.l[k] for k in range(lo, i) if m1.fr_low[k]]

    def cluster(levels):
        if not levels:
            return []
        levels = sorted(levels)
        out = [[levels[0]]]
        for v in levels[1:]:
            if abs(v - out[-1][-1]) <= tol:
                out[-1].append(v)
            else:
                out.append([v])
        return [sum(g) / len(g) for g in out]
    return cluster(highs), cluster(lows)


def generate_setups(m1, midnight, asian, london, disp_mult, point):
    """One pass at a given disp_mult. Records penetration_pts so the 4 sweep_min
    thresholds filter downstream; the displacement candle is the FIRST body that
    clears disp_mult*ATR, so geometry is correct per disp_mult."""
    setups = []
    n = m1.n
    for i in range(POOL_LOOKBACK_BARS, n - FVG_SEARCH_BARS - 2):
        dt = m1.ny[i]
        lbl = in_killzone(dt)
        if lbl is None:
            continue
        d = dt.date()
        mo = midnight.get(d)
        if mo is None:
            continue
        atr = m1.atr[i]
        if not (atr == atr) or atr <= 0:
            continue

        # candidate marked levels: prior session + recent fractal clusters
        buy_pools, sell_pools = nearest_pools(m1, i, point)
        if lbl == "LONDON":
            ps = asian.get(d)
        else:
            ps = london.get(d)
        if ps is not None:
            buy_pools = buy_pools + [ps[0]]
            sell_pools = sell_pools + [ps[1]]

        # ---- SHORT branch: buy-side (high) sweep ABOVE midnight open ----
        for lvl in buy_pools:
            if lvl <= mo:
                continue                          # bias: sweep must be above midnight
            pen = (m1.h[i] - lvl) / point
            if pen < SWEEP_MIN_GRID[0]:
                continue
            if pen > SWEEP_MAX_PTS:
                continue
            if m1.h[i] < lvl + SWEEP_MIN_GRID[0] * point:
                continue
            s = _short_setup(m1, i, lvl, pen, mo, atr, disp_mult, point, lbl,
                             sell_pools)
            if s is not None:
                setups.append(s)
                break                              # one setup per bar/dir

        # ---- LONG branch: sell-side (low) sweep BELOW midnight open ----
        for lvl in sell_pools:
            if lvl >= mo:
                continue
            pen = (lvl - m1.l[i]) / point
            if pen < SWEEP_MIN_GRID[0]:
                continue
            if pen > SWEEP_MAX_PTS:
                continue
            if m1.l[i] > lvl - SWEEP_MIN_GRID[0] * point:
                continue
            s = _long_setup(m1, i, lvl, pen, mo, atr, disp_mult, point, lbl,
                            buy_pools)
            if s is not None:
                setups.append(s)
                break
    return setups


def _short_setup(m1, i, lvl, pen, mo, atr, disp_mult, point, lbl, sell_pools):
    # close back BELOW lvl within SWEEP_WINDOW bars
    cb = None
    for k in range(i, min(i + SWEEP_WINDOW, m1.n)):
        if m1.c[k] < lvl:
            cb = k; break
    if cb is None:
        return None
    sweep_high = max(m1.h[i:cb + 1])
    # displacement: first bar after cb with bearish body >= disp_mult*ATR
    disp = None
    for j in range(cb, min(cb + DISP_SEARCH_BARS, m1.n)):
        body = m1.o[j] - m1.c[j]
        if m1.c[j] < m1.o[j] and body >= disp_mult * atr:
            disp = j; break
    if disp is None:
        return None
    disp_ratio = (m1.o[disp] - m1.c[disp]) / atr
    # MSS: displacement close must break the most recent fractal LOW before sweep
    last_low = None
    for k in range(i, max(FRACTAL_N, i - POOL_LOOKBACK_BARS), -1):
        if m1.fr_low[k]:
            last_low = m1.l[k]; break
    if last_low is None or m1.c[disp] >= last_low:
        return None
    # FVG (bearish): candle[x-2].low > candle[x].high, most proximal after disp
    fvg = None
    for x in range(disp, min(disp + FVG_SEARCH_BARS, m1.n)):
        if x - 2 < 0:
            continue
        if m1.l[x - 2] > m1.h[x]:
            gap_lo, gap_hi = m1.h[x], m1.l[x - 2]      # gap zone
            fvg = (x, gap_lo, gap_hi); break
    if fvg is None:
        return None
    x, gap_lo, gap_hi = fvg
    # OTE: proximal edge (lower edge gap_lo, first touched on retrace up) in 62-79%
    leg_hi = sweep_high
    leg_lo = min(m1.l[cb:disp + 1])
    rng = leg_hi - leg_lo
    if rng <= 0:
        return None
    entry = gap_lo                                   # proximal edge for short
    frac = (entry - leg_lo) / rng
    if not (OTE_LO <= frac <= OTE_HI):
        return None
    sl = sweep_high + STOP_BUFFER_ATR * atr
    risk = sl - entry
    if risk <= 0:
        return None
    opp = max([p for p in sell_pools if p < entry], default=float("nan"))
    return Setup(disp, "SELL", lbl, sweep_high, pen, disp_ratio, entry, sl, risk,
                 atr, opp, x)


def _long_setup(m1, i, lvl, pen, mo, atr, disp_mult, point, lbl, buy_pools):
    cb = None
    for k in range(i, min(i + SWEEP_WINDOW, m1.n)):
        if m1.c[k] > lvl:
            cb = k; break
    if cb is None:
        return None
    sweep_low = min(m1.l[i:cb + 1])
    disp = None
    for j in range(cb, min(cb + DISP_SEARCH_BARS, m1.n)):
        body = m1.c[j] - m1.o[j]
        if m1.c[j] > m1.o[j] and body >= disp_mult * atr:
            disp = j; break
    if disp is None:
        return None
    disp_ratio = (m1.c[disp] - m1.o[disp]) / atr
    last_high = None
    for k in range(i, max(FRACTAL_N, i - POOL_LOOKBACK_BARS), -1):
        if m1.fr_high[k]:
            last_high = m1.h[k]; break
    if last_high is None or m1.c[disp] <= last_high:
        return None
    fvg = None
    for x in range(disp, min(disp + FVG_SEARCH_BARS, m1.n)):
        if x - 2 < 0:
            continue
        if m1.h[x - 2] < m1.l[x]:
            gap_lo, gap_hi = m1.h[x - 2], m1.l[x]
            fvg = (x, gap_lo, gap_hi); break
    if fvg is None:
        return None
    x, gap_lo, gap_hi = fvg
    leg_lo = sweep_low
    leg_hi = max(m1.h[cb:disp + 1])
    rng = leg_hi - leg_lo
    if rng <= 0:
        return None
    entry = gap_hi                                   # proximal edge for long
    frac = (leg_hi - entry) / rng                    # retrace down from impulse high
    if not (OTE_LO <= frac <= OTE_HI):
        return None
    sl = sweep_low - STOP_BUFFER_ATR * atr
    risk = entry - sl
    if risk <= 0:
        return None
    opp = min([p for p in buy_pools if p > entry], default=float("nan"))
    return Setup(disp, "BUY", lbl, sweep_low, pen, disp_ratio, entry, sl, risk,
                 atr, opp, x)


# ── Fill + exit simulation ───────────────────────────────────────────────────
@dataclass
class TradeResult:
    setup: Setup
    fill_idx: int
    fill_time: datetime
    eff_entry: float
    tp: float
    exit_idx: int
    exit_time: datetime
    exit_price: float
    r: float
    outcome: str                   # WIN / LOSS / CANCEL / TIMEOUT_OPEN


def try_fill(m1, s, spread_price, point):
    """Limit fill within ENTRY_CANCEL_BARS after FVG forms. Bid-OHLC bars: limit
    must be traded THROUGH by FILL_BUFFER_PTS. Buy fills at limit+spread, sell at
    limit-spread (one full spread charged per round trip = conservative)."""
    start = s.fvg_idx + 1
    buf = FILL_BUFFER_PTS * point
    for k in range(start, min(start + ENTRY_CANCEL_BARS, m1.n)):
        if in_news_blackout(m1.ny[k]):
            return None, "NEWS"
        if s.direction == "SELL":
            if m1.h[k] >= s.limit + buf:
                return k, s.limit - spread_price
        else:
            if m1.l[k] <= s.limit - buf:
                return k, s.limit + spread_price
    return None, "CANCEL"


def simulate_exit(m1, s, fill_idx, eff_entry, tp):
    """Pure SL/TP on bid OHLC after the fill bar. SL-first on same-bar ambiguity."""
    for k in range(fill_idx + 1, m1.n):
        hi, lo = m1.h[k], m1.l[k]
        if s.direction == "SELL":
            if hi >= s.sl:
                return k, s.sl, "LOSS"
            if lo <= tp:
                return k, tp, "WIN"
        else:
            if lo <= s.sl:
                return k, s.sl, "LOSS"
            if hi >= tp:
                return k, tp, "WIN"
    return None, None, "TIMEOUT_OPEN"


def compute_tp(s, variant, point):
    if variant == "opposing_pool":
        if not (s.opp_pool == s.opp_pool):       # nan -> no pool, skip
            return None
        return s.opp_pool
    pts = {"fixed_1000": 1000, "fixed_1500": 1500, "fixed_2000": 2000}[variant]
    return s.limit + (-pts * point if s.direction == "SELL" else pts * point)


def run_portfolio(m1, setups, sweep_min, tp_variant, spread_price, point, split_idx):
    """Filter candidates by sweep_min, sequentially accept one-position-at-a-time,
    fill + exit. Returns list[TradeResult] for filled trades (chronological)."""
    cand = [s for s in setups if s.penetration_pts >= sweep_min]
    cand.sort(key=lambda s: s.fvg_idx)
    busy_until = -1
    trades = []
    for s in cand:
        if s.fvg_idx <= busy_until:
            continue
        tp = compute_tp(s, tp_variant, point)
        if tp is None:
            continue
        fill_idx, fill_val = try_fill(m1, s, spread_price, point)
        if fill_idx is None:
            continue
        eff_entry = fill_val
        ex_idx, ex_price, outcome = simulate_exit(m1, s, fill_idx, eff_entry, tp)
        if ex_idx is None:
            continue                              # open at data end — not counted
        # one position at a time: block new entries until this one exits
        busy_until = ex_idx
        sgn = 1.0 if s.direction == "BUY" else -1.0
        pnl_price = sgn * (ex_price - eff_entry)
        r = pnl_price / s.risk
        trades.append(TradeResult(s, fill_idx, m1.ny[fill_idx], eff_entry, tp,
                                  ex_idx, m1.ny[ex_idx], ex_price, r, outcome))
    return trades


# ── Metrics ──────────────────────────────────────────────────────────────────
def metrics(trades, start_equity=START_BALANCE):
    n = len(trades)
    if n == 0:
        return {"n": 0, "win_rate": 0.0, "pf": 0.0, "exp_r": 0.0,
                "avg_rr": 0.0, "maxdd": 0.0, "net_r": 0.0, "wins": 0, "losses": 0}
    rs = [t.r for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    # equity curve (compounding 0.5% risk) for MaxDD%
    eq = peak = start_equity
    maxdd = 0.0
    for r in rs:
        eq += r * (RISK_PCT * eq)
        peak = max(peak, eq)
        if peak > 0:
            maxdd = max(maxdd, (peak - eq) / peak * 100.0)
    return {"n": n, "win_rate": len(wins) / n * 100.0, "pf": pf,
            "exp_r": sum(rs) / n, "avg_rr": (gross_win / len(wins)) if wins else 0.0,
            "maxdd": maxdd, "net_r": sum(rs), "wins": len(wins), "losses": len(losses),
            "final_equity": eq}


def pf_s(pf):
    return "inf" if pf == float("inf") else f"{pf:.2f}"


def trade_pnl_usd(t, usd_per_point_per_lot, lot=FIXED_LOT, point=0.01):
    """Realized $ P&L of one trade at fixed `lot` size.
    points moved (signed) * USD/point/lot * lot. Spread is already baked into
    eff_entry (entry side) by try_fill, so this is the net fill-to-exit result."""
    sgn = 1.0 if t.setup.direction == "BUY" else -1.0
    pts = sgn * (t.exit_price - t.eff_entry) / point
    return pts, pts * usd_per_point_per_lot * lot


def money_metrics(trades, usd_per_point_per_lot, lot=FIXED_LOT, point=0.01):
    """$-denominated aggregate metrics at fixed `lot` (NOT % risk sizing).
    Returns net $, PF($), win%, avg win/loss $, expectancy $, max consecutive
    losses, $ max drawdown (running-peak on the fixed-lot $ equity), and DD as %
    of each account size in ACCOUNT_SIZES."""
    pnls = []
    for t in trades:
        _pts, usd = trade_pnl_usd(t, usd_per_point_per_lot, lot, point)
        pnls.append(usd)
    n = len(pnls)
    if n == 0:
        return {"n": 0, "net_usd": 0.0, "pf_usd": 0.0, "win_rate": 0.0,
                "avg_win_usd": 0.0, "avg_loss_usd": 0.0, "exp_usd": 0.0,
                "max_consec_losses": 0, "max_dd_usd": 0.0,
                "dd_pct": {a: 0.0 for a in ACCOUNT_SIZES}, "pnls": []}
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    gw = sum(wins); gl = -sum(losses)
    pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
    # max consecutive losses
    mcl = cur = 0
    for p in pnls:
        if p <= 0:
            cur += 1; mcl = max(mcl, cur)
        else:
            cur = 0
    # $ max drawdown on the running cumulative fixed-lot $ curve
    cum = 0.0; peak = 0.0; max_dd = 0.0
    for p in pnls:
        cum += p
        peak = max(peak, cum)
        max_dd = max(max_dd, peak - cum)
    return {"n": n, "net_usd": sum(pnls), "pf_usd": pf,
            "win_rate": len(wins) / n * 100.0,
            "avg_win_usd": (gw / len(wins)) if wins else 0.0,
            "avg_loss_usd": (-gl / len(losses)) if losses else 0.0,
            "exp_usd": sum(pnls) / n,
            "max_consec_losses": mcl, "max_dd_usd": max_dd,
            "dd_pct": {a: (max_dd / a * 100.0) for a in ACCOUNT_SIZES},
            "pnls": pnls}


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    term = connect()
    symbol, selectable = detect_symbol()
    info = mt5.symbol_info(symbol)
    digits, point = info.digits, info.point

    # ── Contract sizing for the $ ledger (1.00 lot) ─────────────────────────────
    # P&L per point per lot = contract_size(oz) * point(USD/oz). For the standard
    # 100oz gold contract at point=0.01 this is $1.00/point/lot. We CONFIRM the
    # contract size from symbol_info and scale off it (not the feed's trade_tick_value,
    # which on this demo reads 0.1 — a deposit-currency/micro quirk; the contract-size
    # derivation matches the project's established gold cost model). If contract size
    # differs from 100oz we use the actual value and state it.
    contract_size = float(info.trade_contract_size)
    tick_value = float(info.trade_tick_value)
    usd_per_point_per_lot = contract_size * point         # 100 * 0.01 = $1.00
    contract_note = "standard 100oz" if abs(contract_size - 100.0) < 1e-6 else \
                    f"NON-STANDARD {contract_size:g}oz (scaled)"

    # point scaling: spec assumes 2-digit gold (point=0.01 -> 1 USD = 100 pts).
    pt_scale = 1.0
    if digits != 2:
        pt_scale = (0.01 / point)      # scale point-based params if not 2-digit
    print(f"Terminal: {term}")
    print(f"Symbol: {symbol}  (selectable: {selectable})  digits={digits} point={point}")
    print(f"Contract: {contract_size:g}oz ({contract_note}) tick_value={tick_value} "
          f"-> USD/point/lot=${usd_per_point_per_lot:.2f}")
    if digits != 2:
        print(f"WARNING: gold is {digits}-digit, expected 2. Point params scaled x{pt_scale:.3g}")

    end = datetime.now()
    start = end - timedelta(days=int(MAX_MONTHS * 30.5))
    # M1/M15 via chunked-and-stitched fetch (a single 24-month M1 call errors
    # 'Invalid params' on this terminal); D1 is small enough for one call.
    m1_raw = fetch_chunked(symbol, mt5.TIMEFRAME_M1, start, end, 28, "M1")
    # M15 + D1 pulled for structure/session context (required by spec)
    _m15 = fetch_chunked(symbol, mt5.TIMEFRAME_M15, start, end, 28, "M15")
    _d1 = fetch(symbol, mt5.TIMEFRAME_D1, start, end)
    print(f"Fetched M1={len(m1_raw)} M15={len(_m15)} D1={len(_d1)}")

    # Server clock AFTER fetch (uses freshest bar epoch; weekend ticks are stale).
    clock, clk_info = detect_server_clock(symbol, int(m1_raw["time"][-1]))
    print(f"Server clock: method={clk_info['method']} offset_now=UTC+{clock.offset_now} "
          f"base_winter=UTC+{clock.base_winter} regime={clock.regime} "
          f"DST_now={clock.is_dst_now}")

    # spread: max(median bar spread, floor)
    sp_arr = m1_raw["spread"].astype(float)
    sp_arr = sp_arr[sp_arr > 0]
    med_spread = float(np.median(sp_arr)) if len(sp_arr) else 0.0
    spread_pts = max(med_spread, SPREAD_FLOOR_PTS)
    spread_price = spread_pts * point
    print(f"Spread: median_bar={med_spread:.0f}pts floor={SPREAD_FLOOR_PTS} -> used={spread_pts:.0f}pts")

    m1 = build_m1(m1_raw, clock)
    t0, t1 = m1.ny[0], m1.ny[-1]
    span_days = (t1 - t0).days
    print(f"M1 NY range: {t0} -> {t1} ({span_days/365.25:.2f}y)")

    dq = data_quality(m1)
    print(f"Data quality: KZ coverage={dq['coverage']*100:.1f}% "
          f"({dq['kz_present']}/{dq['kz_expected']} min) gaps>5min={dq['kz_gaps_gt5min']} "
          f"trustworthy={dq['trustworthy']}")

    midnight, asian, london = build_day_context(m1)

    # chronological 70/30 split by bar index
    split_idx = int(m1.n * IN_SAMPLE_PCT)
    split_time = m1.ny[split_idx]
    print(f"IS/OOS split @ bar {split_idx}/{m1.n} -> {split_time}")

    # ---- SINGLE LOCKED RUN (no grid search, no re-optimization) ----
    print(f"Locked params (a priori from full-model IS): sweep_min={LOCK_SWEEP_MIN} "
          f"disp_mult={LOCK_DISP_MULT} TP={LOCK_TP} | LONDON-only kill-zone")
    setups = generate_setups(m1, midnight, asian, london, LOCK_DISP_MULT, point)
    print(f"  raw candidate setups (disp_mult={LOCK_DISP_MULT}): {len(setups)}")
    trades = run_portfolio(m1, setups, LOCK_SWEEP_MIN, LOCK_TP,
                           spread_price, point, split_idx)
    is_tr = [t for t in trades if t.fill_idx < split_idx]
    oos_tr = [t for t in trades if t.fill_idx >= split_idx]
    im = metrics(is_tr)
    om = metrics(oos_tr, start_equity=im.get("final_equity", START_BALANCE))
    allm = metrics(trades)
    locked = {"sweep_min": LOCK_SWEEP_MIN, "disp_mult": LOCK_DISP_MULT,
              "tp": LOCK_TP, "trades": trades, "is": im, "oos": om, "all": allm,
              "split_idx": split_idx}

    # ---- $-denominated ledger metrics (fixed 1.00 lot, contract from symbol_info) ----
    money = money_metrics(trades, usd_per_point_per_lot, FIXED_LOT)

    # ---- GO/NO-GO (descriptive split; sample-size + data-quality govern) ----
    oos_pf = om["pf"]
    inverted = (im["pf"] != float("inf") and im["pf"] >= 1.20 and oos_pf < 1.0)
    checks = {
        "oos_pf>=1.20": (oos_pf >= 1.20, oos_pf, ">= 1.20"),
        "oos_trades>=15": (om["n"] >= 15, om["n"], ">= 15"),
        "maxdd<=25%": (max(im["maxdd"], om["maxdd"]) <= 25.0,
                       max(im["maxdd"], om["maxdd"]), "<= 25%"),
        "not_inverted": (not inverted, "INVERTED" if inverted else "ok", "aligned"),
        "data_quality>=95%": (dq["trustworthy"], dq["coverage"]*100, ">= 95%"),
    }
    verdict = "GO" if all(c[0] for c in checks.values()) else "NO-GO"
    pref_conf = om["n"] >= 100

    # ---- write outputs ----
    write_results_md(symbol, selectable, term, digits, point, pt_scale, clock,
                     spread_pts, med_spread, t0, t1, span_days, dq, split_time,
                     locked, checks, verdict, pref_conf, inverted, len(setups),
                     usd_per_point_per_lot, contract_size, tick_value, money)
    write_equity_csv(locked, split_idx, usd_per_point_per_lot)
    persist_db(locked, symbol)

    mt5.shutdown()
    print("\n" + "=" * 72)
    print(f"LONDON-ONLY | LOCKED a priori: sweep_min={LOCK_SWEEP_MIN} "
          f"disp_mult={LOCK_DISP_MULT} TP={LOCK_TP}")
    print(f"FULL: n={allm['n']} PF={pf_s(allm['pf'])} net=${money['net_usd']:+,.0f} "
          f"win={allm['win_rate']:.1f}% $maxDD=${money['max_dd_usd']:,.0f} "
          f"(={money['dd_pct'][10000.0]:.1f}% of $10k)")
    print(f"IS:  n={im['n']} PF={pf_s(im['pf'])} exp={im['exp_r']:+.3f}R win={im['win_rate']:.1f}%")
    print(f"OOS: n={om['n']} PF={pf_s(om['pf'])} exp={om['exp_r']:+.3f}R win={om['win_rate']:.1f}%  "
          f"(DESCRIPTIVE - confirmatory, not independent)")
    print("GO/NO-GO checks:")
    for k, (ok, val, thr) in checks.items():
        vs = f"{val:.2f}" if isinstance(val, float) else str(val)
        print(f"  [{'PASS' if ok else 'FAIL'}] {k:<18} {vs:>10}  ({thr})")
    print("=" * 72)
    print(f"VERDICT: {verdict}")
    return verdict


def write_equity_csv(locked, split_idx, usd_per_point_per_lot):
    import csv
    path = os.path.join(RESULTS_DIR, "ict_london_equity.csv")
    eq = START_BALANCE              # 0.5%-risk compounding curve (R column)
    cum_r = 0.0
    cum_usd = 0.0                   # fixed 1.00-lot $ curve (ledger)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fill_time_ny", "exit_time_ny", "in_sample", "direction",
                    "killzone", "armed_gate", "sweep_extreme", "penetration_pts",
                    "disp_ratio", "limit", "eff_entry", "sl", "tp", "exit_price",
                    "points", "pnl_usd_1lot", "r", "outcome",
                    "cum_r", "cum_usd_1lot", "risk_balance"])
        for t in sorted(locked["trades"], key=lambda x: x.fill_idx):
            cum_r += t.r
            eq += t.r * (RISK_PCT * eq)
            pts, usd = trade_pnl_usd(t, usd_per_point_per_lot)
            cum_usd += usd
            s = t.setup
            w.writerow([t.fill_time.strftime("%Y-%m-%d %H:%M"),
                        t.exit_time.strftime("%Y-%m-%d %H:%M"),
                        int(t.fill_idx < split_idx), s.direction, s.killzone,
                        f"sweep+MSS+FVG/OTE", round(s.sweep_extreme, 2),
                        round(s.penetration_pts, 1), round(s.disp_ratio, 2),
                        round(s.limit, 2), round(t.eff_entry, 2), round(s.sl, 2),
                        round(t.tp, 2), round(t.exit_price, 2),
                        round(pts, 1), round(usd, 2), round(t.r, 4), t.outcome,
                        round(cum_r, 4), round(cum_usd, 2), round(eq, 2)])
    print(f"Equity CSV: {path}")


def persist_db(locked, symbol):
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS ict_london_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            magic_label INTEGER, symbol TEXT,
            fill_time_ny TEXT, exit_time_ny TEXT, in_sample INTEGER,
            direction TEXT, killzone TEXT, sweep_extreme REAL,
            penetration_pts REAL, disp_ratio REAL, limit_price REAL,
            eff_entry REAL, sl REAL, tp REAL, exit_price REAL,
            outcome TEXT, r REAL,
            sweep_min INTEGER, disp_mult REAL, tp_variant TEXT)
    """)
    # fresh run: clear only THIS script's own table (never touches other tables)
    con.execute("DELETE FROM ict_london_trades")
    for t in sorted(locked["trades"], key=lambda x: x.fill_idx):
        s = t.setup
        con.execute("""INSERT INTO ict_london_trades
            (magic_label,symbol,fill_time_ny,exit_time_ny,in_sample,direction,
             killzone,sweep_extreme,penetration_pts,disp_ratio,limit_price,
             eff_entry,sl,tp,exit_price,outcome,r,sweep_min,disp_mult,tp_variant)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MAGIC_RESERVED, symbol, t.fill_time.strftime("%Y-%m-%d %H:%M"),
             t.exit_time.strftime("%Y-%m-%d %H:%M"), None, s.direction, s.killzone,
             s.sweep_extreme, s.penetration_pts, s.disp_ratio, s.limit, t.eff_entry,
             s.sl, t.tp, t.exit_price, t.outcome, t.r,
             locked["sweep_min"], locked["disp_mult"], locked["tp"]))
    con.commit(); con.close()
    print(f"DB: persisted {len(locked['trades'])} trades to ict_london_trades ({DB_PATH})")


def write_results_md(symbol, selectable, term, digits, point, pt_scale, clock,
                     spread_pts, med_spread, t0, t1, span_days, dq, split_time,
                     locked, checks, verdict, pref_conf, inverted, n_setups,
                     usd_per_point_per_lot, contract_size, tick_value, money):
    p = os.path.join(RESULTS_DIR, "ict_london_results.md")
    win_months = span_days / 30.44
    im, om, allm = locked["is"], locked["oos"], locked["all"]
    L = []
    A = L.append
    A("# ICT Scalper — LONDON-ONLY variant (confirmatory re-run)\n")
    A(f"_Generated {datetime.now():%Y-%m-%d %H:%M} — research-only, MAGIC "
      f"{MAGIC_RESERVED} reserved (label only, no live orders)._\n")
    # ── Top caveat (must sit ABOVE the metrics) ──
    A("> 🚩 **Selection-bias caveat — read this first, above the metrics.** "
      "London-only was selected **after** observing it outperform in **this same "
      "window**. This re-run is therefore **confirmatory of the existing data, NOT an "
      "independent test.** The parameters (sweep_min=50, disp_mult=1.75, TP=fixed_1500) "
      "are **locked a priori** — carried verbatim from the full-model IS optimization "
      "and **NOT re-optimized** on this subset. The 70/30 split below is **DESCRIPTIVE "
      f"ONLY**: the OOS leg here is ~{om['n']} trade(s). **Statistical confidence "
      "requires FORWARD trades, not this re-run.** The value of this artifact is a "
      "committed, isolated London config ready to forward-track — not a passing grade.\n")
    A("> ⚠️ **Window caveat.** Only **~{:.1f} months** of M1 history exists on this "
      "feed (chunked-and-stitched; cannot conjure missing data). Any in-sample edge is "
      "on a short, single-regime window.\n".format(win_months))
    A("## Detected runtime\n")
    A(f"- **Terminal:** `{term}` (read-only, copy_rates_* only)")
    A(f"- **Symbol:** `{symbol}` (selectable: {selectable}; canonical XAUUSD preferred)")
    A(f"- **Digits / point:** {digits} / {point}  (point-param scale x{pt_scale:.3g})")
    A(f"- **Contract size:** {contract_size:g}oz "
      f"({'standard 100oz — confirmed' if abs(contract_size-100.0)<1e-6 else 'NON-STANDARD, scaled'}); "
      f"feed `trade_tick_value`={tick_value} (deposit-currency/micro quirk). "
      f"**Ledger uses contract-derived ${usd_per_point_per_lot:.2f}/point/lot** at "
      f"{FIXED_LOT:.2f} lot — matches the project's gold cost model.")
    A(f"- **Server offset now:** UTC+{clock.offset_now}; winter base UTC+{clock.base_winter}; "
      f"regime **{clock.regime}**; DST now: {clock.is_dst_now}")
    A(f"- **Spread used:** {spread_pts:.0f} pts = max(median bar {med_spread:.0f}, "
      f"floor {SPREAD_FLOOR_PTS}); charged once per round trip.")
    A(f"- **Kill-zone:** **LONDON ONLY** 02:00–05:00 NY (NY 07:00–10:00 window dropped).")
    A(f"- **Data window (NY):** {t0:%Y-%m-%d} → {t1:%Y-%m-%d} "
      f"(**~{win_months:.1f} months actual**).\n")
    A("## Data-quality gate\n")
    trust = "✅ trustworthy" if dq["trustworthy"] else "⚠️ **NOT TRUSTWORTHY**"
    A(f"- London-KZ M1 coverage: **{dq['coverage']*100:.1f}%** "
      f"({dq['kz_present']}/{dq['kz_expected']} expected min) → {trust}")
    A(f"- Kill-zone gaps >5min: {dq['kz_gaps_gt5min']}\n")

    # ── $ ledger aggregate (1.00 lot) ──
    A("## Aggregate — full window @ "
      f"{FIXED_LOT:.2f} lot (${usd_per_point_per_lot:.2f}/point)\n")
    A("| metric | value |")
    A("|:--|---:|")
    A(f"| trades | {allm['n']} |")
    A(f"| net P&L | **${money['net_usd']:+,.2f}** |")
    A(f"| profit factor | {pf_s(money['pf_usd'])} |")
    A(f"| win rate | {money['win_rate']:.1f}% |")
    A(f"| avg win | ${money['avg_win_usd']:+,.2f} |")
    A(f"| avg loss | ${money['avg_loss_usd']:+,.2f} |")
    A(f"| expectancy / trade | ${money['exp_usd']:+,.2f} |")
    A(f"| max consecutive losses | {money['max_consec_losses']} |")
    A(f"| max drawdown ($) | ${money['max_dd_usd']:,.2f} |")
    for a in ACCOUNT_SIZES:
        A(f"| └ DD as % of ${a:,.0f} | {money['dd_pct'][a]:.1f}% |")
    A("")

    # ── descriptive IS/OOS split ──
    A("## Descriptive 70/30 split (NOT an independent test)\n")
    A(f"Split @ {split_time:%Y-%m-%d %H:%M} NY. Reported for completeness only — see "
      f"the selection-bias caveat above.\n")
    A("| metric (R-based, 0.5% risk) | IS | OOS |")
    A("|:--|---:|---:|")
    A(f"| trades | {im['n']} | {om['n']} |")
    A(f"| win rate | {im['win_rate']:.1f}% | {om['win_rate']:.1f}% |")
    A(f"| profit factor | {pf_s(im['pf'])} | {pf_s(om['pf'])} |")
    A(f"| expectancy (R) | {im['exp_r']:+.3f} | {om['exp_r']:+.3f} |")
    A(f"| avg win (R) | {im['avg_rr']:.2f} | {om['avg_rr']:.2f} |")
    A(f"| net (R) | {im['net_r']:+.2f} | {om['net_r']:+.2f} |")
    A(f"| max drawdown (%) | {im['maxdd']:.1f}% | {om['maxdd']:.1f}% |\n")

    # ── per-trade ledger ──
    A("## Per-trade ledger (chronological, "
      f"{FIXED_LOT:.2f} lot, ${usd_per_point_per_lot:.2f}/point)\n")
    A("| # | fill (NY) | exit (NY) | IS/OOS | dir | KZ | entry | SL | TP | exit | "
      "pts | $ P&L | R | outcome |")
    A("|--:|:--|:--|:--:|:--:|:--:|--:|--:|--:|--:|--:|--:|--:|:--|")
    split_idx = locked["split_idx"]
    for idx, t in enumerate(sorted(locked["trades"], key=lambda x: x.fill_idx), 1):
        s = t.setup
        pts, usd = trade_pnl_usd(t, usd_per_point_per_lot)
        leg = "IS" if t.fill_idx < split_idx else "OOS"
        A(f"| {idx} | {t.fill_time:%Y-%m-%d %H:%M} | {t.exit_time:%H:%M} | "
          f"{leg} | {s.direction} | {s.killzone} | {t.eff_entry:.2f} | {s.sl:.2f} | "
          f"{t.tp:.2f} | {t.exit_price:.2f} | {pts:+.0f} | ${usd:+,.2f} | "
          f"{t.r:+.2f} | {t.outcome} |")
    A("")

    # ── verdict ──
    A("## GO / NO-GO verdict (sample-size & data-quality govern)\n")
    A("| check | value | threshold | result |")
    A("|:--|---:|:--|:--:|")
    names = {"oos_pf>=1.20": "OOS profit factor", "oos_trades>=15": "OOS trade count",
             "maxdd<=25%": "Max drawdown (worse of IS/OOS)",
             "not_inverted": "IS/OOS alignment", "data_quality>=95%": "Data quality"}
    for k, (ok, val, thr) in checks.items():
        vs = f"{val:.2f}" if isinstance(val, float) else str(val)
        A(f"| {names[k]} | {vs} | {thr} | {'✅ PASS' if ok else '❌ FAIL'} |")
    A(f"\nOOS trade count ≥100 preferred-confidence bar: "
      f"{'met' if pref_conf else '**NOT met**'} (n={om['n']}).")
    A(f"\n### ➡️ VERDICT: **{verdict}**\n")
    A("**Honest reading.** The full-window $ figures above are **strong** "
      f"(net ${money['net_usd']:+,.0f}, PF {pf_s(money['pf_usd'])}, "
      f"${money['max_dd_usd']:,.0f} max DD = {money['dd_pct'][10000.0]:.1f}% of $10k) — "
      "but they are **the very trades that motivated the London filter**, so they "
      "confirm the selection rather than validate it out-of-sample. The verdict is "
      f"**{verdict} on sample size** (OOS n={om['n']} < 15). This is the correct, honest "
      "label: the deliverable is the **committed, isolated London config ready to "
      "forward-track**, and only genuinely forward (post-today) trades can earn a GO.\n")

    A("## Closing analysis — additive to Profile D, or redundant?\n")
    A(closing_analysis_text(locked))

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"Results MD: {p}")


def closing_analysis_text(locked):
    trades = locked["trades"]
    longs = sum(1 for t in trades if t.setup.direction == "BUY")
    shorts = sum(1 for t in trades if t.setup.direction == "SELL")
    return (
        f"This LONDON-ONLY variant fires **{len(trades)}** trades over the full window "
        f"({longs} long / {shorts} short; all London kill-zone by construction). Its "
        f"entry DNA is a counter-trend stop-run reversal on **M1**: liquidity swept "
        f"*against* the intended move (Judas), then displacement/MSS, then a 62–79% FVG "
        f"limit — now armed only in the 02:00–05:00 NY London window.\n\n"
        f"Profile D's existing Option-C concept is an **M1 pullback INTO a pre-marked "
        f"Gann/pivot/fib zone with the higher-timeframe bias** (continuation). This model "
        f"enters **against** a just-created liquidity sweep with no HTF-level dependency, "
        f"and — restricted to London — it no longer even overlaps D on the NY-session "
        f"clock. **Overlap is low** (reversal vs continuation; sweep+FVG vs zone-pullback; "
        f"London-only vs 24h). If forward trades confirm the edge, it would earn a "
        f"distinct live slot rather than duplicating D's timing. Until then this is a "
        f"forward-tracking candidate, not a validated profile."
    )


if __name__ == "__main__":
    v = main()
    print(v)
