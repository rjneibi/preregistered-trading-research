"""CR-1b: are the passing trend rules TIMING or just less exposure?  Run-shuffle twins: the rule's own
in/out run lengths in random order (same exposure, same trade count), 1000 per half. Pre-declared:
p < 0.0125 (0.05 / 4 rules) in BOTH halves on BTC AND ETH, CFD costs."""
import numpy as np, pandas as pd
import crypto_lab as C
RNG = np.random.default_rng(3)

def runs(p):
    v = p.values; out = []; s = 0
    for k in range(1, len(v) + 1):
        if k == len(v) or v[k] != v[s]:
            out.append((v[s], k - s)); s = k
    return out

for name, mk in (("A1 SMA20", lambda c: c > c.rolling(20).mean()), ("A1 SMA50", lambda c: c > c.rolling(50).mean()),
                 ("A1 SMA100", lambda c: c > c.rolling(100).mean()), ("A2 TSMOM30", lambda c: c / c.shift(30) > 1)):
    line = []
    for sym in ("BTCUSDT", "ETHUSDT"):
        d = C.closes(sym)
        pos = mk(d["c"]).astype(float)
        for k, (a, b) in enumerate(C.HALVES):
            m = (d.index >= a) & (d.index < b)
            dh, ph = d[m], pos[m]
            sh = C.stats(C.strat_returns(dh, ph, 0.15))[2]
            R = runs(ph)
            tw = []
            for _ in range(1000):
                perm = [R[i] for i in RNG.permutation(len(R))]
                arr = np.concatenate([np.full(n, v) for v, n in perm])
                tw.append(C.stats(C.strat_returns(dh, pd.Series(arr, index=ph.index), 0.15))[2])
            p = float(np.mean(np.array(tw) >= sh))
            line.append((sym[:3], k + 1, sh, np.mean(tw), p, ph.mean()))
    ok = all(x[4] < 0.0125 for x in line)
    print(f"{name:11s} " + "  ".join(f"{s}h{k}: Sh {sh:.2f} vs twins {tw:.2f} p={p:.3f} expo {e:.0%}" for s, k, sh, tw, p, e in line)
          + f"  -> {'PASS' if ok else 'fail'}")
