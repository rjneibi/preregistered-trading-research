"""Fails if a frozen file changed. Hashes use LF line endings, so they hold on any platform. strategies.json is checked against FREEZE.sha256, and the code against the hashes inside strategies.json."""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)


def sha(p):
    return hashlib.sha256(open(p, "rb").read().replace(b"\r\n", b"\n")).hexdigest()


bad = []
want = open(os.path.join(HERE, "FREEZE.sha256"), encoding="utf-8").read().split()[0]
if sha(os.path.join(HERE, "strategies.json")) != want:
    bad.append("forward/strategies.json")
spec = json.load(open(os.path.join(HERE, "strategies.json"), encoding="utf-8"))
for rel, h in spec["code_sha256_lf"].items():
    if sha(os.path.join(TOP, rel)) != h:
        bad.append(rel)
if bad:
    print("HASH MISMATCH, frozen files changed:", *bad)
    sys.exit(1)
print("freeze intact:", len(spec["code_sha256_lf"]) + 1, "files")
