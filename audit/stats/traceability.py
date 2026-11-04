"""Number-traceability check. Every number in the report documents must appear in registry/, a results file, a run log or a prereg, after rounding. Exits 1 on any mismatch.
A match proves the number exists in the evidence, not that it describes the right thing. Allowed exceptions, each with a reason, live in stats/trace_allow.txt."""
import csv
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.dirname(HERE)
DOCS = ["../README.md", "../FINDINGS.md", "../METHODOLOGY.md", "../DECISIONS.md", "../FUTURE_WORK.md", "../REPRODUCE.md", "AUDIT_REPORT.md", "VERDICTS.md", "CHANGES.md", "findings/CLOCK_BUG.md", "FORWARD_TEST.md", "stats/TRIAL_COUNT.md", "infrastructure/PHASE_B_REPORT.md"]
NUM = re.compile(r"(?<![\w.#/-])[+-]?\$?\d[\d,]*(?:\.\d+)?(?:%|R\b|x\b|h\b|bp\b)?")
TXT = re.compile(r"-?\d[\d,]*\.?\d*(?:[eE][+-]?\d+)?")


def norm(s):
    s = s.replace("$", "").replace(",", "").lstrip("+-").rstrip("%Rxhbp")
    return s


def variants(v):
    out = set()
    try:
        f = abs(float(v))
    except ValueError:
        return out
    for x in (f, f * 100):
        for d in (0, 1, 2, 3, 4):
            out.add(f"{round(x, d):.{d}f}")
    return out


def harvest():
    seen = set()
    pats = ["../registry/*", "../data/MANIFEST.md", "prereg/*.md", "forward/*.json", "forward/*.log", "tools/CLEAN_RUN.json", "phaseC/*.json", "phaseC/*.csv", "phaseD/*.json", "phaseD/*.csv", "phaseE/*.json", "phaseE/*.csv", "stats/*.json", "stats/*.md", "trade_checks/*.json", "trade_checks/*.csv",
            "infrastructure/*.json", "infrastructure/*.log", "phaseC/logs_L1/*.log", "phaseC/logs_true/*.log", "phaseC/logs_recorded/*.log", "phaseC/logs_talab/*.log", "phaseC/logs_D/*.log", "phaseC/logs_partial/*.log"]
    for p in pats:
        for f in glob.glob(os.path.join(A, p)):
            if os.path.isdir(f) or f.endswith("TRIAL_COUNT.md"):
                continue
            try:
                t = open(f, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in set(TXT.findall(t)):
                m = m.replace(",", "")
                seen.add(m.lstrip("-"))
                seen |= variants(m)
    return seen


def scrub(t):
    t = re.sub(r"`[^`]*`", " ", t)
    t = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\b(?:19|20)\d\d-\d\d(?:-\d\d)?\b", " ", t)
    t = re.sub(r"\b20\d\d(?:-\d\d)?\b", " ", t)
    t = re.sub(r"\b\d\<private>/d\d(?::\d\d)?\b", " ", t)
    t = re.sub(r"\b(?:H|E|R|Q|F|V|M|B|A|C|D|S|TP|SL|DECISIONS|round|rounds|Phase|Checkpoint|gate|gates|Gate|item|section|step|top|top-)\s?-?\d+\b", " ", t)
    t = re.sub(r"\b[A-Z][A-Z0-9]*-\d+[A-Z0-9-]*\b", " ", t)
    t = re.sub(r"^\s*\d+\.\s", " ", t, flags=re.M)
    t = re.sub(r"^#+.*$", " ", t, flags=re.M)
    return t


def main():
    ev = harvest()
    allow = set()
    p = os.path.join(HERE, "trace_allow.txt")
    if os.path.exists(p):
        allow = {x.split("#")[0].strip() for x in open(p, encoding="utf-8") if x.strip() and not x.startswith("#")}
    bad, n = [], 0
    for d in DOCS:
        f = os.path.join(A, d)
        if not os.path.exists(f):
            bad.append((d, 0, "MISSING DOCUMENT"))
            continue
        for i, ln in enumerate(scrub(open(f, encoding="utf-8").read()).split("\n"), 1):
            for m in NUM.findall(ln):
                k = norm(m)
                if not k or k in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"):
                    continue
                n += 1
                if k in ev or k.rstrip("0").rstrip(".") in ev or k in allow:
                    continue
                bad.append((d, i, m))
    json.dump(dict(checked=n, unmatched=len(bad), rows=bad), open(os.path.join(HERE, "traceability.json"), "w", newline="\n"), indent=0)
    for b in bad[:80]:
        print(*b)
    print(f"checked {n}, unmatched {len(bad)}")
    sys.exit(1 if bad else 0)


main()
