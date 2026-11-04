"""The no-data level. Checks stored outputs against their hashes, runs the tests, traces every number in the docs, resolves internal links, and rejects absolute paths. About a minute. Exit 0 means all passed."""
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABS = re.compile(r"(?<![A-Za-z0-9])[C-Hc-h]:[\\/]+(?:Users|gann|Projects|MT5|Program)|/[cdf]/(?:Users|gann_bot|Projects)|/home/[a-z]+/")
TEXT = (".py", ".md", ".sh", ".yaml", ".yml", ".json", ".jsonl", ".csv", ".toml", ".txt", ".log", ".cfg", ".ini")
SKIP_DIR = {".git", ".venv", "__pycache__", ".pytest_cache", "raw", ".ruff_cache"}


def walk():
    for d, sub, fs in os.walk(ROOT):
        sub[:] = [x for x in sub if x not in SKIP_DIR and not x.startswith(".venv")]
        for f in fs:
            yield os.path.join(d, f)


def results():
    p = os.path.join(ROOT, "audit", "results.sha256")
    n, bad = 0, []
    for x in open(p, encoding="utf-8"):
        h, r = x.split(None, 1)
        q = os.path.join(ROOT, "audit", r.strip())
        n += 1
        if not os.path.exists(q) or hashlib.sha256(open(q, "rb").read().replace(b"\r\n", b"\n")).hexdigest() != h:
            bad.append(r.strip())
    print(f"results: {n} checked, {len(bad)} differ", *bad[:10])
    return not bad


def paths():
    bad = []
    me = os.path.abspath(__file__)
    for p in walk():
        if p.endswith(TEXT) and os.path.abspath(p) != me:
            t = open(p, encoding="utf-8", errors="replace").read()
            if ABS.search(t):
                bad.append(os.path.relpath(p, ROOT))
    print(f"absolute paths: {len(bad)} files", *bad[:10])
    return not bad


def links():
    bad = []
    rx = re.compile(r"\[[^\]]*\]\(([^)#\s]+)(?:#[^)]*)?\)")
    n = 0
    for p in walk():
        if p.endswith(".md") and f"{os.sep}originals{os.sep}" not in p:
            for m in rx.findall(open(p, encoding="utf-8", errors="replace").read()):
                if re.match(r"[a-z]+:", m):
                    continue
                n += 1
                if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), m))):
                    bad.append(f"{os.path.relpath(p, ROOT)} -> {m}")
    print(f"internal links: {n} checked, {len(bad)} broken", *bad[:10])
    return not bad


def run(name, *cmd, cwd=ROOT):
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", PYTHONPATH=ROOT)
    p = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True)
    print(f"{name}: rc={p.returncode}", (p.stdout + p.stderr).strip().splitlines()[-1:] )
    return p.returncode == 0


def main():
    ok = [results(), paths(), links(),
          run("tests", sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", "audit/engine/test_kat.py"),
          run("freeze", sys.executable, "-B", "audit/forward/verify_freeze.py"),
          run("traceability", sys.executable, "-B", "stats/traceability.py", cwd=os.path.join(ROOT, "audit"))]
    print("PASS" if all(ok) else "FAIL")
    sys.exit(0 if all(ok) else 1)


if __name__ == "__main__":
    main()
