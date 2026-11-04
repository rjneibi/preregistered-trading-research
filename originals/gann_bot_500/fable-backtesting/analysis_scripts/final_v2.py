"""FINAL_v2 composite: session(12/16/20 UTC) + TP8/SL12/ts24h, with and
without ADX-gated pyramid. Both eras + equity curve + trades CSV."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(r"@GANN_ROOT@")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "research" / "flip_scalp"))

import run_flip_scalp as rfs
from research.dr_backtest.data_prep import (
    load_m1, resample_ohlc, resample_d1_utc,
)
from research.dr_backtest.metrics import basic_stats
from innovate_r3s3 import SimX, r3s3_level, stats, OUT
from regime_switch import wilder_adx_d1, regime_at, load_events, P0, ADX_TH

all_trades = []
for era in ("old", "new"):
    if era == "new":
        start, end, fname, scale = (pd.Timestamp("2021-06-19T00:00:00Z"),
                                    pd.Timestamp("2026-06-19T17:57:00Z"),
                                    "events.jsonl", False)
    else:
        start, end, fname, scale = (pd.Timestamp("2015-06-19T00:00:00Z"),
                                    pd.Timestamp("2021-06-18T23:59:00Z"),
                                    "events_2015_2021.jsonl", True)
    rfs.BT_START, rfs.BT_END = start, end
    rfs.apply_config()
    m1 = load_m1(start - pd.Timedelta(days=60), end)
    h4 = resample_ohlc(m1, "4h")
    d1 = resample_d1_utc(m1)
    sim = SimX(m1, h4)
    adx = wilder_adx_d1(d1)
    ev = [e for e in load_events(fname)
          if pd.Timestamp(e["entry_ts"]).hour in (12, 16, 20)]

    res_plain, res_gated = [], []
    for e in ev:
        ts = pd.Timestamp(e["entry_ts"])
        k = (e["h4_close"] / P0) if scale else 1.0
        kw = dict(tp=8. * k, sl=12. * k, level=r3s3_level(e))
        p_plain = sim.run(e, **kw)
        a = regime_at(adx, ts)
        gate = np.isfinite(a) and a > ADX_TH
        p_gated = sim.run(e, pyramid_at=4. * k, **kw) if gate else p_plain
        res_plain.append(p_plain)
        res_gated.append(p_gated)
        all_trades.append({"era": era, "entry_ts": e["entry_ts"],
                           "direction": e["direction"],
                           "zones": "+".join(e["zone_sources"]),
                           "entry_price": e["h4_close"],
                           "pnl_v2": round(p_plain / 100 * 100, 0),
                           "pnl_v2_pyr": round(p_gated / 100 * 100, 0)})
    print(f"=== era {era} (n={len(ev)}) ===")
    print(pd.DataFrame([stats("FINAL_v2 (session)", res_plain),
                        stats("FINAL_v2 + ADX-pyr", res_gated)])
          .to_string(index=False))

df = pd.DataFrame(all_trades).sort_values("entry_ts").reset_index(drop=True)
df.to_csv(OUT / "final_v2_trades.csv", index=False)
for col, lbl, color in [("pnl_v2", "FINAL_v2", "#1b5e20"),
                        ("pnl_v2_pyr", "FINAL_v2 + ADX pyramid", "#b26a00")]:
    cum = df[col].cumsum()
    mdd = (cum.cummax() - cum).max()
    s = basic_stats(list(df[col]))
    print(f"{lbl} POOLED 2015-26: n={s['n']} wr={s['win_rate']} pf={s['pf']} "
          f"net=${df[col].sum():,.0f} maxDD=${mdd:,.0f}")

fig, ax = plt.subplots(figsize=(12, 5))
ts = pd.to_datetime(df.entry_ts)
ax.plot(ts, df.pnl_v2.cumsum(), lw=1.3, color="#1b5e20", label="FINAL_v2")
ax.plot(ts, df.pnl_v2_pyr.cumsum(), lw=1.3, color="#b26a00",
        label="FINAL_v2 + ADX-gated pyramid")
ax.axhline(0, color="grey", lw=0.8)
ax.axvline(pd.Timestamp("2021-06-19"), color="grey", ls="--", lw=0.8)
ax.text(pd.Timestamp("2021-08-01"), ax.get_ylim()[0], "tuning era ->",
        fontsize=8, color="grey")
ax.set_title("FINAL_v2: R3/S3 flip, no-Mon, London/NY closes only, "
             "TP$8/SL$12/ts24h — 11 years, 1 lot (old era price-scaled)")
ax.set_ylabel("cumulative $")
ax.legend(loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "final_v2_equity.png", dpi=130)
print("wrote final_v2_trades.csv + final_v2_equity.png")
