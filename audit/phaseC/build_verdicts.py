"""Builds audit/VERDICTS.md and adds audit_verdict and audit_note to the registry. FR-L figures come from the rerun JSONs. Run once all reruns are in."""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.dirname(HERE)
REG = os.path.join(AUD, "..", "registry")
Y = os.path.join(REG, "experiments.yaml")
C = os.path.join(REG, "experiments.csv")
SB = os.path.join(AUD, "_copy", "sb_fable_%s", "research", "fleet_review", "FR_L_results.json")


def frl(c):
    d = json.load(open(SB % c))
    r = d.get("fixed_1500_reference", d.get("reference"))
    return r["n"], round(r["pf"], 3)


rn, rp = frl("recorded")
tn, tp = frl("true")
V, W, F, N, I, U = "VERIFIED", "VERIFIED-WITH-CORRECTIONS", "REPRODUCES-BUT-FRAGILE", "NOT-REPRODUCIBLE", "INVALID", "UNVERIFIED"
# id, recorded clock, true UTC, verdict, note. "same" means no gold HistData clock dependence.
A = "Reruns exact."
ROWS = {
    "XAU-FINAL-V3": ("n=432 PF 1.667, net $70,596, DD $6,935", "n=436 PF 1.254, net $33,520, DD $14,959", W, "Second engine 428/432 and 427/436 trades within 50c; net differs by gap policy. Spot checks 20/20. Headline is the true-UTC column."),
    "XAU-FINAL-V4": ("n=565 PF 1.331; 2025 n=51 86.3%, PF 2.90", "n=577 PF 1.145; 2025 n=52 76.9%, PF 1.13", W, "Second engine within 1.4%. The 86% year does not survive. Both 2025 slices are INSUFFICIENT SAMPLE."),
    "XAU-FLIP-RAW": ("TP5/SL5 0.965, TP5/SL15 1.057", "TP5/SL5 1.024, TP5/SL15 1.147", W, "Grid byte-identical on the recorded clock. Still not a tradable result at 20-point cost and above."),
    "XAU-R3S3-FADE": ("V3 geometry PF 0.651", "PF 0.736", W, "No harness survives. L2 rebuild on V3 entries confirms the rejection."),
    "H1": ("n=472 PF 1.130, old 0.897, p90 1.045", "n=481 PF 1.009, old 0.831, p90 0.933", W, "Measured-spread PF 0.952 on true UTC. Spot checks 20/20. Earlier Phase B figure n=478 PF 1.012 is withdrawn."),
    "H2": ("n=193 PF 1.174", "n=200 PF 1.035, old 0.658", W, "Partial-matrix claim PF 1.25 also reproduces."),
    "H-S": ("Winner OOS PF 0.200, n=56,260", "PF 0.197, n=55,477", W, "Stored PF 0.307 reproduces on the partial matrix."),
    "H-M": ("Filtered 1.102, uplift -0.028", "0.999, uplift -0.010", W, "Stored 1.206 reproduces on the partial matrix. Guard patched in the true sandbox, DECISIONS 21."),
    "FR-M": ("M0 0.102, M4 0.372 exact", "M0 0.086, M4 0.350", W, "Stored run used the partial matrix. Full matrix: M0 0.019, M4 0.173 recorded; 0.018, 0.165 true."),
    "FR-L": (f"Reference n={rn} PF {rp}", f"n={tn} PF {tp}", W, "Exact on the recorded clock. The PF 2.90 at n=9 is `UNVERIFIED` and `INSUFFICIENT SAMPLE`, is in no file found, and is not a result of this audit."),
    "H-N": ("n=66 PF 1.443, old 1.13", "n=65 PF 0.914, old 0.724", W, "News-day narrative retired. Both slices are INSUFFICIENT SAMPLE."),
    "H-P": ("n=902 PF 1.279, old 0.965", "n=915 PF 1.033, old 0.841", W, "Stored PF 1.373 reproduces on the partial matrix. On the full matrix gate 2 reads false."),
    "H-B": ("n=432 PF 1.376, old 0.977", "n=436 PF 1.040, old 0.847", W, "Binding run exact."),
    "HR": ("Routed n=107 PF 1.336, uplift +0.054", "n=105 PF 1.075, uplift +0.007", W, "Stored 1.484 reproduces on the partial matrix."),
    "SZ": ("One lot old 0.897, new 1.276", "old 0.831, new 1.114", W, "Stored tilt figures reproduce on the partial matrix."),
    "HV": ("All gates fail", "V2 and V3 true, still FAIL: on old 0.879, new 1.288", W, "Gate result differs by clock, verdict does not."),
    "HCRT": ("n=599 PF 0.86", "n=605 PF 0.913", W, "Rises on true UTC, still fails."),
    "HSW": ("n=885 PF 0.827", "PF 0.854", W, "Rises slightly, still fails."),
    "HPF": ("OOS n=27 PF 0.518", "not on the HistData clock", V, "INSUFFICIENT SAMPLE. Identical on the recorded clock."),
    "CYCLES-1-10": ("Net sup-F 2.40 at 2018-12-19; Sidak 0.182, 0.110", "Net 3.65 at 2019-10-24; Sidak 0.954, 0.999", W, "Recomputed without swap, so 3.36 and 0.385, 0.206 stay as stored. Cost break exact at 144.43. Cash-close story retired."),
    "DOOR-3": ("0 of 360 reach $20, max $17.60", "4 of 353, max $37.86", W, "Zero-of-360 claim fails on true UTC."),
    "DR-EDGE-SCREEN": ("D n=1351 PF 1.326; R n=1012 PF 1.06", "D n=1307 PF 1.505; R n=1025 PF 1.014", W, "No spread in the original. D at matrix cost: 0.974 recorded, 1.099 true, 1.001 true at p90. Unthrottled and overlapping, so not a strategy. Remains FAILED."),
    "EXIT-2-FLIP": ("All 6 FAIL; E5 PF 1.01 n=714", "E5 PF 1.00 n=715", V, A),
    "GOLD-LIT-1": ("All 6 FAIL", "unchanged", V, A),
    "PA-1": ("18/18 FAIL; D1 IB +0.134R", "+0.137R", V, A),
    "PA-1B": ("0/4 > 0", "ib_confirm FAIL", V, A),
    "PA-15-30": ("16/16 FAIL", "same", V, A),
    "PA-30-MAX5": ("20/20 FAIL", "same", V, A),
    "D-REVIVAL": ("n=1432 PF 0.87, -91.7R", "New York sensitivity n=1428 PF 0.88", V, "File is broker time from 2019, DECISIONS 20."),
    "BOT-LAB-1": ("NFP PF 1.99-2.29 at $0.80", "same", V, A),
    "WHY-1": ("48.2 / 50.0 / 49.8, VR 0.94-1.05", "same", V, "Claim said 1.06 in the registry; rerun reads 1.05."),
    "ML-1": ("AUC 0.519, shuffled 0.503", "lower thresholds in 2020-26, no skill", V, "Embargo is label resolved before the test year, which exceeds the label horizon."),
    "TA-LAB-R1-R2": ("-0.19R; +0.04R; +0.06R vs random +0.07R", "same, clean clock", V, "Real-gap fills change these by under 0.5R."),
    "TA-LAB-R4-SWEEP": ("+0.048/+0.235R; fixed M15 -0.092R PF 0.78", "same, clean clock", I, "Original figures are a look-ahead leak. The corrected figure in round 12 stands."),
    "TA-LAB-R5-R9": ("All no edge", "same, clean clock", W, "Rounds 8 and 9 reuse the leaky build, so their positive printed figures are invalid. The rejection stands."),
    "TA-LAB-R11": ("n=64 PF 0.73; n=42 PF 1.15", "same, clean clock", V, "Both slices are INSUFFICIENT SAMPLE. Not a test of FINAL_v4: it uses the classic floor R3 and S3 on M15 bars, while FINAL_v4 uses R3 = PP + (H - L) on H1 (found by the second release review)."),
    "XM-1-A1": ("n=124, next open PF 2.37, halves 1.65/3.45; close fill 2.54, halves 1.72/3.79", "no HistData dependence", F, "Rewrite exact. PBO 0.508 on a grid the audit chose. 4 of 14 years lose. In market 11% of days: 4.1%/yr against buy-and-hold 12.3%, with a similar Sharpe and a smaller drawdown. One-bar delay PF 1.80. Spot checks 20/20. DSR in the table below."),
    "XM-1-OTHERS": ("All fail, abs(corr) < 0.03", "same", V, A),
    "SW-1": ("n=397 PF 1.50/2.02 p=0.004", "no HistData dependence", F, "Rewrite exact. PBO 0.167, which flatters: 10 rules on one market, not the 50 cells searched. One-bar delay PF 1.29. Without 2020, PF 1.54. Spot checks 20/20. DSR in the table below."),
    "SC-1": ("n=987 PF 1.22/1.30 p=0.001", "no HistData dependence", V, "Rewrite exact, spot checks 20/20, twin p 0.0025. Realistic entries PF 1.247. DSR 0.81 at N=18, 0.03 at ledger N. 2026 PF 0.88, sealed PF 0.87. Former PASS stays failed."),
    "VS-1": ("All FAIL", "same", V, A),
    "CR-1": ("All FAIL twin gate", "same", V, A),
    "EDGE-1-F1": ("Net Sharpe -0.27", "same", V, A),
    "EDGE-1-F3-F5-F7": ("All FAIL", "same", V, A),
    "EDGE-1-F6": ("Sharpe 1.52 vs 0.96, DD 26.6/48.3", "no HistData dependence", F, "Rewrite exact. PBO 0.742 on 5 variants, all with Sharpe 1.03 to 1.52, so it shows which neighbour won and not whether trend works. Delay barely matters: 1.52, 1.50, 1.43 at lags 1, 2, 3. Sharpe 0.33 since 2025. The twelve coins stay hindsight picks, so survivorship is not cleared. E5: Sharpe 1.36 to 1.49 on real cost tiers, 1.51 with eight collapsed coins added. Spot checks 20/20."),
    "EDGE-1-F9": ("Sharpe 3.01, DD 1.9% on 5 streams", "same", W, "Script later added TSMOM, which reads 2.58. Stays INCONCLUSIVE. Replaced by the descriptive E3, which gives no verdict."),
    "TVS-1": ("Phase 1: 1,296 rows, trade metrics 100%; Phase 2 stored 0/20 on 64,521 configs", "same", W, "The stored search cannot be replayed: its grid seed uses Python's salted hash, a defect. All 1,020 stored configs checked re-evaluate exactly, including the top 20. A new draw of 64,431 configs also gives 0/20. Random-baseline columns are unseeded and differ. TVS-1's own DSR counts its own configs, not the ledger, and its best config reads 0.957 stored and 0.969 rerun. A pass needed eight conditions at once, and no config met them all."),
    "SWEEP-MTF-1": ("4/4 FAIL", "same", V, A),
    "TUNE-1-DIP": ("HOLD-T n=122 PF 3.05; HOLD-M n=2,158 PF 1.59 raw, n=2,195 PF 1.36 split-adjusted", "same", F, "The registered test failed: 0 of 3 finalists passed. PASSED in the registry attaches to the live baseline, which had no gate, and which is the same rule as XM-1-A1, so this is not a fourth independent result. HOLD-M 1.59 came from a reverse split in raw ETF prices, one EWJ trade booking +295%. Adjusted HOLD-M PF is 1.36 with 83% of markets above 1. Holdout CONTAMINATED. Spot checks 20/20 did not reach HOLD-M."),
    "TUNE-1-ORB": ("Live ORB-30 n=245 PF 0.87", "same", V, "Holdout CONTAMINATED. Byte-identical."),
    "CRT-FVG-1": ("0/15 PASS, cells and 3,829 trades exact", "true UTC data", V, "Gap asymmetry at most 0.0045R per cell."),
    "LBO-1": ("OOS -0.0083R n=204 PF 0.98", "true UTC data", V, "Second out-of-sample read happens in a sandbox only, DECISIONS 28. Frozen rule has no target exits."),
    "VP-FILTER": ("Baselines 1.025 / 1.027", "not on the SUSPECT list; not rerun on true UTC", V, "all_summaries identical."),
    "FX-TRANSFER-1": ("0/9; best 0.90, all 6 D/R files exact", "no gold clock", V, "Recomputed from stored trades. R EURUSD OOS PF 1.03 is a single cell."),
    "LABELSIZING-CORE": ("all gating asserts pass, synthetic data", "n/a", V, "Rerun in its own pinned environment. No market result."),
    "DESIGN-A-MODULES": ("18 tests pass", "n/a", V, "Design B has no artifact."),
    "FLIP-BOT-DEFECTS": ("15 tests pass", "n/a", V, "Bot refuses non-demo accounts. No goldbot, flip_scalp or dr_backtest script imports flip_bot.py; the last two import the live levels and signals modules."),
    "H3-SILVER": ("half-life 488h, gate needs 4h to 240h", "half-life 504h, gate needs 4h to 240h", V, "Completed in Phase D as frozen. Result: FAILED at validity gate 1, so no trading conclusion. The 504h is an artefact: 57% of the joined spread's movement comes from month-end beta jumps, and with one beta there is no mean reversion. The 4.4% valid share is mostly test power. Both blind predictions were FAIL."),
    "H-20": ("not run", "not run", U, "Withdrawn. The audit did not open the sealed prediction. Premise gone on true UTC."),
    "TAEVAL-1": ("no result", "n/a", U, "INCOMPLETE. Stopped by the author before it finished."),
    "CHANNEL-A": ("P1 PF 0.58", "same", V, "Real beats 1.4% of twins."),
    "CHANNEL-C": ("All FAIL", "same", V, "Output identical."),
    "CHANNEL-B-SCORE": ("scored file missing", "n/a", U, "scored_calls.json not found. Its figures stay out of every summary."),
    "GANN-PROFILE-D-BASE": ("MT5 bars not cached", "n/a", U, "Reported figure only."),
    "HA-ADDITIONS": ("MT5 bars not cached", "n/a", U, "Reported tables only."),
    "NQ-TRANSFER": ("no output located", "n/a", U, ""),
    "ARB-BTC-PAPER": ("no result exists", "n/a", U, "Scaffold."),
    "BINANCE-TESTNET-P1": ("no result exists", "n/a", U, "Infrastructure."),
    "FORWARD-FLIP-DEMO": ("no closing report", "n/a", U, "INCOMPLETE."),
    "EDGE-1-F2": ("not run", "n/a", U, "4 of 9 ETFs have history."),
    "HLCOPY-1": ("no journal", "n/a", U, "INCOMPLETE."),
    "E1-PAIRS": ("new", "new", V, "Nothing reached validation, so validation and holdout were not evaluated. On the frozen rule 7 cells are INSUFFICIENT SAMPLE at dev and 2 FAIL: XAU/XAG V3 n=109 PF 0.03, BTC/ETH V3 n=310 PF 0.618. The 2-to-4 entry band is a logged deviation, shown beside the frozen rule, and all its cells are INSUFFICIENT SAMPLE. Bugs fixed and logged in CHANGES."),
    "E2-SILVER-TRANSFER": ("new", "new", V, "FAILED. H1 PF 0.487, FINAL_v3 0.683, FINAL_v4 0.450 at silver costs. Twins for FINAL rules reuse H1 holding times. Night fees were not added; all three fail before them."),
    "E3-PORTFOLIO": ("new", "new", V, "Descriptive only. It cannot produce a pass."),
    "E4-NEWS": ("new", "new", V, "FAILED. On the frozen cost basis H1 PF 1.008, FINAL_v3 1.056, FINAL_v4 0.898. Events take off under 0.01 of PF: 7, 0 and 15 trades enter in a window. First-minute spreads run 1.43x to 1.51x same-hour non-event days, so the 3x to 6x blind prediction was wrong. Exits use the matrix spread because no exit time is saved."),
    "E5-CRYPTO": ("new", "new", V, "Cost correction of opened slices. No verdict moves. No trend rule passes. MR3 clears CR-1's gate at spot VIP0 at n=82, INSUFFICIENT SAMPLE, and stays failed: these slices were already opened, so a verdict cannot improve, and p 0.003 against 0.007 and 0.008 on the other tiers is noise. F6 Sharpe 1.36 to 1.49. Coin history stays incomplete: only 8 dead coins added."),
    "E6-PAPER": ("new", "new", V, "INSUFFICIENT SAMPLE. 6 of 19 demo trades matched. Median exit gap on those 6 is $11.66, mostly because the bot trails and the backtester does not."),
    "E7-INDICATORS": ("new", "new", V, "FX FAILED at dev. Gold INSUFFICIENT SAMPLE at dev and CONTAMINATED in advance. FX costs are charged on mid prices with a measured spread, which suits a rule this size."),
}
OUT = "EXCLUDED-01 EXCLUDED-02 EXCLUDED-03 EXCLUDED-04 EXCLUDED-05 EXCLUDED-06 EXCLUDED-07 EXCLUDED-08 EXCLUDED-09 EXCLUDED-10 EXCLUDED-11 EXCLUDED-12 EXCLUDED-13 EXCLUDED-14 EXCLUDED-15 EXCLUDED-16 EXCLUDED-17 EXCLUDED-18".split()

text = open(Y, encoding="utf-8").read()
ids = re.findall(r"^- id: (\S+)", text, re.M)
miss = [i for i in ids if i not in ROWS and i not in OUT]
assert not miss, miss
assert not [i for i in ROWS if i not in ids], [i for i in ROWS if i not in ids]
orig = {}
for row in csv.DictReader(open(C, encoding="utf-8", newline="")):
    orig[row["id"]] = row["verdict"]
cnt = {}
lines = ["# Audit verdicts", "",
         "Each verdict rests on the true-UTC column where the clock matters. Both clocks are shown. Original verdicts are kept in the second column.",
         "A verdict says how far a stored claim holds up. It does not say a strategy works. Nothing here is a statement about future returns.",
         "`REPRODUCES-BUT-FRAGILE` means the numbers are exact but fail the ledger-count deflated Sharpe, DECISIONS 23.",
         "A figure from fewer than 100 trades is `INSUFFICIENT SAMPLE` whether or not the row says so. `same` means the experiment does not use the HistData gold file. `ledger N` is 114,500 variants in Phase C notes. Years 2010-2012 of the gold file are `ASSUMED-CLOCK`, see the last section.", "", "COUNTS", "",
         "| ID | Original | Recorded clock | True UTC | Audit verdict | Note |", "|---|---|---|---|---|---|"]
for i in ids:
    if i in OUT:
        continue
    r, t, v, n = ROWS[i]
    cnt[v] = cnt.get(v, 0) + 1
    lines.append(f"| {i} | {orig[i]} | {r} | {t} | **{v}** | {n} |")
lines[7] = "Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda kv: -kv[1])) + f". {len(OUT)} entries are excluded by the author's decision and not tested: " + ", ".join(OUT) + "."
G = json.load(open(os.path.join(AUD, "stats", "gate_table.json")))
FC = json.load(open(os.path.join(AUD, "stats", "family_counts.json")))
AC = json.load(open(os.path.join(AUD, "stats", "assumed_clock.json")))
lines += ["", "## Results with PF above 1.1 that are not passes", "",
          "A PF above 1.1 here does not mean a pass. Each row names what it fails. FINAL_v3's 1.254 and FINAL_v4's 1.145 use a flat assumed cost, and measured costs take them far lower.", "",
          "| Result | PF | Basis | Fails | Why it does not count |", "|---|---:|---|---|---|"]
for r in G["rows"]:
    lines.append(f"| {r['id']} | {r['pf'] if r['pf'] is not None else 'n/a'} | {r['basis']} | {'; '.join(r['gates'])} | {r['why']} |")
lines += ["", "## Deflated Sharpe, two counts", "",
          f"Primary DSR uses the ledger count, now {FC['total']:,} variants. Phase C files hold the same statistic at 114,500. Secondary DSR uses the variants in the programme that produced the result, and it decides nothing. The dated column uses the ledger as it stood on the result's own date. Read all of these as orders of magnitude: `stats/TRIAL_COUNT.md`.", "",
          "| Result | Primary DSR, ledger N | Secondary DSR, family N | Family N | DSR at dated N | Dated N |", "|---|---:|---:|---:|---:|---:|"]
for r in G["rows"]:
    if r["dsr"] is not None and r["dsr_fam"] is not None:
        lines.append(f"| {r['id']} | {r['dsr']} | {r['dsr_fam']} | {r['fam_n']} | {r.get('dsr_dated', '')} | {r.get('dated_n', '')} |")
lines += ["", f"TUNE-1-DIP's trades cluster in {G['tune_clustered']['week_clustered_T']} weeks. Averaged by week, its ledger DSR is {G['tune_clustered']['dsr_ledger']}. EDGE-1-F6 clears 0.95 only on the secondary count, and the verdict uses the primary.", "", "## ASSUMED-CLOCK: 2010-2012", "", AC["note"], "",
          "| Result | With 2010-2012 | Without 2010-2012 |", "|---|---|---|"]
for r in AC["rows"]:
    lines.append(f"| {r['id']} | {r['with_2010_2012']} | {r['without']} |")
lines += ["", "No pass or fail line changes in any of these reruns. Results not touching those years: " + "; ".join(AC["unaffected"]) + "."]
open(os.path.join(AUD, "VERDICTS.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

if "audit_verdict:" not in text:
    out, cur = [], None
    for ln in text.split("\n"):
        m = re.match(r"- id: (\S+)", ln)
        if m:
            cur = m.group(1)
        out.append(ln)
        if ln.startswith("  verdict:"):
            out.append(f"  audit_verdict: {ROWS[cur][2] if cur in ROWS else 'NOT TESTED (excluded)'}")
            if cur in ROWS:
                out.append(f"  audit_true_utc: {json.dumps(ROWS[cur][1])}")
    open(Y, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    rows = list(csv.DictReader(open(C, encoding="utf-8", newline="")))
    fn = list(rows[0]) + ["audit_verdict", "audit_true_utc"]
    with open(C, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fn)
        w.writeheader()
        for r in rows:
            r["audit_verdict"] = ROWS[r["id"]][2] if r["id"] in ROWS else "NOT TESTED (excluded)"
            r["audit_true_utc"] = ROWS[r["id"]][1] if r["id"] in ROWS else ""
            w.writerow(r)
print(cnt, len(ids))

# Keep the registry in step with ROWS on later runs.
text = open(Y, encoding="utf-8").read()
cur, out = None, []
for ln in text.split("\n"):
    m = re.match(r"- id: (\S+)", ln)
    if m:
        cur = m.group(1)
    if cur in ROWS and ln.startswith("  audit_verdict:"):
        ln = f"  audit_verdict: {ROWS[cur][2]}"
    elif cur in ROWS and ln.startswith("  audit_true_utc:"):
        ln = f"  audit_true_utc: {json.dumps(ROWS[cur][1])}"
    out.append(ln)
open(Y, "w", encoding="utf-8", newline="\n").write("\n".join(out))
rows = list(csv.DictReader(open(C, encoding="utf-8", newline="")))
with open(C, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, list(rows[0]))
    w.writeheader()
    for r in rows:
        if r["id"] in ROWS:
            r["audit_verdict"], r["audit_true_utc"] = ROWS[r["id"]][2], ROWS[r["id"]][1]
        w.writerow(r)
