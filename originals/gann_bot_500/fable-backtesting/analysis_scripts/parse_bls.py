"""Parse BLS schedule HTML files -> CPI + NFP release dates per file.
Verifies each file actually covers its nominal year."""
import re
from pathlib import Path
from datetime import datetime

CAL = Path(r"@GANN_ROOT@/research/flip_scalp/calendar")
DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),\s+(\d{4})")

for f in sorted(CAL.glob("bls_*.htm")):
    html = f.read_text(errors="ignore")
    # rows: find all table rows, check release name
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    cpi, nfp = [], []
    for row in rows:
        text = re.sub(r"<[^>]+>", " ", row)
        m = DATE_RE.search(text)
        if not m:
            continue
        d = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}",
                              "%B %d %Y").date()
        if "Consumer Price Index" in text and "Chained" not in text:
            cpi.append(d)
        if "Employment Situation" in text and "Metropolitan" not in text \
                and "State" not in text:
            nfp.append(d)
    years_c = sorted({d.year for d in cpi})
    years_n = sorted({d.year for d in nfp})
    print(f"{f.name}: CPI n={len(cpi)} years={years_c} | "
          f"NFP n={len(nfp)} years={years_n}")
