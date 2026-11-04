"""XAU/XAG spread diagnostic: exact-OU half-life vs carry test.

    python run_spread_research.py xau_m1.csv xag_m1.csv [--config config.yaml]
    python run_spread_research.py --selftest

The real run needs silver data (none on disk yet — download XAGUSD ticks with
fable-backtesting/bi5_downloader.py, already XAG-aware). --selftest exercises
the FULL report path on simulated OU data with known parameters, so the
pipeline is proven before the data lands.

Verdict logic: fit spread = log(XAU) - beta*log(XAG) as OU; if the fit is
invalid (random walk / anti-persistent / too short) STOP — no trading
conclusion. If valid, compare the expected reversion capture of one
half-life-scale round trip against 2-leg round-trip costs plus admin fee for
~half-life nights held. PASS means "worth a deeper look", not "trade it".
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from goldbot.config import load_config  # noqa: E402
from goldbot.costs import CostModel  # noqa: E402
from goldbot.data import load_ohlc, resample_ohlc  # noqa: E402
from goldbot.ou_estimator import fit_ou, simulate_ou  # noqa: E402

BAR_HOURS = {"1h": 1.0, "4h": 4.0, "1D": 24.0}


def report(spread: np.ndarray, dt_hours: float, cfg, xau_px: float) -> int:
    fit = fit_ou(spread, dt=dt_hours, min_obs=cfg.spread_research.min_obs)
    print(f"OU fit on {fit.n:,} bars (dt={dt_hours}h):")
    if not fit.valid:
        print(f"  INVALID — {fit.reason}")
        print("  No trading conclusion may be drawn from an invalid fit.")
        return 1
    hl_hours = fit.half_life
    print(f"  phi1={fit.phi1:.5f}  theta={fit.theta:.5f}/h  mu={fit.mu:.5f}")
    print(f"  sigma={fit.sigma:.5f}/sqrt(h)  half-life={hl_hours:.1f}h "
          f"({hl_hours / 24:.1f} days)")

    # carry test: one round trip capturing ~half the typical displacement
    eq_sd = fit.sigma / np.sqrt(2 * fit.theta)      # stationary sd (log units)
    capture_usd = 0.5 * eq_sd * xau_px              # per oz, XAU leg
    cost_model = CostModel(cfg)
    nights = max(1, int(round(hl_hours / 24)))
    ts = pd.Timestamp.now(tz="UTC")
    one_leg = cost_model.round_trip_usd(ts, ts, "realistic", nights=nights)
    two_leg_usd = 2 * one_leg / 100.0               # pts->$/oz, 2 legs
    print(f"  expected reversion capture ~${capture_usd:.2f}/oz "
          f"(0.5 x stationary sd x price)")
    print(f"  2-leg realistic round-trip cost ~${two_leg_usd:.2f}/oz "
          f"incl. admin fee x {nights} nights [ESTIMATE]")
    if capture_usd > 2 * two_leg_usd:
        print("  PASS: capture > 2x costs — worth a deeper look "
              "(NOT a green light)")
        return 0
    print("  FAIL: reversion does not clear costs with margin")
    return 1


def selftest(cfg) -> int:
    print("== spread-research selftest (simulated OU, known params) ==")
    theta, mu, sigma = 0.02, 0.0, 0.004      # half-life ~35h, log-spread units
    x = simulate_ou(theta, mu, sigma, x0=mu, n=50_000, dt=1.0, seed=3)
    fit = fit_ou(x, dt=1.0)
    assert fit.valid, fit.reason
    assert abs(fit.theta - theta) / theta < 0.2, fit.theta
    assert abs(fit.half_life - np.log(2) / theta) / (np.log(2) / theta) < 0.2
    rc = report(x, 1.0, cfg, xau_px=2500.0)
    print(f"selftest fit OK (theta {fit.theta:.4f} vs {theta}, "
          f"half-life {fit.half_life:.1f}h vs {np.log(2)/theta:.1f}h); "
          f"report path exit={rc}")
    print("SELFTEST PASSED")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("xau_path", nargs="?")
    ap.add_argument("xag_path", nargs="?")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)

    if args.selftest:
        return selftest(cfg)
    if not (args.xau_path and args.xag_path):
        ap.error("need xau_m1 and xag_m1 paths (or --selftest)")

    bar = cfg.spread_research.bar
    dt_hours = BAR_HOURS[bar]
    xau = resample_ohlc(load_ohlc(args.xau_path, cfg.data.data_tz), bar)["close"]
    xag = resample_ohlc(load_ohlc(args.xag_path, cfg.data.data_tz), bar)["close"]
    both = pd.concat({"xau": xau, "xag": xag}, axis=1).dropna()
    print(f"aligned {len(both):,} {bar} bars "
          f"({both.index[0]} -> {both.index[-1]})")

    la, lg = np.log(both.xau.to_numpy()), np.log(both.xag.to_numpy())
    hedge = cfg.spread_research.hedge
    if hedge.mode == "fixed":
        beta = float(hedge.beta)
    else:                                            # ols_log
        beta = float(np.cov(lg, la, bias=True)[0, 1] / np.var(lg))
    print(f"hedge beta ({hedge.mode}): {beta:.4f}")
    spread = la - beta * lg
    return report(spread, dt_hours, cfg, xau_px=float(both.xau.iloc[-1]))


if __name__ == "__main__":
    sys.exit(main())
