"""Month-by-month profile of each passing stream (descriptive): how often a month loses."""
import numpy as np, pandas as pd
import importlib.util, sys, os, io, contextlib
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "combo.py")).read().split("M = pd.DataFrame(streams)")[0]
g = {"__file__": os.path.abspath("combo.py"), "__name__": "x"}
with contextlib.redirect_stdout(io.StringIO()):
    exec(src, g)
M = pd.DataFrame(g["streams"]).drop(columns=["Multi-asset trend (TSMOM)"], errors="ignore"); M = M[M.index >= "2012-01-01"]
for k in M:
    s = M[k].dropna()
    print(f"{k:28s} {s.index[0]:%Y-%m} months {len(s):3d}  losing {(s<0).mean():4.0%}  no-trade {(s==0).mean():4.0%}  "
          f"worst {s.min():+6.2%}  avg {s.mean():+6.2%}")
sc = M.apply(lambda s: s * (0.10 / (s.std() * np.sqrt(12))))
c = sc.dropna(how="any"); b = c.mean(axis=1)
print(f"COMBINED book {c.index[0]:%Y-%m}..{c.index[-1]:%Y-%m}: months {len(c)} losing {(b<0).mean():.0%} worst {b.min():+.2%} avg {b.mean():+.2%}")
print("losing months:", ", ".join(f"{d:%Y-%m} {v:+.2%}" for d, v in b[b < 0].items()))
