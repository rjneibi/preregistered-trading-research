"""HV verdict run — absolute-volatility regime gate (frozen prereg, verbatim).

Primary V: trade gate ON when trade ATR% (day-build ATR / entry price) >
full-sample median of the DAILY ATR% series over the entire 2010-2026 M1
history (parameter-free convention, computed once, disclosed).
Secondary Y: rolling 90d corr(daily gold returns, dDFII10) > -0.30, lagged
one day, from FRED. Gates incl. the within-era mechanism control.
"""

from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
sys.path.insert(0, str(ROOT))

from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.data import load_ohlc, resample_ohlc, wilder_atr  # noqa: E402


def pf(x) -> float:
    x = np.asarray(x, float)
    w, l = x[x > 0].sum(), x[x <= 0].sum()
    return float(w / abs(l)) if l != 0 else float("inf")


def gates_for(on: pd.DataFrame, off: pd.DataFrame, tag: str) -> dict:
    g = {
        f"{tag}1_on_pf_ge_1.30_n_ge_150": pf(on.net_med) >= 1.30 and len(on) >= 150,
        f"{tag}2_off_pf_le_1.05": pf(off.net_med) <= 1.05,
        f"{tag}3_within_era_control": (
            (pf(on[on.era == "new"].net_med) - pf(off[off.era == "new"].net_med) >= 0.20)
            and (pf(on[on.era == "old"].net_med) >= pf(off[off.era == "old"].net_med))
        ),
        f"{tag}4_p90_on_ge_1.15": pf(on.net_p90) >= 1.15,
    }
    return g


def report(name, on, off):
    for era in ("old", "new"):
        o, f_ = on[on.era == era], off[off.era == era]
        print(f"  {name} {era}: ON n={len(o)} PF={pf(o.net_med):.3f} | "
              f"OFF n={len(f_)} PF={pf(f_.net_med):.3f} | "
              f"gap {pf(o.net_med)-pf(f_.net_med):+.3f}")
    print(f"  {name} full: ON n={len(on)} PF={pf(on.net_med):.3f} "
          f"p90={pf(on.net_p90):.3f} | OFF n={len(off)} "
          f"PF={pf(off.net_med):.3f}")


def main() -> int:
    cfg = load_config(ROOT / "config.yaml")
    trades = pd.read_csv(RESULTS / "verdict_trades.csv",
                         parse_dates=["event_ts"])
    print("computing full-history daily ATR% series (2010-2026) ...", flush=True)
    m1 = load_ohlc(resolve_path(cfg, cfg.data.m1_path), data_tz=cfg.data.data_tz)
    h1 = resample_ohlc(m1, "1h")
    atr_h1 = wilder_atr(h1, 14)
    d1 = resample_ohlc(m1, "1D")
    pos = h1.index.searchsorted(d1.index - pd.Timedelta(hours=1), side="right") - 1
    ok = pos >= 0
    daily_atrpct = pd.Series(atr_h1.to_numpy()[pos[ok]]
                             / d1["open"].to_numpy()[ok], index=d1.index[ok]).dropna()
    V_MEDIAN = float(daily_atrpct.median())
    print(f"daily ATR% median (parameter-free gate): {V_MEDIAN:.6f} "
          f"({V_MEDIAN*100:.3f}%) over {len(daily_atrpct):,} days")

    trades["atr_pct"] = trades.atr / trades.entry_px
    v_on = trades[trades.atr_pct > V_MEDIAN]
    v_off = trades[trades.atr_pct <= V_MEDIAN]
    print("\n== PRIMARY V: absolute ATR% gate ==")
    report("V", v_on, v_off)
    gv = gates_for(v_on, v_off, "V")
    v_pass = all(gv.values())
    print(f"  gates: {gv}\n  V {'PASS' if v_pass else 'FAIL'}")

    # ── secondary Y: real-yield correlation state (FRED DFII10) ─────────
    y_res = {}
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10"
        raw = urllib.request.urlopen(url, timeout=60).read().decode()
        fred = pd.read_csv(io.StringIO(raw))
        fred.columns = ["dt", "dfii10"]
        fred["dt"] = pd.to_datetime(fred.dt)
        fred["dfii10"] = pd.to_numeric(fred.dfii10, errors="coerce")
        fred = fred.dropna().set_index("dt")
        gold_d = d1["close"].copy()
        gold_d.index = gold_d.index.tz_localize(None).normalize()
        both = pd.concat([gold_d.pct_change().rename("g"),
                          fred.dfii10.diff().rename("y")], axis=1).dropna()
        corr = both.g.rolling(90).corr(both.y).shift(1)   # lag one day
        day = trades.event_ts.dt.tz_convert("UTC").dt.normalize().dt.tz_localize(None)
        c_at = corr.reindex(day, method="ffill").to_numpy()
        y_on = trades[c_at > -0.30]
        y_off = trades[~(c_at > -0.30)]
        print("\n== SECONDARY Y: real-yield correlation state ==")
        report("Y", y_on, y_off)
        gy = gates_for(y_on, y_off, "Y")
        y_pass = all(gy.values())
        displace = (y_pass and v_pass is not None
                    and pf(y_on.net_med) >= pf(v_on.net_med) + 0.05
                    and pf(y_on[y_on.era == "old"].net_med)
                    >= pf(v_on[v_on.era == "old"].net_med) + 0.05
                    and pf(y_on[y_on.era == "new"].net_med)
                    >= pf(v_on[v_on.era == "new"].net_med) + 0.05)
        print(f"  gates: {gy}\n  Y {'PASS' if y_pass else 'FAIL'} "
              f"(displaces V: {displace})")
        y_res = {"gates": gy, "pass": bool(y_pass), "displaces": bool(displace),
                 "n_on": int(len(y_on)), "pf_on": pf(y_on.net_med)}
    except Exception as e:
        print(f"\nsecondary Y unavailable ({e}) — recorded, primary decides")
        y_res = {"error": str(e)}

    verdict = ("HV PASS: absolute-vol regime gate certified -> resolves the "
               "standing risk disclosure; ops prereg for a live regime "
               "kill-switch is next" if v_pass else
               "HV FAIL: the era boundary remains unexplained; the "
               "live-deployment risk disclosure stands and HARDENS")
    print(f"\n== {verdict} ==")
    out = {"v_median": V_MEDIAN, "v": {"gates": gv, "pass": bool(v_pass),
           "on": {e: {"n": int(len(v_on[v_on.era == e])),
                      "pf": pf(v_on[v_on.era == e].net_med)} for e in ("old", "new")},
           "off": {e: {"n": int(len(v_off[v_off.era == e])),
                       "pf": pf(v_off[v_off.era == e].net_med)} for e in ("old", "new")}},
           "y": y_res, "verdict": verdict}
    (RESULTS / "HV_run.json").write_text(json.dumps(out, indent=1, default=str))
    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  HV VERDICT (frozen prereg): {verdict}\n")
        for k, v in gv.items():
            f.write(f"            HV gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            V median {V_MEDIAN*100:.3f}%; ON "
                f"old {out['v']['on']['old']} new {out['v']['on']['new']}; "
                f"OFF old {out['v']['off']['old']} new {out['v']['off']['new']}; "
                f"Y: {json.dumps(y_res, default=str)[:200]}; predictions "
                f"(blind) Rashed FAIL-low, Claude FAIL-medium\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
