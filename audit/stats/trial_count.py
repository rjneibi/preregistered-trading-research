"""Builds stats/TRIAL_COUNT.md and stats/family_counts.json from registry/trial_ledger.csv, so the DSR count can be checked by a reader."""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "..", "..", "registry", "trial_ledger.csv"), encoding="utf-8", newline="")))
FAM = {}
for r in rows:
    f = r["programme_or_family"]
    n = int(float(r["n_variants"] or 0))
    a = FAM.setdefault(f, dict(rows=0, variants=0))
    a["rows"] += 1
    a["variants"] += n
total = sum(v["variants"] for v in FAM.values())
head = sorted(FAM.items(), key=lambda kv: -kv[1]["variants"])
# Family DSR counts for the four fragile results: variants in the programme that produced each one, including the family's own grid.
MAP = {"XM-1-A1": ["XM-1-A1", "XM-1-OTHERS"], "SW-1": ["SW-1"], "EDGE-1-F6": ["CR-1", "EDGE-1-F1", "EDGE-1-F3-F5-F7", "EDGE-1-F6", "EDGE-1-F9"], "TUNE-1-DIP": ["TUNE-1-DIP"]}
byid = {r["trial_id"]: r for r in rows}
fam_n = {}
for k, ids in MAP.items():
    fam_n[k] = sum(int(float(byid[i]["n_variants"] or 0)) for i in ids if i in byid)
    assert all(i in byid for i in ids), [i for i in ids if i not in byid]
CP = os.path.join(HERE, "..", "..", "registry", "ledger_corrections.csv")
COR = list(csv.DictReader(open(CP, encoding="utf-8", newline="")))
added = sum(int(c["added"]) for c in COR)
for c in COR:
    assert c["trial_id"] in byid and int(float(byid[c["trial_id"]]["n_variants"] or 0)) == int(c["ledger_n_variants"]), c["trial_id"]
fam_c = {k: v + sum(int(c["added"]) for c in COR if c["trial_id"] in MAP[k]) for k, v in fam_n.items()}
json.dump(dict(total=total, rows=len(rows), families=FAM, fragile_family_n=fam_n, corrected_total=total + added, corrected_fragile_family_n=fam_c), open(os.path.join(HERE, "family_counts.json"), "w"), indent=1)
L = ["# How the trial count is built", "",
     f"Generated from `registry/trial_ledger.csv` by `stats/trial_count.py`. Current total: **{total:,} variants** over {len(rows)} ledger rows.", "",
     "## What counts as a trial", "",
     "- One variant is one distinct rule, parameter set and market combination that produced a result, whether or not anyone looked at it closely.",
     "- A grid counts every cell. An optimiser counts every configuration it evaluated. TVS-1's 64,521 configs are all counted.",
     "- Audit reruns of the same rule count 0, because they add no new choice. The one exception is TVS-1's rerun, which drew 64,431 mostly new configs, and they count (DECISIONS 46). New audit experiments count their stated variants.",
     "- Analyst-derived work stays in the count although it is not published or tested. Removing it would flatter the rest.",
     "- Row counts with `count_basis` marked as a floor are lower bounds.",
     "- Blank counts are read as 0. NQ-TRANSFER is the one case that matters, and it has no recorded count.", "",
     "## Primary and secondary DSR", "",
     f"The primary DSR uses the ledger total, {total:,} now. Phase C used the floor at that time, 114,500, and those files keep it. The rise comes from TVS-1's fresh draw of 64,431 configs and Phase E's stated variants. It treats all work as one search, including unrelated markets.",
     "That is harsh, and it is deliberate: this is one researcher selecting what to look at next from everything tried so far.",
     "The secondary DSR uses the variants inside the programme that produced the result. It answers a narrower question, and passing it does not change a verdict.",
     "Read the DSR as an order of magnitude. Two inputs pull opposite ways and neither is measured. Trial Sharpe variance uses the null value 1/T (DECISIONS 24), which understates the hurdle. N treats every variant as independent, which overstates it, since TVS-1 and its redraw sample one grid and LBO-1's cells are near-duplicates.",
     f"At {total:,} trials a DSR of 0.95 needs a t-statistic of about 6.2, so almost nothing can clear this gate. Failing it alone carries little information, which is why VERDICTS also shows N as dated at each result and the other weaknesses.", "",
     "## Counts corrected by the second release review", "",
     f"A release review in November 2026 counted the configurations in the published code and results and found {len(COR)} rows where the ledger counts fewer than were run. The ledger is left as it was, and the counts sit beside it in `registry/ledger_corrections.csv`. With them the total is **{total + added:,}** rather than {total:,}.",
     "The deflated Sharpe in VERDICTS keeps the ledger count. A larger count only raises the hurdle, and the t-statistic it needs grows with the log of the count, so no verdict can change. Family counts for the fragile results become: " + ", ".join(f"{k} {fam_n[k]:,} to {fam_c[k]:,}" for k in fam_n) + ".", "",
     "| Trial | Ledger | Counted | Basis |", "|---|---:|---:|---|"] + [f"| {c['trial_id']} | {int(c['ledger_n_variants']):,} | {int(c['counted_n_variants']):,} | {c['count_basis']} |" for c in COR] + ["",
     "## By family", "", "| Family | Rows | Variants |", "|---|---:|---:|"]
L += [f"| {k} | {v['rows']} | {v['variants']:,} |" for k, v in head]
L += ["", "## Family counts used for the secondary DSR", "", "| Result | Ledger rows counted | Family N |", "|---|---|---:|"]
L += [f"| {k} | {', '.join(MAP[k])} | {fam_n[k]:,} |" for k in MAP]
open(os.path.join(HERE, "TRIAL_COUNT.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print(total, len(rows), fam_n, head[:8])
