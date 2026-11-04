"""goldbot self-checks — assert-gated, ordered; ALL must pass.

    python tests/run_tests.py            # fast suite (no market data needed)
    python tests/run_tests.py --full     # + slow parity vs bot_spec_trades.csv

Repo convention: plain asserts, no pytest (see labelsizing_core).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from goldbot import clock  # noqa: E402
from goldbot.config import Cfg, load_config, resolve_path  # noqa: E402
from goldbot.costs import CostModel  # noqa: E402
from goldbot.cpcv import CombinatorialPurgedCV  # noqa: E402
from goldbot.data import load_ohlc, resample_ohlc, resample_d1_utc, wilder_atr  # noqa: E402
from goldbot.dsr import dsr, expected_max_sharpe, pbo_cscv, psr, sharpe  # noqa: E402
from goldbot.events import generate_events_final  # noqa: E402
from goldbot.guards import NewsBlackout, SpreadGate  # noqa: E402
from goldbot.ou_estimator import fit_ou, simulate_ou  # noqa: E402
from goldbot.pivots import daily_pivots, dead_levels, r3s3_fade_events  # noqa: E402
from goldbot.triple_barrier import run_exits  # noqa: E402
from tests._synth import flat_bars, mk_bars, mk_event  # noqa: E402


def check_01_isolation():
    assert importlib.util.find_spec("MetaTrader5") is None, (
        "MetaTrader5 importable — run inside research/goldbot/.venv, "
        "never the live bot's interpreter")


def check_02_config_tags():
    cfg = load_config(ROOT / "config.yaml")
    assert cfg.guards.spread_gate.enabled is False
    assert cfg.guards.news_blackout.enabled is False
    assert cfg.strategy.variant in ("final", "base")

    import copy
    import yaml
    bad = copy.deepcopy(cfg.raw())
    bad["costs"]["sneaky_pts"] = 42.0                      # bare cost number
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.yaml"
        p.write_text(yaml.safe_dump(bad))
        try:
            load_config(p)
            raise AssertionError("bare cost number accepted")
        except ValueError:
            pass
        bad2 = copy.deepcopy(cfg.raw())
        bad2["costs"]["untagged"] = {"value": 3.0}         # dict but no tag
        p.write_text(yaml.safe_dump(bad2))
        try:
            load_config(p)
            raise AssertionError("untagged cost dict accepted")
        except ValueError:
            pass


def check_03_ou_recovery():
    for theta, mu, sigma, tol_th in ((0.05, 0.0, 1.0, 0.15),
                                     (0.5, 5.0, 2.0, 0.10)):
        x = simulate_ou(theta, mu, sigma, x0=mu, n=20_000, dt=1.0, seed=7)
        fit = fit_ou(x, dt=1.0)
        assert fit.valid, f"valid fit rejected: {fit.reason}"
        assert abs(fit.theta - theta) / theta <= tol_th, \
            f"theta {fit.theta:.4f} vs {theta}"
        assert abs(fit.mu - mu) <= 0.5, f"mu {fit.mu:.3f} vs {mu}"
        assert abs(fit.sigma - sigma) / sigma <= 0.05, \
            f"sigma {fit.sigma:.4f} vs {sigma}"
        assert abs(fit.half_life - np.log(2) / fit.theta) < 1e-12
    # determinism
    a = simulate_ou(0.1, 0.0, 1.0, 0.0, 500, seed=1)
    b = simulate_ou(0.1, 0.0, 1.0, 0.0, 500, seed=1)
    assert np.array_equal(a, b)


def check_04_ou_rejection():
    rng = np.random.default_rng(11)
    rw = rng.standard_normal(5000).cumsum()               # random walk
    fit = fit_ou(rw)
    assert not fit.valid, f"random walk accepted: phi1={fit.phi1:.5f}"

    anti = np.empty(5000)                                  # phi1 = -0.5
    anti[0] = 0.0
    eps = rng.standard_normal(4999)
    for i in range(1, 5000):
        anti[i] = -0.5 * anti[i - 1] + eps[i - 1]
    fit = fit_ou(anti)
    assert not fit.valid and "phi1" in fit.reason

    fit = fit_ou(np.zeros(50))                             # too short
    assert not fit.valid and "min_obs" in fit.reason


def check_05_clock():
    # US DST starts 2025-03-09: rollover is 22:00 UTC before, 21:00 UTC after
    before = pd.Timestamp("2025-03-07T21:30:00Z")   # 16:30 NY EST -> same day
    after_roll = pd.Timestamp("2025-03-07T22:30:00Z")  # 17:30 NY -> next day
    assert clock.day_key(before, "ny17") == pd.Timestamp("2025-03-07")
    assert clock.day_key(after_roll, "ny17") == pd.Timestamp("2025-03-08")
    post_dst = pd.Timestamp("2025-03-10T21:30:00Z")  # 17:30 EDT -> next day
    post_dst_early = pd.Timestamp("2025-03-10T20:30:00Z")  # 16:30 EDT
    assert clock.day_key(post_dst, "ny17") == pd.Timestamp("2025-03-11")
    assert clock.day_key(post_dst_early, "ny17") == pd.Timestamp("2025-03-10")
    assert clock.day_key(before, "utc00") == pd.Timestamp("2025-03-07")

    # nights over a weekend spanning the DST switch: Fri 15:00 NY -> Mon 18:00 NY
    n = clock.nights_held(pd.Timestamp("2025-03-07T20:00:00Z"),
                          pd.Timestamp("2025-03-10T22:00:00Z"))
    assert n == 4, f"expected 4 rollovers (Fri/Sat/Sun/Mon 17:00), got {n}"
    assert clock.nights_held(pd.Timestamp("2025-03-07T20:00:00Z"),
                             pd.Timestamp("2025-03-07T21:00:00Z")) == 0

    assert clock.in_flatten_window(pd.Timestamp("2025-03-07T21:55:00Z"))  # 16:55 NY
    assert not clock.in_flatten_window(pd.Timestamp("2025-03-07T22:01:00Z"))
    assert not clock.in_flatten_window(pd.Timestamp("2025-03-07T21:40:00Z"))


def check_06_pivot_lookahead():
    idx = pd.date_range("2024-01-02", periods=3, freq="1D", tz="UTC")
    d1 = pd.DataFrame({"open": [95.0, 160.0, 170.0],
                       "high": [110.0, 200.0, 210.0],
                       "low": [90.0, 150.0, 160.0],
                       "close": [100.0, 180.0, 190.0]}, index=idx)
    piv = daily_pivots(d1)
    assert piv.iloc[0].isna().all(), "first day must have no pivots"
    assert piv.loc[idx[1], "pp"] == 100.00      # (110+90+100)/3
    assert piv.loc[idx[1], "r3"] == 120.00      # 100 + 20
    assert piv.loc[idx[1], "s3"] == 80.00
    assert piv.loc[idx[2], "r3"] == 226.67      # 176.6667 + 50, rounded once
    assert piv.loc[idx[2], "s3"] == 126.67

    d1b = d1.copy()                              # perturb day 2's OWN bars:
    d1b.loc[idx[1], ["high", "low", "close"]] = [999.0, 1.0, 500.0]
    pivb = daily_pivots(d1b)
    assert (pivb.loc[idx[1]] == piv.loc[idx[1]]).all(), \
        "day-D pivots leaked day-D data"

    day_open = idx[1]
    h4_idx = pd.date_range(day_open - pd.Timedelta(hours=16), periods=5,
                           freq="4h", tz="UTC")   # last bar closes AFTER day_open
    h4 = pd.DataFrame({"open": 100.0, "high": 122.0, "low": 78.0,
                       "close": [119.0, 119.0, 119.0, 119.0, 121.0]},
                      index=h4_idx)
    r3_dead, s3_dead, n_done = dead_levels(h4, day_open, r3=120.0, s3=80.0)
    assert n_done == 4, "bar closing after day_open must not count"
    assert not r3_dead and not s3_dead, "future/at-level closes leaked in"
    h4.iloc[2, h4.columns.get_loc("close")] = 120.0      # AT level: strict
    assert not dead_levels(h4, day_open, 120.0, 80.0)[0]
    h4.iloc[2, h4.columns.get_loc("close")] = 120.5      # above -> dead
    assert dead_levels(h4, day_open, 120.0, 80.0)[0]
    h4.iloc[1, h4.columns.get_loc("close")] = 79.0       # below S3 -> dead
    assert dead_levels(h4, day_open, 120.0, 80.0)[1]

    try:
        r3s3_fade_events()
        raise AssertionError("placeholder fade must raise")
    except NotImplementedError:
        pass


def check_07_triple_barrier():
    atr = 10.0
    kw = dict(k_tp_atr=0.8, k_sl_atr=2.4, time_stop_h=24)

    # (a) TP touch fills at the barrier
    m1 = mk_bars("2024-01-02T13:00Z",
                 [(100, 101, 99, 100), (107, 108.5, 106, 107)])
    tr = run_exits(m1, mk_event("2024-01-02T13:00Z", 1, atr, False),
                   fill_mode="barrier_level", **kw)
    assert tr.iloc[0].resolution == "TP" and tr.iloc[0].gross_usd == 800.0

    # (b) open gaps through SL: gap_open fills at open, barrier_level at SL
    m1 = mk_bars("2024-01-02T13:00Z",
                 [(100, 101, 99, 100), (70, 71, 69, 70)])
    ev = mk_event("2024-01-02T13:00Z", 1, atr, False)
    gap = run_exits(m1, ev, fill_mode="gap_open", **kw).iloc[0]
    lvl = run_exits(m1, ev, fill_mode="barrier_level", **kw).iloc[0]
    assert gap.resolution == "SL" and gap.gross_usd == -3000.0
    assert lvl.resolution == "SL" and lvl.gross_usd == -2400.0

    # (c) ambiguous bar (both barriers) resolves as SL and is counted
    m1 = mk_bars("2024-01-02T13:00Z",
                 [(100, 101, 99, 100), (100, 109, 75, 100)])
    tr = run_exits(m1, mk_event("2024-01-02T13:00Z", 1, atr, False),
                   fill_mode="barrier_level", **kw).iloc[0]
    assert tr.resolution == "SL" and bool(tr.ambiguous) and tr.gross_usd == -2400.0

    # (d) no touch -> TIMEOUT at the horizon close
    m1 = mk_bars("2024-01-02T13:00Z", flat_bars(5))
    tr = run_exits(m1, mk_event("2024-01-02T13:00Z", 1, atr, False),
                   fill_mode="barrier_level", **kw).iloc[0]
    assert tr.resolution == "TIMEOUT" and tr.gross_usd == 0.0

    # (e) hivol: close HALF at -1.2*ATR, remainder runs to TP
    m1 = mk_bars("2024-01-02T13:00Z",
                 [(100, 101, 99, 100), (95, 96, 87.5, 88), (90, 109, 89, 105)],
                 freq="1h")
    tr = run_exits(m1, mk_event("2024-01-02T13:00Z", 1, atr, True),
                   fill_mode="barrier_level", bail_enabled=True, **kw).iloc[0]
    assert tr.resolution == "TP" and bool(tr.derisked)
    assert tr.gross_usd == (0.5 * (88 - 100) + 0.5 * (108 - 100)) * 100  # -200

    # (f)/(g) lovol: bail only fires after 8h; disabled == pure 3-barrier
    bars = ([(100, 100.5, 99.5, 100)] +
            [(89.5, 90.5, 88.5, 89)] * 7 +          # adverse but < 8h old
            [(89, 89.5, 88, 89), (89, 92, 88, 91)])
    m1 = mk_bars("2024-01-02T13:00Z", bars, freq="1h")
    ev = mk_event("2024-01-02T13:00Z", 1, atr, False)
    bail = run_exits(m1, ev, fill_mode="barrier_level", bail_enabled=True,
                     **kw).iloc[0]
    pure = run_exits(m1, ev, fill_mode="barrier_level", bail_enabled=False,
                     **kw).iloc[0]
    assert bail.resolution == "BAIL" and bail.gross_usd == -1100.0
    assert pure.resolution == "TIMEOUT" and pure.gross_usd == -900.0

    # fixed-$ mode (base variant): TP $8 / SL $12
    m1 = mk_bars("2024-01-02T13:00Z",
                 [(100, 101, 99, 100), (106, 108.2, 105, 107)])
    tr = run_exits(m1, mk_event("2024-01-02T13:00Z", 1, atr, False),
                   tp_usd=8.0, sl_usd=12.0, time_stop_h=24,
                   fill_mode="barrier_level").iloc[0]
    assert tr.resolution == "TP" and tr.gross_usd == 800.0


def check_08_cpcv():
    t = np.arange(0, 6000, 10)                    # 600 evenly spaced events
    labels = pd.DataFrame({"signal_idx": t})
    cv = CombinatorialPurgedCV(n_groups=6, k_test=2, tau_max=24,
                               embargo=24, l_feature_max=40)
    bounds = cv._group_bounds(t)
    margin = max(cv.embargo, cv.l_feature_max)
    seen = 0
    for train_idx, test_idx, sid in cv.split(labels):
        seen += 1
        tg = cv.split_test_groups()[sid]
        train_t = t[train_idx]
        for g in tg:                               # leakage probe
            g_lo, g_hi = bounds[g]
            inside = (train_t >= g_lo - cv.tau_max) & (train_t <= g_hi + margin)
            assert not inside.any(), f"leak in split {sid} group {g}"
        assert len(np.intersect1d(train_idx, test_idx)) == 0
    assert seen == 15, f"C(6,2) must be 15 splits, got {seen}"

    paths = cv.paths()
    assert len(paths) == 5, "phi(6,2) must be 5 paths"
    for path in paths:
        for g, sid in path.items():
            assert g in cv.split_test_groups()[sid], \
                "path assigns a group to a split not testing it"
    # each group's K test appearances are spread over distinct splits per path
    for g in range(6):
        sids = [p[g] for p in paths]
        assert len(set(sids)) == 5

    tiny = pd.DataFrame({"signal_idx": np.arange(0, 60)})  # purge swallows all
    try:
        list(cv.split(tiny))
        raise AssertionError("collapsed split not detected")
    except RuntimeError:
        pass


def check_09_costs():
    with tempfile.TemporaryDirectory() as td:
        mpath = Path(td) / "cost_matrix.json"
        mpath.write_text(json.dumps({
            "matrix": {}, "news": None,
            "overall": {"n": 1986, "med": 0.72, "p75": 0.75, "p95": 0.79}}))
        cm = CostModel(Cfg({"costs": {
            "matrix_path": str(mpath), "news_calendar_json": "",
            "spread_median_usd": {"value": 0.72, "tag": "VERIFIED"},
            "slippage_pts": {"optimistic": 0.0, "realistic": 5.0,
                             "worst": 10.0, "tag": "ESTIMATE"},
            "commission_pts_rt": {"value": 7.0, "tag": "BROKER"},
            "legacy_flat_rt_pts": {"value": 20.0, "tag": "ESTIMATE"},
            "islamic_admin_fee_usd_per_lot_night": {"value": 5.0,
                                                    "tag": "ESTIMATE"},
        }}))
        # hand-check: realistic = 2*(72/2 + 5) + 7 = 89 pts -> $0.89/oz
        assert abs(cm.breakeven_move_usd("realistic") - 0.89) < 1e-9
        assert abs(cm.breakeven_move_usd("flat") - 0.20) < 1e-9
        assert (cm.breakeven_move_usd("optimistic")
                < cm.breakeven_move_usd("realistic")
                < cm.breakeven_move_usd("worst"))
        ts = pd.Timestamp("2024-06-05T14:00:00Z")
        assert cm.round_trip_usd(ts, ts, "flat", nights=3) == 20.0
        assert abs(cm.round_trip_usd(ts, ts, "realistic", nights=2)
                   - (89.0 + 10.0)) < 1e-9


def check_10_guards():
    spread = pd.Series(np.ones(30))
    spread.iloc[20] = 5.0
    gate = SpreadGate(window_bars=10, mult=2.0)
    flags = gate.flags(spread)
    assert bool(flags.iloc[20]) and not bool(flags.iloc[5])
    assert not gate.ok(5.0, pd.Series(np.ones(20)))
    assert gate.ok(1.5, pd.Series(np.ones(20)))

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cal.csv"
        p.write_text("ts_utc,event\n2026-01-02T13:30:00Z,NFP\n")
        nb = NewsBlackout(p)
        assert nb.blocked(pd.Timestamp("2026-01-02T13:20:00Z"))
        assert nb.blocked(pd.Timestamp("2026-01-02T13:45:00Z"))
        assert not nb.blocked(pd.Timestamp("2026-01-02T14:00:00Z"))


def check_12_dsr_known_answers():
    """HCRT prereg harness gate (a): N=1 => SR0=0 and DSR reduces to PSR;
    PSR closed-form value; SR0 monotone in N."""
    # closed form: SR=0.1, T=101, Normal returns => z = 1/sqrt(1.005)
    assert abs(psr(0.1, 0.0, 101, 0.0, 3.0) - 0.84074) < 1e-3

    rng = np.random.default_rng(42)
    r = rng.normal(0.002, 0.01, 250)
    d1 = dsr(r, trial_srs=[sharpe(r)])                 # N=1: sole trial
    assert d1["sr0"] == 0.0
    g1, g2 = d1["skew"], d1["kurt_raw"]
    assert abs(d1["dsr"] - psr(d1["sr"], 0.0, 250, g1, g2)) < 1e-12
    assert 2.5 < g2 < 3.6, "Gaussian sample kurtosis should be near 3"

    assert expected_max_sharpe(1, 0.25) == 0.0
    s2, s10, s100 = (expected_max_sharpe(n, 0.25) for n in (2, 10, 100))
    assert 0.0 < s2 < s10 < s100, "SR0 must grow with trial count"


def check_13_dsr_null_calibration():
    """HCRT prereg harness gate (b): Gaussian zero-edge null, best of N=10
    trials. Deflated rejection at 0.95 stays near/below nominal; the
    UNdeflated PSR of the max trial rejects far more often (~40% expected:
    1 - 0.95^10). This is the multiplicity penalty working."""
    rng = np.random.default_rng(7)
    sims, n_trials, t_obs = 400, 10, 252
    rej_dsr = rej_naive = 0
    for _ in range(sims):
        trials = rng.normal(0.0, 0.01, (t_obs, n_trials))
        srs = [sharpe(trials[:, j]) for j in range(n_trials)]
        best = int(np.argmax(srs))
        d = dsr(trials[:, best], trial_srs=srs)
        g1, g2 = d["skew"], d["kurt_raw"]
        rej_dsr += d["dsr"] >= 0.95
        rej_naive += psr(d["sr"], 0.0, t_obs, g1, g2) >= 0.95
    frac_dsr, frac_naive = rej_dsr / sims, rej_naive / sims
    print(f"    null rejection: deflated={frac_dsr:.3f} "
          f"naive={frac_naive:.3f}")
    assert frac_dsr < 0.12, f"DSR not calibrated: {frac_dsr:.3f}"
    assert frac_naive > 0.25, f"naive PSR unexpectedly strict: {frac_naive:.3f}"
    assert frac_dsr < frac_naive / 2, "deflation must bite"


def check_14_pbo_cscv():
    """HCRT prereg harness gate (c): pure-noise trials => PBO ~ 0.5; one
    genuinely superior trial => PBO low. Embargo purge path exercised."""
    rng = np.random.default_rng(11)
    t_obs, n_trials = 400, 8
    noise = rng.normal(0.0, 0.01, (t_obs, n_trials))
    p_noise = pbo_cscv(noise, s=8)
    assert p_noise["n_combinations"] == 70                # C(8,4)
    assert 0.30 <= p_noise["pbo"] <= 0.70, f"noise PBO {p_noise['pbo']:.2f}"

    edged = noise.copy()
    edged[:, 3] = rng.normal(0.008, 0.01, t_obs)          # real edge column
    p_edge = pbo_cscv(edged, s=8)
    assert p_edge["pbo"] <= 0.20, f"edge PBO {p_edge['pbo']:.2f}"
    print(f"    PBO: noise={p_noise['pbo']:.2f} edge={p_edge['pbo']:.2f}")

    times = np.arange(t_obs) * 24.0                       # daily trades
    p_purged = pbo_cscv(edged, s=8, times=times, embargo_h=24.0)
    assert p_purged["purged"] and p_purged["pbo"] <= 0.25


def check_11_parity_full():
    """Slow: replays flip_bot v1.1 as-coded per era and diffs against the
    round-17 harness output fable-backtesting/bot_spec_trades.csv."""
    cfg = load_config(ROOT / "config.yaml")
    m1_path = resolve_path(cfg, cfg.data.m1_path)
    target_csv = REPO / "fable-backtesting" / "bot_spec_trades.csv"
    assert m1_path.exists(), f"parity needs the M1 file at {m1_path}"
    assert target_csv.exists(), f"parity target missing: {target_csv}"
    expected_all = pd.read_csv(target_csv)
    expected_counts = {"old": 267, "new": 205}

    print(f"    loading {m1_path.name} ...", flush=True)
    m1_full = load_ohlc(m1_path)
    eras = {"old": (pd.Timestamp("2015-06-19T00:00:00Z"),
                    pd.Timestamp("2021-06-18T23:59:00Z")),
            "new": (pd.Timestamp("2021-06-19T00:00:00Z"),
                    pd.Timestamp("2026-06-19T17:57:00Z"))}
    e = cfg.exits.final
    for era, (start, end) in eras.items():
        m1 = m1_full[(m1_full.index >= start - pd.Timedelta(days=100))
                     & (m1_full.index <= end)]
        h1 = resample_ohlc(m1, "1h")
        h4 = resample_ohlc(m1, "4h")
        d1 = resample_d1_utc(m1)
        atr_h1 = wilder_atr(h1, 14)
        events = generate_events_final(h1, h4, d1, atr_h1, cfg, start, end)
        trades = run_exits(
            m1, events, k_tp_atr=e.k_tp_atr, k_sl_atr=e.k_sl_atr,
            time_stop_h=e.time_stop_h, fill_mode="barrier_level",
            bail_enabled=True, hivol_half_x=e.bail.hivol_half_x,
            lovol_bail_h=e.bail.lovol_bail_h, lovol_bail_x=e.bail.lovol_bail_x)
        trades["pnl_flat"] = trades["gross_usd"] - 20.0

        exp = expected_all[expected_all.era == era].copy()
        exp["ts_parsed"] = pd.to_datetime(exp.ts, utc=True)
        assert len(exp) == expected_counts[era], \
            f"target CSV changed: {era} has {len(exp)} rows"

        got_set = set(zip(trades.event_ts,
                          np.where(trades.side > 0, "BUY", "SELL"),
                          trades.hivol.astype(bool)))
        exp_set = set(zip(exp.ts_parsed, exp.dir, exp.hivol.astype(bool)))
        diff = got_set ^ exp_set
        if diff:
            print(f"    [{era}] event-set diff ({len(diff)} items):")
            for d in sorted(diff, key=str)[:10]:
                where = "goldbot-only" if d in got_set else "harness-only"
                print(f"      {where}: {d}")
        assert len(diff) <= 4, f"{era}: event mismatch beyond budget"
        print(f"    [{era}] events: goldbot={len(trades)} "
              f"harness={len(exp)} diff={len(diff)}")

        merged = pd.merge(
            trades.assign(dir=np.where(trades.side > 0, "BUY", "SELL")),
            exp, left_on=["event_ts", "dir"], right_on=["ts_parsed", "dir"])
        pnl_diff = (merged.pnl_flat - merged.pnl).abs()
        worst = float(pnl_diff.max()) if len(merged) else 0.0
        assert worst <= 1.0, f"{era}: worst per-trade pnl diff ${worst:.2f} > $1"
        net_g, net_h = float(merged.pnl_flat.sum()), float(merged.pnl.sum())
        assert abs(net_g - net_h) <= 300.0, \
            f"{era}: net ${net_g:,.0f} vs harness ${net_h:,.0f}"
        print(f"    [{era}] pnl: worst per-trade diff ${worst:.2f}, "
              f"net ${net_g:,.0f} vs harness ${net_h:,.0f}")


FAST = [check_01_isolation, check_02_config_tags, check_03_ou_recovery,
        check_04_ou_rejection, check_05_clock, check_06_pivot_lookahead,
        check_07_triple_barrier, check_08_cpcv, check_09_costs,
        check_10_guards, check_12_dsr_known_answers,
        check_13_dsr_null_calibration, check_14_pbo_cscv]


def main() -> int:
    full = "--full" in sys.argv
    checks = FAST + ([check_11_parity_full] if full else [])
    for fn in checks:
        fn()
        print(f"PASS  {fn.__name__}")
    if not full:
        print("(fast suite only — run with --full for the slow parity check "
              "against bot_spec_trades.csv)")
    print(f"ALL {len(checks)} CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
