"""Truncation test: a signal known at time T must be identical whether or not later data exists.

The round-4 sweep build carries a leak the programme already documented. It is the positive control:
if this harness cannot flag it, a clean result from the harness means nothing.
"""
import contextlib
import io
import json
import os
import runpy
import sys
import traceback

import numpy as np
import pandas as pd

R = "@GANN_ROOT@/research"
C = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_copy")
sys.path[:0] = [R + "/ta_lab", R + "/pa_lab", R + "/d_revival", R + "/sweep_mtf", os.path.join(C, "goldbot")]
rep = {}
rng = np.random.default_rng(20261031)


def tr(d, n):
    return {k: (v[:n] if isinstance(v, np.ndarray) else v) for k, v in d.items()}


def compare(full, f, d, cuts, margin=int(os.environ.get("LOOK_MARGIN", "1"))):
    """f(d) returns a sorted list of tuples whose first element is the bar index the signal is acted on."""
    bad = []
    tot = 0
    for n in cuts:
        a = [x for x in full if x[0] < n - margin]
        b = [x for x in f(tr(d, n)) if x[0] < n - margin]
        tot += len(a)
        if a != b:
            sa, sb = set(a), set(b)
            bad.append(dict(cut=int(n), only_full=len(sa - sb), only_trunc=len(sb - sa)))
    return dict(cuts=len(cuts), signals_compared=tot, cuts_differing=len(bad), example=bad[:3], clean=not bad)


def talab():
    import lab
    with contextlib.redirect_stdout(io.StringIO()):
        g4 = runpy.run_path(R + "/ta_lab/round4.py", run_name="r4")
        g12 = runpy.run_path(R + "/ta_lab/round12.py", run_name="r12")
    d = lab.load("M15")
    keep = len(d["t"]) - 40000
    d = {k: v[keep:] for k, v in d.items()}
    cuts = np.sort(rng.integers(2000, len(d["t"]) - 10, 40))

    def fold(b):
        return lambda x: sorted((o.i, o.sgn, round(o.stop, 6)) for o in b(x, 4, win_end=20))

    rep["CONTROL round4.build (known leak)"] = compare(fold(g4["build"])(d), fold(g4["build"]), d, cuts)
    rep["round12.build_fixed"] = compare(fold(g12["build_fixed"])(d), fold(g12["build_fixed"]), d, cuts)


def pa():
    import pa1
    D = pa1.load()["M30"]
    cuts = np.sort(rng.integers(3000, len(D["t"]) - 10, 25))
    for name in ("PIN", "ENG", "IB", "BO20"):
        f = lambda x, name=name: sorted((s[0], s[1], s[2] if s[2] is None else round(s[2], 6), s[3]) for s in pa1.signals(x, name))
        rep[f"pa1.signals {name}"] = compare(sorted(f(D), key=lambda z: (z[0], z[1])), lambda x: sorted(f(x), key=lambda z: (z[0], z[1])), D, cuts, margin=5)


def goldbot_events():
    from goldbot.config import load_config
    from goldbot.data import load_ohlc, resample_d1_utc, resample_ohlc, wilder_atr
    from goldbot.events import generate_events_final
    cfg = load_config(os.path.join(C, "goldbot", "config.yaml"))
    m1 = load_ohlc(R + "/data/xauusd_m1_histdata.csv", data_tz="UTC")
    m1 = m1[(m1.index >= "2022-06-01") & (m1.index < "2025-01-01")]
    start = pd.Timestamp("2023-01-01", tz="UTC")

    def ev(m):
        h1, h4, d1 = resample_ohlc(m, "1h"), resample_ohlc(m, "4h"), resample_d1_utc(m)
        e = generate_events_final(h1, h4, d1, wilder_atr(h1, cfg.exits.final.atr.period if hasattr(cfg.exits.final.atr, "period") else 14), cfg, start, m.index[-1])
        return e

    full = ev(m1)
    bad = []
    cols = ["event_ts", "side", "level"]
    tot = 0
    for cut in pd.date_range("2023-03-07 17:30", "2024-12-10 15:45", periods=12, tz="UTC"):
        a = full[full.event_ts < cut - pd.Timedelta(hours=1)][cols].reset_index(drop=True)
        b = ev(m1[m1.index < cut])
        b = b[b.event_ts < cut - pd.Timedelta(hours=1)][cols].reset_index(drop=True)
        tot += len(a)
        if len(a) != len(b) or not (a.values == b.values).all():
            bad.append(dict(cut=str(cut), full=len(a), trunc=len(b)))
    rep["goldbot.generate_events_final"] = dict(cuts=12, signals_compared=tot, full_events=len(full), cuts_differing=len(bad), example=bad[:3], clean=not bad)


def sweep():
    with contextlib.redirect_stdout(io.StringIO()):
        import sweep_mtf as s
    a = int(np.searchsorted(s.t, 1704067200))
    base = {k: getattr(s, k)[a:] for k in ("t", "o", "h", "l", "c")}

    def go(n):
        for k, v in base.items():
            setattr(s, k, v[:n])
        s.N = n
        s.H4 = s.bars(240, 0.5)
        s.H4["ema"] = s.ema(s.H4["c"], 50)
        return sorted((x["k"], x["sgn"], round(float(x["stop"]), 6)) for x in s.setups(60, 5, "h4ema"))

    n0 = len(base["t"])
    full = go(n0)
    cuts = np.sort(rng.integers(100000, n0 - 20, 10))
    bad = []
    tot = 0
    for n in cuts:
        x = [z for z in full if z[0] < n - 60]
        y = [z for z in go(int(n)) if z[0] < n - 60]
        tot += len(x)
        if x != y:
            bad.append(dict(cut=int(n), only_full=len(set(x) - set(y)), only_trunc=len(set(y) - set(x))))
    rep["sweep_mtf.setups h4ema"] = dict(cuts=len(cuts), signals_compared=tot, cuts_differing=len(bad), example=bad[:3], clean=not bad)


for fn in (talab, pa, goldbot_events, sweep):
    try:
        fn()
    except Exception:
        rep["ERROR " + fn.__name__] = traceback.format_exc()[-500:]
    print(fn.__name__, "done", flush=True)
json.dump(rep, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lookahead.json"), "w"), indent=1)
for k, v in rep.items():
    print(k, v if isinstance(v, str) else {x: v[x] for x in ("signals_compared", "cuts_differing", "clean")}, v.get("example", "")[:1] if isinstance(v, dict) else "")
