"""Compares every committed result file with the clean rerun, with line endings and path tokens normalised. Writes tools/CLEAN_RUN.json into the clean tree. A file the rerun did not rewrite counts as not regenerated, never as a match. Exit 1 if an output differs or was not regenerated and has no stated reason.
Usage: check_hashes.py <committed audit> <clean audit> <clean repo> <full|public>"""
import datetime
import glob
import hashlib
import json
import os
import sys

src, new, repo, tier = sys.argv[1:5]
PAT = ["phaseC/*.json", "phaseC/*.csv", "phaseD/*.json", "phaseD/*.csv", "phaseE/*.json", "phaseE/*.csv", "stats/*.json", "trade_checks/*.json", "infrastructure/*.json", "VERDICTS.md", "stats/TRIAL_COUNT.md"]
SKIP = ("first_run", "second_run", "third_run", "traceability.json", "data_check")
R = os.path.abspath(repo).replace(os.sep, "/")
D = os.path.abspath(os.environ.get("DATA_DIR", R)).replace(os.sep, "/")
PAIRS = [(f"{D}/gann_bot_500", "@GANN_ROOT@"), (f"{R}/originals/gann_bot_500", "@GANN_ROOT@"), (f"{R}/originals/london-breakout", "@LBO_ROOT@"), (f"{R}/audit", "@AUDIT@"), ("originals/gann_bot_500", "@GANN_ROOT@"), ("originals/london-breakout", "@LBO_ROOT@")]
PAIRS = [(a.encode(), b.encode()) for a, b in PAIRS] + [(a.replace("/", "\\\\").encode(), b.encode()) for a, b in PAIRS]


def sha(p):
    b = open(p, "rb").read().replace(b"\r\n", b"\n")
    for x, y in PAIRS:
        b = b.replace(x, y)
    return hashlib.sha256(b).hexdigest()


def table(name):
    out = {}
    p = os.path.join(src, "tools", name)
    if os.path.exists(p):
        for x in open(p, encoding="utf-8"):
            if "|" in x:
                a, b = x.split("|", 1)
                out[a.strip()] = b.strip()
    return out


why = table("expected_diffs.txt")
if tier == "public":
    why.update(table("outputs_broker.txt"))
same, diff, missing, stale = [], [], [], []
t0 = os.path.getmtime(os.path.join(new, "tools", "clean_logs", "sources.log"))
for pat in PAT:
    for f in sorted(glob.glob(os.path.join(src, pat))):
        r = os.path.relpath(f, src).replace("\\", "/")
        if any(s in r for s in SKIP):
            continue
        g = os.path.join(new, r)
        if not os.path.exists(g):
            missing.append(r)
        elif os.path.getmtime(g) < t0:
            stale.append(r)
        elif sha(f) == sha(g):
            same.append(r)
        else:
            diff.append(r)
stages = open(os.path.join(new, "tools", "clean_logs", "_stages.txt")).read().splitlines()
bad = [s for s in stages if " rc=0 " not in s and " rc=skip " not in s and " rc=expected-" not in s]
skipped = [s.split()[0] for s in stages if " rc=skip " in s]
expected = [s for s in stages if " rc=expected-" in s]
for f in glob.glob(os.path.join(new, "phaseC", "logs*", "_status.txt")):
    bad += [os.path.basename(os.path.dirname(f)) + " " + x for x in open(f).read().splitlines() if " rc=0" not in x and tier == "full"]
open_ = [d for d in diff + missing + stale if d not in why]
json.dump(dict(tier=tier, run_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), same=len(same), differ=diff, missing=missing, not_regenerated=stale, unexplained=open_, explained={k: why[k] for k in diff + missing + stale if k in why}, stages_failed=bad, stages_broker_ran=expected, stages_skipped=skipped, stages=len(stages)), open(os.path.join(new, "tools", "CLEAN_RUN.json"), "w"), indent=1)
print(f"tier {tier}: same {len(same)}, differ {len(diff)}, missing {len(missing)}, not regenerated {len(stale)}, unexplained {len(open_)}, stages failed {len(bad)}, expected broker failures {len(expected)}, skipped {len(skipped)} of {len(stages)}")
for x in bad[:30]:
    print(" stage", x)
for x in open_[:60]:
    print(" file", x)
sys.exit(1 if open_ or bad else 0)
