"""SC-1: the classic SCALP / intraday techniques.  (pre-declared, written before any result was seen)

Data: M1, all times converted to New York time.  Indices: US500, USTEC, US30 (broker demo feed; server = NY+7,
checked by the 09:30 volatility spike).  Gold: histdata M1 2010-2026 (d_revival/data.py, broker = NY+7).
Costs: spread = 1.5 x median in-session M1 spread, charged per trade; stop exits pay an extra 0.5 spread slip.
All trades flat by 16:00 NY (indices) / end of window (gold).  One trade per rule per day.

  O1 ORB-range  : range = first N min after 09:30 (N=5,15,30); first break of high -> long / low -> short,
                  stop = other side of the range, exit 16:00.
  O2 ORB-candle : direction of the first 5-min candle (Zarattini et al. 2023), enter 09:35, stop = 10% of
                  14-day ATR, exit 16:00.
  M1 intraday momentum (Gao et al. 2018): sign of (prev 16:00 close -> 10:00) = direction for 15:30->16:00.
  G1 gap fade   : |09:30 open - prev 16:00 close| > 0.3% -> fade at 09:30, target prev close, stop = 1 gap
                  further, exit 16:00.
  X1 stretch fade: 10:30-15:00, price > 2.5 x (30-min ATR) from the session's running mean price -> fade,
                  target the mean, stop 1.25 x ATR(30m) further, exit 16:00.
  R1 first-hour reversal: fade the 09:30-10:30 move from 10:30 to 16:00, no stop.
Gold (broker clock):
  L1 Asia-range breakout at London: range 19:00-02:59 NY, first break 03:00-11:00 NY, stop other side, exit 11:00.
  L2 London 15-min ORB 03:00-03:15 NY, stop other side, exit 11:00.
  L3 NY-open 15-min ORB on gold 09:30-09:45, stop other side, exit 16:00.

PASS  = PF >= 1.15 in BOTH halves, n >= 100 per half, and beats the SAME entries with random direction
        (2000 twins, p < 0.005).  Index rules CONFIRMED only if also PF > 1.0 on both other indices.
"""
import sys

import numpy as np
import pandas as pd

DD = r"@GANN_ROOT@/research/cross_market/data"
RNG = np.random.default_rng(5)


def load_index(sym):
    z = np.load(f"{DD}\\{sym}_M1.npz")
    # server clock = Athens local time (EU DST); NY+7 except ~3 weeks/yr when US/EU DST dates differ
    t = (pd.to_datetime(z["t"], unit="s").tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT")
         .tz_convert("America/New_York").tz_localize(None))
    keep = ~pd.isna(t) & ~pd.Index(t).duplicated()
    df = pd.DataFrame({k: z[k][keep] for k in "ohlc"}, index=t[keep])
    mins = df.index.hour * 60 + df.index.minute
    sp = z["sp"][keep]
    in_sess = (mins >= 570) & (mins < 960)
    cost = 1.5 * float(np.median(sp[in_sess & (sp > 0)]))
    return df, cost


def load_gold():
    sys.path.insert(0, r"@GANN_ROOT@/research/d_revival")
    import data
    d = data.load()
    t = pd.to_datetime(d["t"], unit="s") - pd.Timedelta(hours=7)
    df = pd.DataFrame({"o": d["o"], "h": d["h"], "l": d["l"], "c": d["c"]}, index=t)
    return df[~df.index.duplicated()], 0.35


def days(df):
    m = df.index.hour * 60 + df.index.minute
    df = df.assign(m=m, d=df.index.normalize())
    return {k: g for k, g in df.groupby("d")}


def walk(g, i0, side, entry, stop, target, t_end):
    """From bar position i0 (entry at `entry`), walk M1 bars to exit. Stop first if both hit in a bar."""
    h, l, c, m = g["h"].values, g["l"].values, g["c"].values, g["m"].values
    for k in range(i0, len(g)):
        if m[k] >= t_end:
            return c[k - 1] if k > i0 else entry, "time"
        if stop is not None and ((side > 0 and l[k] <= stop) or (side < 0 and h[k] >= stop)):
            return stop, "stop"
        if target is not None and ((side > 0 and h[k] >= target) or (side < 0 and l[k] <= target)):
            return target, "tgt"
    return c[-1], "eod"


def trade(side, entry, exit_, how, cost):
    """(net, gross, cost) as fractions of the entry price."""
    g = side * (exit_ - entry) / entry
    c = (cost + (0.5 * cost if how == "stop" else 0)) / entry
    return g - c, g, c


# ------------------------------------------------------------------ index rules
def rules_index(D, cost):
    keys = sorted(D)
    closes = {k: D[k][D[k]["m"] < 960]["c"].iloc[-1] for k in keys if (D[k]["m"] < 960).any()}
    rng_d = {k: D[k]["h"].max() - D[k]["l"].min() for k in keys}
    atr = pd.Series(rng_d).rolling(14).mean().shift(1).to_dict()
    out = {f"O1 ORB-range {n}m": [] for n in (5, 15, 30)}
    out.update({"O2 ORB-candle 5m": [], "M1 intraday momentum": [], "G1 gap fade": [], "X1 stretch fade": [],
                "R1 first-hour reversal": []})
    prev = None
    for k in keys:
        g = D[k]
        s = g[(g["m"] >= 570) & (g["m"] < 960)]
        if len(s) < 300 or s["m"].values[0] > 571 or not (s["m"].values >= 931).any():   # need a clean open
            prev = k if k in closes else prev
            continue
        m, o, h, l, c = s["m"].values, s["o"].values, s["h"].values, s["l"].values, s["c"].values
        for n in (5, 15, 30):
            rh, rl = h[m < 570 + n].max(), l[m < 570 + n].min()
            for i in np.flatnonzero(m >= 570 + n):
                if h[i] > rh or l[i] < rl:
                    side = 1 if h[i] > rh else -1
                    if h[i] > rh and l[i] < rl:
                        break
                    ent = rh if side > 0 else rl
                    ex, how = walk(s, i + 1, side, ent, rl if side > 0 else rh, None, 960)
                    out[f"O1 ORB-range {n}m"].append((k, side, trade(side, ent, ex, how, cost), (ent, rl if side > 0 else rh, i + 1, None)))
                    break
        if atr.get(k) and not np.isnan(atr[k]):
            i5 = np.flatnonzero(m >= 575)[0]
            side = int(np.sign(c[i5 - 1] - o[0]))
            if side:
                ent = o[i5]
                st = ent - side * 0.10 * atr[k]
                ex, how = walk(s, i5, side, ent, st, None, 960)
                out["O2 ORB-candle 5m"].append((k, side, trade(side, ent, ex, how, cost), (ent, st, i5, None)))
        if prev is not None:
            pc = closes[prev]
            i10, i1530 = np.flatnonzero(m >= 600)[0], np.flatnonzero(m >= 930)
            if len(i1530):
                j = i1530[0]
                side = int(np.sign(o[i10] - pc))
                if side:
                    ex, how = walk(s, j, side, o[j], None, None, 960)
                    out["M1 intraday momentum"].append((k, side, trade(side, o[j], ex, how, cost), (o[j], None, j, None)))
            gap = (o[0] - pc) / pc
            if abs(gap) > 0.003:
                side = -int(np.sign(gap))
                st = o[0] - side * abs(o[0] - pc)
                ex, how = walk(s, 0, side, o[0], st, pc, 960)
                out["G1 gap fade"].append((k, side, trade(side, o[0], ex, how, cost), (o[0], st, 0, pc)))
        # X1 stretch fade
        tp = (h + l + c) / 3
        mean = np.cumsum(tp) / np.arange(1, len(tp) + 1)
        tr30 = pd.Series(h - l).rolling(30).sum().values / 30 * np.sqrt(30)    # ~30-min range scale
        for i in np.flatnonzero((m >= 630) & (m < 900)):
            if np.isnan(tr30[i]) or tr30[i] <= 0:
                continue
            z = (c[i] - mean[i]) / tr30[i]
            if abs(z) > 2.5 and i + 1 < len(s):
                side = -int(np.sign(z))
                ent = o[i + 1]
                st = ent - side * 1.25 * tr30[i]
                ex, how = walk(s, i + 1, side, ent, st, mean[i], 960)
                out["X1 stretch fade"].append((k, side, trade(side, ent, ex, how, cost), (ent, st, i + 1, mean[i])))
                break
        i1030 = np.flatnonzero(m >= 630)[0]
        side = -int(np.sign(o[i1030] - o[0]))
        if side:
            ex, how = walk(s, i1030, side, o[i1030], None, None, 960)
            out["R1 first-hour reversal"].append((k, side, trade(side, o[i1030], ex, how, cost), (o[i1030], None, i1030, None)))
        prev = k
    return out


# ------------------------------------------------------------------ gold rules
def rules_gold(df, cost):
    out = {"L1 Asia-range breakout": [], "L2 London 15m ORB": [], "L3 NY-open 15m ORB (gold)": []}
    m = df.index.hour * 60 + df.index.minute
    # trading day = NY date of the London session; Asia = previous day 19:00 .. 02:59
    td = (df.index + pd.Timedelta(hours=5)).normalize()            # 19:00 NY rolls into next trading day
    df = df.assign(m=m, td=td)
    for k, g in df.groupby("td"):
        mm = g["m"].values
        asia = g[(mm >= 19 * 60) | (mm < 180)]
        lon = g[(mm >= 180) & (mm < 660)]
        if len(asia) < 300 or len(lon) < 300:
            continue
        for name, rh, rl, sess, t_end in (
                ("L1 Asia-range breakout", asia["h"].max(), asia["l"].min(), lon, 660),
                ("L2 London 15m ORB", lon["h"].values[lon["m"].values < 195].max(), lon["l"].values[lon["m"].values < 195].min(),
                 lon[lon["m"] >= 195], 660)):
            h, l = sess["h"].values, sess["l"].values
            for i in range(len(sess)):
                up, dn = h[i] > rh, l[i] < rl
                if up and dn:
                    break
                if up or dn:
                    side = 1 if up else -1
                    ent = rh if up else rl
                    st = rl if up else rh
                    ex, how = walk(sess, i + 1, side, ent, st, None, t_end)
                    out[name].append((k, side, trade(side, ent, ex, how, cost), (ent, st, i + 1, None)))
                    break
        ny = g[(mm >= 570) & (mm < 960)]
        if len(ny) > 300:
            first = ny[ny["m"] < 585]
            rest = ny[ny["m"] >= 585]
            rh, rl = first["h"].max(), first["l"].min()
            h, l = rest["h"].values, rest["l"].values
            for i in range(len(rest)):
                up, dn = h[i] > rh, l[i] < rl
                if up and dn:
                    break
                if up or dn:
                    side = 1 if up else -1
                    ent, st = (rh, rl) if up else (rl, rh)
                    ex, how = walk(rest, i + 1, side, ent, st, None, 960)
                    out["L3 NY-open 15m ORB (gold)"].append((k, side, trade(side, ent, ex, how, cost), (ent, st, i + 1, None)))
                    break
    return out


# ------------------------------------------------------------------ evaluation
def pf(r):
    r = np.asarray(r)
    return r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else float("inf")


def twin_p(tr):
    """Same entries and exits, direction flipped at random (sign-flip test on the gross move), cost kept.
    Approximate for stop exits (a flipped stop trade is treated as the mirror move) - a control, not a sim."""
    g = np.array([x[2][1] for x in tr])
    c = np.array([x[2][2] for x in tr])
    actual = (g - c).mean()
    s = RNG.choice([-1, 1], (2000, len(g)))
    return float(((s * g - c).mean(1) >= actual).mean())


def report(name, tr, extra=""):
    r = np.array([x[2][0] for x in tr])
    if len(r) < 20:
        print(f"  {name:28s} n={len(r)} too few"); return False
    h = len(r) // 2
    a, b = r[:h], r[h:]
    p = twin_p(tr)
    ok = len(a) >= 100 and len(b) >= 100 and pf(a) >= 1.15 and pf(b) >= 1.15 and p < 0.005
    yrs = (tr[-1][0] - tr[0][0]).days / 365.25
    print(f"  {name:28s} n={len(r):5d} ({len(r)/max(yrs,0.1):4.0f}/yr) win {np.mean(r>0):4.0%} avg {r.mean()*1e4:+6.2f}bp "
          f"PF {pf(a):.2f}/{pf(b):.2f} p={p:.3f} {'PASS' if ok else 'fail'} {extra}")
    return ok


if __name__ == "__main__":
    res = {}
    for sym in ("US500", "USTEC", "US30"):
        df, cost = load_index(sym)
        print(f"\n{sym} M1 {df.index[0].date()} -> {df.index[-1].date()}  cost {cost:.2f} pts "
              f"({cost / df['c'].median() * 1e4:.2f} bp)")
        res[sym] = rules_index(days(df), cost)
        for nm, tr in res[sym].items():
            report(nm, tr)
    print("\nconfirmation across indices (PF full sample):")
    for nm in res["US500"]:
        print(f"  {nm:28s} " + "  ".join(f"{s} {pf([x[2][0] for x in res[s][nm]]):.2f}" for s in res))
    print("\nGOLD (histdata M1 2010-2026, NY clock)")
    gdf, gcost = load_gold()
    for nm, tr in rules_gold(gdf, gcost).items():
        report(nm, tr)
