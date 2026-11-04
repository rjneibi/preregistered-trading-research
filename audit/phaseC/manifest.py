"""SHA-256 of Phase C inputs and outputs. Writes phaseC/MANIFEST.sha256."""
import glob
import hashlib
import os

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.dirname(HERE)
IN = ["@GANN_ROOT@/research/data/xauusd_m1_histdata.csv", "@LBO_ROOT@/data/m1/XAUUSD.npz", A + "/_copy/data/xauusd_m1_trueutc.csv", A + "/_copy/cost_matrix_partial.json", A + "/_copy/sb_true/research/goldbot/results/cost_matrix.json", A + "/_copy/rs_recorded/research/cross_market/data/USTEC_M1.npz"]
OUT = sorted(glob.glob(HERE + "/*.json") + glob.glob(HERE + "/*.csv") + glob.glob(A + "/stats/*.json") + glob.glob(A + "/trade_checks/*.json") + glob.glob(A + "/trade_checks/*.csv") + glob.glob(A + "/trade_checks/*.png") + glob.glob(A + "/infrastructure/*.json"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


with open(HERE + "/MANIFEST.sha256", "w", newline="\n") as f:
    for tag, ps in (("input", IN), ("output", OUT)):
        for p in ps:
            n = os.path.relpath(p, A).replace("\\", "/") if p.startswith(A) else os.path.basename(p)
            f.write(f"{sha(p)}  {tag}  {n}\n")
print(len(IN), len(OUT))
