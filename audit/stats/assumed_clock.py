"""Gold results with and without 2010-2012 (ASSUMED-CLOCK). Reads the same scripts' logs from rs_recorded and rs_no1012. Results that start after 2012 are listed as unaffected."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
L = os.path.join(HERE, "..", "phaseC", "logs_L1")


def read(tag, p):
    f = f"recorded.{p.replace('/', '.')}_py.log" if tag == "with" else f"no1012.{p.replace('/', '.')}.py.log"
    return open(os.path.join(L, f), encoding="utf-8", errors="ignore").read().splitlines()


def line(tag, p, start):
    for x in read(tag, p):
        if x.strip().startswith(start):
            return re.sub(r"\s+", " ", x.strip())
    return None


def after(tag, p, head, start):
    on = False
    for x in read(tag, p):
        if x.strip() == head:
            on = True
        elif on and x.strip().startswith(start):
            return re.sub(r"\s+", " ", x.strip())
    return None


def fails(tag, p):
    t = read(tag, p)
    return sum("FAIL" in x for x in t), sum(x.strip().endswith("PASS") or "-> PASS" in x for x in t)


rows = []
for rid, p, get in (("D-REVIVAL", "d_revival.sim", lambda t: line(t, "d_revival.sim", "D faithful")),
                    ("WHY-1 pivots", "d_revival.diag", lambda t: line(t, "d_revival.diag", "pivot")),
                    ("BOT-LAB-1 buy & hold control", "d_revival.anomalies", lambda t: line(t, "d_revival.anomalies", "buy & hold")),
                    ("BOT-LAB-1 Asia long", "d_revival.asia", lambda t: line(t, "d_revival.asia", "long 01-09 spread 0.6")),
                    ("EXIT-2-FLIP E5", "exit2.exit2", lambda t: after(t, "exit2.exit2", "E5", "ALL:")),
                    ("GOLD-LIT-1 H-A1", "gold_lit.gold_lit", lambda t: after(t, "gold_lit.gold_lit", [x for x in read(t, "gold_lit.gold_lit") if x.startswith("H-A1")][0].strip(), "ALL")),
                    ("PA-1 H4 PIN", "price_action.pa1", lambda t: line(t, "price_action.pa1", "H4 PIN ")),
                    ("SWEEP-MTF-1 variant A", "sweep_mtf.sweep_mtf", lambda t: line(t, "sweep_mtf.sweep_mtf", "ALL 2010-26"))):
    a, b = get("with"), get("without") if False else get("no")
    fa, fb = fails("with", p), fails("no", p)
    rows.append(dict(id=rid, with_2010_2012=a, without=b, fail_lines_with=fa[0], fail_lines_without=fb[0], pass_lines_with=fa[1], pass_lines_without=fb[1]))
unaffected = ["H-family, FINAL_v3, FINAL_v4, XAU-R3S3-FADE: start 2015-06", "DR-EDGE-SCREEN: 2021-06 on", "FR-M: 2021-06 on", "XAU-FLIP-RAW: 2021-06 on", "FR-L: see its script", "TA-LAB, PA-15-30, PA-30-MAX5: 2022-07 on", "ML-1: 2014 on", "CRT-FVG-1, LBO-1: Dukascopy, measured clock"]
rep = dict(label="ASSUMED-CLOCK", note="2010-2012 HistData stamps have no Dukascopy overlap. The US switch rule there is an assumption, supported only by reopen and break hours.", rows=rows, unaffected=unaffected)
json.dump(rep, open(os.path.join(HERE, "assumed_clock.json"), "w"), indent=1)
for r in rows:
    print(r["id"], "\n  W ", (r["with_2010_2012"] or "")[:150], "\n  WO", (r["without"] or "")[:150], r["fail_lines_with"], r["fail_lines_without"], r["pass_lines_with"], r["pass_lines_without"])
