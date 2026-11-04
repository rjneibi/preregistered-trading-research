"""Rerun the whole study:  python run_all.py            (all stages)
                             python run_all.py --stage report   (one stage)

Stages, in order: download, data, test, grids, analyze, deep, freeze, oos, docs, report.
`oos` runs the frozen config exactly once; delete results/oos_*.json to force a rerun
(and record why in RESEARCH_LOG.md).
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

STAGES = ["download", "data", "test", "grids", "analyze", "deep", "freeze", "oos", "docs", "report"]


def _grid(job):
    variant, name = job
    from lbo import grid_a, grid_b
    (grid_a if variant == "A" else grid_b).run(name)
    return job


def stage(name):
    print(f"== {name}", flush=True)
    if name == "download":
        subprocess.run(["npm", "ci", "--prefix", str(ROOT / "tools")], check=True, shell=True)
        subprocess.run([sys.executable, str(ROOT / "tools" / "download.py")], check=True)
    elif name == "data":
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_data.py")], check=True)
    elif name == "test":
        subprocess.run([sys.executable, "-m", "pytest", "-q"], check=True, cwd=ROOT)
    elif name == "grids":
        jobs = [("A", "GER40"), ("A", "UK100")] + [("B", n) for n in
                ("GER40", "UK100", "US30", "NAS100", "EURUSD", "GBPUSD", "XAUUSD")]
        with ProcessPoolExecutor(max_workers=6) as ex:
            for j in ex.map(_grid, jobs):
                print("done", j, flush=True)
    elif name == "analyze":
        from lbo import analyze_stage1
        import pandas as pd
        for v in ("A", "B"):
            analyze_stage1.run(v)
        rows = []
        for n in ("GER40", "UK100", "US30", "NAS100", "EURUSD", "GBPUSD", "XAUUSD"):
            f = pd.read_csv(ROOT / "results" / f"stage1_B_{n}.csv")
            for s, g in f.groupby("session"):
                g = g[g.IS_n >= 150]
                rows.append(dict(inst=n, session=s, configs=len(g), share_IS_pos=(g.IS_exp > 0).mean(),
                                 share_both_pos=((g.IS_exp > 0) & (g.VAL_exp > 0)).mean(),
                                 mean_IS=g.IS_exp.mean(), mean_VAL=g.VAL_exp.mean(), best_IS=g.IS_exp.max()))
        pd.DataFrame(rows).to_csv(ROOT / "results" / "stage1_B_all_instruments_by_session.csv", index=False)
    elif name == "deep":
        from lbo import pipeline as P
        from lbo.gaps import box_behaviour, summarise_box
        P.deep("pick", *P.pick_from_stage1("A"))
        P.deep("author", *P.AUTHOR)
        P.wfo_all()
        out = []
        for n in ("GER40", "UK100"):
            for box in ("utc0007", "ny1904"):
                df = box_behaviour(n, box=box)
                df.to_csv(ROOT / "results" / f"box_behaviour_{n}_{box}.csv", index=False)
                s = summarise_box(df)
                s.update(inst=n, box=box)
                out.append(s)
        json.dump(out, open(ROOT / "results" / "box_behaviour_summary.json", "w"), indent=1)
    elif name == "freeze":
        from lbo import pipeline as P
        sc, stop, rr = P.pick_from_stage1("A")
        kept = json.load(open(ROOT / "results" / "deep_pick" / "summary.json")).get("fixes_kept", [])
        P.freeze(sc, stop, rr, kept, "FAILED VALIDATION - NO EDGE. Frozen for the required single OOS run and "
                 "for documentation; NOT recommended for live trading.")
    elif name == "oos":
        from lbo import pipeline as P
        print(P.oos(*P.pick_from_stage1("A"), label="final")["1.0"])
        P.oos(*P.AUTHOR, label="author_reference")
    elif name == "docs":
        from lbo import docs_gen
        docs_gen.data_quality()
    elif name == "report":
        from lbo import report
        report.build()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=STAGES)
    ap.add_argument("--skip-download", action="store_true", default=None)
    a = ap.parse_args()
    if a.stage:
        stage(a.stage)
        return
    have_raw = (ROOT / "data" / "raw" / "deuidxeur").exists()
    for s in STAGES:
        if s == "download" and have_raw:
            print("== download (raw data present, skipped)")
            continue
        stage(s)


if __name__ == "__main__":
    main()
