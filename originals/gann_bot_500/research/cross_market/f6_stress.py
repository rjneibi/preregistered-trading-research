import numpy as np, pandas as pd, edge_lab as L
close = L.crypto_close(); r = close.pct_change(); vol = r.rolling(60).std()
def run(cols, ma=50, lag=1, cost=0.001, tgt=0.02, start=None):
    c = close[cols]; rr = r[cols]; v = vol[cols]
    sm = c.rolling(ma).mean(); sig = (c > sm).astype(float).where(sm.notna())
    w = (sig * (tgt / v)).clip(upper=1.0); n = w.notna().sum(axis=1).replace(0, np.nan); w = w.div(n, axis=0)
    pos = w.shift(lag); out = (pos * rr).sum(axis=1) - pos.diff().abs().sum(axis=1) * cost
    out = out[pos.notna().any(axis=1)]
    return out[out.index >= start] if start else out
def line(name, s):
    a, b = L.halves(s, "2022-07-01")
    print(f"{name:42s} {L.stats(s, 365)} | H1 {L.sharpe(a,365):.2f} H2 {L.sharpe(b,365):.2f}")
C = L.COINS
for ma in (20, 30, 50, 100, 200): line(f"SMA{ma}", run(C, ma))
line("SMA50, 2-day lag", run(C, lag=2)); line("SMA50, 3x cost (0.3%/side)", run(C, cost=0.003))
line("SMA50, BTC+ETH only", run(["BTC", "ETH"]))
line("SMA50, without BTC/ETH (10 alts)", run([c for c in C if c not in ("BTC", "ETH")]))
best = max(C, key=lambda c: (close[c].iloc[-1] / close[c].dropna().iloc[0]))
line(f"SMA50, drop best coin ({best})", run([c for c in C if c != best]))
line("SMA50, since 2021-01 only", run(C, start="2021-01-01"))
s = run(C); y = s.groupby(s.index.year).apply(lambda x: (1 + x).prod() - 1)
print("by year:", ", ".join(f"{k} {v:+.0%}" for k, v in y.items()))
bh = run(C, ma=1)  # ma=1 -> always long when price > itself? no: use sig all ones
