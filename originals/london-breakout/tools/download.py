"""Download Dukascopy M1 bid+ask candles (with tick volume) per instrument and year.

Resumable: a (instrument, side, year) chunk is skipped if its CSV already exists.
Usage: python tools/download.py [--start 2013] [--end 2026] [--inst deuidxeur,gbridxgbp]
"""
import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "node_modules" / ".bin" / "dukascopy-node.cmd"
RAW = ROOT / "data" / "raw"
DEFAULT_INST = ["deuidxeur", "gbridxgbp", "usa30idxusd", "usatechidxusd",
                "eurusd", "gbpusd", "xauusd"]


def chunk(inst, side, year, end_date):
    out = RAW / inst
    out.mkdir(parents=True, exist_ok=True)
    final = out / f"{inst}-{side}-{year}.csv"
    if final.exists():
        return "skip"
    d0 = f"{year}-01-01"
    d1 = min(dt.date(year + 1, 1, 1), end_date).isoformat()
    tmpdir = out / f"tmp_{side}_{year}"
    tmpdir.mkdir(exist_ok=True)
    cmd = [str(CLI), "-i", inst, "-from", d0, "-to", d1, "-t", "m1", "-p", side,
           "-v", "true", "-f", "csv", "-dir", str(tmpdir), "-bs", "15", "-bp", "250",
           "-r", "5", "-rp", "2000", "-s"]
    for attempt in range(3):
        r = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        files = list(tmpdir.glob("*.csv"))
        if r.returncode == 0 and files:
            files[0].replace(final)
            tmpdir.rmdir()
            return "ok"
        print(f"  retry {inst} {side} {year}: rc={r.returncode} {r.stderr[-300:]}", flush=True)
    return "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2013)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--end-date", default="2026-10-30")
    ap.add_argument("--inst", default=",".join(DEFAULT_INST))
    a = ap.parse_args()
    end_date = dt.date.fromisoformat(a.end_date)
    for inst in a.inst.split(","):
        for year in range(a.start, a.end + 1):
            for side in ("bid", "ask"):
                s = chunk(inst, side, year, end_date)
                print(f"{inst} {side} {year}: {s}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
