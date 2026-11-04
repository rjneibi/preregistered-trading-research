"""Audit of the four strategy PASS results. Independent numpy rewrite of each rule, compared trade by trade with the original code,
then the statistics that no earlier report ran: DSR with the ledger count, PBO, block bootstrap, MinTRL, benchmarks, top-5 removal, years.
Parameters are the frozen ones. The neighbourhood grids below are reporting only: nothing here picks a variant."""
import itertools
import json
import math
import os
import sys

import numpy as np
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(HERE, "..", "_copy", "rs_recorded", "research"))
DD = "@GANN_ROOT@/research/cross_market/data"
D2 = "@GANN_ROOT@/research/cross_market/data_edge"
FIN = 0.05 / 365
LEDGER_N = 114500
rng = np.random.default_rng(20261031)


def load(sym):
    for d in (DD, D2):
        p = f"{d}/{sym}_D1.npz"
        if os.path.exists(p):
            z = np.load(p)
            t = z["t"].astype(np.int64)
            _, u = np.unique(t[::-1], return_index=True)
            k = np.sort(len(t) - 1 - u)
            k = k[np.argsort(t[k], kind="stable")]
            pos = z["sp"][z["sp"] > 0]
            sp = 1.5 * float(np.median(pos)) if len(pos) else 0.0
            return dict(t=t[k], o=z["o"][k].astype(float), h=z["h"][k].astype(float), l=z["l"][k].astype(float), c=z["c"][k].astype(float), sp=sp)
    raise FileNotFoundError(sym)


def sma(x, n):
    c = np.cumsum(np.insert(x, 0, 0.0))
    out = np.full(len(x), np.nan)
    out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def rsi2(c):
    """Adjusted exponential average, alpha 0.5, as the original's ewm default, written as a recursion."""
    d = np.diff(c, prepend=np.nan)
    a = 0.5
    s_u = s_d = w = 0.0
    out = np.full(len(c), np.nan)
    for i in range(1, len(c)):
        s_u = max(d[i], 0.0) + (1 - a) * s_u
        s_d = max(-d[i], 0.0) + (1 - a) * s_d
        w = 1.0 + (1 - a) * w
        u, v = s_u / w, s_d / w
        out[i] = 100 - 100 / (1 + u / (v if v != 0 else 1e-12))
    return out


def a1(m, thr=10, ex=5, maxd=10, trend=200, next_open=True, sp_mult=1.0, fin=FIN, floor=False):
    c, o, t = m["c"], m["o"], m["t"]
    sp = m["sp"]
    if sp == 0 or floor:
        sp = max(sp, 0.0002 * float(np.median(c)))
    sp *= sp_mult
    r, st_, mt = rsi2(c), sma(c, trend), sma(c, ex)
    n, i, out = len(c), trend, []
    while i < n - 2:
        if r[i] < thr and c[i] > st_[i]:
            j = i + 1
            while j < n - 2 and j - i < maxd and c[j] <= mt[j]:
                j += 1
            a, b = (o[i + 1], o[j + 1]) if next_open else (c[i], c[j])
            ta, tb = (t[i + 1], t[j + 1]) if next_open else (t[i], t[j])
            nights = int(tb // 86400 - ta // 86400)
            out.append((int(t[i]), a, b, b / a - 1 - sp / a - nights * fin, j - i))
            i = j + 1
        else:
            i += 1
    return out


def ibs_rule(m, thr=0.2, maxh=15, sp_mult=1.0):
    c, o, h, l, t = m["c"], m["o"], m["h"], m["l"], m["t"]
    sp = m["sp"] if m["sp"] else 0.0002 * float(np.median(c))
    sp *= sp_mult
    with np.errstate(invalid="ignore", divide="ignore"):
        ibs = np.where(h > l, (c - l) / (h - l), np.nan)
    n, i, out = len(c), 0, []
    while i < n - 2:
        if i >= 252 and ibs[i] < thr:
            j = i + 1
            while j < n - 2 and j - i < maxh and not (ibs[j] > 0.8 or c[j] > h[j - 1]):
                j += 1
            a, b = o[i + 1], o[j + 1]
            nights = int(t[j + 1] // 86400 - t[i + 1] // 86400)
            out.append((int(t[i]), a, b, b / a - 1 - sp / a - nights * FIN, j - i))
            i = j + 1
        else:
            i += 1
    return out


def ret(tr):
    return np.array([x[3] for x in tr])


def pf(r):
    r = np.asarray(r)
    return float(r[r > 0].sum() / -r[r < 0].sum()) if (r < 0).any() else float("inf")


def block_boot(r, f, b=5, k=10000):
    r = np.asarray(r)
    n = len(r)
    m = int(np.ceil(n / b))
    s = rng.integers(0, n, (k, m))
    idx = (s[:, :, None] + np.arange(b)) % n
    x = r[idx.reshape(k, -1)[:, :n]]
    v = np.array([f(q) for q in x])
    return [round(float(np.quantile(v, q)), 4) for q in (0.025, 0.975)]


def dsr(r, trials):
    """Bailey and Lopez de Prado. Under the null each trial's per-period Sharpe has variance about 1/T."""
    r = np.asarray(r)
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = st.skew(r), st.kurtosis(r, fisher=False)
    em = 0.5772156649015329
    v = 1.0 / T
    sr0 = math.sqrt(v) * ((1 - em) * st.norm.ppf(1 - 1 / trials) + em * st.norm.ppf(1 - 1 / (trials * math.e)))
    den = math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr * sr)
    return round(float(st.norm.cdf((sr - sr0) * math.sqrt(T - 1) / den)), 4), round(float(sr0), 4)


def mintrl(r, target=0.0, alpha=0.05):
    r = np.asarray(r)
    sr = r.mean() / r.std(ddof=1)
    if sr <= target:
        return None
    g3, g4 = st.skew(r), st.kurtosis(r, fisher=False)
    return int(math.ceil(1 + (1 - g3 * sr + (g4 - 1) / 4 * sr * sr) * (st.norm.ppf(1 - alpha) / (sr - target)) ** 2))


def cscv(M, S=10):
    """M: periods by variants. Fraction of splits whose in-sample best falls at or below the out-of-sample median."""
    T = M.shape[0] - M.shape[0] % S
    blocks = np.array_split(np.arange(T), S)
    lam = []
    for c in itertools.combinations(range(S), S // 2):
        a = np.concatenate([blocks[i] for i in c])
        b = np.concatenate([blocks[i] for i in range(S) if i not in c])
        sa = M[a].mean(0) / (M[a].std(0, ddof=1) + 1e-12)
        sb = M[b].mean(0) / (M[b].std(0, ddof=1) + 1e-12)
        best = int(np.argmax(sa))
        w = (st.rankdata(sb)[best]) / (M.shape[1] + 1)
        lam.append(math.log(w / (1 - w)))
    lam = np.array(lam)
    return dict(pbo=round(float((lam <= 0).mean()), 3), splits=len(lam), variants=M.shape[1])


def monthly(tr, months):
    key = np.array([str(np.datetime64(x[0], "s"))[:7] for x in tr]) if len(tr) else np.array([])
    r = ret(tr) if len(tr) else np.array([])
    return np.array([r[key == m].sum() for m in months])


def report(name, tr, m, trials, sp_fn, variants=None):
    r = ret(tr)
    years = {}
    for x in tr:
        years.setdefault(str(np.datetime64(x[0], "s"))[:4], []).append(x[3])
    h = len(r) // 2
    srt = np.sort(r)
    bh = m["c"][-1] / m["c"][252] - 1
    held = sum(x[4] for x in tr)
    bars = len(m["c"]) - 252
    out = dict(n=len(r), win=round(float((r > 0).mean()), 3), avg_pct=round(float(r.mean() * 100), 3), pf=round(pf(r), 3), pf_h1=round(pf(r[:h]), 3), pf_h2=round(pf(r[h:]), 3),
               total_compounded_pct=round(float((np.prod(1 + r) - 1) * 100), 1), exposure=round(held / bars, 3), buy_hold_pct=round(float(bh * 100), 1),
               annual_rule_pct=None, pf_without_top5=round(pf(srt[:-5]), 3), avg_without_top5_pct=round(float(srt[:-5].mean() * 100), 3),
               share_of_sum_from_top5=round(float(srt[-5:].sum() / r.sum()), 3), boot_mean_ci=block_boot(r, np.mean), boot_pf_ci=block_boot(r, pf),
               psr0=round(float(st.norm.cdf((r.mean() / r.std(ddof=1)) * math.sqrt(len(r) - 1) / math.sqrt(1 - st.skew(r) * r.mean() / r.std(ddof=1) + (st.kurtosis(r, fisher=False) - 1) / 4 * (r.mean() / r.std(ddof=1)) ** 2))), 4),
               dsr={str(k): dsr(r, k) for k in trials}, mintrl_trades=mintrl(r), by_year={y: dict(n=len(v), sum_pct=round(float(np.sum(v) * 100), 1), pf=round(pf(v), 2) if pf(v) != float("inf") else "inf") for y, v in sorted(years.items())},
               cost_2x=dict(pf=round(pf(ret(sp_fn(2.0))), 3)), cost_3x=dict(pf=round(pf(ret(sp_fn(3.0))), 3)))
    yrs = (m["t"][-1] - m["t"][252]) / (365.25 * 86400)
    out["annual_rule_pct"] = round(float((np.prod(1 + r) ** (1 / yrs) - 1) * 100), 2)
    out["buy_hold_annual_pct"] = round(float(((1 + bh) ** (1 / yrs) - 1) * 100), 2)
    if variants is not None:
        months = sorted({str(np.datetime64(int(u), "s"))[:7] for u in m["t"]})
        M = np.column_stack([monthly(v, months) for v in variants])
        out["cscv"] = cscv(M)
    return out


def compare(mine, theirs):
    a = np.array([x[3] for x in mine])
    b = np.asarray(theirs, float)
    return dict(n_mine=len(a), n_orig=len(b), same_count=len(a) == len(b), max_abs_diff=float(np.abs(a - b).max()) if len(a) == len(b) else None, pct_within_half_pct_of_each=None)


def main():
    sys.path[:0] = [SB + "/cross_market", SB + "/tune1"]
    import a1_stress
    import swing_lab
    import edge_lab
    import tune_dip
    rep = {}
    us = load("US500")
    mine = a1(us)
    orig = a1_stress.rsi2_trades("US500", next_open=True)
    rep["XM-1-A1 engine check"] = compare(mine, orig.values)
    close = a1(us, next_open=False)
    orig2 = a1_stress.rsi2_trades("US500", next_open=False)
    rep["XM-1-A1 close-fill engine check"] = compare(close, orig2.values)
    grid = [a1(us, thr=t, ex=e) for t, e in itertools.product((5, 10, 15, 25), (3, 5, 10))]
    rep["XM-1-A1"] = report("A1", mine, us, (12, 100, 2000, LEDGER_N), lambda k: a1(us, sp_mult=k), grid)
    rep["XM-1-A1 signal-close fill"] = dict(n=len(close), pf=round(pf(ret(close)), 3), note="the next-open row is the tradable one")
    print(json.dumps(rep["XM-1-A1 engine check"]), json.dumps(rep["XM-1-A1"])[:1400], flush=True)

    d, sp = swing_lab.prep("US500")
    side, sig, ex = swing_lab.rule("MR2", d)
    o2 = swing_lab.run(d, sp, side, sig, ex)
    m2 = ibs_rule(us)
    rep["SW-1 engine check"] = compare(m2, [x[1] for x in o2])
    fam = []
    for nm in swing_lab.RULES:
        s_, g_, e_ = swing_lab.rule(nm, d)
        tr = swing_lab.run(d, sp, s_, g_, e_)
        fam.append([(int(t.timestamp()), 0, 0, x, h) for t, x, h in tr])
    rep["SW-1"] = report("MR2", m2, us, (10, 100, 2000, LEDGER_N), lambda k: ibs_rule(us, sp_mult=k), fam)
    print(json.dumps(rep["SW-1 engine check"]), json.dumps(rep["SW-1"])[:1400], flush=True)

    # F6: daily returns, numpy only
    cl = edge_lab.crypto_close()
    dates, X = cl.index, cl.values
    def f6(n=50, lag=1, cost=0.001):
        T, K = X.shape
        with np.errstate(invalid="ignore", divide="ignore"):
            r = X[1:] / X[:-1] - 1
            r = np.vstack([np.full(K, np.nan), r])
            vol = np.full((T, K), np.nan)
            ma = np.full((T, K), np.nan)
            for k in range(K):
                for i in range(T):
                    w = r[max(0, i - 59): i + 1, k]
                    if i >= 59 and np.isfinite(w).all():
                        vol[i, k] = w.std(ddof=1)
                    w2 = X[max(0, i - n + 1): i + 1, k]
                    if i >= n - 1 and np.isfinite(w2).all():
                        ma[i, k] = w2.mean()
            sig = np.where(np.isfinite(ma), (X > ma).astype(float), np.nan)
            w = np.minimum(sig * (0.02 / vol), 1.0)
            cnt = np.isfinite(w).sum(1).astype(float)
            cnt[cnt == 0] = np.nan
            w = w / cnt[:, None]
            pos = np.vstack([np.full((lag, K), np.nan), w[:-lag]])
            dp = np.abs(np.diff(pos, axis=0, prepend=np.nan))
            out = np.nansum(pos * r, axis=1) - np.nansum(dp, axis=1) * cost
            live = np.isfinite(pos).any(1)
        return out[live], dates[live]
    s, ds = f6()
    orig_s, _ = edge_lab.f6()
    a = s
    b = orig_s.reindex(ds).values
    rep["EDGE-1-F6 engine check"] = dict(days_mine=len(a), days_orig=len(orig_s), max_abs_diff=float(np.nanmax(np.abs(a - b))), corr=float(np.corrcoef(a, np.nan_to_num(b))[0, 1]))
    srd = s.mean() / s.std(ddof=1)
    srt = np.sort(s)
    yrs = {}
    for t, x in zip(ds, s):
        yrs.setdefault(str(t.year), []).append(x)
    M = np.column_stack([f6(n=n)[0][-len(s) + 200:] if False else f6(n=n)[0][-(len(s) - 200):] for n in (20, 30, 50, 100, 200)])
    rep["EDGE-1-F6"] = dict(days=len(s), sharpe_ann=round(float(srd * math.sqrt(365)), 2), psr0=round(float(st.norm.cdf(srd * math.sqrt(len(s) - 1) / math.sqrt(1 - st.skew(s) * srd + (st.kurtosis(s, fisher=False) - 1) / 4 * srd * srd))), 4),
                            dsr={str(k): dsr(s, k) for k in (5, 100, 2000, LEDGER_N)}, mintrl_days=mintrl(s), boot_mean_ci=block_boot(s, np.mean, b=20, k=5000),
                            drop_top5_days_ann_sharpe=round(float(srt[:-5].mean() / srt[:-5].std(ddof=1) * math.sqrt(365)), 2), by_year={y: round(float((np.prod(1 + np.array(v)) - 1) * 100), 1) for y, v in sorted(yrs.items())},
                            cost_3x_sharpe=round(float(f6(cost=0.003)[0].mean() / f6(cost=0.003)[0].std(ddof=1) * math.sqrt(365)), 2), cscv=cscv(M, S=10))
    print(json.dumps(rep["EDGE-1-F6 engine check"]), json.dumps(rep["EDGE-1-F6"])[:1100], flush=True)

    # TUNE-1 live baseline: the same RSI2 rule, sealed markets
    k = tune_dip
    t0 = np.datetime64("2023-10-13").astype("datetime64[s]").astype(np.int64)
    pool_t, pool_m, per = [], [], {}
    for sym in k.HOLD_T:
        m = load(sym)
        sp = max(m["sp"], 0.0002 * float(np.median(m["c"])))
        m2_ = dict(m, sp=sp)
        tr = [x for x in a1(m2_) if x[0] >= int(t0)]
        per[sym] = len(tr)
        pool_t += tr
    for sym in k.HOLD_M:
        m = load(sym)
        sp = max(m["sp"], 0.0002 * float(np.median(m["c"])))
        tr = a1(dict(m, sp=sp))
        pool_m += tr
    rep["TUNE-1-DIP independent"] = dict(hold_t=dict(n=len(pool_t), pf=round(pf(ret(pool_t)), 3), per=per), hold_m=dict(n=len(pool_m), pf=round(pf(ret(pool_m)), 3)), hold_t_dsr={str(q): dsr(ret(pool_t), q) for q in (9, 2000, LEDGER_N)}, hold_m_dsr={str(q): dsr(ret(pool_m), q) for q in (9, 2000, LEDGER_N)}, mintrl_t=mintrl(ret(pool_t)))
    print(json.dumps(rep["TUNE-1-DIP independent"]), flush=True)
    json.dump(rep, open(os.path.join(HERE, "pass_audit.json"), "w"), indent=1, default=str)


main()
