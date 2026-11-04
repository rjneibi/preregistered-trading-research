"""Stages after the grids: deep dive (IS+VAL), freeze, single OOS run."""
import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import yaml

from . import variant_a as A
from .common import RESULTS, ROOT, config
from .deep import (KS, Setup, baselines, breakdowns, cost_and_sizing, decay, evaluate_fixes,
                   stats_table, to_json, wfo)
from .gaps import trade_weak_spots
from .metrics import full_report, r_stats
from .robustness import cost_breakeven, monte_carlo

ROB = ("US30", "NAS100", "EURUSD", "GBPUSD", "XAUUSD")


def pick_from_stage1(variant="A"):
    p = json.load(open(RESULTS / f"stage1_{variant}.json"))["pick"]
    sc = A.SigA(box=p["box"], tf=int(p["tf"]), order=p["order"], strong=p["strong"], breakout=p["breakout"],
                buffer_atr=float(p["buffer_atr"]), window=int(p["window"]))
    return sc, p["stop"], float(p["rr"])


AUTHOR = (A.SigA(box="utc0007", tf=5, strong="body50", breakout="close", window=120), "in25", 2.0)


def deep(label, sc, stop, rr, with_fixes=True):
    out = RESULTS / f"deep_{label}"
    out.mkdir(parents=True, exist_ok=True)
    S = Setup(sc, stop, rr)
    tr = S.trades(k=1.0)
    tr.to_csv(out / "trades_k1.csv", index=False)
    res = dict(label=label, config=dict(asdict(sc), stop=stop, rr=rr))
    res["stats_k1"] = stats_table(tr)
    cs = cost_and_sizing(S)
    cs.to_csv(out / "cost_sizing.csv")
    exps = [cs.loc[(k, "IS+VAL", 0.01), "exp"] for k in KS]
    res["cost_breakeven_mult"] = cost_breakeven(KS, exps)
    res["exp_by_cost"] = dict(zip(map(str, KS), exps))
    ivs = tr[tr.split.isin(["IS", "VAL"])]
    bd = breakdowns(ivs)
    for k, v in bd.items():
        v.to_csv(out / f"by_{k}.csv")
    base, Ra, Rm = baselines(S, ivs)
    res["baseline"] = base
    np.save(out / "R_actual.npy", Ra)
    np.save(out / "R_mirror.npy", Rm)
    mc = {}
    for risk in config()["risk_fractions"]:
        m = monte_carlo(ivs.sort_values("entry_min").R.values, risk, config()["robustness"]["monte_carlo_runs"], config()["seed"])
        np.save(out / f"mc_fan_{risk}.npy", m.pop("_fan"))
        np.save(out / f"mc_dd_{risk}.npy", m.pop("_dd_b"))
        np.save(out / f"mc_fin_{risk}.npy", m.pop("_fin_b"))
        mc[str(risk)] = m
    res["monte_carlo"] = mc
    res["decay"] = decay(ivs)
    res["weak_spots"] = trade_weak_spots(ivs)
    res["outlier_top10_share_of_sumR"] = float(np.sort(ivs.R.values)[::-1][:10].sum() / ivs.R.sum()) if ivs.R.sum() else None
    if with_fixes:
        fx = evaluate_fixes(S, tr)
        fx.to_csv(out / "fixes.csv", index=False)
        res["fixes_kept"] = fx[fx.keep].fix.tolist()
        res["n_fix_trials"] = len(fx)
    # robustness instruments: the identical rules
    rob = {}
    for n in ROB:
        Sr = Setup(sc, stop, rr, insts=(n,))
        t2 = Sr.trades(k=1.0)
        rob[n] = {p: r_stats(t2[t2.split.isin(p.split("+"))].R.values) for p in ("IS", "VAL", "IS+VAL")}
        t0 = Sr.trades(k=0.0)
        rob[n]["gross_IS+VAL"] = r_stats(t0.R.values)
    res["robustness_instruments"] = rob
    to_json(res, out / "summary.json")
    return res, S, tr


def wfo_all():
    out = {}
    for v in ("A", "B"):
        r, n, picks = wfo(v)
        out[v] = dict(stitched_exp=float(r.sum() / max(n.sum(), 1)), stitched_trades=int(n.sum()),
                      stitched_t=float(_t_daily(r, n)), windows=picks)
        pd.DataFrame({"R": r, "n": n}).to_csv(RESULTS / f"wfo_{v}_stitched.csv")
    to_json(out, RESULTS / "wfo.json")
    return out


def _t_daily(r, n):
    x = r[n > 0] / n[n > 0]
    return x.mean() / x.std(ddof=1) * np.sqrt(len(x)) if len(x) > 2 else np.nan


def freeze(sc, stop, rr, fixes, status, path=ROOT / "config" / "final_strategy.yaml"):
    y = {
        "strategy": "London Breakout - Variant A (Asian box)",
        "status": status,
        "frozen_on": str(pd.Timestamp.now(tz="UTC").date()),
        "instruments": {"GER40": "Dukascopy DEU.IDX/EUR CFD (DAX)", "UK100": "Dukascopy GBR.IDX/GBP CFD (FTSE 100)"},
        "time": {"all_times": "computed with zoneinfo; never fixed UTC offsets",
                 "london_open": "08:00 Europe/London",
                 "trading_days": "Mon-Fri London dates with a 1m bar within 5 min of 08:00 London"},
        "signal": {
            "price": "mid ((bid+ask)/2) 1-minute bars, UTC bar-open timestamps",
            "box_rule": sc.box,
            "box_rule_meaning": {"utc0007": "00:00-07:00 UTC", "utc2307": "23:00 (prev day)-07:00 UTC",
                                 "tokyo": "09:00-15:00 Asia/Tokyo", "ny1904": "19:00 (prev day)-04:00 America/New_York"}[sc.box],
            "box_end_cap": "box ends no later than 08:00 London",
            "box": "highest high / lowest low of all 1m bars in the box window",
            "min_box_coverage": 0.5,
            "signal_tf_min": sc.tf,
            "signal_bars": "UTC-aligned buckets of signal_tf minutes; only complete, closed buckets",
            "entry_window_min": sc.window,
            "entry_window_meaning": "signal bar must open at/after 08:00 London and close by 08:00 + window",
            "breakout": sc.breakout,
            "breakout_meaning": {"close": "signal-bar close beyond the box edge",
                                 "whole": "entire signal bar beyond the edge (low > box high / high < box low)",
                                 "buffer": f"close beyond edge + {sc.buffer_atr} x ATR14(signal tf)"}[sc.breakout],
            "buffer_atr": sc.buffer_atr,
            "strong_candle": sc.strong,
            "strong_candle_meaning": {"none": "no condition",
                                      "body50": "candle in breakout direction and |close-open| >= 50% of range",
                                      "range1atr": "candle in breakout direction and range >= ATR14 of the previous signal bars",
                                      "close25": "candle in breakout direction and close in the outer 25% of its range"}[sc.strong],
            "volume_k": sc.vol_k,
            "fresh_break": sc.fresh,
            "box_filter": sc.box_filter,
            "trend_filter": sc.trend,
            "first_signal_only": True,
        },
        "entry": {"type": "market at the open of the next 1m bar after the signal bar closes",
                  "planned_entry": "that bar's open (mid)"},
        "exits": {
            "stop_rule": stop,
            "stop_meaning": {"in25": "box edge moved 25% of box width back inside the box",
                             "mid": "box midpoint", "opp": "opposite box edge",
                             "candle": "signal-bar extreme"}.get(stop, f"{stop[3:]} x ATR14(signal tf) from planned entry"),
            "rr": rr if np.isfinite(rr) else "none",
            "target": "planned_entry + rr x (planned_entry - stop)" if np.isfinite(rr) else "no target",
            "forced_exit_london": [16, 30],
            "same_bar_stop_and_target": "assume stop",
            "management": fixes or "none",
        },
        "risk": {"risk_per_trade": "0.5% of equity (1% tested)", "max_trades_per_day": 1,
                 "position_size": "equity x risk / (|entry - stop| x value_per_point)"},
        "costs_assumed": {n: dict(spread="Dukascopy bid/ask per bar", **{k: config()["instruments"][n][k] for k in ("slip", "comm")})
                          for n in ("GER40", "UK100")},
    }
    path.write_text(yaml.safe_dump(y, sort_keys=False, allow_unicode=True))
    return y


def oos(sc, stop, rr, manage=None, label="final"):
    """THE single out-of-sample run. Writes results/oos_<label>.json; never re-runs."""
    flag = RESULTS / f"oos_{label}.json"
    if flag.exists():
        return json.load(open(flag))
    S = Setup(sc, stop, rr, allow_oos=True)
    res = {}
    for k in KS:
        tr = S.trades(k=k, manage=manage) if manage else S.trades(k=k)
        o = tr[tr.split == "OOS"]
        if k == 1.0:
            o.to_csv(RESULTS / f"oos_{label}_trades_k1.csv", index=False)
            tr.to_csv(RESULTS / f"all_trades_{label}_k1_incl_oos.csv", index=False)
        st = r_stats(o.R.values)
        rep, _, _ = full_report(o, S.all_dates(["OOS"]), risk=0.005) if len(o) else ({}, None, None)
        res[str(k)] = dict(st, **{f"eq_{x}": rep.get(x) for x in ("sharpe", "max_dd", "cagr", "final_equity")},
                           by_inst={n: r_stats(o[o.inst == n].R.values) for n in S.insts})
    to_json(res, flag)
    return res
