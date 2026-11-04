"""Single-shot watcher: fires the H-B BINDING run (prereg a734cd7) once the
confirmation watcher has finished the full-coverage matrix rebuild + H1
rerun (signalled by results/confirmation_done.flag). Detached, sentinel-
guarded, 48h timeout. Activity -> results/watcher.log."""

from __future__ import annotations

import subprocess
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results"
PY = ROOT / ".venv" / "Scripts" / "python.exe"
TRIGGER = RESULTS / "confirmation_done.flag"
SENTINEL = RESULTS / "hb_binding_done.flag"
WLOG = RESULTS / "watcher.log"


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  [HB] {msg}"
    with open(WLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def main() -> int:
    if SENTINEL.exists():
        log("sentinel present — binding run already done; exiting")
        return 0
    log("armed: waiting for confirmation_done.flag (full-coverage matrix)")
    t0 = time.time()
    while not TRIGGER.exists():
        if time.time() - t0 > 48 * 3600:
            log("TIMEOUT after 48h — binding run not fired")
            return 1
        time.sleep(300)
    log("full-coverage matrix ready — firing H-B binding run")
    p = subprocess.run([str(PY), str(HERE / "hb_runner.py"), "--tag", "binding"],
                       capture_output=True, text=True, cwd=str(ROOT),
                       timeout=3600)
    (RESULTS / "hb_binding_run.log").write_text(
        (p.stdout or "") + "\n--- stderr ---\n" + (p.stderr or ""),
        encoding="utf-8")
    log(f"binding run exit={p.returncode} (output -> results/hb_binding_run.log)")
    subprocess.run(["git", "-C", str(ROOT.parents[1]), "add", "-f",
                    "research/goldbot/results/HB_run_binding.json",
                    "research/goldbot/results/DECISIONS.log",
                    "research/goldbot/results/hb_binding_run.log"],
                   capture_output=True, text=True)
    subprocess.run(["git", "-C", str(ROOT.parents[1]), "commit", "-m",
                    "verdict: H-B binding run on full-coverage matrix "
                    "(automated)\n\nCo-Authored-By: Claude Fable 5 "
                    "<noreply@anthropic.com>\nClaude-Session: "
                    "https://claude.ai/code/session_01JBcqyETZcJrpPatfjFCpVg"],
                   capture_output=True, text=True)
    SENTINEL.write_text(datetime.now().isoformat(), encoding="utf-8")
    log("H-B binding COMPLETE — sentinel written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
