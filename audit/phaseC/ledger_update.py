"""Replaces the GB-42-60 placeholder with the row mapping and logs Phase C runs. Reruns of stored hypotheses count 0 new variants. Idempotent."""
import csv
import os

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "registry", "trial_ledger.csv")
rows = list(csv.reader(open(P, encoding="utf-8", newline="")))
if any(r[0] == "GB-42" for r in rows):
    raise SystemExit("already updated")
head, body = rows[0], rows[1:]
MAP = [(42, "FR-M"), (43, "FR-L"), (44, "H-P"), (45, "H-N"), (46, "H3"), (47, "H-B"), (48, "HR"), (49, "SZ"), (50, "HV"), (51, "HCRT"), (52, "HSW"), ("53-60", "HPF, part of its +1 to +12 unnumbered rows")]
out = []
for r in body:
    if r[0] == "GB-42-60":
        for k, v in MAP:
            out.append([f"GB-{k}", r[1], f"Row maps to {v}", "0", r[4], "see entry", "mapped by audit, counted at its own entry", "PREREGISTRATION.md numbering and DECISIONS.log", "public"])
    else:
        out.append(r)
A = [
    ("AUD-C-01", "L1 reruns, recorded clock, 56 entries", "reproductions"),
    ("AUD-C-02", "Goldbot and zone-flip families rerun on true UTC", "corrections, 22 SUSPECT results"),
    ("AUD-C-03", "Partial-matrix reruns of H-P, SZ, HR, H-M, H-S, FR-M", "reproductions"),
    ("AUD-C-04", "TA-LAB rounds with real-gap stops", "sensitivity, no verdict moves"),
    ("AUD-C-05", "LBO and CRT symmetric gaps", "sensitivity, no verdict moves"),
    ("AUD-C-06", "Second engine on V3, V4; numpy rewrites of A1, IBS, F6, ORB-30", "cross-checks"),
    ("AUD-C-07", "Fade rebuild, cycles and DOOR-3 recomputes, FX recompute", "L2 recomputes"),
    ("AUD-C-08", "Entry delay, spreads, swap, gaps, cross-source, lookahead", "deferred checks"),
    ("AUD-C-09", "DR screen at matrix cost", "disclosure, no new rule"),
    ("AUD-C-10", "ORB-30 neighbourhood N=5 to 60 and A1, SW-1 neighbours", "robustness only, not a selection"),
]
for i, l, o in A:
    out.append([i, "audit Phase C", l, "0", "2026-10-31", o, "run log, no new hypothesis", "audit/phaseC, audit/stats, audit/trade_checks", "public"])
with open(P, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(head)
    w.writerows(out)
print(sum(int(r[3]) for r in out if r[3].isdigit()), len(out))
