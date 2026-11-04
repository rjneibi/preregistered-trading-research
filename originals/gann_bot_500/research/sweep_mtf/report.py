"""Builds the HTML report from results/report_data.json + summary.txt. Usage: python report.py OUT.html"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "results", "report_data.json")))
NAMES = {"A": "H1 → M5", "B": "H4 → M15", "C": "H1 → M5 + H4 trend", "D": "H1 → M5, 07–20 UTC"}
rows, curves = [], []
for v in "ABCD":
    pk = d[v]["pick"]; cell = d[v]["cells"][str(pk)]
    m, i, o = cell["main"], cell["is_"], cell["oos"]
    rows.append(dict(v=v, name=NAMES[v], tgt=pk, n=m["n"], win=m["win"], gross=cell["main_gross"], net=m["avg"], pf=m["pf"],
                     dd=m["dd"], streak=m["streak"], is_=i["avg"], is_n=i["n"], oos=o["avg"], oos_n=o["n"],
                     twin_is=cell["twin_is"], twin_oos=cell["twin_oos"], stop=cell["med_stop"], t=cell["t"],
                     verdict=cell["verdict"], gates=cell["gates"]))
    curves.append(dict(v=v, name=NAMES[v], tgt=pk, ts=[x[0] for x in cell["eq"]], net=[x[1] for x in cell["eq"]],
                       zero=cell["eq_zero"]))
data = dict(rows=rows, curves=curves, samples=d["samples"])
tpl = open(os.path.join(HERE, "report_template.html"), encoding="utf-8").read()
open(sys.argv[1], "w", encoding="utf-8").write(tpl.replace("/*DATA*/null", json.dumps(data, separators=(",", ":"))))
