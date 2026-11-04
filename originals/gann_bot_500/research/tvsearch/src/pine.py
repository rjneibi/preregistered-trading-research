"""Write Pine Script v5 strategies for the top configurations (and the Phase-1 video rule) so they can be checked in
TradingView's Strategy Tester. Expect small differences, see NOTES at the top of every generated file.
    python src/pine.py            (reads results/phase2_top20.csv, writes pine/top_1..3.pine and pine/video_ema9_vwap.pine)
"""
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

NOTES = """// NOTES - why TradingView will not match the Python backtest to the cent:
//  * Data: Python used {data}. TradingView's feed for your symbol has other ticks/volume (VWAP uses volume).
//  * Same-bar stop+target: Python assumes the STOP filled first (worst case); TradingView's broker emulator guesses
//    the path from the bar's open. Turn on "Bar Magnifier" (Premium) to get closer.
//  * Costs: Python charged {cost}. Set the same in Properties.
//  * Session: Python resets sessions at {sess}; TradingView uses the symbol's session (check the chart's session settings).
//  * Fills: both fill at the next bar's open after the signal bar closes (process_orders_on_close = false).
"""

KAMA = """kama(src, n) =>
    float k = na
    ch = math.abs(src - src[n])
    vol = math.sum(math.abs(src - src[1]), n)
    er = vol != 0 ? ch / vol : 0
    sc = math.pow(er * (2.0 / 3 - 2.0 / 31) + 2.0 / 31, 2)
    k := na(k[1]) ? src : k[1] + sc * (src - k[1])
    k
"""


def ma_expr(kind, n, src="close"):
    return {"sma": f"ta.sma({src}, {n})", "ema": f"ta.ema({src}, {n})", "wma": f"ta.wma({src}, {n})",
            "hma": f"ta.hma({src}, {n})", "vwma": f"ta.vwma({src}, {n})", "rma": f"ta.rma({src}, {n})",
            "dema": f"(2 * ta.ema({src}, {n}) - ta.ema(ta.ema({src}, {n}), {n}))",
            "tema": f"(3 * ta.ema({src}, {n}) - 3 * ta.ema(ta.ema({src}, {n}), {n}) + ta.ema(ta.ema(ta.ema({src}, {n}), {n}), {n}))",
            "alma": f"ta.alma({src}, {n}, 0.85, 6)", "kama": f"kama({src}, {n})"}[kind]


ANCH = {"sess": 'timeframe.change("D")', "wk": 'timeframe.change("W")', "mon": 'timeframe.change("M")'}
SRC = {"c": "close", "hl2": "hl2", "hlc3": "hlc3", "ohlc4": "ohlc4"}


def body(c, asset, tf):
    L = []  # pine lines
    t = c["template"]
    if t == "xover":
        L.append(f"fastLine = {ma_expr(c['fast_kind'], c['fast_len'])}")
        if c["slow"] == "ma":
            L.append(f"slowLine = {ma_expr(c['slow_kind'], c['slow_len'])}")
        elif c["slow"] == "vwap":
            L.append(f"slowLine = ta.vwap({SRC[c['vw_src']]}, {ANCH[c['vw_anchor']]}, 1)")
        else:
            L.append("slowLine = fastLine"); L.append("fastLine := close")
        L += ["longSig = ta.crossover(fastLine, slowLine)", "shortSig = ta.crossunder(fastLine, slowLine)"]
        if c["slow"] == "price":
            L = [f"slowLine = {ma_expr(c['fast_kind'], c['fast_len'])}", "longSig = ta.crossover(close, slowLine)",
                 "shortSig = ta.crossunder(close, slowLine)"]
    elif t == "trend":
        y = c["sys"]
        if y == "supertrend":
            L += [f"[stLine, stDir] = ta.supertrend({c['st_mult']}, {c['st_len']})",
                  "longSig = stDir < 0 and stDir[1] > 0", "shortSig = stDir > 0 and stDir[1] < 0"]
        elif y == "psar":
            L += [f"sar = ta.sar({c['sar_start']}, 0.02, {c['sar_max']})",
                  "longSig = sar < close and sar[1] > close[1]", "shortSig = sar > close and sar[1] < close[1]"]
        elif y in ("ichi_tk", "ichi_cloud"):
            L += ["don(n) => math.avg(ta.lowest(n), ta.highest(n))", "tenkan = don(9)", "kijun = don(26)",
                  "spanA = math.avg(tenkan, kijun)[25]", "spanB = don(52)[25]"]
            L += (["longSig = ta.crossover(tenkan, kijun)", "shortSig = ta.crossunder(tenkan, kijun)"] if y == "ichi_tk" else
                  ["longSig = ta.crossover(close, math.max(spanA, spanB))", "shortSig = ta.crossunder(close, math.min(spanA, spanB))"])
        elif y == "dmi":
            L += [f"[diP, diM, adxV] = ta.dmi({c['dmi_len']}, {c['dmi_len']})", f"adxOk = adxV > {c['dmi_adx']}",
                  "longSig = ta.crossover(diP, diM) and adxOk", "shortSig = ta.crossunder(diP, diM) and adxOk"]
        elif y == "aroon":
            n = c["aroon_len"]
            L += [f"aUp = 100 * (ta.highestbars(high, {n + 1}) + {n}) / {n}", f"aDn = 100 * (ta.lowestbars(low, {n + 1}) + {n}) / {n}",
                  "longSig = ta.crossover(aUp, aDn)", "shortSig = ta.crossunder(aUp, aDn)"]
        elif y in ("macd_sig", "macd_zero"):
            a, b, s = c["macd"].split("/")
            L.append(f"[macdL, sigL, histL] = ta.macd(close, {a}, {b}, {s})")
            L += (["longSig = ta.crossover(macdL, sigL)", "shortSig = ta.crossunder(macdL, sigL)"] if y == "macd_sig" else
                  ["longSig = ta.crossover(macdL, 0)", "shortSig = ta.crossunder(macdL, 0)"])
        elif y == "tsi":
            L += ["tsiV = ta.tsi(close, 13, 25)", "tsiS = ta.ema(tsiV, 13)", "longSig = ta.crossover(tsiV, tsiS)",
                  "shortSig = ta.crossunder(tsiV, tsiS)"]
        elif y == "ao":
            L += ["aoV = ta.sma(hl2, 5) - ta.sma(hl2, 34)", "longSig = ta.crossover(aoV, 0)", "shortSig = ta.crossunder(aoV, 0)"]
        else:
            fn = "ta.roc" if y == "roc" else "ta.mom"
            L += [f"mV = {fn}(close, {c['mom_len']})", "longSig = ta.crossover(mV, 0)", "shortSig = ta.crossunder(mV, 0)"]
    elif t == "breakout":
        b = c["brk"]
        if b == "donchian":
            L += [f"dHi = ta.highest(high, {c['dc_len']})[1]", f"dLo = ta.lowest(low, {c['dc_len']})[1]",
                  "longSig = ta.crossover(close, dHi)", "shortSig = ta.crossunder(close, dLo)"]
        elif b == "orb":
            m = c["orb_min"]
            L += ["newDay = timeframe.change(\"D\")", "var int dayStart = na", "var float orH = na", "var float orL = na",
                  "var bool tookL = false", "var bool tookS = false",
                  "if newDay\n    dayStart := time\n    orH := high\n    orL := low\n    tookL := false\n    tookS := false",
                  f"inRange = (time - dayStart) < {m} * 60000",
                  "if inRange and not newDay\n    orH := math.max(orH, high)\n    orL := math.min(orL, low)",
                  "longSig = not inRange and close > orH and not tookL", "shortSig = not inRange and close < orL and not tookS",
                  "if longSig\n    tookL := true", "if shortSig\n    tookS := true"]
        elif b == "pdhl":
            L += ['pdh = request.security(syminfo.tickerid, "D", high[1], lookahead = barmerge.lookahead_on)',
                  'pdl = request.security(syminfo.tickerid, "D", low[1], lookahead = barmerge.lookahead_on)',
                  "longSig = ta.crossover(close, pdh)", "shortSig = ta.crossunder(close, pdl)"]
        elif b == "bb":
            L += [f"[bbM, bbU, bbL] = ta.bb(close, {c['bb_len']}, {c['bb_k']})", "longSig = ta.crossover(close, bbU)",
                  "shortSig = ta.crossunder(close, bbL)"]
        else:
            L += [f"kcM = ta.ema(close, {c['kc_len']})", "kcA = ta.atr(10)", f"kcU = kcM + {c['kc_k']} * kcA",
                  f"kcL = kcM - {c['kc_k']} * kcA", "longSig = ta.crossover(close, kcU)", "shortSig = ta.crossunder(close, kcL)"]
    elif t == "meanrev":
        o = c["osc"]
        if o == "rsi":
            lv = c["rsi_lvl"]
            L += [f"r = ta.rsi(close, {c['rsi_len']})", f"longSig = ta.crossover(r, {lv})", f"shortSig = ta.crossunder(r, {100 - lv})"]
        elif o in ("stoch", "stochrsi", "mfi"):
            lv = c["osc_lvl"]
            L.append({"stoch": "k = ta.sma(ta.stoch(close, high, low, 14), 3)",
                      "stochrsi": "rr = ta.rsi(close, 14)\nk = ta.sma(ta.stoch(rr, rr, rr, 14), 3)",
                      "mfi": "k = ta.mfi(hlc3, 14)"}[o])
            L += [f"longSig = ta.crossover(k, {lv})", f"shortSig = ta.crossunder(k, {100 - lv})"]
        elif o == "cci":
            lv = c["cci_lvl"]
            L += ["k = ta.cci(hlc3, 20)", f"longSig = ta.crossover(k, -{lv})", f"shortSig = ta.crossunder(k, {lv})"]
        elif o == "willr":
            lv = c["wr_lvl"]
            L += ["k = ta.wpr(14)", f"longSig = ta.crossover(k, {-100 + lv})", f"shortSig = ta.crossunder(k, {-lv})"]
        elif o == "bb_touch":
            L += [f"[bbM, bbU, bbL] = ta.bb(close, {c['bb_len']}, {c['bb_k']})", "longSig = ta.crossover(close, bbL)",
                  "shortSig = ta.crossunder(close, bbU)"]
        elif o == "vwap_band":
            L += [f"[vwM, vwU, vwL] = ta.vwap(ohlc4, timeframe.change(\"D\"), {c['band_k']})",
                  "longSig = ta.crossover(close, vwL)", "shortSig = ta.crossunder(close, vwU)"]
        else:
            L += [f"kcM = ta.ema(close, {c['kc_len']})", "kcA = ta.atr(10)", f"kcU = kcM + {c['kc_k']} * kcA",
                  f"kcL = kcM - {c['kc_k']} * kcA", "longSig = ta.crossover(close, kcL)", "shortSig = ta.crossunder(close, kcU)"]
    else:
        s = c["state"]
        st = {"ema_side": f"math.sign(close - ta.ema(close, {c.get('state_len')}))",
              "ema_slope": f"math.sign(ta.ema(close, {c.get('state_len')}) - ta.ema(close, {c.get('state_len')})[5])",
              "st_dir": "-stD2",
              "dmi_dir": "dmiAdx > 20 ? math.sign(dmiP - dmiM) : 0",
              "htf": "math.sign(close - htfEma)",
              "vwap_side": 'math.sign(close - ta.vwap(ohlc4, timeframe.change("D"), 1))',
              "cloud": "close > math.max(spanA, spanB) ? 1 : close < math.min(spanA, spanB) ? -1 : 0"}[s]
        if s == "dmi_dir":
            L.append("[dmiP, dmiM, dmiAdx] = ta.dmi(14, 14)")
        if s == "st_dir":
            L.append("[stL2, stD2] = ta.supertrend(3, 10)")
        if s == "cloud":
            L += ["don(n) => math.avg(ta.lowest(n), ta.highest(n))", "spanA = math.avg(don(9), don(26))[25]", "spanB = don(52)[25]"]
        if s == "htf":
            L.append(htf_line(tf))
        L.append(f"trendState = {st}")
        g = c["trig"]
        if g == "rsi_pb":
            lv = c["pb_lvl"]
            L += [f"r = ta.rsi(close, {c['pb_rsi_len']})", f"tL = ta.crossover(r, {lv})", f"tS = ta.crossunder(r, {100 - lv})"]
        elif g == "stoch_pb":
            L += ["k = ta.sma(ta.stoch(close, high, low, 14), 3)", "d = ta.sma(k, 3)",
                  "tL = ta.crossover(k, d) and k < 30", "tS = ta.crossunder(k, d) and k > 70"]
        elif g in ("ma_touch", "vwap_touch"):
            ref = "ta.ema(close, 20)" if g == "ma_touch" else 'ta.vwap(ohlc4, timeframe.change("D"), 1)'
            L += [f"ref = {ref}", "tL = low <= ref and close > ref", "tS = high >= ref and close < ref"]
        else:
            L += ["[macdL, sigL, histL] = ta.macd(close, 12, 26, 9)", "tL = ta.crossover(macdL, sigL)", "tS = ta.crossunder(macdL, sigL)"]
        L += ["longSig = tL and trendState == 1", "shortSig = tS and trendState == -1"]
    return L


def htf_line(tf):
    return f'htfEma = request.security(syminfo.tickerid, "{int(tf) * 4}", ta.ema(close, 50)[1], lookahead = barmerge.lookahead_on)'


def filters(c, asset, tf):
    L, okL, okS = [], ["true"], ["true"]
    span = 1380 if asset == "XAU" else 390
    for f in (c["filt1"], c["filt2"]):
        if f == "none":
            continue
        if f == "tod":
            L.append(f"minsIn = ta.barssince(timeframe.change(\"D\")) * {tf}")
            okL.append(f"minsIn >= {c['tod_skip_open']} and minsIn + {tf} <= {span - c['tod_skip_close']}")
        elif f == "dow":
            okL.append("dayofweek != " + ("dayofweek.monday" if c["dow_skip"] == 0 else "dayofweek.friday"))
        elif f == "adx":
            L.append("[fP, fM, fAdx] = ta.dmi(14, 14)"); okL.append(f"fAdx > {c['adx_min']}")
        elif f == "ma_side":
            L.append(f"sideEma = ta.ema(close, {c['side_len']})"); okL.append("close > sideEma"); okS.append("close < sideEma")
        elif f == "htf":
            if htf_line(tf) not in L:
                L.append(htf_line(tf))
            okL.append("close > htfEma"); okS.append("close < htfEma")
        elif f == "atr_pct":
            a, b = c["atr_band"].split("-")
            L.append("atrPct = ta.percentrank(ta.atr(14), 500)"); okL.append(f"atrPct >= {a} and atrPct <= {b}")
        elif f == "rvol":
            okL.append(f"volume / ta.sma(volume, 20)[1] > {c['rvol_min']}")
    common = [x for x in okL if x not in ("close > sideEma", "close > htfEma")]
    long_ok = " and ".join(okL); short_ok = " and ".join(common + [x for x in okS if x != "true"])
    return L, long_ok, short_ok


def exits(c):
    e = c["exit"]
    lines = ["atrV = ta.atr(14)"]
    if e == "fixed":
        lines += [f"tpDist = {c['tp_fix']}", f"slDist = {c['sl_fix']}"]
    elif e == "atr":
        lines += [f"tpDist = {c['tp_atr']} * atrV", f"slDist = {c['sl_atr']} * atrV"]
    elif e == "r":
        lines += [f"slDist = {c['sl_atr']} * atrV", f"tpDist = {c['tp_r']} * slDist"]
    elif e == "trail":
        lines += ["float tpDist = na", f"slDist = {c['trail_sl']} * atrV", f"trailDist = {c['trail_atr']} * atrV"]
    elif e == "opp":
        lines += ["float tpDist = na", f"slDist = {c['opp_sl']} * atrV"]
    else:
        lines += ["float tpDist = na", f"slDist = {c['time_sl']} * atrV"]
    return lines


def strategy(c, asset, tf, title, data_note, cost_note, sess_note):
    head = NOTES.format(data=data_note, cost=cost_note, sess=sess_note)
    sig = body(c, asset, tf)
    fl, long_ok, short_ok = filters(c, asset, tf)
    ex = exits(c)
    side = c["side"]
    s = ["//@version=5", head,
         f'strategy("{title}", overlay = true, process_orders_on_close = false, default_qty_type = strategy.fixed, default_qty_value = 1)',
         "// config: " + json.dumps(c, sort_keys=True), ""]
    if any("kama(" in x for x in sig):
        s.append(KAMA)
    s += sig + fl + ex
    s += [f"goLong = longSig and {long_ok}" + (" and false" if side == "short" else ""),
          f"goShort = shortSig and {short_ok}" + (" and false" if side == "long" else ""),
          "var float lvlSL = na", "var float lvlTP = na", "var float lvlTrail = na"]
    eos = bool(c.get("eos"))
    if eos:
        s.append("lastBar = session.islastbar_regular or session.islastbar")
        s.append("nextIsNewDay = lastBar")
        s += ["goLong := goLong and not nextIsNewDay", "goShort := goShort and not nextIsNewDay"]
    s += ["if goLong", "    strategy.entry(\"L\", strategy.long)", "    lvlSL := slDist", "    lvlTP := tpDist",
          "if goShort", "    strategy.entry(\"S\", strategy.short)", "    lvlSL := slDist", "    lvlTP := tpDist"]
    if c["exit"] == "opp":
        s += ["if strategy.position_size > 0 and shortSig", "    strategy.close(\"L\")",
              "if strategy.position_size < 0 and longSig", "    strategy.close(\"S\")"]
    if c["exit"] == "time":
        s += [f"if strategy.position_size != 0 and bar_index - strategy.opentrades.entry_bar_index(0) >= {c['tbars'] - 1}",
              "    strategy.close_all()"]
    trail = c["exit"] == "trail"
    s += ["ep = strategy.position_avg_price",
          "if strategy.position_size > 0",
          "    strategy.exit(\"xL\", \"L\", stop = ep - lvlSL, limit = na(lvlTP) ? na : ep + lvlTP"
          + (", trail_points = 0, trail_offset = trailDist / syminfo.mintick" if trail else "") + ")",
          "if strategy.position_size < 0",
          "    strategy.exit(\"xS\", \"S\", stop = ep + lvlSL, limit = na(lvlTP) ? na : ep - lvlTP"
          + (", trail_points = 0, trail_offset = trailDist / syminfo.mintick" if trail else "") + ")"]
    if eos:
        s += ["if lastBar", "    strategy.close_all(immediately = true)"]
    return "\n".join(s) + "\n"


VIDEO = """//@version=5
{notes}
strategy("EMA9 x VWAP(OHLC4, session) - video rule, variant {v}", overlay = true, process_orders_on_close = false,
     default_qty_type = strategy.fixed, default_qty_value = 1)
tpUsd = input.float(5.0, "Take profit ($ move in the underlying)")
vw = ta.vwap(ohlc4, timeframe.change("D"), 1)
e9 = ta.ema(close, 9)
plot(vw, "VWAP", color.orange)
plot(e9, "EMA 9", color.blue)
longSig = ta.crossover(e9, vw)
shortSig = ta.crossunder(e9, vw)
lastBar = session.islastbar_regular or session.islastbar
{entries}
ep = strategy.position_avg_price
if strategy.position_size > 0
    strategy.exit("tpL", "L", limit = ep + tpUsd)
if strategy.position_size < 0
    strategy.exit("tpS", "S", limit = ep - tpUsd)
{eos}
"""


def video(v):
    if v == "a":   # stop-and-reverse
        ent = 'if longSig\n    strategy.entry("L", strategy.long)\nif shortSig\n    strategy.entry("S", strategy.short)'
        eos = ""
    elif v == "b":  # TP or end of session; opposite cross ignored while in a trade
        ent = ('if longSig and strategy.position_size == 0 and not lastBar\n    strategy.entry("L", strategy.long)\n'
               'if shortSig and strategy.position_size == 0 and not lastBar\n    strategy.entry("S", strategy.short)')
        eos = "if lastBar\n    strategy.close_all(immediately = true)"
    else:
        ent = ('if longSig and not lastBar\n    strategy.entry("L", strategy.long)\n'
               'if shortSig and not lastBar\n    strategy.entry("S", strategy.short)')
        eos = "if lastBar\n    strategy.close_all(immediately = true)"
    notes = NOTES.format(data="Yahoo SPY/QQQ regular hours + broker XAUUSD (bid bars, tick volume)",
                         cost="SPY/QQQ $0.01/share per side; XAU the bar spread", sess="09:30 ET (SPY/QQQ), 17:00 NY (XAU)")
    return VIDEO.format(notes=notes, v=v, entries=ent, eos=eos)


def main():
    top = pd.read_csv(os.path.join(ROOT, "results", "phase2_top20.csv"))
    for i, r in top.head(3).iterrows():
        c = json.loads(r.cfg); asset, tf = r.asset, int(r.tf)
        title = f"TVS top{i + 1} {asset} {tf}m {c['template']}"
        data_note = "broker XAUUSD bid bars + spread, tick volume" if asset == "XAU" else f"Yahoo {asset} regular-hours bars"
        cost_note = "the bar's spread (min $0.22)" if asset == "XAU" else "$0.01/share per side"
        sess_note = "00:00 broker time (= 17:00 New York)" if asset == "XAU" else "09:30 New York"
        open(os.path.join(ROOT, "pine", f"top_{i + 1}.pine"), "w", encoding="utf-8").write(
            strategy(c, asset, tf, title, data_note, cost_note, sess_note))
    for v in "abc":
        open(os.path.join(ROOT, "pine", f"video_ema9_vwap_{v}.pine"), "w", encoding="utf-8").write(video(v))
    print("pine written:", sorted(os.listdir(os.path.join(ROOT, "pine"))))


if __name__ == "__main__":
    main()
