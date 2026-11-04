"""How much the US500 dip rules overlap, on the full audited trade lists. Run from audit/stats with the audit venv, like parity_rules.py. Output: forward/rule_overlap.json."""
import json
import sys

import numpy as np

sys.argv = ["x"]
src = open("../forward/forward_update.py", encoding="utf-8").read().replace("\nmain()\n", "\n").replace("HERE = os.path.dirname(os.path.abspath(__file__))", "HERE = '../forward'")
g = {}
exec(compile(src, "fw", "exec"), g)
s = open("pass_audit.py", encoding="utf-8").read()
s = s[: s.rindex("main()")] if s.rstrip().endswith("main()") else s.split("if __name__")[0]
p = {"__file__": "pass_audit.py", "__name__": "pa"}
exec(compile(s, "pa", "exec"), p)
us = p["load"]("US500")
m = {k: us[k] for k in "t o h l c".split()}
if m["t"].dtype.kind == "M":
    m["t"] = m["t"].astype("datetime64[s]").astype(np.int64)
sp = us["sp"] if np.isscalar(us["sp"]) else float(np.median(us["sp"]))
a = g["dip"](m, sp, 0.05 / 365)
b = g["ibs"](m, sp, 0.05 / 365)
ix = {g["day"](t): i for i, t in enumerate(m["t"])}


def bars(ts):
    out = set()
    for x in ts:
        out |= set(range(ix[x[1]], ix[x[2]]))
    return out


A, B = bars(a), bars(b)
sa, sb = {x[0] for x in a}, {x[0] for x in b}
rep = dict(
    a1_trades=len(a),
    sw1_trades=len(b),
    a1_signals_same_day_as_sw1=len(sa & sb),
    a1_signals_same_day_as_sw1_pct=round(100 * len(sa & sb) / len(sa), 1),
    a1_days_in_market=len(A),
    sw1_days_in_market=len(B),
    days_in_both=len(A & B),
    a1_days_also_in_sw1_pct=round(100 * len(A & B) / len(A), 1),
    sw1_days_also_in_a1_pct=round(100 * len(A & B) / len(B), 1),
)
json.dump(rep, open("../forward/rule_overlap.json", "w", encoding="utf-8", newline="\n"), indent=1)
print(rep)
