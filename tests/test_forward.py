import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(ROOT, "audit", "forward")


def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(F, name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def row(s, m, d, x):
    return [s, m, d, d, d, x, "2026-12-01"]


def test_shared_rule_is_counted_once(tmp_path):
    log, out = tmp_path / "l.csv", tmp_path / "s.md"
    with open(log, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "market", "signal_day", "entry_day", "exit_day", "net_return", "run_utc"])
        w.writerow(row("FW-XM-1-A1", "US500", "2026-11-02", 0.01))
        w.writerow(row("FW-TUNE-1-DIP", "US500", "2026-11-02", 0.009))
        w.writerow(row("FW-TUNE-1-DIP", "US30", "2026-11-02", 0.02))
    load("summarize").main(str(log), str(out))
    t = out.read_text(encoding="utf-8")
    us = [x for x in t.splitlines() if x.startswith("| RSI2 dip") and "| US500 |" in x]
    assert len(us) == 1 and "| 1 |" in us[0] and "1.0000%" in us[0]
    assert "monitored, no edge claimed" in t and "INSUFFICIENT SAMPLE" in t


def test_every_frozen_leg_has_a_group():
    s = json.load(open(os.path.join(F, "strategies.json"), encoding="utf-8"))
    g = json.load(open(os.path.join(F, "rule_groups.json"), encoding="utf-8"))
    have = {(x["strategy"], m) for y in g["groups"] for x in y["legs"] for m in x["markets"]} | {(x["strategy"], x["market"]) for y in g["groups"] for x in y["dropped"]}
    want = {(x["id"], m["name"]) for x in s["strategies"] for m in x["markets"]} | {("FW-EDGE-1-F6", "basket")}
    assert have == want


def test_freeze_matches():
    assert subprocess.run([sys.executable, os.path.join(F, "verify_freeze.py")], capture_output=True).returncode == 0


def test_freeze_catches_a_changed_file(tmp_path):
    d = tmp_path / "forward"
    shutil.copytree(F, d)
    with open(d / "forward_update.py", "a", encoding="utf-8") as f:
        f.write("# changed\n")
    p = subprocess.run([sys.executable, str(d / "verify_freeze.py")], capture_output=True, text=True)
    assert p.returncode != 0 and "MISMATCH" in p.stdout + p.stderr
