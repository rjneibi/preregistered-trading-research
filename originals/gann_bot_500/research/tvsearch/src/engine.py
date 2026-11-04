"""Bar-by-bar trade simulator (one position at a time) and the metrics every run reports.

Timing: a signal is read on the CLOSE of bar s and filled at the OPEN of bar s+1 - no lookahead.
Prices: XAU bars are BID - a long buys at ask (o+sp) and exits on bid; a short sells at bid and its stop/target/exit
are watched on ask (bar + sp). SPY/QQQ bars are trades (sp = 0); slippage per side and commission are added.
Inside one bar: if stop and target are both touchable, the STOP is assumed (worse outcome). A bar that OPENS beyond
the stop/target fills at that open (gap).
Exit spec (dict):
  tp / sl        fixed $ distance from entry           tp_atr / sl_atr  multiples of ATR(14) at the signal bar
  tp_r           target = tp_r x the stop distance      trail_atr        trailing stop, ATR multiple, from best price
  opp            exit at the next open after an opposite signal (and that signal opens the reverse trade = SAR)
  eos            flat at the close of the session's last bar; no entry that would fill in the next session
  tbars          time stop: flat at the close of the N-th bar held
"""
import numpy as np

COST = {"XAU": dict(slip=0.0, comm=0.0), "SPY": dict(slip=0.01, comm=0.0), "QQQ": dict(slip=0.01, comm=0.0)}


def next_idx(mask):
    N = len(mask)
    idx = np.where(mask, np.arange(N), N)
    return np.minimum.accumulate(idx[::-1])[::-1]


def simulate(D, L, S, ex, cost, atr=None):
    N = D["N"]; o, h, l, c, sp = D["o"], D["h"], D["l"], D["c"], D["sp"]
    sid, slast = D["sid"], D["sess_last"]
    L = np.asarray(L, bool); S = np.asarray(S, bool)
    bars = np.flatnonzero(L ^ S)
    nL, nS = next_idx(L), next_idx(S)
    tp, sl, tpa, sla, tpr, tra = (ex.get(k) for k in ("tp", "sl", "tp_atr", "sl_atr", "tp_r", "trail_atr"))
    opp, eos, tb = ex.get("opp", False), ex.get("eos", False), int(ex.get("tbars", 0) or 0)
    fee = 2 * cost["slip"] + cost["comm"]
    E, X, Dn, P, R, TPh = [], [], [], [], [], []
    pos_from = 0
    nb = len(bars)
    while True:
        q = np.searchsorted(bars, pos_from, "left")
        if q >= nb:
            break
        s = bars[q]; k = s + 1
        if k >= N:
            break
        if eos and sid[k] != sid[s]:
            pos_from = s + 1; continue
        d = 1 if L[s] else -1
        a = atr[s] if atr is not None else np.nan
        sld = sl if sl else (sla * a if sla else None)
        if sld is not None and not sld > 0:
            pos_from = s + 1; continue
        tpd = tp if tp else (tpa * a if tpa else (tpr * sld if (tpr and sld) else None))
        trd = tra * a if tra else None
        if trd is not None and not trd > 0:
            pos_from = s + 1; continue
        shift = 0.0 if d == 1 else 1.0
        entry = o[k] + sp[k] if d == 1 else o[k]
        end, why = N - 1, "end"
        if eos and slast[k] < end:
            end, why = slast[k], "eos"
        if tb and k + tb - 1 < end:
            end, why = k + tb - 1, "time"
        j_opp = -1
        if opp:
            j = (nS if d == 1 else nL)[k]
            if j < end:
                end, why, j_opp = j, "opp", j
        sl_px = entry - d * sld if sld else None
        tp_px = entry + d * tpd if tpd else None
        seg = slice(k, end + 1)
        OO = o[seg] + shift * sp[seg]; HH = h[seg] + shift * sp[seg]; LO = l[seg] + shift * sp[seg]
        fav, adv = (HH, LO) if d == 1 else (LO, HH)
        hit, m, px = None, -1, None
        if trd is None:
            hs = (d * (adv - sl_px) <= 0) if sl_px is not None else np.zeros(len(OO), bool)
            ht = (d * (fav - tp_px) >= 0) if tp_px is not None else np.zeros(len(OO), bool)
            any_ = hs | ht
            if any_.any():
                m = int(np.argmax(any_))
                if hs[m]:
                    hit, px = "sl", (OO[m] if m > 0 and d * (OO[m] - sl_px) <= 0 else sl_px)
                else:
                    hit, px = "tp", (OO[m] if m > 0 and d * (OO[m] - tp_px) >= 0 else tp_px)
        else:
            stop = sl_px; best = entry
            for m in range(len(OO)):
                if stop is not None and d * (adv[m] - stop) <= 0:
                    hit, px = "sl", (OO[m] if m > 0 and d * (OO[m] - stop) <= 0 else stop); break
                if tp_px is not None and d * (fav[m] - tp_px) >= 0:
                    hit, px = "tp", (OO[m] if m > 0 and d * (OO[m] - tp_px) >= 0 else tp_px); break
                if d * (fav[m] - best) > 0:
                    best = fav[m]
                ts = best - d * trd
                if stop is None or d * (ts - stop) > 0:
                    stop = ts
            else:
                m = -1
        if hit is not None:
            xb = k + m; nxt = xb
        elif why == "opp" and j_opp + 1 < N:
            xb = j_opp + 1; px = o[xb] + shift * sp[xb]; hit = "opp"; nxt = j_opp
        else:
            xb = end; px = c[end] + shift * sp[end]; hit = why; nxt = end
        E.append(k); X.append(xb); Dn.append(d); P.append(d * (px - entry) - fee); R.append(hit); TPh.append(hit == "tp")
        pos_from = max(nxt, s + 1)
    return dict(e=np.array(E, int), x=np.array(X, int), d=np.array(Dn, int), pnl=np.array(P, float),
                why=np.array(R, object), tp=np.array(TPh, bool))


def subset(tr, D, t0=None, t1=None):
    t = D["t"][tr["e"]] if len(tr["e"]) else np.array([], int)
    m = np.ones(len(t), bool)
    if t0 is not None:
        m &= t >= t0
    if t1 is not None:
        m &= t < t1
    return {k: v[m] for k, v in tr.items()}


def maxdd(p):
    if not len(p):
        return 0.0
    c = np.cumsum(p)
    return float((np.maximum.accumulate(np.r_[0.0, c])[1:] - c).max())


def metrics(tr, D, t0=None, t1=None):
    tr = subset(tr, D, t0, t1)
    p = tr["pnl"]; n = len(p)
    t = D["t"]; msk = np.ones(len(t), bool)
    if t0 is not None:
        msk &= t >= t0
    if t1 is not None:
        msk &= t < t1
    sess = np.unique(D["sid"][msk])
    out = dict(n=n)
    if not msk.any():
        return out
    px0 = D["c"][np.flatnonzero(msk)[0]]
    w, ls = p[p > 0], p[p < 0]
    daily = np.zeros(len(sess))
    if n:
        ix = np.searchsorted(sess, D["sid"][tr["x"]])
        ok = (ix < len(sess))
        np.add.at(daily, ix[ok], p[ok])
    sd = daily.std(ddof=1) if len(daily) > 1 else 0.0
    dn = np.sqrt(np.mean(np.minimum(daily, 0) ** 2)) if len(daily) else 0.0
    streak = cur = 0
    for v in p:
        cur = cur + 1 if v < 0 else 0
        streak = max(streak, cur)
    hold = (tr["x"] - tr["e"] + 1) * (D["tf"] if D["tf"] != "D" else 1440)
    out.update(net=float(p.sum()), net_pct=float(100 * p.sum() / px0), win=float((p > 0).mean()) if n else np.nan,
               avg_win=float(w.mean()) if len(w) else 0.0, avg_loss=float(ls.mean()) if len(ls) else 0.0,
               pf=float(w.sum() / -ls.sum()) if len(ls) else (np.inf if len(w) else np.nan),
               exp=float(p.mean()) if n else np.nan, maxdd=maxdd(p),
               sharpe=float(daily.mean() / sd * np.sqrt(252)) if sd > 0 else np.nan,
               sortino=float(daily.mean() / dn * np.sqrt(252)) if dn > 0 else np.nan,
               lose_streak=int(streak), hold_min=float(hold.mean()) if n else np.nan,
               tp_rate=float(tr["tp"].mean()) if n else np.nan,
               exposure=float((tr["x"] - tr["e"] + 1).sum() / msk.sum()), days=int(len(sess)))
    return out
