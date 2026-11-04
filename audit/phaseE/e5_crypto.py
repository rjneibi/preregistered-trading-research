"""E5 crypto cost realism, per prereg/E5-CRYPTO.md. Rules come from sandboxed crypto_lab, swing_lab and edge_lab unchanged. Only costs and the universe differ."""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
SB = os.path.abspath(os.path.join(HERE, "..", "_copy", "rs_recorded", "research"))
sys.path[:0] = [HERE, SB + "/cross_market"]
import crypto_lab as C
import edge_lab as E
import swing_lab as S
import xm_lab as X

PUB = os.path.join(HERE, "..", "_copy", "data", "public")
COINS = E.COINS
DEAD = "LUNA FTT UST SRM WAVES MITH BTS ANC".split()
TIERS = {"spot_vip0": 0.001, "spot_bnb": 0.00075, "perp": 0.0005}


def slip(c):
    return 0.0002 if c in ("BTC", "ETH") else 0.001


def funding():
    d = {}
    for c in COINS:
        rows = json.load(open(os.path.join(PUB, f"funding_{c}.json")))
        if rows:
            a = np.array(rows, float)
            d[c] = pd.Series(a[:, 1], index=pd.to_datetime(a[:, 0], unit="ms")).resample("D").sum()
    return pd.DataFrame(d)


FUND = funding()


def sharpe(r):
    return float(r.mean() / r.std() * np.sqrt(365)) if r.std() > 0 else 0.0


def stats(r):
    cg, dd, sh, mar = C.stats(r)
    return dict(sharpe=round(float(sh), 3), mar=round(float(mar), 3), cagr=round(float(cg), 3), dd=round(float(dd), 3))


TWIN = {"A1 SMA20": lambda c: c > c.rolling(20).mean(), "A1 SMA50": lambda c: c > c.rolling(50).mean(), "A1 SMA100": lambda c: c > c.rolling(100).mean(), "A2 TSMOM30": lambda c: c / c.shift(30) > 1}


def runs(v):
    out, s = [], 0
    for k in range(1, len(v) + 1):
        if k == len(v) or v[k] != v[s]:
            out.append((v[s], k - s))
            s = k
    return out


def twin(name, tier, draws=1000):
    """Run-shuffle twin of crypto_twin.py, CR-1b's gate of p < 0.0125 on both halves and both coins, at this tier's costs. Rules without a CR-1b row keep the first gate only."""
    rng = np.random.default_rng(3)
    fee = TIERS[tier]
    ps = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        co = sym[:3]
        d = C.closes(sym)
        pos = TWIN[name](d["c"]).astype(float)
        fund = FUND[co].reindex(d.index).fillna(0.0).values if tier == "perp" else np.zeros(len(d))
        cost = fee + slip(co)
        o = d["o"].values
        roo = np.append(o[1:] / o[:-1] - 1, np.nan)
        for k, (a, b) in enumerate(C.HALVES):
            m = (d.index >= a) & (d.index < b)
            ph, r, f = pos.values[m], roo[m], fund[m]

            def sh(p):
                q = np.append(0.0, p[:-1])
                tr = np.abs(np.diff(q, prepend=0.0))
                x = q * r - tr * cost - q * f
                x = x[np.isfinite(x)]
                return x.mean() / x.std() * np.sqrt(365)

            real = sh(ph)
            R = runs(ph)
            tw = np.array([sh(np.concatenate([np.full(R[i][1], R[i][0]) for i in rng.permutation(len(R))])) for _ in range(draws)])
            ps[f"{co}_h{k}"] = round(float((tw >= real).mean()), 4)
    return ps


def trend(tier):
    fee = TIERS[tier]
    res = {}
    for sym in ("BTCUSDT", "ETHUSDT"):
        co = sym[:3]
        d = C.closes(sym)
        c = d["c"]
        rules = {f"A1 SMA{n}": (c > c.rolling(n).mean()).astype(float) for n in (20, 50, 100, 200)}
        rules["A2 TSMOM30"] = (c / c.shift(30) > 1).astype(float)
        hi, lo = d["h"].rolling(20).max().shift(1), d["l"].rolling(10).min().shift(1)
        st, pos = 0.0, []
        for x, h_, l_ in zip(c, hi, lo):
            st = 1.0 if (st == 0 and x > h_) else (0.0 if (st == 1 and x < l_) else st)
            pos.append(st)
        rules["A3 Donchian20/10"] = pd.Series(pos, index=c.index)
        rules["buy&hold"] = pd.Series(1.0, index=c.index)
        o = d["o"]
        roo = o.shift(-1) / o - 1
        fund = FUND[co].reindex(d.index) if tier == "perp" else None
        fees = pd.Series(fee, index=d.index) if fund is None else pd.Series(np.where(fund.notna(), fee, TIERS["spot_vip0"]), index=d.index)
        fund = 0.0 if fund is None else fund.fillna(0.0)
        for name, p in rules.items():
            q = p.shift(1).fillna(0)
            tr = q.diff().abs().fillna(q.abs())
            r = (q * roo - tr * (fees + slip(co)) - q * fund).dropna()
            for k, (a, b) in enumerate(C.HALVES):
                res[f"{co} {name} {k}"] = stats(r[(r.index >= a) & (r.index < b)])
    out = {}
    names = sorted({k.split(" ", 1)[1].rsplit(" ", 1)[0] for k in res} - {"buy&hold"})
    for n in names:
        ok = all(res[f"{s} {n} {k}"]["sharpe"] > res[f"{s} buy&hold {k}"]["sharpe"] and res[f"{s} {n} {k}"]["mar"] > res[f"{s} buy&hold {k}"]["mar"] for s in ("BTC", "ETH") for k in (0, 1))
        out[n] = dict(beats_bh_both_halves=bool(ok), **{f"{s}_h{k}": res[f"{s} {n} {k}"]["sharpe"] for s in ("BTC", "ETH") for k in (0, 1)})
        if n in TWIN:
            ps = twin(n, tier)
            out[n]["twin_p"] = ps
            out[n]["passes_original_gate"] = bool(ok and all(v < 0.0125 for v in ps.values()))
        else:
            out[n]["passes_original_gate"] = False
    out["buy&hold"] = {f"{s}_h{k}": res[f"{s} buy&hold {k}"]["sharpe"] for s in ("BTC", "ETH") for k in (0, 1)}
    return out


def swing(tier):
    fee = TIERS[tier]
    data = {}
    for s in ("BTCUSDT", "ETHUSDT"):
        d, _ = S.prep(s)
        data[s] = (d, 2 * (fee + slip(s[:3])) * d["c"].median())
    res = {}
    for nm in S.RULES:
        if nm == "MR6":
            continue
        out = {}
        for s in ("BTCUSDT", "ETHUSDT"):
            d, sp = data[s]
            side, sig, ex = S.rule(nm, d)
            tr = S.run(d, sp, side, sig, ex, fin_l=0.0)
            if tier == "perp":
                f = FUND[s[:3]].fillna(0.0)
                tr = [(t, x - float(f[(f.index >= t.normalize()) & (f.index < t.normalize() + pd.Timedelta(days=int(h) + 1))].sum()), h) for t, x, h in tr]
            r = np.array([x for _, x, _ in tr])
            t = np.array([x[0] for x in tr])
            out[s[:3] + "_pf_all"] = round(float(X.pf(r)), 3) if len(r) else 0.0
            if len(r) == 0:
                out[s[:3]] = dict(n=0)
                continue
            a, b = r[t < pd.Timestamp("2022-01-01")], r[t >= pd.Timestamp("2022-01-01")]
            out[s[:3]] = dict(n=len(r), pf_h1=round(float(X.pf(a)), 3), pf_h2=round(float(X.pf(b)), 3), na=len(a), nb=len(b))
            if s == "BTCUSDT":
                out["p"] = round(float(S.twin_p(d, sp, side, tr)), 4)
        b_ = out["BTC"]
        out["passes_original_gate"] = bool(b_.get("n", 0) and b_["na"] >= 30 and b_["nb"] >= 30 and b_["pf_h1"] >= 1.15 and b_["pf_h2"] >= 1.15 and out.get("p", 1) < 0.005 and out["ETH_pf_all"] > 1)
        out["sample"] = "INSUFFICIENT SAMPLE" if b_.get("n", 0) < 100 else "ok"
        res[nm] = out
    return res


def f6_run(close, tier, costs=None, fund=None):
    r = close.pct_change(fill_method=None)
    vol = r.rolling(60).std()
    ma = close.rolling(50).mean()
    sig = (close > ma).astype(float).where(ma.notna())

    def run(sg):
        w = (sg * (0.02 / vol)).clip(upper=1.0)
        n = w.notna().sum(axis=1).replace(0, np.nan)
        w = w.div(n, axis=0)
        pos = w.shift(1)
        c = pd.Series({k: TIERS[tier] + slip(k) for k in close}) if costs is None else pd.Series(costs)
        cf = pd.DataFrame({k: c[k] for k in close}, index=pos.index)
        if fund is not None:
            sp = pd.DataFrame({k: TIERS["spot_vip0"] + slip(k) for k in close}, index=pos.index)
            cf = cf.where(fund.reindex(index=pos.index, columns=pos.columns).notna(), sp)
        out = (pos * r).sum(axis=1) - (pos.diff().abs() * cf).sum(axis=1)
        if fund is not None:
            out = out - (pos * fund.reindex(index=pos.index, columns=pos.columns).fillna(0.0)).sum(axis=1)
        return out[pos.notna().any(axis=1)]

    return run(sig), run(sig.notna().astype(float).where(sig.notna()))


def f6_report(s, b):
    h = pd.Timestamp("2022-07-01")
    return dict(sharpe=round(sharpe(s), 3), bh=round(sharpe(b), 3), dd=round(float(((1 + s).cumprod() / (1 + s).cumprod().cummax() - 1).min()), 3), bh_dd=round(float(((1 + b).cumprod() / (1 + b).cumprod().cummax() - 1).min()), 3),
                h1=round(sharpe(s[s.index < h]), 3), h2=round(sharpe(s[s.index >= h]), 3), bh_h1=round(sharpe(b[b.index < h]), 3), bh_h2=round(sharpe(b[b.index >= h]), 3))


def dead_panel(base):
    add, notes = {}, {}
    end = base.index.max()
    for c in DEAD:
        rows = json.load(open(os.path.join(PUB, f"kl_{c}.json")))
        if not rows:
            notes[c] = "unavailable"
            continue
        a = np.array(rows, float)
        s = pd.Series(a[:, 4], index=pd.to_datetime(a[:, 0], unit="ms"))
        gap = np.flatnonzero(np.diff(s.index.values).astype("timedelta64[D]").astype(int) > 3)
        cut = "first run before a gap over 3 days" if len(gap) else "none"
        if len(gap):
            s = s.iloc[:gap[0] + 1]
        last = s.index[-1]
        delist = last < end - pd.Timedelta(days=7)
        if delist:
            s.loc[last + pd.Timedelta(days=1)] = s.iloc[-1] * 0.5
        add[c] = s
        notes[c] = dict(first=str(s.index[0].date()), last=str(last.date()), days=len(s), delisted=bool(delist), cut=cut)
    return add, notes


base = E.crypto_close()
base.index = pd.to_datetime(base.index).normalize()
rep = {}
s0, b0 = f6_run(base, "spot_vip0", costs={k: 0.001 for k in base})
rep["F6_check_original_cost"] = f6_report(s0, b0)
rep["CR1_trend"], rep["CR1_swing"], rep["F6"] = {}, {}, {}
for tier in TIERS:
    rep["CR1_trend"][tier] = trend(tier)
    rep["CR1_swing"][tier] = swing(tier)
    fund = FUND if tier == "perp" else None
    s, b = f6_run(base, tier, fund=fund)
    rep["F6"][tier] = f6_report(s, b)
    print(tier, rep["F6"][tier], flush=True)
add, notes = dead_panel(base)
rep["survivorship_notes"] = notes
w = pd.concat([base, pd.DataFrame(add)], axis=1).sort_index()
s, b = f6_run(w, "spot_vip0")
rep["F6_survivorship_spot_vip0"] = f6_report(s, b)
rep["F6_coin_days_added"] = int(pd.DataFrame(add).notna().sum().sum())
json.dump(rep, open(os.path.join(HERE, "e5_result.json"), "w"), indent=1, default=str)
print(json.dumps({k: rep[k] for k in ("F6_check_original_cost", "F6", "F6_survivorship_spot_vip0", "survivorship_notes")}, indent=0, default=str))
print({t: [k for k, v in rep["CR1_trend"][t].items() if v.get("passes_original_gate")] for t in TIERS}, {t: [k for k, v in rep["CR1_swing"][t].items() if v.get("passes_original_gate")] for t in TIERS})
