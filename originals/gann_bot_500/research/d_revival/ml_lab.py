"""ML-1: can machine learning find an edge in gold's OWN price? (pre-declared, walk-forward)

Decision every H1 open, features from CLOSED bars only (H1, broker D1, H4 EMA). Label = triple
barrier on M1 from the H1 open: +1 ATR before -1 ATR within 24h (ties -> stop first).
Model: gradient-boosted trees (gbm.py, numpy; sklearn DLLs blocked), expanding walk-forward: train on all years before
the test year (with a 24h embargo), test years 2014..2026, never refit on test data.
Trade rule: long if p >= thr, short if p <= 1-thr, one position at a time, 1 ATR stop/target,
spread $0.35 charged in R (0.35/ATR).
PASS (fixed before the run): OOS AUC > 0.52, net PF >= 1.15 in 2014-19 AND 2020-26 with n >= 200
each, and beating a model trained on SHUFFLED labels.
"""
import datetime as dt

import numpy as np
from gbm import GBM, auc as roc_auc_score

import data
import sim

d = data.load()
T, O, H, L, C = d["t"], d["o"], d["h"], d["l"], d["c"]
H1, D1 = sim.Bars(d, 3600), sim.Bars(d, 86400)
SP = 0.35
HZ = 24 * 60


def ema(x, n):
    a, out, e = 2 / (n + 1), np.empty(len(x)), x[0]
    for i, v in enumerate(x):
        e += a * (v - e)
        out[i] = e
    return out


def build():
    c, h, l, o = H1.c, H1.h, H1.l, H1.o
    n = len(c)
    tr = np.r_[h[0] - l[0], np.maximum(h[1:] - l[1:], np.maximum(abs(h[1:] - c[:-1]), abs(l[1:] - c[:-1])))]
    atr = ema(tr, 27)               # ~Wilder 14
    atr100 = ema(tr, 199)
    e50h4 = ema(c, 50 * 4 * 2 - 1)  # ~H4 EMA50 on H1 closes
    e200 = ema(c, 399)
    d = np.diff(c, prepend=c[0])
    up, dn = ema(np.maximum(d, 0), 27), ema(np.maximum(-d, 0), 27)
    rsi = 100 - 100 / (1 + up / np.maximum(dn, 1e-9))
    di = np.searchsorted(D1.t, H1.t, side="right") - 1
    X, idx = [], []
    for k in range(400, n - 30):
        j = k - 1                   # last CLOSED H1 bar
        a = atr[j]
        if a <= 0:
            continue
        g = di[k] - 1               # previous broker day
        ph, pl, pc = D1.h[g], D1.l[g], D1.c[g]
        pp = (ph + pl + pc) / 3
        rng = ph - pl
        pivs = np.array([pp, pp + .382 * rng, pp + .618 * rng, pp + rng, pp - .382 * rng, pp - .618 * rng, pp - rng])
        m24h, m24l = h[j - 23:j + 1].max(), l[j - 23:j + 1].min()
        m120h, m120l = h[j - 119:j + 1].max(), l[j - 119:j + 1].min()
        u = sim.broker_to_utc(int(H1.t[k]))
        ud = dt.datetime.fromtimestamp(u, dt.timezone.utc)
        body = c[j] - o[j]
        r6h, r6l = h[j - 5:j + 1].max(), l[j - 5:j + 1].min()
        X.append([
            (c[j] - c[j - 1]) / a, (c[j] - c[j - 2]) / a, (c[j] - c[j - 4]) / a, (c[j] - c[j - 8]) / a,
            (c[j] - c[j - 24]) / a, (c[j] - c[j - 72]) / a, (c[j] - c[j - 240]) / a,
            a / c[j] * 1e3, a / atr100[j], (h[j] - l[j]) / a,
            (c[j] - m24l) / max(m24h - m24l, 1e-9), (c[j] - m120l) / max(m120h - m120l, 1e-9),
            (c[j] - ph) / a, (c[j] - pl) / a, (c[j] - pc) / a, np.min(np.abs(pivs - c[j])) / a,
            (c[j] - e50h4[j]) / a, (c[j] - e200[j]) / a, (e50h4[j] - e50h4[j - 24]) / a, rsi[j],
            body / max(h[j] - l[j], 1e-9), (h[j] - max(o[j], c[j])) / a, (min(o[j], c[j]) - l[j]) / a,
            float(r6h > ph and c[j] < ph), float(r6l < pl and c[j] > pl),
            ud.hour, ud.weekday(),
        ])
        idx.append((k, a))
    return np.array(X), idx


def barriers(idx):
    """For each decision: (long_up_first, exit_index, long_R_gross)."""
    y, ex, rl = [], [], []
    for k, a in idx:
        i = int(H1.s[k])
        e = min(i + HZ, len(T) - 1)
        p = O[i]
        hu = np.flatnonzero(H[i:e] >= p + a)
        hd = np.flatnonzero(L[i:e] <= p - a)
        fu = hu[0] if len(hu) else 10 ** 9
        fd = hd[0] if len(hd) else 10 ** 9
        if fu == 10 ** 9 and fd == 10 ** 9:
            y.append(int(C[e] > p)); ex.append(e); rl.append((C[e] - p) / a)
        elif fu < fd:
            y.append(1); ex.append(i + fu); rl.append(1.0)
        else:
            y.append(0); ex.append(i + fd); rl.append(-1.0)
    return np.array(y), np.array(ex), np.array(rl)


def trade(p, idx, ex, rl, thr, years, yr):
    out = []
    busy = -1
    for q, (k, a) in enumerate(idx):
        if yr[q] not in years or np.isnan(p[q]):
            continue
        i = int(H1.s[k])
        if i <= busy:
            continue
        if p[q] >= thr:
            s = 1
        elif p[q] <= 1 - thr:
            s = -1
        else:
            continue
        out.append((yr[q], s * rl[q] - SP / a))
        busy = ex[q]
    return out


def main():
    X, idx = build()
    y, ex, rl = barriers(idx)
    yr = np.array([dt.datetime.fromtimestamp(int(H1.t[k]), dt.timezone.utc).year for k, _ in idx])
    print(f"decisions {len(y)}, up-first base rate {y.mean():.3f}")
    rng = np.random.default_rng(0)
    preds = {"model": np.full(len(y), np.nan), "shuffled": np.full(len(y), np.nan)}
    for ty in range(2014, 2027):
        te = yr == ty
        first_test = int(H1.s[idx[np.flatnonzero(te)[0]][0]])
        tr_ = (yr < ty) & (ex < first_test)            # embargo: label resolved before test year
        for name in preds:
            yy = y[tr_] if name == "model" else rng.permutation(y[tr_])
            m = GBM(n_iter=200, lr=0.05, depth=3, min_leaf=200, lam=1.0)
            m.fit(X[tr_], yy)
            preds[name][te] = m.predict_proba(X[te])[:, 1]
        auc = roc_auc_score(y[te], preds["model"][te])
        print(f"  {ty}: train {tr_.sum():6d} test {te.sum():5d}  OOS AUC {auc:.3f}")
    oos = ~np.isnan(preds["model"])
    print(f"\nOOS AUC 2014-2026: model {roc_auc_score(y[oos], preds['model'][oos]):.3f}  "
          f"shuffled {roc_auc_score(y[oos], preds['shuffled'][oos]):.3f}  (0.500 = no information)")
    pf = lambda r: r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else 0
    for thr in (0.52, 0.55, 0.58, 0.60):
        for name in preds:
            a_ = np.array([r for _, r in trade(preds[name], idx, ex, rl, thr, range(2014, 2020), yr)])
            b_ = np.array([r for _, r in trade(preds[name], idx, ex, rl, thr, range(2020, 2027), yr)])
            if len(a_) < 5 or len(b_) < 5:
                print(f"  thr {thr:.2f} {name:8s} too few trades ({len(a_)}/{len(b_)})")
                continue
            ok = name == "model" and pf(a_) >= 1.15 and pf(b_) >= 1.15 and len(a_) >= 200 and len(b_) >= 200
            print(f"  thr {thr:.2f} {name:8s} 2014-19 n={len(a_):5d} PF {pf(a_):.2f} avg {a_.mean():+.3f}R | "
                  f"2020-26 n={len(b_):5d} PF {pf(b_):.2f} avg {b_.mean():+.3f}R{'  <== PASS' if ok else ''}")
    # feature importance proxy: gross R by decile of model probability (2014-2026)
    r_long = rl[oos]
    p_ = preds["model"][oos]
    qs = np.quantile(p_, np.linspace(0, 1, 11))
    print("\nlong gross R by model-probability decile (should rise left->right if the model knows anything):")
    print("  " + " ".join(f"{r_long[(p_ >= qs[i]) & (p_ <= qs[i + 1])].mean():+.3f}" for i in range(10)))


if __name__ == "__main__":
    main()
