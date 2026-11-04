"""Builds FORWARD_SUMMARY.md from FORWARD_LOG.csv. Reporting only, and not part of the freeze. Each rule on each market counts once, as set in rule_groups.json."""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MIN_N = 100


def main(log=os.path.join(HERE, "FORWARD_LOG.csv"), out=os.path.join(HERE, "FORWARD_SUMMARY.md")):
    G = json.load(open(os.path.join(HERE, "rule_groups.json"), encoding="utf-8"))
    rows = list(csv.DictReader(open(log, encoding="utf-8"))) if os.path.exists(log) else []
    known = {(x["strategy"], m) for g in G["groups"] for x in g["legs"] for m in x["markets"]}
    known |= {(x["strategy"], x["market"]) for g in G["groups"] for x in g["dropped"]}
    odd = {(r["strategy"], r["market"]) for r in rows} - known
    if odd:
        sys.exit(f"rows outside rule_groups.json: {sorted(odd)}")
    L = [f"# Forward summary: {G['label']}", "", "Built by `summarize.py` from `FORWARD_LOG.csv`. Each rule on each market counts once. Nothing here is a claim about future returns.", "",
         "| Rule | Family | Market | n | Mean net return | Label |", "|---|---|---|---:|---:|---|"]
    for g in G["groups"]:
        for leg in g["legs"]:
            for m in leg["markets"]:
                x = [float(r["net_return"]) for r in rows if r["strategy"] == leg["strategy"] and r["market"] == m]
                mean = f"{sum(x) / len(x):.4%}" if x else "n/a"
                L.append(f"| {g['rule']} | {g['family']} | {m} | {len(x)} | {mean} | {'INSUFFICIENT SAMPLE' if len(x) < MIN_N else 'monitored, no edge claimed'} |")
    L += ["", "FW-TUNE-1-DIP on US500 is logged but not counted here, because it repeats FW-XM-1-A1. The two US500 rules are one family, so read them as related, not as two confirmations.", ""]
    open(out, "w", encoding="utf-8", newline="\n").write("\n".join(L))
    print(len(rows), "rows summarised")


if __name__ == "__main__":
    main()
