"""Performance metrics in R and on a fixed-fractional equity curve."""
import numpy as np
import pandas as pd


def r_stats(R):
    R = np.asarray(R, float)
    R = R[np.isfinite(R)]
    n = len(R)
    if n == 0:
        return dict(n=0, exp=np.nan, t=np.nan, win=np.nan, pf=np.nan, avg_win=np.nan, avg_loss=np.nan)
    w, lo = R[R > 0], R[R <= 0]
    sd = R.std(ddof=1) if n > 1 else np.nan
    return dict(n=n, exp=R.mean(), t=R.mean() / sd * np.sqrt(n) if sd and sd > 0 else np.nan,
                win=len(w) / n, pf=w.sum() / -lo.sum() if lo.sum() < 0 else np.inf,
                avg_win=w.mean() if len(w) else 0.0, avg_loss=lo.mean() if len(lo) else 0.0)


def longest_streak(R):
    best = cur = 0
    for r in R:
        cur = cur + 1 if r <= 0 else 0
        best = max(best, cur)
    return best


def full_report(trades, all_dates, risk=0.01, r_col="R"):
    """trades: DataFrame with columns date (datetime.date), R, entry_min, exit_min (epoch min).
    all_dates: every trading date in the period (for daily returns incl. flat days).
    Equity compounds: each trade returns risk*R of equity at entry; same-day trades are
    applied sequentially. Returns dict of metrics plus the daily equity Series.
    """
    tr = trades.sort_values("entry_min")
    R = tr[r_col].values
    rs = r_stats(R)
    daily_r = tr.groupby("date")[r_col].apply(lambda x: np.prod(1 + risk * x.values) - 1)
    idx = pd.Index(sorted(set(all_dates)))
    daily = daily_r.reindex(idx, fill_value=0.0)
    eq = (1 + daily).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1
    # drawdown duration in trading days
    under = (dd < 0).astype(int).values
    dur = best = 0
    for u in under:
        dur = dur + 1 if u else 0
        best = max(best, dur)
    years = len(idx) / 252
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 and eq.iloc[-1] > 0 else np.nan
    mu, sd = daily.mean(), daily.std(ddof=1)
    down = daily[daily < 0]
    dsd = np.sqrt((down ** 2).sum() / len(daily)) if len(daily) else np.nan
    monthly = (1 + daily).groupby(pd.to_datetime(daily.index).to_period("M")).prod() - 1
    exposure_min = (tr.exit_min - tr.entry_min).clip(lower=0).sum()
    rep = dict(rs)
    rep.update(dict(
        sharpe=mu / sd * np.sqrt(252) if sd > 0 else np.nan,
        sortino=mu / dsd * np.sqrt(252) if dsd > 0 else np.nan,
        max_dd=dd.min(), max_dd_days=best, cagr=cagr, final_equity=eq.iloc[-1],
        longest_losing_streak=longest_streak(R),
        pct_months_profitable=(monthly > 0).mean() if len(monthly) else np.nan,
        exposure=exposure_min / (len(idx) * 1440) if len(idx) else np.nan,
        trades_per_year=len(R) / years if years else np.nan))
    return rep, eq, dd


def by_group(trades, key, r_col="R"):
    g = trades.groupby(key)[r_col]
    return pd.DataFrame({"n": g.size(), "exp": g.mean(), "win": g.apply(lambda x: (x > 0).mean()),
                         "sum_R": g.sum(),
                         "t": g.apply(lambda x: x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 else np.nan)})
