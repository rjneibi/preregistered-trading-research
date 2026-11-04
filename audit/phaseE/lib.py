"""Shared helpers for Phase E: slices, PF, random twin, DSR, gates as frozen in prereg/COMMON.md."""
import json
import math
import os
import sys

import numpy as np
from scipy import stats as st

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER_N = json.load(open(os.path.join(HERE, "..", "stats", "family_counts.json")))["total"]


def pf(r):
    r = np.asarray(r, float)
    w, l = r[r > 0].sum(), -r[r < 0].sum()
    return float(w / l) if l > 0 else (float("inf") if w > 0 else 0.0)


def cuts(t0, t1):
    """50/20/30 by calendar span."""
    s = t1 - t0
    return t0 + 0.5 * s, t0 + 0.7 * s


def dsr(r, trials):
    r = np.asarray(r, float)
    n = len(r)
    if n < 3 or r.std(ddof=1) == 0:
        return None
    sr = r.mean() / r.std(ddof=1)
    g = 0.5772156649
    v = 1.0 / n
    emax = math.sqrt(v) * ((1 - g) * st.norm.ppf(1 - 1 / trials) + g * st.norm.ppf(1 - 1 / (trials * math.e)))
    sk, ku = st.skew(r), st.kurtosis(r, fisher=False)
    den = 1 - sk * sr + (ku - 1) / 4 * sr * sr
    return float(st.norm.cdf((sr - emax) * math.sqrt(n - 1) / math.sqrt(max(den, 1e-9))))


def twin_p(real_mean, close_ret, holds, n, draws=2000, seed=7):
    """Random entries on a per-bar log-return series: same trade count, resampled holding times, one-sided p of the mean trade."""
    rng = np.random.default_rng(seed)
    c = np.concatenate([[0.0], np.cumsum(close_ret)])
    holds = np.maximum(np.asarray(holds, int), 1)
    N = len(close_ret)
    hit = 0
    for _ in range(draws):
        h = rng.choice(holds, n)
        i = rng.integers(0, np.maximum(N - h, 1))
        sg = rng.choice([-1.0, 1.0], n)
        hit += (sg * (c[i + h] - c[i])).mean() >= real_mean
    return (hit + 1) / (draws + 1)


def gates(net, net2x, p, n_min=100):
    n = len(net)
    a, b = pf(net), pf(net2x)
    if n < n_min:
        return dict(n=n, pf=round(a, 3), pf2x=round(b, 3), twin_p=p, status="INSUFFICIENT SAMPLE", passed=False)
    ok = a >= 1.20 and b >= 1.00 and p < 0.05
    return dict(n=n, pf=round(a, 3), pf2x=round(b, 3), twin_p=round(p, 4), status="PASS" if ok else "FAIL", passed=bool(ok))
