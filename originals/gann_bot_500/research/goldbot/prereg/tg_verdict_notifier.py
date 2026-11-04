"""Single-shot Telegram notifier for the overnight verdict chain.

Waits for confirmation_done.flag (H1 confirmation rerun complete), allows up
to 30 extra minutes for hb_binding_done.flag (H-B binding), then sends ONE
Telegram message with both verdicts' key numbers. Sends an arming ping at
start so delivery is verified. Reads the token/chat from the live config.py
by TEXT (no import — no side effects). Sentinel-guarded, 48h timeout.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[1]
RESULTS = ROOT / "results"
CONF_FLAG = RESULTS / "confirmation_done.flag"
HB_FLAG = RESULTS / "hb_binding_done.flag"
SENTINEL = RESULTS / "tg_notified.flag"
WLOG = RESULTS / "watcher.log"


def log(msg: str) -> None:
    line = f"{datetime.now().isoformat(timespec='seconds')}  [TG] {msg}"
    with open(WLOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line, flush=True)


def creds() -> tuple[str, str]:
    txt = (REPO / "config.py").read_text(encoding="utf-8", errors="replace")
    tok = re.search(r'TELEGRAM_TOKEN\s*=\s*["\']([^"\']+)["\']', txt).group(1)
    cid = re.search(r'TELEGRAM_CHAT_ID\s*=\s*["\']([^"\']+)["\']', txt).group(1)
    return tok, cid


def send(token: str, chat: str, text: str) -> bool:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat, "text": text}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = r.status == 200
    except Exception as e:
        log(f"telegram send FAILED: {e}")
        return False
    log(f"telegram send ok={ok}")
    return ok


def compose() -> str:
    lines = ["🌅 OVERNIGHT VERDICTS (goldbot prereg chain)"]
    h1 = RESULTS / "H1_rerun.json"
    if h1.exists() and CONF_FLAG.exists():
        d = json.loads(h1.read_text())
        t = d["tables"]["matrix_median"]
        lines.append(
            f"H1 CONFIRMATION (full tick coverage): "
            f"{'PASS' if d['pass'] else 'FAIL'} — full PF {t['full']['pf']:.2f}, "
            f"old {t['old']['pf']:.2f}, new {t['new']['pf']:.2f}, "
            f"splits {d['positive_splits']}/15")
        lines.append("→ breakout line " +
                     ("REOPENS (Phase-2 path live)" if d["pass"]
                      else "stays STOPPED"))
    else:
        lines.append("H1 confirmation: result file missing — check "
                     "results/confirmation_verdict.log")
    hb = RESULTS / "HB_run_binding.json"
    if hb.exists():
        d = json.loads(hb.read_text())
        lines.append(
            f"H-B ARM-B BINDING: {'PASS' if d['pass'] else 'FAIL'} — "
            f"PF {d['pf']:.2f} (old {d['pf_old']:.2f}/new {d['pf_new']:.2f}), "
            f"splits {d['splits_positive']}/15, p90 {d['pf_p90']:.2f} "
            f"(old {d['pf_p90_old']:.2f})")
        lines.append("→ arm B " +
                     ("earns the second-magic demo slot" if d["pass"]
                      else "solo CLOSED") +
                     f" (predictions: Claude PASS-lean, Rashed FAIL — "
                     f"{'Claude' if d['pass'] else 'Rashed'} called it)")
    else:
        lines.append("H-B binding: not yet complete (see watcher.log)")
    lines.append("Full detail: research/goldbot/results/DECISIONS.log")
    return "\n".join(lines)


def main() -> int:
    if SENTINEL.exists():
        log("sentinel present — already notified; exiting")
        return 0
    token, chat = creds()
    send(token, chat,
         "🤖 Verdict notifier armed: you'll get the H1 confirmation + arm-B "
         "binding results here the moment the overnight chain completes "
         "(ETA ~03:00–04:00).")
    t0 = time.time()
    while not CONF_FLAG.exists():
        if time.time() - t0 > 48 * 3600:
            send(token, chat, "⚠️ Overnight verdict chain did NOT complete "
                              "within 48h — downloader or watcher stalled; "
                              "check watcher.log.")
            return 1
        time.sleep(300)
    log("confirmation flag seen; allowing 30 min for H-B binding")
    t1 = time.time()
    while not HB_FLAG.exists() and time.time() - t1 < 1800:
        time.sleep(60)
    send(token, chat, compose())
    SENTINEL.write_text(datetime.now().isoformat(), encoding="utf-8")
    log("verdicts sent — notifier exiting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
