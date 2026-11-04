"""Overfitting and significance checks."""
import numpy as np
import pandas as pd
from scipy import stats

from .engine import simulate


# ---------- baselines: same entry bar, same stop distance, same RR ----------

def mirror_R(m, trades, rr, k, slip, comm, kind_col=None):
    """R of the opposite-direction trade for each trade (entry bar and risk unchanged)."""
    out = np.empty(len(trades))
    for n, t in enumerate(trades.itertuples(index=False)):
        d = -t.dir
        stop = t.planned - d * t.risk
        kind = getattr(t, "kind", "market") if kind_col else "market"
        R, _, _ = simulate(m, int(t.i_entry), int(t.i_exit_day), d, t.planned, stop, [rr], k, slip, comm, kind=kind)
        out[n] = R[0]
    return out


def random_direction_test(R_actual, R_mirror, runs, seed):
    """Strategy mean vs random-direction mean at identical times. Each run flips a fair
    coin per trade. Returns dict with the random distribution summary and p-value."""
    rng = np.random.default_rng(seed)
    n = len(R_actual)
    flips = rng.random((runs, n)) < 0.5
    rand_means = np.where(flips, R_actual, R_mirror).mean(axis=1)
    act = R_actual.mean()
    return dict(actual=act, random_mean=rand_means.mean(), random_p95=np.percentile(rand_means, 95),
                p_value=(np.sum(rand_means >= act) + 1) / (runs + 1),
                fade_mean=R_mirror.mean(),
                fade_minus_actual_t=_paired_t(R_actual, R_mirror))


def _paired_t(a, b):
    d = a - b
    return d.mean() / d.std(ddof=1) * np.sqrt(len(d)) if len(d) > 2 and d.std() > 0 else np.nan


# ---------- Monte Carlo on the trade sequence ----------

def max_dd_from_R(R, risk):
    eq = np.cumprod(1 + risk * R, axis=-1)
    peak = np.maximum.accumulate(eq, axis=-1)
    return (eq / peak - 1).min(axis=-1), eq[..., -1]


def monte_carlo(R, risk, runs, seed):
    rng = np.random.default_rng(seed)
    R = np.asarray(R, float)
    n = len(R)
    shuf = np.array([rng.permutation(R) for _ in range(runs)])
    dd_s, _ = max_dd_from_R(shuf, risk)
    boot = R[rng.integers(0, n, (runs, n))]
    dd_b, fin_b = max_dd_from_R(boot, risk)
    q = lambda x, p: float(np.percentile(x, p))
    return dict(
        shuffle_dd_median=q(dd_s, 50), shuffle_dd_p5=q(dd_s, 5), shuffle_dd_p1=q(dd_s, 1),
        boot_dd_median=q(dd_b, 50), boot_dd_p5=q(dd_b, 5),
        boot_final_p5=q(fin_b, 5), boot_final_median=q(fin_b, 50), boot_final_p95=q(fin_b, 95),
        boot_prob_loss=float((fin_b < 1).mean()),
        _fan=np.cumprod(1 + risk * boot[:200], axis=1), _dd_b=dd_b, _fin_b=fin_b)


# ---------- deflated Sharpe ratio (Bailey & Lopez de Prado 2014) ----------

def deflated_sharpe(returns, sr_trials, n_trials):
    """returns: per-period returns of the selected strategy (daily R sums).
    sr_trials: per-period Sharpe ratios of all trials (for their variance).
    Returns (DSR probability, expected max SR under the null, observed SR)."""
    r = np.asarray(returns, float)
    T = len(r)
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    var_sr = np.nanvar(sr_trials, ddof=1)
    emc = 0.5772156649
    N = max(int(n_trials), 2)
    sr0 = np.sqrt(var_sr) * ((1 - emc) * stats.norm.ppf(1 - 1 / N) + emc * stats.norm.ppf(1 - 1 / (N * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return float(stats.norm.cdf(z)), float(sr0), float(sr)


# ---------- White's Reality Check and Hansen's SPA ----------

def _stationary_bootstrap_counts(T, B, mean_block, rng):
    """For each bootstrap replicate, how many times each day is drawn (B x T)."""
    p = 1.0 / mean_block
    counts = np.zeros((B, T), np.float32)
    for b in range(B):
        idx = np.empty(T, int)
        idx[0] = rng.integers(T)
        jumps = rng.random(T) < p
        newstart = rng.integers(0, T, T)
        for t in range(1, T):
            idx[t] = newstart[t] if jumps[t] else (idx[t - 1] + 1) % T
        counts[b] = np.bincount(idx, minlength=T)
    return counts


def reality_check(X, B=1000, mean_block=10, seed=0):
    """X: (K configs x T days) of daily excess returns vs a zero benchmark (no trade).
    Returns White RC p-value and Hansen SPA (consistent) p-value for H0: no config beats 0."""
    rng = np.random.default_rng(seed)
    X = np.asarray(X, np.float64)
    K, T = X.shape
    mu = X.mean(axis=1)
    sd = X.std(axis=1, ddof=1)
    sd[sd == 0] = np.inf
    counts = _stationary_bootstrap_counts(T, B, mean_block, rng)
    mu_b = (counts @ X.T) / T                       # B x K bootstrap means
    # White RC (non-studentized)
    V = np.sqrt(T) * mu.max()
    Vb = np.sqrt(T) * (mu_b - mu).max(axis=1)
    p_rc = float((Vb >= V).mean())
    # Hansen SPA, studentized, consistent recentring
    tstat = np.sqrt(T) * mu / sd
    Vs = max(tstat.max(), 0)
    thresh = -np.sqrt(2 * np.log(np.log(T))) * sd / np.sqrt(T)
    mu_c = np.where(mu >= thresh, mu, 0.0)
    Vsb = (np.sqrt(T) * (mu_b - mu_c) / sd).max(axis=1)
    p_spa = float((np.maximum(Vsb, 0) >= Vs).mean())
    return dict(K=K, T=T, best_mean=float(mu.max()), best_t=float(tstat.max()), p_white_rc=p_rc,
                p_hansen_spa=p_spa)


# ---------- walk-forward ----------

def walk_forward(S, N, dates, train_m=24, test_m=6, min_trades=60, eligible=None):
    """Rolling selection on daily matrices. S/N: (K x T) daily R-sum and trade count.
    At each step pick the config with the highest train expectancy (sum R / trades) among
    those with >= min_trades, then record its test-window daily R. Returns (stitched daily
    R Series, stitched daily trade counts, list of chosen config ids per window)."""
    d = pd.to_datetime(pd.Series(dates))
    start = d.iloc[0]
    out_r, out_n, picks = [], [], []
    while True:
        tr0, tr1 = start, start + pd.DateOffset(months=train_m)
        te1 = tr1 + pd.DateOffset(months=test_m)
        if tr1 >= d.iloc[-1]:
            break
        trm = ((d >= tr0) & (d < tr1)).values
        tem = ((d >= tr1) & (d < te1)).values
        sR, sN = S[:, trm].sum(axis=1), N[:, trm].sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            exp = np.where(sN >= min_trades, sR / np.maximum(sN, 1), -np.inf)
        if eligible is not None:
            exp = np.where(eligible, exp, -np.inf)
        k = int(np.argmax(exp))
        picks.append(dict(train_start=tr0.date(), test_start=tr1.date(), test_end=te1.date(), cfg=k,
                          train_exp=float(exp[k]), train_n=int(sN[k]),
                          test_exp=float(S[k, tem].sum() / max(N[k, tem].sum(), 1)), test_n=int(N[k, tem].sum())))
        out_r.append(pd.Series(S[k, tem], index=d[tem].dt.date.values))
        out_n.append(pd.Series(N[k, tem], index=d[tem].dt.date.values))
        start = start + pd.DateOffset(months=test_m)
    if not out_r:
        return pd.Series(dtype=float), pd.Series(dtype=float), []
    return pd.concat(out_r), pd.concat(out_n), picks


def cost_breakeven(ks, exps):
    """Linear interpolation of the cost multiplier at which expectancy crosses zero."""
    ks, exps = np.asarray(ks, float), np.asarray(exps, float)
    if exps[0] <= 0:
        return 0.0
    for i in range(1, len(ks)):
        if exps[i] <= 0:
            return float(ks[i - 1] + (ks[i] - ks[i - 1]) * exps[i - 1] / (exps[i - 1] - exps[i]))
    slope = (exps[-1] - exps[0]) / (ks[-1] - ks[0])
    return float(ks[0] - exps[0] / slope) if slope < 0 else np.inf
