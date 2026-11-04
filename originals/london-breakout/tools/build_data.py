"""Build data/m1/*.npz from the raw Dukascopy CSVs and write docs/data_quality.md."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

from lbo import data, quality  # noqa: E402


def main(names=None):
    cfg = yaml.safe_load(open(ROOT / "config" / "research.yaml"))
    out = []
    for name, ic in cfg["instruments"].items():
        if names and name not in names:
            continue
        arr, qc = data.build(name, ic["symbol"], cfg["data"]["start"], cfg["data"]["end"])
        qc = quality.report(name, arr, qc)
        out.append(qc)
        print(json.dumps(qc, default=str)[:600], flush=True)
    path = ROOT / "results" / "data_quality.json"
    old = json.load(open(path)) if path.exists() else []
    keep = [q for q in old if q["instrument"] not in {q2["instrument"] for q2 in out}]
    json.dump(keep + out, open(path, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
