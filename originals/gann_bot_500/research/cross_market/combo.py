"""F9 (EDGE-1): the combined book. Every strategy that passed its own test, as MONTHLY returns, each scaled
to 10%/yr volatility, equal risk.  Question: how correlated are they, and what does the mix do vs any one?"""
import os
import sys

import numpy as np
import pandas as pd

import edge_lab as L
import scalp_lab as S
import swing_lab as W

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "signal_ai"))


def from_trades(dates, rets, start, end):
    """Monthly sum of trade returns; months inside the data span with no trade count as 0%."""
    s = pd.Series(rets, index=pd.to_datetime(dates))
    m = s.groupby(s.index.to_period("M")).sum()
    full = pd.period_range(pd.Timestamp(start).to_period("M"), pd.Timestamp(end).to_period("M"), freq="M")
    return m.reindex(full, fill_value=0.0).to_timestamp()


def monthly(daily):
    d = pd.Series(daily).dropna()
    return (1 + d).groupby(d.index.to_period("M")).prod().sub(1).to_timestamp()


streams = {}
d, sp = W.prep("US500")
for nm, lab in (("MR1", "Index dip RSI2"), ("MR2", "Index dip IBS")):
    side, sig, ex = W.rule(nm, d)
    tr = W.run(d, sp, side, sig, ex)
    streams[lab] = from_trades([t for t, _, _ in tr], [r * 1 / 3 for _, r, _ in tr], d.index[252], d.index[-1])   # live sizing 1/3 notional

df, cost = S.load_index("USTEC")
orb = S.rules_index(S.days(df), cost)["O1 ORB-range 30m"]
rows = []
for k, side, (net, g, c), (ent, st, *_ ) in orb:
    risk = abs(ent - st)
    if st is None or risk / ent < 0.0015:                        # live range floor
        continue
    rows.append((pd.Timestamp(k), 0.0025 * net / risk))          # 0.25% equity risk per trade
streams["Nasdaq ORB"] = from_trades([a for a, _ in rows], [b for _, b in rows], df.index[0], df.index[-1])

res = pd.read_pickle(os.path.join(HERE, "edge_results.pkl")) if os.path.exists(os.path.join(HERE, "edge_results.pkl")) else {}
streams["Crypto trend (12 coins)"] = monthly(res["f6"] if "f6" in res else L.f6()[0])
if "f1" in res:
    streams["Multi-asset trend (TSMOM)"] = monthly(res["f1"])
if "f4" in res:
    streams["Crypto funding carry"] = monthly(res["f4"])

M = pd.DataFrame(streams)
M = M[M.index >= "2012-01-01"]
print("months per stream:", {k: int(v.notna().sum()) for k, v in M.items()})
scaled = M.apply(lambda s: s * (0.10 / (s.std() * np.sqrt(12))))
print("\nper stream (scaled to 10% vol):")
for k in scaled:
    s = scaled[k].dropna()
    print(f"  {k:28s} Sharpe {L.sharpe(s, 12):5.2f}  worst month {s.min():+6.1%}  maxDD {L.maxdd(s):5.1%}  ({s.index[0]:%Y-%m}..)")
print("\ncorrelation of monthly returns:")
print(scaled.corr().round(2).to_string())
common = scaled.dropna(how="any")
book = common.mean(axis=1)
print(f"\nCOMBINED equal-risk book, {common.index[0]:%Y-%m}..{common.index[-1]:%Y-%m} ({len(common)} months, all streams live):")
print(f"  Sharpe {L.sharpe(book, 12):.2f}  vol {book.std() * np.sqrt(12):.1%}  maxDD {L.maxdd(book):.1%}  "
      f"worst month {book.min():+.1%}  losing months {(book < 0).mean():.0%}")
for k in common:
    print(f"  vs {k:28s} alone over same months: Sharpe {L.sharpe(common[k], 12):5.2f}  maxDD {L.maxdd(common[k]):5.1%}")
lev = 0.10 / (book.std() * np.sqrt(12))
b2 = book * lev
print(f"  book re-levered to 10% vol: CAGR {((1 + b2).prod() ** (12 / len(b2)) - 1):+.1%}  maxDD {L.maxdd(b2):.1%}")
y = (1 + b2).groupby(b2.index.year).prod() - 1
print("  by year:", ", ".join(f"{k} {v:+.0%}" for k, v in y.items()))
