"""Phase 2 search space: strategy templates x filters x exits, built from TradingView built-in indicators.

A config is a flat dict of categorical choices. `make_config(pick, asset)` builds one; `pick(name, options)` is either
a seeded random choice (coarse grid) or optuna's trial.suggest_categorical (refinement) - same space for both.
`build(cfg, D, C)` turns it into long/short signal masks (decided on bar close) plus the exit spec.
"""
import numpy as np

import ind

MA_KINDS = ["sma", "ema", "wma", "hma", "vwma", "dema", "tema", "alma", "kama"]
FIXED = {"XAU": [2.0, 3.0, 5.0, 8.0, 12.0], "SPY": [0.25, 0.5, 1.0, 2.0, 3.0], "QQQ": [0.25, 0.5, 1.0, 2.0, 3.0]}
TEMPLATES = ["xover", "trend", "breakout", "meanrev", "pullback"]


def make_config(pick, asset):
    c = {"template": pick("template", TEMPLATES)}
    t = c["template"]
    if t == "xover":
        c["fast_kind"] = pick("fast_kind", MA_KINDS); c["fast_len"] = pick("fast_len", [5, 9, 13, 21])
        c["slow"] = pick("slow", ["ma", "vwap", "price"])
        if c["slow"] == "ma":
            c["slow_kind"] = pick("slow_kind", MA_KINDS); c["slow_len"] = pick("slow_len", [34, 50, 100, 200])
        elif c["slow"] == "vwap":
            c["vw_anchor"] = pick("vw_anchor", ["sess", "wk", "mon"]); c["vw_src"] = pick("vw_src", ["c", "hl2", "hlc3", "ohlc4"])
    elif t == "trend":
        c["sys"] = pick("sys", ["supertrend", "psar", "ichi_tk", "ichi_cloud", "dmi", "aroon", "macd_sig", "macd_zero",
                                "tsi", "ao", "roc", "mom"])
        if c["sys"] == "supertrend":
            c["st_len"] = pick("st_len", [7, 10, 14]); c["st_mult"] = pick("st_mult", [2.0, 3.0, 4.0])
        elif c["sys"] == "psar":
            c["sar_start"] = pick("sar_start", [0.01, 0.02]); c["sar_max"] = pick("sar_max", [0.1, 0.2])
        elif c["sys"] == "dmi":
            c["dmi_len"] = pick("dmi_len", [14, 21]); c["dmi_adx"] = pick("dmi_adx", [0, 20, 25])
        elif c["sys"] == "aroon":
            c["aroon_len"] = pick("aroon_len", [14, 25])
        elif c["sys"] in ("macd_sig", "macd_zero"):
            c["macd"] = pick("macd", ["12/26/9", "8/21/5", "5/35/5"])
        elif c["sys"] in ("roc", "mom"):
            c["mom_len"] = pick("mom_len", [9, 14, 21])
    elif t == "breakout":
        c["brk"] = pick("brk", ["donchian", "orb", "pdhl", "bb", "kc"])
        if c["brk"] == "donchian":
            c["dc_len"] = pick("dc_len", [10, 20, 55])
        elif c["brk"] == "orb":
            c["orb_min"] = pick("orb_min", [5, 15, 30])
        elif c["brk"] == "bb":
            c["bb_len"] = pick("bb_len", [20, 50]); c["bb_k"] = pick("bb_k", [1.5, 2.0, 2.5])
        elif c["brk"] == "kc":
            c["kc_len"] = pick("kc_len", [20, 50]); c["kc_k"] = pick("kc_k", [1.0, 1.5, 2.0])
    elif t == "meanrev":
        c["osc"] = pick("osc", ["rsi", "stoch", "stochrsi", "cci", "willr", "mfi", "bb_touch", "vwap_band", "kc_touch"])
        o = c["osc"]
        if o == "rsi":
            c["rsi_len"] = pick("rsi_len", [2, 7, 14]); c["rsi_lvl"] = pick("rsi_lvl", [10, 20, 30])
        elif o in ("stoch", "stochrsi", "mfi"):
            c["osc_lvl"] = pick("osc_lvl", [10, 20, 30])
        elif o == "cci":
            c["cci_lvl"] = pick("cci_lvl", [100, 150, 200])
        elif o == "willr":
            c["wr_lvl"] = pick("wr_lvl", [10, 20])
        elif o == "bb_touch":
            c["bb_len"] = pick("bb_len", [20, 50]); c["bb_k"] = pick("bb_k", [1.5, 2.0, 2.5])
        elif o == "vwap_band":
            c["band_k"] = pick("band_k", [1.0, 2.0])
        elif o == "kc_touch":
            c["kc_len"] = pick("kc_len", [20, 50]); c["kc_k"] = pick("kc_k", [1.0, 1.5, 2.0])
    else:  # pullback = one trend state + one trigger
        c["state"] = pick("state", ["ema_side", "ema_slope", "st_dir", "dmi_dir", "htf", "vwap_side", "cloud"])
        if c["state"] in ("ema_side", "ema_slope"):
            c["state_len"] = pick("state_len", [50, 100, 200])
        c["trig"] = pick("trig", ["rsi_pb", "stoch_pb", "ma_touch", "vwap_touch", "macd_x"])
        if c["trig"] == "rsi_pb":
            c["pb_rsi_len"] = pick("pb_rsi_len", [2, 7, 14]); c["pb_lvl"] = pick("pb_lvl", [20, 30, 40])
    # up to two filters
    c["filt1"] = pick("filt1", ["none", "tod", "dow", "adx", "ma_side", "htf", "atr_pct", "rvol"])
    c["filt2"] = pick("filt2", ["none", "tod", "dow", "adx", "ma_side", "htf", "atr_pct", "rvol"])
    for f in {c["filt1"], c["filt2"]}:
        if f == "tod":
            c["tod_skip_open"] = pick("tod_skip_open", [0, 15, 30, 60]); c["tod_skip_close"] = pick("tod_skip_close", [0, 15, 30, 60])
        elif f == "dow":
            c["dow_skip"] = pick("dow_skip", [0, 4])
        elif f == "adx":
            c["adx_min"] = pick("adx_min", [20, 25, 30])
        elif f == "ma_side":
            c["side_len"] = pick("side_len", [50, 200])
        elif f == "atr_pct":
            c["atr_band"] = pick("atr_band", ["0-50", "20-80", "50-100"])
        elif f == "rvol":
            c["rvol_min"] = pick("rvol_min", [1.0, 1.5])
    c["side"] = pick("side", ["both", "long", "short"])
    # exits
    c["exit"] = pick("exit", ["fixed", "atr", "r", "trail", "opp", "time"])
    e = c["exit"]
    if e == "fixed":
        c["tp_fix"] = pick("tp_fix", FIXED[asset]); c["sl_fix"] = pick("sl_fix", FIXED[asset])
    elif e == "atr":
        c["tp_atr"] = pick("tp_atr", [1.0, 1.5, 2.0, 3.0]); c["sl_atr"] = pick("sl_atr", [0.5, 1.0, 1.5, 2.0])
    elif e == "r":
        c["sl_atr"] = pick("sl_atr", [0.5, 1.0, 1.5, 2.0]); c["tp_r"] = pick("tp_r", [1.0, 1.5, 2.0, 3.0])
    elif e == "trail":
        c["trail_atr"] = pick("trail_atr", [1.0, 2.0, 3.0]); c["trail_sl"] = pick("trail_sl", [1.0, 2.0])
    elif e == "opp":
        c["opp_sl"] = pick("opp_sl", [2.0, 3.0])
    else:
        c["tbars"] = pick("tbars", [5, 10, 20]); c["time_sl"] = pick("time_sl", [1.0, 2.0])
    c["eos"] = pick("eos", [False, True])
    return c


def exit_spec(c):
    e = c["exit"]
    ex = dict(eos=bool(c["eos"]))
    if e == "fixed":
        ex.update(tp=c["tp_fix"], sl=c["sl_fix"])
    elif e == "atr":
        ex.update(tp_atr=c["tp_atr"], sl_atr=c["sl_atr"])
    elif e == "r":
        ex.update(sl_atr=c["sl_atr"], tp_r=c["tp_r"])
    elif e == "trail":
        ex.update(trail_atr=c["trail_atr"], sl_atr=c["trail_sl"])
    elif e == "opp":
        ex.update(opp=True, sl_atr=c["opp_sl"])
    else:
        ex.update(tbars=c["tbars"], sl_atr=c["time_sl"])
    return ex


# ---------------------------------------------------------------- indicator cache (per dataset)
def get(C, key, fn):
    if key not in C:
        C[key] = fn()
    return C[key]


def src(D, name):
    return {"c": D["c"], "hl2": (D["h"] + D["l"]) / 2, "hlc3": (D["h"] + D["l"] + D["c"]) / 3, "ohlc4": D["ohlc4"]}[name]


def sess_vwap(D, C, anchor="sess", s="ohlc4"):
    return get(C, ("vwap", anchor, s), lambda: ind.vwap(src(D, s), D["v"], D[anchor]))


def ma(D, C, kind, n):
    return get(C, ("ma", kind, n), lambda: ind.ma(kind, D["c"], n, D["v"]))


def htf_ema(D, C, n=50, mult=4):
    def f():
        tf = D["tf"] if D["tf"] != "D" else 1440
        key = D["sess"] * 10_000 + D["mins"] // (tf * mult)
        new = np.r_[True, key[1:] != key[:-1]]
        gid = np.cumsum(new) - 1
        last = np.r_[np.flatnonzero(new)[1:] - 1, len(key) - 1]
        e = ind.ema(D["c"][last], n)
        prev = np.r_[np.nan, e[:-1]]            # the last COMPLETED higher-timeframe bar
        return prev[gid]
    return get(C, ("htf", n, mult), f)


def per_session(D, C):
    def f():
        sid = D["sid"]; starts = np.flatnonzero(np.r_[True, sid[1:] != sid[:-1]])
        hi = np.maximum.reduceat(D["h"], starts); lo = np.minimum.reduceat(D["l"], starts)
        pdh = np.r_[np.nan, hi[:-1]][sid]; pdl = np.r_[np.nan, lo[:-1]][sid]
        return pdh, pdl
    return get(C, ("pdhl",), f)


def first_per_session(mask, sid):
    """Keep only the first True of each session."""
    idx = np.flatnonzero(mask)
    if not len(idx):
        return mask
    keep = np.r_[True, sid[idx][1:] != sid[idx][:-1]]
    out = np.zeros_like(mask); out[idx[keep]] = True
    return out


def macd_params(s):
    return [int(x) for x in s.split("/")]


def state(c, D, C):
    s = c["state"]; cl = D["c"]
    with np.errstate(invalid="ignore"):
        if s == "ema_side":
            return np.sign(cl - ma(D, C, "ema", c["state_len"]))
        if s == "ema_slope":
            e = ma(D, C, "ema", c["state_len"]); return np.sign(e - np.r_[np.full(5, np.nan), e[:-5]])
        if s == "st_dir":
            return get(C, ("st", 10, 3.0), lambda: ind.supertrend(D["h"], D["l"], cl, 10, 3.0))[0]
        if s == "dmi_dir":
            p, m, a = get(C, ("dmi", 14), lambda: ind.adx(D["h"], D["l"], cl, 14))
            return np.where(a > 20, np.sign(p - m), 0)
        if s == "htf":
            return np.sign(cl - htf_ema(D, C))
        if s == "vwap_side":
            return np.sign(cl - sess_vwap(D, C)[0])
        t, k, a, b = get(C, ("ichi",), lambda: ind.ichimoku(D["h"], D["l"]))
        return np.where(cl > np.fmax(a, b), 1, np.where(cl < np.fmin(a, b), -1, 0))


def build(c, D, C):
    h, l, cl = D["h"], D["l"], D["c"]
    cu, cd = ind.cross_up, ind.cross_dn
    t = c["template"]
    with np.errstate(invalid="ignore"):
        if t == "xover":
            f = ma(D, C, c["fast_kind"], c["fast_len"])
            if c["slow"] == "ma":
                s = ma(D, C, c["slow_kind"], c["slow_len"])
            elif c["slow"] == "vwap":
                s = sess_vwap(D, C, c["vw_anchor"], c["vw_src"])[0]
            else:
                f, s = cl, f
            L, S = cu(f, s), cd(f, s)
        elif t == "trend":
            y = c["sys"]
            if y == "supertrend":
                d = get(C, ("st", c["st_len"], c["st_mult"]), lambda: ind.supertrend(h, l, cl, c["st_len"], c["st_mult"]))[0]
                L, S = cu(d, 0), cd(d, 0)
            elif y == "psar":
                d = get(C, ("sar", c["sar_start"], c["sar_max"]), lambda: ind.psar(h, l, c["sar_start"], 0.02, c["sar_max"]))[0]
                L, S = cu(d, 0), cd(d, 0)
            elif y in ("ichi_tk", "ichi_cloud"):
                tk, kj, a, b = get(C, ("ichi",), lambda: ind.ichimoku(h, l))
                if y == "ichi_tk":
                    L, S = cu(tk, kj), cd(tk, kj)
                else:
                    L, S = cu(cl, np.fmax(a, b)), cd(cl, np.fmin(a, b))
            elif y == "dmi":
                p, m, a = get(C, ("dmi", c["dmi_len"]), lambda: ind.adx(h, l, cl, c["dmi_len"]))
                ok = a > c["dmi_adx"] if c["dmi_adx"] else np.ones(len(cl), bool)
                L, S = cu(p, m) & ok, cd(p, m) & ok
            elif y == "aroon":
                u, d = get(C, ("aroon", c["aroon_len"]), lambda: ind.aroon(h, l, c["aroon_len"]))
                L, S = cu(u, d), cd(u, d)
            elif y in ("macd_sig", "macd_zero"):
                a, b, s9 = macd_params(c["macd"])
                m, sg = get(C, ("macd", c["macd"]), lambda: ind.macd(cl, a, b, s9))
                L, S = (cu(m, sg), cd(m, sg)) if y == "macd_sig" else (cu(m, 0), cd(m, 0))
            elif y == "tsi":
                x = get(C, ("tsi",), lambda: ind.tsi(cl)); sg = get(C, ("tsi_sig",), lambda: ind.ema(x, 13))
                L, S = cu(x, sg), cd(x, sg)
            elif y == "ao":
                x = get(C, ("ao",), lambda: ind.ao(h, l)); L, S = cu(x, 0), cd(x, 0)
            else:
                fn = ind.roc if y == "roc" else ind.mom
                x = get(C, (y, c["mom_len"]), lambda: fn(cl, c["mom_len"])); L, S = cu(x, 0), cd(x, 0)
        elif t == "breakout":
            b = c["brk"]
            if b == "donchian":
                n = c["dc_len"]
                hi, lo = get(C, ("dc", n), lambda: ind.donchian(h, l, n))
                hi, lo = np.r_[np.nan, hi[:-1]], np.r_[np.nan, lo[:-1]]
                L, S = cu(cl, hi), cd(cl, lo)
            elif b == "orb":
                m = c["orb_min"]; tf = D["tf"]
                if tf == "D" or tf > m or m % tf:
                    return None
                def f():
                    sid = D["sid"]; inr = D["mins"] < m
                    hh = np.where(inr, h, -np.inf); ll = np.where(inr, l, np.inf)
                    starts = np.flatnonzero(np.r_[True, sid[1:] != sid[:-1]])
                    return np.maximum.reduceat(hh, starts)[sid], np.minimum.reduceat(ll, starts)[sid]
                oh, ol = get(C, ("orb", m), f)
                after = D["mins"] >= m
                L = first_per_session(after & (cl > oh), D["sid"]); S = first_per_session(after & (cl < ol), D["sid"])
            elif b == "pdhl":
                pdh, pdl = per_session(D, C); L, S = cu(cl, pdh), cd(cl, pdl)
            elif b == "bb":
                mid, up, lo = get(C, ("bb", c["bb_len"], c["bb_k"]), lambda: ind.bbands(cl, c["bb_len"], c["bb_k"]))
                L, S = cu(cl, up), cd(cl, lo)
            else:
                mid, up, lo = get(C, ("kc", c["kc_len"], c["kc_k"]), lambda: ind.keltner(h, l, cl, c["kc_len"], c["kc_k"]))
                L, S = cu(cl, up), cd(cl, lo)
        elif t == "meanrev":
            o = c["osc"]
            if o == "rsi":
                r = get(C, ("rsi", c["rsi_len"]), lambda: ind.rsi(cl, c["rsi_len"])); lv = c["rsi_lvl"]
                L, S = cu(r, lv), cd(r, 100 - lv)
            elif o in ("stoch", "stochrsi"):
                k, d = get(C, (o,), lambda: ind.stoch(h, l, cl) if o == "stoch" else ind.stochrsi(cl)); lv = c["osc_lvl"]
                L, S = cu(k, lv), cd(k, 100 - lv)
            elif o == "mfi":
                x = get(C, ("mfi",), lambda: ind.mfi(h, l, cl, D["v"])); lv = c["osc_lvl"]
                L, S = cu(x, lv), cd(x, 100 - lv)
            elif o == "cci":
                x = get(C, ("cci",), lambda: ind.cci(h, l, cl)); lv = c["cci_lvl"]
                L, S = cu(x, -lv), cd(x, lv)
            elif o == "willr":
                x = get(C, ("willr",), lambda: ind.willr(h, l, cl)); lv = c["wr_lvl"]
                L, S = cu(x, -100 + lv), cd(x, -lv)
            elif o == "bb_touch":
                mid, up, lo = get(C, ("bb", c["bb_len"], c["bb_k"]), lambda: ind.bbands(cl, c["bb_len"], c["bb_k"]))
                L, S = cu(cl, lo), cd(cl, up)          # close back inside after being outside
            elif o == "vwap_band":
                vw, sd = sess_vwap(D, C); k = c["band_k"]
                L, S = cu(cl, vw - k * sd), cd(cl, vw + k * sd)
            else:
                mid, up, lo = get(C, ("kc", c["kc_len"], c["kc_k"]), lambda: ind.keltner(h, l, cl, c["kc_len"], c["kc_k"]))
                L, S = cu(cl, lo), cd(cl, up)
        else:
            st = state(c, D, C); g = c["trig"]
            if g == "rsi_pb":
                r = get(C, ("rsi", c["pb_rsi_len"]), lambda: ind.rsi(cl, c["pb_rsi_len"])); lv = c["pb_lvl"]
                tl, ts = cu(r, lv), cd(r, 100 - lv)
            elif g == "stoch_pb":
                k, d = get(C, ("stoch",), lambda: ind.stoch(h, l, cl))
                tl, ts = cu(k, d) & (k < 30), cd(k, d) & (k > 70)
            elif g in ("ma_touch", "vwap_touch"):
                ref = ma(D, C, "ema", 20) if g == "ma_touch" else sess_vwap(D, C)[0]
                tl, ts = (l <= ref) & (cl > ref), (h >= ref) & (cl < ref)
            else:
                m, sg = get(C, ("macd", "12/26/9"), lambda: ind.macd(cl, 12, 26, 9)); tl, ts = cu(m, sg), cd(m, sg)
            L, S = tl & (st == 1), ts & (st == -1)
        ok = np.ones(len(cl), bool); okL = np.ones(len(cl), bool); okS = np.ones(len(cl), bool)
        for f in (c["filt1"], c["filt2"]):
            if f == "none":
                continue
            if f == "tod":
                span = 1380 if D["asset"] == "XAU" else 390
                tf = D["tf"] if D["tf"] != "D" else 0
                ok &= (D["mins"] >= c["tod_skip_open"]) & (D["mins"] + tf <= span - c["tod_skip_close"])
            elif f == "dow":
                ok &= D["dow"] != c["dow_skip"]
            elif f == "adx":
                ok &= get(C, ("dmi", 14), lambda: ind.adx(h, l, cl, 14))[2] > c["adx_min"]
            elif f == "ma_side":
                e = ma(D, C, "ema", c["side_len"]); okL &= cl > e; okS &= cl < e
            elif f == "htf":
                e = htf_ema(D, C); okL &= cl > e; okS &= cl < e
            elif f == "atr_pct":
                pr = get(C, ("atrpct",), lambda: ind.pct_rank(D["atr14"], 500)); a, b = map(int, c["atr_band"].split("-"))
                ok &= (pr >= a) & (pr <= b)
            elif f == "rvol":
                ok &= get(C, ("rvol",), lambda: ind.rvol(D["v"], 20)) > c["rvol_min"]
        L = L & ok & okL; S = S & ok & okS
        if c["side"] == "long":
            S = np.zeros_like(S)
        elif c["side"] == "short":
            L = np.zeros_like(L)
    return np.asarray(L, bool), np.asarray(S, bool)


NUMERIC = ["fast_len", "slow_len", "st_len", "st_mult", "sar_start", "sar_max", "dmi_len", "dmi_adx", "aroon_len",
           "mom_len", "dc_len", "orb_min", "bb_len", "bb_k", "kc_len", "kc_k", "rsi_len", "rsi_lvl", "osc_lvl", "cci_lvl",
           "wr_lvl", "band_k", "state_len", "pb_rsi_len", "pb_lvl", "tod_skip_open", "tod_skip_close", "adx_min",
           "side_len", "rvol_min", "tp_fix", "sl_fix", "tp_atr", "sl_atr", "tp_r", "trail_atr", "trail_sl", "opp_sl",
           "tbars", "time_sl"]


def grid_of(name, asset, _cache={}):
    """The option list of one parameter (used by the stability check)."""
    if asset not in _cache:
        opts, rng = {}, np.random.default_rng(0)
        for _ in range(3000):
            make_config(lambda n, o: (opts.setdefault(n, o), o[rng.integers(len(o))])[1], asset)
        _cache[asset] = opts
    return _cache[asset].get(name)
