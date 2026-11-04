"""One command for everything: python src/run_all.py [--no-fetch]
fetch SPY/QQQ -> unit tests -> phase 1 -> phase 2 -> Pine scripts -> HTML report.
(XAU data comes from the trading VM - see README - and is not re-fetched here.)"""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PY = sys.executable


def run(*args):
    print(">>", " ".join(args), flush=True)
    subprocess.run([PY, *args], cwd=ROOT, check=True)


if __name__ == "__main__":
    if "--no-fetch" not in sys.argv:
        run("src/fetch_yf.py")
    run("-m", "pytest", "-q", "tests")
    with open(os.path.join(ROOT, "results", "phase1_log.txt"), "w") as f:
        subprocess.run([PY, "src/phase1.py"], cwd=ROOT, check=True, stdout=f, stderr=subprocess.STDOUT)
    with open(os.path.join(ROOT, "results", "phase2_log.txt"), "w") as f:
        subprocess.run([PY, "src/phase2.py"], cwd=ROOT, check=True, stdout=f, stderr=subprocess.STDOUT)
    run("src/pine.py")
    run("src/report.py")
