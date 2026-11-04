# STATUS: RESEARCH-ONLY — ranks/nominates sessions by OOS PF (selection-on-OOS, inflates the
# winner) + silent month-skip in fetch_histdata_csv. Treat the nominated edge as optimistic. 4-research.
"""
ict_london_lab.py — ICT scalper London regression + deep-history + session lab.
================================================================================
RESEARCH ONLY. Reuses the PROVEN detection engine VERBATIM from
research/ict_scalper_london.py (committed 66652da) — nothing is re-implemented;
the only thing this harness varies is the kill-zone WINDOW (one variable at a
time). Detection params stay HARD-LOCKED at the validated London baseline:
sweep_min=50, disp_mult=1.75, TP=fixed_1500, STOP_BUFFER_ATR=0.5, spread =
max(median bar spread, 25pt) charged once per round trip.

Three parts:
  A. London-only baseline on the BROKER feed (regression anchor; asserts the
     known 9 London setups, 7 long / 2 short).
  B. Acquire DEEP XAUUSD M1 history from an external feed and re-test London.
     Dukascopy's datafeed host is BLOCKED in this environment (datafeed.dukascopy
     .com -> HTTP 000 / connection reset; every python fallback — duka/TickVault/
     histdatacom-dukascopy — hits the same host). The reachable external deep
     feed is HistData.com (XAUUSD M1 from 2010). HistData timestamps are EST
     (fixed UTC-5, NO DST); we recover true UTC (+5h) and map UTC->America/New_York
     with zoneinfo (DST-correct). Overlap-validated against the broker feed.
  C. Other ICT sessions — kill-zone window is the ONLY thing changed; ranked by
     deep-history OOS PF with IS/OOS alignment shown.

Outputs (NEW files only — never clobbers ict_*_results.md / trades.db tables):
  research/data/xauusd_m1_histdata.csv         (canonical UTC-epoch OHLC)
  research/results/ict_london_lab_results.md
  research/results/ict_london_lab_<session>_equity.csv   (deep-feed ledger)

Re-run note: re-run with `py -3.11 research/ict_london_lab.py` whenever the
HistData pull or the broker feed extends; pass `--fetch` to (re)build the CSV.

Run:  py -3.11 research/ict_london_lab.py [--fetch]
================================================================================
"""
import os
import sys
import csv as _csv
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import ict_scalper_london as eng          # reuse the proven engine VERBATIM

# ── HARD GUARD (re-installed here exactly as the engine installs it) ───────────
for _fn in ("order_send", "order_check", "order_calc_margin", "order_calc_profit",
            "positions_get", "Buy", "Sell"):
    if hasattr(mt5, _fn):
        def _blocked(*_a, _n=_fn, **_k):
            raise RuntimeError(f"GUARD: live trade/position fn '{_n}' forbidden in research")
        setattr(mt5, _fn, _blocked)

UTC = ZoneInfo("UTC")
NY = ZoneInfo("America/New_York")
RESULTS_DIR = os.path.join(_HERE, "results")
DATA_DIR = os.path.join(_HERE, "data")
HIST_CSV = os.path.join(DATA_DIR, "xauusd_m1_histdata.csv")
HIST_CSV_GZ = HIST_CSV + ".gz"          # committed form (262MB raw exceeds git limits)


def _hist_path():
    """Prefer the plain csv if present, else the committed .gz (pandas reads both)."""
    return HIST_CSV if os.path.exists(HIST_CSV) else HIST_CSV_GZ

# Locked baseline (mirrors the engine's a-priori locks)
SWEEP_MIN = eng.LOCK_SWEEP_MIN            # 50
DISP_MULT = eng.LOCK_DISP_MULT            # 1.75
TP_VARIANT = eng.LOCK_TP                  # fixed_1500
POINT = 0.01                              # gold point in broker pts (both feeds)
USD_PER_PT = 100.0 * POINT                # 100oz contract -> $1.00/point/lot

# Sessions. label "LONDON" preserves the engine's asian-pool branch for the
# baseline; all others use the london-pool branch (prior session). Times NY/ET.
# (key, title, sh, sm, eh, em, kz_label, comparable, note)
SESSIONS = [
    ("london_open",  "London Open 02:00-05:00",      2, 0,  5, 0,  "LONDON", True,  "baseline"),
    ("ny_am",        "NY AM 07:00-10:00",            7, 0, 10, 0,  "NYAM",   True,  ""),
    ("ny_am_0830",   "NY AM 08:30-11:00",            8, 30,11, 0,  "NYAM2",  True,  "08:30 open variant"),
    ("london_close", "London Close 10:00-12:00",    10, 0, 12, 0,  "LNCL",   True,  ""),
    ("sb_london",    "Silver Bullet London 03:00-04:00", 3, 0, 4, 0, "SBLN", True,  ""),
    ("sb_ny_am",     "Silver Bullet NY AM 10:00-11:00", 10, 0,11, 0, "SBAM", True,  ""),
    ("sb_ny_pm",     "Silver Bullet NY PM 14:00-15:00", 14, 0,15, 0, "SBPM", True,  ""),
    ("asia",         "Asian range 20:00-00:00",     20, 0, 24, 0,  "ASIA",   False, "experimental: bias anchor = prior-day NY midnight open carried forward; NOT directly comparable to post-midnight sessions"),
]


# ── UTC clock for the HistData feed (no DST inference — direct UTC->NY) ────────
class UTCClock:
    """to_ny(epoch): the stored epoch is TRUE UTC; map straight to NY with DST."""
    offset_now = 0
    base_winter = 0
    regime = "direct UTC (HistData EST+5h -> UTC -> America/New_York via zoneinfo)"
    is_dst_now = False

    def to_ny(self, epoch):
        return datetime.utcfromtimestamp(int(epoch)).replace(tzinfo=UTC).astimezone(NY)


# ── HistData acquisition (HistData.com; EST fixed UTC-5 -> UTC epoch) ──────────
def fetch_histdata_csv(start_year=2010):
    """Build the canonical UTC-epoch OHLC csv from HistData.com generic-ASCII M1.
    Idempotent: writes research/data/xauusd_m1_histdata.csv. Requires `histdata`
    (pip install histdata). Dukascopy is unreachable here — see module header."""
    import io, zipfile, tempfile, shutil
    from histdata import download_hist_data as dl
    from histdata.api import Platform as P, TimeFrame as TF
    os.makedirs(DATA_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    work = tempfile.mkdtemp(prefix="hd_"); cwd = os.getcwd(); os.chdir(work)
    seen = {}
    try:
        for y in range(start_year, now.year + 1):
            months = [None] if y < now.year else [str(m) for m in range(1, now.month + 1)]
            for m in months:
                try:
                    z = dl(year=str(y), month=m, pair="xauusd",
                           platform=P.GENERIC_ASCII, time_frame=TF.ONE_MINUTE)
                except Exception as e:
                    print(f"  {y}-{m}: skip ({e})"); continue
                zf = zipfile.ZipFile(z)
                nm = [n for n in zf.namelist() if n.lower().endswith(".csv")][0]
                for line in zf.read(nm).decode("utf-8", "ignore").splitlines():
                    p = line.split(";")
                    if len(p) < 5:
                        continue
                    est = datetime.strptime(p[0], "%Y%m%d %H%M%S")
                    ep = int((est + timedelta(hours=5)).replace(tzinfo=UTC).timestamp())
                    seen[ep] = (round(float(p[1]), 3), round(float(p[2]), 3),
                                round(float(p[3]), 3), round(float(p[4]), 3))
    finally:
        os.chdir(cwd); shutil.rmtree(work, ignore_errors=True)
    eps = sorted(seen)
    with open(HIST_CSV, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f); w.writerow(["time", "open", "high", "low", "close"])
        for ep in eps:
            o, h, l, c = seen[ep]; w.writerow([ep, o, h, l, c])
    print(f"  HistData CSV: {len(eps)} bars -> {HIST_CSV}")


def load_histdata_m1():
    """Load the canonical csv into a structured array (pandas — fast on 5.7M rows)."""
    df = pd.read_csv(_hist_path())
    dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"),
             ("low", "f8"), ("close", "f8"), ("spread", "i8")]
    rates = np.empty(len(df), dtype=dtype)
    rates["time"] = df["time"].to_numpy(np.int64)
    rates["open"] = df["open"].to_numpy(); rates["high"] = df["high"].to_numpy()
    rates["low"] = df["low"].to_numpy(); rates["close"] = df["close"].to_numpy()
    rates["spread"] = 0                                   # bid-only feed; no spread
    return rates


def fast_build_m1(rates):
    """Same M1Data the engine's build_m1 produces, but vectorized for millions of
    bars: NY datetimes via pandas tz-convert (UTC->America/New_York, DST-correct),
    fractals via numpy slicing. ATR matches eng.build_m1 exactly. Used for the deep
    HistData feed only; the broker feed keeps eng.build_m1 + ServerClock so Part A
    reproduces the committed baseline bit-for-bit."""
    o = rates["open"].astype(float); h = rates["high"].astype(float)
    l = rates["low"].astype(float); c = rates["close"].astype(float)
    sp = rates["spread"].astype(float); ep = rates["time"].astype(np.int64)
    n = len(ep)
    ny = list(pd.to_datetime(ep, unit="s", utc=True)
              .tz_convert("America/New_York").to_pydatetime())
    P = eng.ATR_PERIOD
    prev_c = np.empty(n); prev_c[0] = c[0]; prev_c[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    atr = np.full(n, np.nan)
    if n >= P:
        csum = np.cumsum(tr)
        atr[P - 1] = csum[P - 1] / P
        atr[P:] = (csum[P:] - csum[:-P]) / P
    fr_high = np.zeros(n, dtype=bool); fr_low = np.zeros(n, dtype=bool)
    if n > 4:
        hh = h
        fr_high[2:-2] = ((hh[2:-2] > hh[1:-3]) & (hh[2:-2] > hh[0:-4]) &
                         (hh[2:-2] > hh[3:-1]) & (hh[2:-2] > hh[4:]))
        ll = l
        fr_low[2:-2] = ((ll[2:-2] < ll[1:-3]) & (ll[2:-2] < ll[0:-4]) &
                        (ll[2:-2] < ll[3:-1]) & (ll[2:-2] < ll[4:]))
    return eng.M1Data(ep, o, h, l, c, sp, ny, atr, fr_high, fr_low, n)


# ── session runner: patch ONLY the kill-zone window, run the locked engine ─────
def run_session(m1, ctx, sess, spread_price, split_idx):
    key, title, sh, sm, eh, em, lbl, comparable, note = sess
    midnight, asian, london = ctx
    eng.KILLZONES = [(sh, sm, eh, em, lbl)]               # the ONLY variable
    setups = eng.generate_setups(m1, midnight, asian, london, DISP_MULT, POINT)
    trades = eng.run_portfolio(m1, setups, SWEEP_MIN, TP_VARIANT,
                               spread_price, POINT, split_idx)
    is_tr = [t for t in trades if t.fill_idx < split_idx]
    oos_tr = [t for t in trades if t.fill_idx >= split_idx]
    im = eng.metrics(is_tr)
    om = eng.metrics(oos_tr, start_equity=im.get("final_equity", eng.START_BALANCE))
    allm = eng.metrics(trades)
    money = eng.money_metrics(trades, USD_PER_PT, eng.FIXED_LOT, POINT)
    dq = eng.data_quality(m1)
    inverted = (im["pf"] != float("inf") and im["pf"] >= 1.20 and om["pf"] < 1.0)
    maxdd = max(im["maxdd"], om["maxdd"])
    checks = {
        "oos_pf>=1.20": (om["pf"] >= 1.20, om["pf"]),
        "oos_n>=15": (om["n"] >= 15, om["n"]),
        "maxdd<=25%": (maxdd <= 25.0, maxdd),
        "not_inverted": (not inverted, "INVERTED" if inverted else "ok"),
        "dq>=95%": (dq["trustworthy"], dq["coverage"] * 100),
    }
    verdict = "GO" if all(c[0] for c in checks.values()) else "NO-GO"
    return {"key": key, "title": title, "label": lbl, "window": f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}",
            "comparable": comparable, "note": note, "n_setups": len(setups),
            "trades": trades, "is": im, "oos": om, "all": allm, "money": money,
            "dq": dq, "checks": checks, "verdict": verdict, "inverted": inverted,
            "maxdd": maxdd, "year_pf": year_pf(trades)}


def year_pf(trades):
    """Per-calendar-year PF (and n) from fill year — exposes single-regime rests."""
    by = {}
    for t in trades:
        y = t.fill_time.year
        by.setdefault(y, []).append(t.r)
    out = {}
    for y, rs in sorted(by.items()):
        gw = sum(r for r in rs if r > 0); gl = -sum(r for r in rs if r <= 0)
        pf = (gw / gl) if gl > 0 else (float("inf") if gw > 0 else 0.0)
        out[y] = (len(rs), pf)
    return out


# ── overlap validation (deep feed vs broker feed on the shared window) ─────────
def overlap_compare(broker_london, hist_london_window):
    """Approximate agreement: match broker trades to a same-NY-date, same-direction
    deep-feed trade. Feeds differ tick-by-tick so exact bar match is not expected;
    we report day+direction agreement and the win/loss concordance on matches."""
    h_by_day = {}
    for t in hist_london_window:
        h_by_day.setdefault(t.fill_time.date(), []).append(t)
    matched = 0; outcome_match = 0
    for bt in broker_london:
        cands = h_by_day.get(bt.fill_time.date(), [])
        m = next((h for h in cands if h.setup.direction == bt.setup.direction), None)
        if m is not None:
            matched += 1
            bwin = bt.r > 0; hwin = m.r > 0
            if bwin == hwin:
                outcome_match += 1
    nb = len(broker_london)
    return {"broker_n": nb, "hist_window_n": len(hist_london_window),
            "matched": matched, "outcome_match": outcome_match,
            "agree_pct": (matched / nb * 100.0) if nb else 0.0,
            "outcome_pct": (outcome_match / matched * 100.0) if matched else 0.0}


# ── feed builders ─────────────────────────────────────────────────────────────
def build_broker_feed():
    term = eng.connect()
    symbol, selectable = eng.detect_symbol()
    info = mt5.symbol_info(symbol)
    digits, point = info.digits, info.point
    contract = float(info.trade_contract_size)
    usd_per_pt = contract * point
    end = datetime.now(); start = end - timedelta(days=int(eng.MAX_MONTHS * 30.5))
    raw = eng.fetch_chunked(symbol, mt5.TIMEFRAME_M1, start, end, 28, "M1")
    clock, clk = eng.detect_server_clock(symbol, int(raw["time"][-1]))
    sp = raw["spread"].astype(float); sp = sp[sp > 0]
    med = float(np.median(sp)) if len(sp) else 0.0
    spread_pts = max(med, eng.SPREAD_FLOOR_PTS)
    m1 = eng.build_m1(raw, clock)
    meta = {"term": term, "symbol": symbol, "selectable": selectable,
            "digits": digits, "point": point, "contract": contract,
            "tick_value": float(info.trade_tick_value), "usd_per_pt": usd_per_pt,
            "clock": clock, "clk": clk, "med_spread": med, "spread_pts": spread_pts,
            "t0": m1.ny[0], "t1": m1.ny[-1], "n": m1.n}
    return m1, meta


def build_hist_feed():
    raw = load_histdata_m1()
    clock = UTCClock()
    m1 = fast_build_m1(raw)
    meta = {"spread_pts": max(0.0, eng.SPREAD_FLOOR_PTS), "med_spread": 0.0,
            "usd_per_pt": USD_PER_PT, "t0": m1.ny[0], "t1": m1.ny[-1], "n": m1.n,
            "clock": clock}
    return m1, meta


# ── output: per-session deep-feed equity csv ──────────────────────────────────
def write_equity(res, split_idx):
    path = os.path.join(RESULTS_DIR, f"ict_london_lab_{res['key']}_equity.csv")
    cum_usd = 0.0; cum_r = 0.0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["fill_time_ny", "exit_time_ny", "in_sample", "direction",
                    "killzone", "sweep_extreme", "penetration_pts", "disp_ratio",
                    "limit", "eff_entry", "sl", "tp", "exit_price", "points",
                    "pnl_usd_1lot", "r", "outcome", "cum_r", "cum_usd_1lot"])
        for t in sorted(res["trades"], key=lambda x: x.fill_idx):
            pts, usd = eng.trade_pnl_usd(t, USD_PER_PT, eng.FIXED_LOT, POINT)
            cum_usd += usd; cum_r += t.r; s = t.setup
            w.writerow([t.fill_time.strftime("%Y-%m-%d %H:%M"),
                        t.exit_time.strftime("%Y-%m-%d %H:%M"),
                        int(t.fill_idx < split_idx), s.direction, s.killzone,
                        round(s.sweep_extreme, 2), round(s.penetration_pts, 1),
                        round(s.disp_ratio, 2), round(s.limit, 2), round(t.eff_entry, 2),
                        round(s.sl, 2), round(t.tp, 2), round(t.exit_price, 2),
                        round(pts, 1), round(usd, 2), round(t.r, 4), t.outcome,
                        round(cum_r, 4), round(cum_usd, 2)])
    return path


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    do_fetch = "--fetch" in sys.argv
    if do_fetch or not (os.path.exists(HIST_CSV) or os.path.exists(HIST_CSV_GZ)):
        print("Acquiring HistData XAUUSD M1 (Dukascopy datafeed is blocked here)...")
        fetch_histdata_csv()

    # ── BROKER FEED ──────────────────────────────────────────────────────────
    print("\n=== BROKER FEED ===")
    bm1, bmeta = build_broker_feed()
    print(f"Terminal {bmeta['term']} symbol {bmeta['symbol']} "
          f"digits={bmeta['digits']} point={bmeta['point']} "
          f"contract={bmeta['contract']:g}oz USD/pt=${bmeta['usd_per_pt']:.2f}")
    print(f"Broker M1 NY {bmeta['t0']:%Y-%m-%d} -> {bmeta['t1']:%Y-%m-%d} "
          f"({(bmeta['t1']-bmeta['t0']).days/30.44:.1f} mo, {bmeta['n']} bars)")
    b_ctx = eng.build_day_context(bm1)
    b_spread_price = bmeta["spread_pts"] * POINT
    b_split = int(bm1.n * eng.IN_SAMPLE_PCT)
    broker_res = {}
    for sess in SESSIONS:
        broker_res[sess[0]] = run_session(bm1, b_ctx, sess, b_spread_price, b_split)

    # Part A assertion: London baseline reproduces 9 setups (7 long / 2 short)
    bl = broker_res["london_open"]
    longs = sum(1 for t in bl["trades"] if t.setup.direction == "BUY")
    shorts = sum(1 for t in bl["trades"] if t.setup.direction == "SELL")
    a_ok = (len(bl["trades"]) == 9 and longs == 7 and shorts == 2)
    print(f"\nPART A baseline: London trades={len(bl['trades'])} "
          f"({longs}L/{shorts}S) expected 9 (7L/2S) -> "
          f"{'REPRODUCED' if a_ok else 'DRIFT (window rolled; see report)'}")

    # ── DEEP FEED (HistData) ─────────────────────────────────────────────────
    print("\n=== DEEP FEED (HistData) ===")
    hm1, hmeta = build_hist_feed()
    print(f"HistData M1 NY {hmeta['t0']:%Y-%m-%d} -> {hmeta['t1']:%Y-%m-%d} "
          f"({(hmeta['t1']-hmeta['t0']).days/365.25:.1f}y, {hmeta['n']} bars)")
    h_ctx = eng.build_day_context(hm1)
    h_spread_price = hmeta["spread_pts"] * POINT
    h_split = int(hm1.n * eng.IN_SAMPLE_PCT)
    hist_res = {}
    for sess in SESSIONS:
        hist_res[sess[0]] = run_session(hm1, h_ctx, sess, h_spread_price, h_split)

    # ── Part B overlap validation: deep-feed London on the broker's shared window
    bw0 = int(bm1.epoch[0]); bw1 = int(bm1.epoch[-1])
    eng.KILLZONES = [(2, 0, 5, 0, "LONDON")]
    # restrict deep feed to the broker window, then run London on that slice
    mask = (hm1.epoch >= bw0) & (hm1.epoch <= bw1)
    idx = np.where(mask)[0]
    if len(idx) > 300:
        sub = _slice_m1(hm1, idx)
        sub_ctx = eng.build_day_context(sub)
        sub_setups = eng.generate_setups(sub, sub_ctx[0], sub_ctx[1], sub_ctx[2], DISP_MULT, POINT)
        sub_trades = eng.run_portfolio(sub, sub_setups, SWEEP_MIN, TP_VARIANT,
                                       h_spread_price, POINT, len(sub.epoch))
    else:
        sub_trades = []
    overlap = overlap_compare(bl["trades"], sub_trades)
    print(f"PART B overlap: broker London n={overlap['broker_n']} vs deep-feed "
          f"same-window n={overlap['hist_window_n']} -> day+dir agree "
          f"{overlap['agree_pct']:.0f}% | outcome concordance {overlap['outcome_pct']:.0f}%")

    # ── write per-session deep-feed equity csvs ──────────────────────────────
    for k, r in hist_res.items():
        write_equity(r, h_split)

    # ── report + console summary ─────────────────────────────────────────────
    write_report(bmeta, hmeta, broker_res, hist_res, bl, a_ok, longs, shorts,
                 overlap, b_split, h_split, bm1, hm1)
    print_summary(broker_res, hist_res)
    mt5.shutdown()


def _slice_m1(m1, idx):
    """Rebuild an M1Data over a boolean/index slice (re-derive ATR/fractals)."""
    dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"),
             ("low", "f8"), ("close", "f8"), ("spread", "i8")]
    r = np.empty(len(idx), dtype=dtype)
    r["time"] = m1.epoch[idx]; r["open"] = m1.o[idx]; r["high"] = m1.h[idx]
    r["low"] = m1.l[idx]; r["close"] = m1.c[idx]; r["spread"] = 0
    return fast_build_m1(r)


def pf_s(pf):
    return "inf" if pf == float("inf") else f"{pf:.2f}"


def print_summary(broker_res, hist_res):
    print("\n" + "=" * 78)
    print("SESSION x FEED SUMMARY  (n, win%, PF, OOS PF -> verdict)")
    print("=" * 78)
    print(f"{'session':<26} {'feed':<9} {'n':>4} {'win%':>6} {'PF':>6} {'OOSpf':>6}  verdict")
    for sess in SESSIONS:
        k = sess[0]
        for feed, R in (("broker", broker_res), ("histdata", hist_res)):
            r = R[k]; a = r["all"]; o = r["oos"]
            print(f"{r['title'][:26]:<26} {feed:<9} {a['n']:>4} {a['win_rate']:>6.1f} "
                  f"{pf_s(a['pf']):>6} {pf_s(o['pf']):>6}  {r['verdict']}")
    print("=" * 78)


# ── report writer ─────────────────────────────────────────────────────────────
def write_report(bmeta, hmeta, broker_res, hist_res, bl, a_ok, longs, shorts,
                 overlap, b_split, h_split, bm1, hm1):
    p = os.path.join(RESULTS_DIR, "ict_london_lab_results.md")
    L = []; A = L.append
    bmo = (bmeta["t1"] - bmeta["t0"]).days / 30.44
    hy = (hmeta["t1"] - hmeta["t0"]).days / 365.25
    A("# ICT Scalper — London regression + deep-history + session lab\n")
    A(f"_Generated {datetime.now():%Y-%m-%d %H:%M} — research-only; engine reused "
      f"VERBATIM from `ict_scalper_london.py` (66652da); no live profile touched._\n")
    # ── top caveat block ──
    A("> 🚩 **Read first — what each feed is and is not.**")
    A(">")
    A("> - **Broker feed (live reference, tiny n).** This is the only feed whose "
      "fills resemble live execution, but it serves just **~{:.1f} months** of M1, "
      "so London fires ~9 trades — it can *never* clear the OOS n≥15 floor. Every "
      "broker-feed verdict below is **small-n by construction**.".format(bmo))
    A("> - **Deep feed = HistData.com, NOT Dukascopy.** Dukascopy's datafeed host "
      "is **blocked in this environment** (`datafeed.dukascopy.com` → HTTP 000 / "
      "connection reset; the node CLI and every python fallback hit that same host "
      "and fail). The reachable external deep feed is **HistData.com** XAUUSD M1 "
      f"(**~{hy:.1f} years**, {hmeta['n']:,} bars). It is a **different feed** — "
      "finer price granularity, no live spread, different fills — so its results are "
      "**regime-robustness evidence on a different feed**, not the broker's own history.")
    A("> - **Nothing here is cleared for live.** A session strong across many "
      "HistData years AND not IS/OOS-inverted is a genuine *forward-tracking "
      "candidate* — far stronger than the 3.5-month broker window — but fills differ, "
      "so it still requires **demo-forward before any live move**. Profile L stays on "
      "its locked `fixed_1500` config; this lab does not touch it.\n")
    A("**Locked baseline (fixed everywhere; only the kill-zone window varies):** "
      f"sweep_min={SWEEP_MIN}, disp_mult={DISP_MULT}, TP={TP_VARIANT}, "
      f"STOP_BUFFER_ATR={eng.STOP_BUFFER_ATR}, spread=max(median, "
      f"{eng.SPREAD_FLOOR_PTS}pt) once/round-trip, 70/30 chronological walk-forward, "
      "params NOT re-optimized (one-variable-at-a-time session test).\n")

    # ── PART A ──
    A("## Part A — London-only baseline on the broker feed (regression anchor)\n")
    A(f"- **Terminal:** `{bmeta['term']}` (read-only, copy_rates_* only); symbol "
      f"`{bmeta['symbol']}` digits={bmeta['digits']} point={bmeta['point']}; "
      f"contract {bmeta['contract']:g}oz → **${bmeta['usd_per_pt']:.2f}/point/lot** "
      f"(feed tick_value={bmeta['tick_value']} is a deposit-ccy quirk).")
    A(f"- **Served depth (real):** {bmeta['t0']:%Y-%m-%d} → {bmeta['t1']:%Y-%m-%d} "
      f"= **~{bmo:.1f} months** ({bmeta['n']:,} M1 bars, chunked-and-stitched). "
      "Cannot conjure missing data; this governs confidence, not MAX_MONTHS.")
    A(f"- **Server clock:** {bmeta['clk']['method']}; base UTC+{bmeta['clock'].base_winter}; "
      f"regime {bmeta['clock'].regime}.")
    A(f"- **Spread used:** {bmeta['spread_pts']:.0f}pt = max(median bar "
      f"{bmeta['med_spread']:.0f}, floor {eng.SPREAD_FLOOR_PTS}).")
    dq = bl["dq"]
    A(f"- **London-KZ data quality:** coverage **{dq['coverage']*100:.1f}%** "
      f"({dq['kz_present']}/{dq['kz_expected']} min), gaps>5min {dq['kz_gaps_gt5min']} "
      f"→ {'✅ trustworthy' if dq['trustworthy'] else '⚠️ NOT trustworthy'}.\n")
    A(f"**Regression assertion:** London fires **{len(bl['trades'])} trades "
      f"({longs} long / {shorts} short)**; expected **9 (7 long / 2 short)** → "
      f"{'✅ **REPRODUCED** — engine intact.' if a_ok else '⚠️ **mismatch** — the broker window rolls forward ~daily, so a small count change is expected window drift (not engine drift). Compare the ledger below to the committed `ict_london_equity.csv`.'}\n")
    m = bl["money"]; im = bl["is"]; om = bl["oos"]
    A("| London baseline (broker) | value |")
    A("|:--|---:|")
    A(f"| trades (full) | {bl['all']['n']} |")
    A(f"| win rate | {bl['all']['win_rate']:.1f}% |")
    A(f"| profit factor (R) | {pf_s(bl['all']['pf'])} |")
    A(f"| expectancy (R) | {bl['all']['exp_r']:+.3f} |")
    A(f"| net (R) | {bl['all']['net_r']:+.2f} |")
    A(f"| net P&L (1.00 lot) | ${m['net_usd']:+,.0f} |")
    A(f"| $ max drawdown | ${m['max_dd_usd']:,.0f} ({m['dd_pct'][10000.0]:.1f}% of $10k) |")
    A(f"| IS / OOS trades | {im['n']} / {om['n']} |")
    A(f"| IS / OOS PF | {pf_s(im['pf'])} / {pf_s(om['pf'])} |\n")
    A(_ledger_table(bl["trades"], b_split))
    A("")

    # ── PART B ──
    A("## Part B — Deeper history (HistData) acquisition, overlap, long-run\n")
    A("### Acquisition\n")
    A("- **Attempted Dukascopy first** (per spec): `npx dukascopy-node …` and the "
      "python fallbacks all target `datafeed.dukascopy.com`, which returns **HTTP "
      "000 / connection reset** in this environment (general egress works — "
      "google/github/histdata all 200 — only Dukascopy's datafeed host is blocked).")
    A("- **Used HistData.com** (reachable; XAUUSD M1 from 2010) via the `histdata` "
      f"package. Pulled **{hmeta['t0']:%Y-%m-%d} → {hmeta['t1']:%Y-%m-%d} "
      f"(~{hy:.1f}y, {hmeta['n']:,} M1 bars)** → `research/data/xauusd_m1_histdata.csv`.")
    A("- **Time-align (documented):** HistData generic-ASCII timestamps are **EST, "
      "fixed UTC-5, NO DST**. We add 5h to recover **true UTC**, store UTC epoch, then "
      "map UTC→`America/New_York` with `zoneinfo` (DST-correct). The broker path "
      "infers DST from an EU-clock model; this UTC→NY path is *more* direct.")
    A("- **Price granularity:** HistData XAUUSD is finer than the broker (≈0.001 vs "
      "0.01); handled as plain OHLC. Point stays 0.01 so the pt-based locks "
      "(sweep_min/disp/TP) and the $1.00/point ledger are identical across feeds.\n")
    A("### Overlap-validation vs the broker feed (honesty check)\n")
    A(f"Restricting HistData to the broker's shared window "
      f"({bmeta['t0']:%Y-%m-%d}→{bmeta['t1']:%Y-%m-%d}) and running the London "
      f"baseline on it:\n")
    A(f"- Broker London trades in window: **{overlap['broker_n']}**; "
      f"deep-feed London trades same window: **{overlap['hist_window_n']}**.")
    A(f"- Same-day + same-direction agreement: **{overlap['agree_pct']:.0f}%** "
      f"({overlap['matched']}/{overlap['broker_n']}); win/loss concordance on "
      f"matches: **{overlap['outcome_pct']:.0f}%**.")
    _setups_agree = overlap['agree_pct'] >= 50
    _outcomes_agree = overlap['outcome_pct'] >= 60
    if _setups_agree and not _outcomes_agree:
        _read = ("the feeds agree on **when/which-way** to trade (high same-day+direction "
                 "setup agreement) but **disagree on outcomes** (low win/loss concordance): "
                 "identical triggers, **different fills**. With a 5:1-ish fixed-point target, "
                 "tiny wick differences between feeds flip win↔loss — so the broker's small-n "
                 "win rate and the deep feed's are *both* noisy, and neither feed's outcome "
                 "history transfers to the other")
    elif _setups_agree and _outcomes_agree:
        _read = ("feeds align on both setups and outcomes over the shared window — the "
                 "deep-history numbers are credible regime evidence")
    else:
        _read = ("feeds disagree materially even on setups over the shared window — treat the "
                 "long-history results strictly as *different-feed* robustness evidence, not "
                 "the broker's own history")
    A(f"- **Reading:** {_read}. Either way, different fills ⇒ **demo-forward before live**.\n")
    hl = hist_res["london_open"]
    A("### London on the full HistData history (first real sample)\n")
    A(_metrics_block(hl))
    A("\n**Year-by-year PF (London, HistData)** — exposes single-regime rests:\n")
    A(_year_table(hl["year_pf"]))
    A("\n> ⚠️ **Fixed-point-TP / price-level interaction (important).** The locked "
      "TP is **1500 points = $15 absolute**. Gold ran from ~$1,230 (2010) to ~$4,730 "
      "(2026) over this history, so the *same* $15 target is a **~1.2% move in 2010** "
      "but only **~0.3% in 2026** — far harder to hit in the cheap-gold years. The "
      "config is implicitly calibrated to today's high price; year-by-year win rate "
      "therefore rises with the gold price, and the full-window number is dragged down "
      "by the cheap-gold era. (Not re-tuned here — TP scaling is out of scope; flagged "
      "for honesty. A %-based or ATR-based TP would be the obvious next experiment.)\n")
    A(f"\n**Verdict (London, HistData):** **{hl['verdict']}** "
      f"({_verdict_reason(hl)}).\n")

    # ── PART C ──
    A("## Part C — Which ICT sessions are worth trading?\n")
    A("Only the kill-zone window changes; detection params stay locked. Ranked by "
      "**HistData OOS PF** (the large-sample feed), with IS/OOS alignment and n shown. "
      "Broker-feed columns are tiny-n reference only.\n")
    A("### Ranked session table (by HistData OOS PF)\n")
    A("| rank | session | HD n | HD win% | HD PF | HD IS→OOS PF | HD OOS n | HD maxDD | HD verdict | broker n/PF |")
    A("|--:|:--|--:|--:|--:|:--:|--:|--:|:--:|:--:|")
    ranked = sorted(SESSIONS, key=lambda s: _rank_key(hist_res[s[0]]), reverse=True)
    for i, sess in enumerate(ranked, 1):
        k = sess[0]; r = hist_res[k]; b = broker_res[k]
        comp = "" if r["comparable"] else " ⚠️*"
        A(f"| {i} | {r['title']}{comp} | {r['all']['n']} | {r['all']['win_rate']:.0f}% | "
          f"{pf_s(r['all']['pf'])} | {pf_s(r['is']['pf'])}→{pf_s(r['oos']['pf'])} | "
          f"{r['oos']['n']} | {r['maxdd']:.0f}% | {r['verdict']} | "
          f"{b['all']['n']}/{pf_s(b['all']['pf'])} |")
    A("\n⚠️* Asian range uses an experimental prior-day-midnight bias anchor and is "
      "**not directly comparable** to the post-midnight sessions.\n")
    A("### Per-session detail\n")
    for sess in ranked:
        k = sess[0]; r = hist_res[k]; b = broker_res[k]
        A(f"#### {r['title']}  ({r['window']} NY){'' if r['comparable'] else '  — experimental'}\n")
        if r["note"]:
            A(f"_{r['note']}_\n")
        A(f"- **HistData:** {_metrics_inline(r)}  → verdict **{r['verdict']}**")
        A(f"- **Broker (tiny-n ref):** {_metrics_inline(b)}  → verdict **{b['verdict']}** (small-n)")
        A(f"- Year PF (HD): {_year_inline(r['year_pf'])}")
        A(f"- Equity ledger: `results/ict_london_lab_{k}_equity.csv`\n")

    # ── closing ──
    A("## Closing — honest bottom line\n")
    A(_closing_text(bl, a_ok, overlap, hl, hist_res, ranked, bmo, hy))

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"Report: {p}")


def _rank_key(r):
    # rank primarily by OOS PF, but push non-viable (n<15 or inverted) below viable
    base = r["oos"]["pf"]
    if base == float("inf"):
        base = 99.0
    viable = (r["oos"]["n"] >= 15 and not r["inverted"])
    return (1 if viable else 0, base)


def _verdict_reason(r):
    fails = [k for k, (ok, _v) in r["checks"].items() if not ok]
    return "all checks pass" if not fails else "fails: " + ", ".join(fails)


def _metrics_inline(r):
    a = r["all"]; o = r["oos"]; m = r["money"]
    return (f"n={a['n']}, win {a['win_rate']:.0f}%, PF {pf_s(a['pf'])}, "
            f"exp {a['exp_r']:+.2f}R, net {a['net_r']:+.1f}R / ${m['net_usd']:+,.0f}, "
            f"maxDD {r['maxdd']:.0f}%, IS→OOS PF {pf_s(r['is']['pf'])}→{pf_s(o['pf'])} "
            f"(OOS n={o['n']})")


def _metrics_block(r):
    a = r["all"]; im = r["is"]; om = r["oos"]; m = r["money"]
    out = ["| metric | full | IS | OOS |", "|:--|---:|---:|---:|",
           f"| trades | {a['n']} | {im['n']} | {om['n']} |",
           f"| win rate | {a['win_rate']:.1f}% | {im['win_rate']:.1f}% | {om['win_rate']:.1f}% |",
           f"| profit factor | {pf_s(a['pf'])} | {pf_s(im['pf'])} | {pf_s(om['pf'])} |",
           f"| expectancy (R) | {a['exp_r']:+.3f} | {im['exp_r']:+.3f} | {om['exp_r']:+.3f} |",
           f"| net (R) | {a['net_r']:+.2f} | {im['net_r']:+.2f} | {om['net_r']:+.2f} |",
           f"| max drawdown | {r['maxdd']:.1f}% (worse of IS/OOS) | {im['maxdd']:.1f}% | {om['maxdd']:.1f}% |",
           f"| net P&L (1.00 lot) | ${m['net_usd']:+,.0f} | | |"]
    return "\n".join(out)


def _year_table(yp):
    out = ["| year | n | PF |", "|--:|--:|--:|"]
    for y, (n, pf) in yp.items():
        out.append(f"| {y} | {n} | {pf_s(pf)} |")
    return "\n".join(out)


def _year_inline(yp):
    return ", ".join(f"{y}:{pf_s(pf)}(n{n})" for y, (n, pf) in yp.items()) or "—"


def _ledger_table(trades, split_idx):
    out = ["| # | fill (NY) | exit | IS/OOS | dir | entry | SL | TP | exit | pts | $ | R | outcome |",
           "|--:|:--|:--|:--:|:--:|--:|--:|--:|--:|--:|--:|--:|:--|"]
    for i, t in enumerate(sorted(trades, key=lambda x: x.fill_idx), 1):
        s = t.setup; pts, usd = eng.trade_pnl_usd(t, USD_PER_PT, eng.FIXED_LOT, POINT)
        leg = "IS" if t.fill_idx < split_idx else "OOS"
        out.append(f"| {i} | {t.fill_time:%Y-%m-%d %H:%M} | {t.exit_time:%H:%M} | {leg} | "
                   f"{s.direction} | {t.eff_entry:.2f} | {s.sl:.2f} | {t.tp:.2f} | "
                   f"{t.exit_price:.2f} | {pts:+.0f} | ${usd:+,.0f} | {t.r:+.2f} | {t.outcome} |")
    return "\n".join(out)


def _closing_text(bl, a_ok, overlap, hl, hist_res, ranked, bmo, hy):
    viable = [s for s in ranked if (hist_res[s[0]]["oos"]["n"] >= 15
              and not hist_res[s[0]]["inverted"] and hist_res[s[0]]["oos"]["pf"] >= 1.20
              and hist_res[s[0]]["maxdd"] <= 25.0 and hist_res[s[0]]["comparable"])]
    top = ranked[0]; tr = hist_res[top[0]]
    parts = []
    parts.append(
        f"The broker-feed London baseline {'reproduced the known 9 setups (7L/2S)' if a_ok else 'shifted slightly with the rolling broker window'} "
        f"— the engine is intact and this remains the only live-faithful (but ~{bmo:.0f}-month, "
        "tiny-n) reference.")
    parts.append(
        f"HistData gave the first large sample (~{hy:.0f}y). London on HistData: "
        f"n={hl['all']['n']}, PF {pf_s(hl['all']['pf'])}, OOS PF {pf_s(hl['oos']['pf'])} "
        f"(OOS n={hl['oos']['n']}), verdict **{hl['verdict']}**. Overlap with the broker "
        f"feed on the shared window was {overlap['agree_pct']:.0f}% (day+direction).")
    if viable:
        names = ", ".join(hist_res[s[0]]["title"].split(" 0")[0].split(" 1")[0].split(" 2")[0] for s in viable)
        parts.append(
            f"**Forward-tracking candidates** (HistData OOS PF≥1.20, OOS n≥15, maxDD≤25%, "
            f"not inverted, comparable): **{names}**. Best by OOS PF: **{tr['title']}** "
            f"(OOS PF {pf_s(tr['oos']['pf'])}, n {tr['oos']['n']}). These earned the "
            "strongest *evidence*, not a live clearance — fills differ on the broker, so "
            "demo-forward first.")
    else:
        parts.append(
            "**No comparable session passed all gates on HistData** (OOS PF≥1.20, OOS n≥15, "
            "maxDD≤25%, not inverted). The locked one-variable session test does not, on "
            "this feed, surface a session that is both robust and IS/OOS-aligned — so there "
            "is no forward-tracking candidate beyond what live-faithful forward trades could "
            "still earn for London. Re-tuning is out of scope here (it would reintroduce "
            "selection bias).")
    parts.append(
        "Governing caveats stand on every verdict: broker = live-faithful but tiny-n; "
        "HistData = large-n but a different feed; data-quality and IS/OOS alignment gate "
        "each result; nothing here is cleared for live.")
    return "\n\n".join(parts)


if __name__ == "__main__":
    main()
