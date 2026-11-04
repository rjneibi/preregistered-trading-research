"""Metrics, random-direction twin, Monte Carlo and the prop-firm window check. R values in,
risk fraction from config; equity compounds per trade in exit order."""
import numpy as np
import pandas as pd

DAY = 1440


def equity(R, risk, start=100_000.0):
    eq = start * np.cumprod(1 + risk * np.asarray(R, float))
    return np.r_[start, eq]


def max_dd(R, risk):
    eq = equity(R, risk)
    peak = np.maximum.accumulate(eq)
    return float(((peak - eq) / peak).max()) if len(eq) > 1 else 0.0


def longest_losing(R):
    best = cur = 0
    for r in R:
        cur = cur + 1 if r < 0 else 0
        best = max(best, cur)
    return best


def sharpe_daily(tr, risk, t0, t1):
    """Annualised Sharpe of daily % P&L over every weekday in [t0, t1) (zero on idle days)."""
    days = np.arange(t0 // DAY, t1 // DAY)
    days = days[(days + 3) % 7 < 5]
    if len(days) < 20:
        return np.nan
    pnl = pd.Series(risk * tr.R.values, index=tr.t_exit.values // DAY).groupby(level=0).sum()
    x = pnl.reindex(days, fill_value=0.0).values
    return float(x.mean() / x.std() * np.sqrt(252)) if x.std() > 0 else np.nan


def metrics(tr, risk, t0, t1, start=100_000.0):
    tr = tr.sort_values("t_exit")
    R = tr.R.values
    n = len(R)
    months = (t1 - t0) / (DAY * 30.4375)
    if n == 0:
        return dict(n=0, win=np.nan, avgR=np.nan, t=np.nan, exp_usd=np.nan, pf=np.nan, maxdd=np.nan,
                    sharpe=np.nan, lose_streak=0, per_month=0.0, totR=0.0)
    eq = equity(R, risk, start)
    usd = np.diff(eq)
    gain, loss = R[R > 0].sum(), -R[R < 0].sum()
    return dict(n=n, win=float((R > 0).mean()), avgR=float(R.mean()),
                t=float(R.mean() / R.std(ddof=1) * np.sqrt(n)) if n > 2 and R.std() > 0 else np.nan,
                exp_usd=float(usd.mean()), pf=float(gain / loss) if loss > 0 else np.inf,
                maxdd=max_dd(R, risk), sharpe=sharpe_daily(tr, risk, t0, t1),
                lose_streak=longest_losing(R), per_month=n / months, totR=float(R.sum()))


def twin_p(R_real, R_flip, runs, seed):
    """Same entries, coin-flip direction. One-sided p = P(twin avg >= real avg)."""
    ok = np.isfinite(R_flip)
    a, b = np.asarray(R_real)[ok], np.asarray(R_flip)[ok]
    if len(a) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    pick = rng.random((runs, len(a))) < 0.5
    avg = np.where(pick, a, b).mean(axis=1)
    return float((avg >= a.mean()).mean()), float(avg.mean())


def mc_maxdd(R, risk, runs, seed):
    rng = np.random.default_rng(seed)
    R = np.asarray(R, float)
    if len(R) < 2:
        return dict(p50=np.nan, p95=np.nan, p99=np.nan, actual=np.nan)
    dd = np.array([max_dd(rng.permutation(R), risk) for _ in range(runs)])
    return dict(p50=float(np.median(dd)), p95=float(np.quantile(dd, 0.95)),
                p99=float(np.quantile(dd, 0.99)), actual=max_dd(R, risk))


def prop_windows(tr, risk, t0, t1, P, start=100_000.0):
    """FTMO-style: from each weekday start, trades entered within window_days. Pass = +target
    before a day loses max_daily_loss of its opening balance or balance falls max_total_loss
    below start. Closed-trade P&L only (one position per symbol, stops cap open risk)."""
    tr = tr.sort_values("t_exit")
    te, tx, R = tr.t_entry.values, tr.t_exit.values, tr.R.values
    out = {"pass": 0, "fail": 0, "neither": 0}
    win = P["window_days"] * DAY
    for d in range(t0 // DAY, (t1 - win) // DAY):
        if (d + 3) % 7 >= 5:
            continue
        s = d * DAY
        sel = (te >= s) & (te < s + win)
        bal, day, day_open, res = start, None, start, "neither"
        for x, r in zip(tx[sel], R[sel]):
            if x // DAY != day:
                day, day_open = x // DAY, bal
            bal *= 1 + risk * r
            if bal <= day_open * (1 - P["max_daily_loss"]) or bal <= start * (1 - P["max_total_loss"]):
                res = "fail"
                break
            if bal >= start * (1 + P["target"]):
                res = "pass"
                break
        out[res] += 1
    tot = sum(out.values())
    return {k: v / tot if tot else np.nan for k, v in out.items()} | {"windows": tot}
