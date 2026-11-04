"""Python entry point, for systems without make. The audit stages are shell scripts, so `public` and `full` need bash, which Git for Windows provides.
Usage: python scripts/reproduce_all.py verify
       python scripts/reproduce_all.py public --work ../clean --data data/raw
       python scripts/reproduce_all.py full --work ../clean --data data/raw
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("level", choices=["verify", "public", "full"])
    ap.add_argument("--work", default=os.path.join(ROOT, "..", "_audit_clean"))
    ap.add_argument("--data", default=os.environ.get("DATA_DIR", os.path.join(ROOT, "data", "raw")))
    a = ap.parse_args()
    if a.level == "verify":
        sys.exit(subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "verify.py")]).returncode)
    bash = shutil.which("bash")
    if not bash:
        sys.exit("bash is needed for this level. On Windows install Git for Windows.")
    env = dict(os.environ, DATA_DIR=os.path.abspath(a.data), PYTHON311=os.environ.get("PYTHON311", sys.executable))
    sys.exit(subprocess.run([bash, "audit/tools/make_audit.sh", os.path.abspath(a.work), a.level], cwd=ROOT, env=env).returncode)


if __name__ == "__main__":
    main()
