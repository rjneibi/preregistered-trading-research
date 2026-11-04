"""Build calendar/news_days.json: FOMC (exact, Fed website), NFP (first-Friday
rule, validated vs exact 2015 BLS list), CPI (exact where available).
Sources: federalreserve.gov calendars (fetched 2026-07-02), BLS 2015 schedule
via Wayback, cpiinflationcalculator.com for 2025-26."""
import json
import re
from datetime import date, timedelta
from pathlib import Path

CAL = Path(__file__).parent / "calendar"

FOMC = """2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17
2015-10-28 2015-12-16 2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27
2016-09-21 2016-11-02 2016-12-14 2017-02-01 2017-03-15 2017-05-03 2017-06-14
2017-07-26 2017-09-20 2017-11-01 2017-12-13 2018-01-31 2018-03-21 2018-05-02
2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19 2019-01-30 2019-03-20
2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-04 2019-10-30 2019-12-11
2020-01-29 2020-03-03 2020-03-15 2020-04-29 2020-06-10 2020-07-29 2020-09-16
2020-11-05 2020-12-16 2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28
2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15
2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03
2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20
2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18 2025-01-29
2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17""".split()

CPI_KNOWN = """2025-02-12 2025-03-12 2025-04-10 2025-05-13 2025-06-11
2025-07-15 2025-08-12 2025-09-11 2025-10-24 2025-11-13 2025-12-10 2026-01-13
2026-02-11 2026-03-11 2026-04-10 2026-05-12 2026-06-10""".split()


def first_friday(year, month):
    d = date(year, month, 1)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def parse_bls_2015():
    html = (CAL / "bls_2015.htm").read_text(errors="ignore")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)
    months = ("January February March April May June July August September "
              "October November December").split()
    pat = re.compile(rf"({'|'.join(months)})\s+(\d{{1,2}}),\s+(2015)")
    cpi, nfp = [], []
    for row in rows:
        text = re.sub(r"<[^>]+>", " ", row)
        m = pat.search(text)
        if not m:
            continue
        d = date(2015, months.index(m.group(1)) + 1, int(m.group(2)))
        if "Consumer Price Index" in text and "Chained" not in text:
            cpi.append(d)
        if ("Employment Situation" in text and "Metropolitan" not in text
                and "State" not in text):
            nfp.append(d)
    return sorted(set(cpi)), sorted(set(nfp))


cpi_2015, nfp_2015_exact = parse_bls_2015()
nfp_rule_2015 = [first_friday(2015, m) for m in range(1, 13)]
hits = sum(1 for d in nfp_rule_2015 if d in nfp_2015_exact)
print(f"NFP first-Friday rule vs exact 2015: {hits}/12 match "
      f"(exact list has {len(nfp_2015_exact)})")

nfp = []
for y in range(2015, 2027):
    for m in range(1, 13):
        if (y, m) <= (2026, 7):
            nfp.append(first_friday(y, m))

days = sorted({*FOMC,
               *[d.isoformat() for d in nfp],
               *CPI_KNOWN,
               *[d.isoformat() for d in cpi_2015]})
out = CAL / "news_days.json"
out.write_text(json.dumps({
    "fomc_n": len(FOMC), "nfp_n": len(nfp),
    "cpi_n": len(CPI_KNOWN) + len(cpi_2015),
    "note": ("FOMC exact 2015-2026 (Fed website). NFP = first-Friday rule "
             "2015-2026. CPI exact only 2015 + 2025-26; 2016-2024 CPI "
             "missing (BLS bot-walled, Wayback incomplete)."),
    "days": days}, indent=1))
print(f"wrote {out}: {len(days)} blackout days")
