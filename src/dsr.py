"""Deflated Sharpe ratio, after Bailey and Lopez de Prado (2014). Same calculation as audit/phaseE/lib.py.

Trial Sharpe variance uses the null value 1/T, because not all trial Sharpes are on disk. Read the result as an order of magnitude.
"""
import math

import numpy as np
from scipy import stats as st

EULER = 0.5772156649


def expected_max_sharpe(trials, t):
    """Expected best per-period Sharpe among `trials` null strategies over `t` periods."""
    return math.sqrt(1.0 / t) * ((1 - EULER) * st.norm.ppf(1 - 1 / trials) + EULER * st.norm.ppf(1 - 1 / (trials * math.e)))


def dsr(returns, trials):
    r = np.asarray(returns, float)
    n = len(r)
    if n < 3 or r.std(ddof=1) == 0:
        return None
    sr = r.mean() / r.std(ddof=1)
    sk, ku = st.skew(r), st.kurtosis(r, fisher=False)
    den = 1 - sk * sr + (ku - 1) / 4 * sr * sr
    return float(st.norm.cdf((sr - expected_max_sharpe(trials, n)) * math.sqrt(n - 1) / math.sqrt(max(den, 1e-9))))
