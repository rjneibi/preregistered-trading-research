"""Automated watcher for the pre-committed H1 confirmation rerun.

Waits for the XAUUSD tick block (2015-2026-06) to finish downloading, then
fires, in order: matrix rebuild -> H1 confirmation rerun -> DECISIONS.log
note -> archive commit. Runs detached; safe to leave overnight.

Trigger logic (any of):
  * a "BI5 XAGUSD" line appears in ticks_download.log (the downloader only
    starts silver after gold is fully done), or
  * "ALL COMPLETE" appears, or
  * xauusd-bi5-2026-06.csv exists >10KB (crash-after-gold fallback).
Then it waits until the newest xauusd file is >16 min old — run_build_matrix
excludes files modified <15 min ago, so firing early would silently drop the
freshest months from the matrix.

Safety: single-shot (sentinel file), 48h timeout, stall warnings, all
activity logged to results/watcher.log.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
RESULTS = ROOT / "results"
DL_LOG = REPO / "fable-backtesting" / "ticks_download.log"
DL_DIR = REPO / "fable-backtesting" / "download"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
SENTINEL = RESULTS / "confirmation_done.flag"
WLOG = RESULTS / "watcher.log"
POLL_S = 300
TIMEOUT_H = 48
QUIET_MIN = 16          # newest-gold-file age required before matrix build

COMMIT_MSG = """confirmation: H1 rerun on full gold tick coverage (automated watcher)

Pre-committed at freeze (35deedc): rebuild the per-year cost matrix on the
completed 2015-2026 XAUUSD tick archive and rerun the H1 verdict. This run
REPLACES the partial-coverage deviation for gold; the verdict lines in
DECISIONS.log are the decision-grade record. Executed hands-off by
confirmation_watcher.py.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01JBcqyETZcJrpPatfjFCpVg
"""


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  {msg}"
    with open(WLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def gold_done() -> bool:
    if DL_LOG.exists():
        txt = DL_LOG.read_text(encoding="utf-8", errors="replace")
        if "BI5 XAGUSD" in txt or "ALL COMPLETE" in txt:
            return True
    f = DL_DIR / "xauusd-bi5-2026-06.csv"
    return f.exists() and f.stat().st_size > 10_000


def newest_gold_age_min() -> float:
    files = list(DL_DIR.glob("xauusd-bi5-*.csv"))
    if not files:
        return 1e9
    return (time.time() - max(f.stat().st_mtime for f in files)) / 60.0


def run_step(tag: str, args: list[str], out_name: str) -> bool:
    log(f"START {tag}")
    p = subprocess.run(args, capture_output=True, text=True,
                       cwd=str(ROOT), timeout=3600)
    (RESULTS / out_name).write_text(
        (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""),
        encoding="utf-8")
    log(f"END {tag} exit={p.returncode} (output -> results/{out_name})")
    return p.returncode == 0


def main() -> int:
    if SENTINEL.exists():
        log("sentinel present — confirmation already ran; exiting")
        return 0
    log("watcher armed: waiting for gold tick block to complete "
        f"(poll {POLL_S}s, timeout {TIMEOUT_H}h)")
    t0 = time.time()
    last_size = DL_LOG.stat().st_size if DL_LOG.exists() else 0
    last_change = time.time()

    while not gold_done():
        if time.time() - t0 > TIMEOUT_H * 3600:
            log("TIMEOUT: gold block not complete after 48h — giving up "
                "(downloader may have stalled; restart it and rerun watcher)")
            return 1
        size = DL_LOG.stat().st_size if DL_LOG.exists() else 0
        if size != last_size:
            last_size, last_change = size, time.time()
        elif time.time() - last_change > 5400:
            log("WARNING: no downloader log progress for 90 min "
                "(still waiting)")
            last_change = time.time()
        time.sleep(POLL_S)

    log("gold block COMPLETE detected")
    while newest_gold_age_min() < QUIET_MIN:
        log(f"waiting for newest gold file to age past {QUIET_MIN} min "
            f"(currently {newest_gold_age_min():.1f})")
        time.sleep(120)

    ok1 = run_step("matrix rebuild", [str(PY), str(HERE / "run_build_matrix.py")],
                   "confirmation_matrix_build.log")
    if not ok1:
        log("ABORT: matrix rebuild failed — no rerun, no commit")
        return 1
    ok2 = run_step("H1 confirmation rerun", [str(PY), str(HERE / "run_verdict.py")],
                   "confirmation_verdict.log")
    if not ok2:
        log("ABORT: verdict rerun failed — no commit")
        return 1

    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().date().isoformat()}  NOTE: the VERDICT RUN "
                f"block immediately above is the PRE-COMMITTED CONFIRMATION "
                f"RERUN on FULL gold tick coverage (2015-2026), fired "
                f"automatically by confirmation_watcher.py. It supersedes the "
                f"partial-coverage H1 numbers for gold-cost purposes.\n")

    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(REPO), *args],
                              capture_output=True, text=True)

    git("add", "-f",
        "research/goldbot/results/cost_matrix.json",
        "research/goldbot/results/H1_rerun.json",
        "research/goldbot/results/verdict_trades.csv",
        "research/goldbot/results/DECISIONS.log",
        "research/goldbot/results/confirmation_matrix_build.log",
        "research/goldbot/results/confirmation_verdict.log")
    r = git("commit", "-m", COMMIT_MSG)
    log(f"git commit exit={r.returncode}: {(r.stdout or r.stderr).strip()[:200]}")

    SENTINEL.write_text(datetime.now().isoformat(), encoding="utf-8")
    log("confirmation rerun COMPLETE — sentinel written; watcher exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
