"""Adds Phase D and E rows to the ledger and the registry. Idempotent. Bug-fix reruns are logged with 0 new variants."""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "..", "..", "registry")
L = os.path.join(REG, "trial_ledger.csv")
rows = list(csv.reader(open(L, encoding="utf-8", newline="")))
have = {r[0] for r in rows}
D = "2026-10-31"
NEW = [
    ("AUD-D-TVS", "audit Phase D", "TVS-1 Phase 2 rerun, a new draw because the stored seed was salted by process", 64431, "0 of 20 PASS", "exact, new configs drawn from the same space", "audit/phaseC/logs_D/tvs_phase2.log"),
    ("AUD-D-TVS2", "audit Phase D", "TVS-1 stored configs re-evaluated", 0, "1,020 of 1,020 exact", "run log, no new hypothesis", "audit/phaseC/tvs_recheck.json"),
    ("AUD-D-LS", "audit Phase D", "LABELSIZING-CORE synthetic asserts", 0, "all asserts pass", "run log, no market result", "audit/phaseC/logs_D/labelsizing_validation.log"),
    ("AUD-D-H3", "audit Phase D", "H3-SILVER run as frozen, both clocks", 0, "FAILED at validity gate", "counted at GB row for H3", "audit/phaseD/h3_result.json"),
    ("AUD-D-TAP", "audit Phase D", "TA-LAB rounds with both same-bar orderings", 0, "no failed row turns positive", "sensitivity, 2 orderings, no selection", "audit/phaseC/talab_pess.json"),
    ("AUD-D-1012", "audit Phase D", "Gold studies rerun without 2010-2012", 0, "no verdict moves", "sensitivity", "audit/stats/assumed_clock.json"),
    ("AUD-E1", "audit Phase E", "Pairs: 3 pairs x OLS, Kalman, no filter", 9, "none reach validation", "exact", "audit/phaseE/e1_result.json"),
    ("AUD-E1-FIX1", "audit Phase E", "E1 first run, inverted exit, bug", 0, "superseded", "bug-fix rerun", "audit/phaseE/e1_result_first_run_buggy.json"),
    ("AUD-E1-FIX2", "audit Phase E", "E1 second run, 2-to-4 entry band, a rule change first logged as a bug", 0, "shown beside the frozen rule", "see AUD-E1-BAND", "audit/phaseE/e1_result_second_run_churn.json"),
    ("AUD-E1-BAND", "audit Phase E", "E1 entry band as a logged deviation", 9, "all INSUFFICIENT SAMPLE at dev", "exact, not in the prereg", "audit/phaseE/e1_result.json"),
    ("AUD-E1-FIX3", "audit Phase E", "E1 month-skip and half-spread bugs", 0, "superseded", "bug-fix rerun", "audit/phaseE/e1_result_third_run_band.json"),
    ("AUD-E4-FIX", "audit Phase E", "E4 FINAL rules on the frozen cost basis", 0, "superseded", "bug-fix rerun", "audit/phaseE/e4_result_first_run.json"),
    ("AUD-E5-FIX2", "audit Phase E", "E5 perp fee before listing", 0, "superseded", "bug-fix rerun", "audit/phaseE/e5_result_second_run.json"),
    ("AUD-E6-FIX", "audit Phase E", "E6 exit gap and backtest R added", 0, "added", "reporting only", "audit/phaseE/e6_pairs.csv"),
    ("AUD-D-ADJ", "audit Phase D", "Cross-market labs on split-adjusted ETF prices", 0, "no verdict moves", "sensitivity, no selection", "audit/phaseC/logs_L1/adj.*.log"),
    ("AUD-E2", "audit Phase E", "H1, FINAL_v3, FINAL_v4 on XAGUSD", 3, "FAILED", "exact", "audit/phaseE/e2_result.json"),
    ("AUD-E3", "audit Phase E", "Portfolio statistics, descriptive", 0, "no verdict by design", "no selection", "audit/phaseE/e3_result.json"),
    ("AUD-E4", "audit Phase E", "Event-aware spreads and blackout on 3 rules", 6, "FAILED", "exact", "audit/phaseE/e4_result.json"),
    ("AUD-E5", "audit Phase E", "CR-1 and F6 on 3 cost tiers plus survivorship", 7, "cost correction, no verdict moves", "exact", "audit/phaseE/e5_result.json"),
    ("AUD-E5-FIX", "audit Phase E", "E5 first run, twin gate missing and weak ETH test, bug", 0, "superseded", "bug-fix rerun", "audit/phaseE/e5_result_first_run.json"),
    ("AUD-E6", "audit Phase E", "Demo journal against backtest", 1, "INSUFFICIENT SAMPLE", "exact", "audit/phaseE/e6_result.json"),
    ("AUD-E7", "audit Phase E", "Gold 200-day, EURUSD and GBPUSD Bollinger RSI", 3, "none reach validation", "exact", "audit/phaseE/e7_result.json"),
]
add = [[i, f, l, str(n), D, o, b, s, "public"] for i, f, l, n, o, b, s in NEW if i not in have]
if add:
    with open(L, "a", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(add)

E = [
    ("E1-PAIRS", "pairs", "XAU/XAG, BTC/ETH, gold/GDX", "H1, D1", "Dukascopy, Binance, Yahoo", "Cointegrated spreads revert at a profit after two-leg costs.", 9, "audit/prereg/E1-PAIRS.md", "Frozen rule 7 cells INSUFFICIENT SAMPLE, 2 FAIL at dev. Validation not evaluated. See audit/phaseE/e1_result.json.", "FAILED OR INSUFFICIENT SAMPLE"),
    ("E2-SILVER-TRANSFER", "transfer test", "XAGUSD", "M1", "Dukascopy M1 bid and ask 2015-2026", "Gold rules transfer unchanged.", 3, "audit/prereg/E2-SILVER-TRANSFER.md", "All three FAIL. See audit/phaseE/e2_result.json.", "FAILED"),
    ("E3-PORTFOLIO", "portfolio", "four fragile streams", "D1", "as sources", "Descriptive only.", 0, "audit/prereg/E3-PORTFOLIO.md", "Descriptive. No verdict can come from this entry.", "DESCRIPTIVE"),
    ("E4-NEWS", "execution", "XAUUSD", "ticks", "Dukascopy ticks 2015-2026", "Event spreads change the verdicts.", 6, "audit/prereg/E4-NEWS.md", "No rule reaches its gate. See audit/phaseE/e4_result.json.", "FAILED"),
    ("E5-CRYPTO", "execution", "crypto", "D1", "Binance", "Real fees, funding and delisted coins change the results.", 7, "audit/prereg/E5-CRYPTO.md", "Cost correction, no verdict moves. See audit/phaseE/e5_result.json.", "CORRECTION"),
    ("E6-PAPER", "reconciliation", "XAUUSD", "M1", "demo journal, Dukascopy M1", "Backtest matches the demo trades.", 1, "audit/prereg/E6-PAPER.md", "6 of 19 matched. INSUFFICIENT SAMPLE.", "INSUFFICIENT SAMPLE"),
    ("E7-INDICATORS", "indicators", "XAUUSD, EURUSD, GBPUSD", "D1, H1", "HistData corrected, Dukascopy", "200-day filter and Bollinger RSI pay after costs.", 3, "audit/prereg/E7-INDICATORS.md", "FX FAIL at dev. Gold INSUFFICIENT SAMPLE at dev.", "FAILED"),
]
Y = os.path.join(REG, "experiments.yaml")
t = open(Y, encoding="utf-8").read()
if "- id: E1-PAIRS" not in t:
    b = []
    for i, f, m, tf, dat, h, n, p, res, v in E:
        b.append(f"- id: {i}\n  date: '{D}'\n  family: {f}\n  market: {m}\n  timeframe: {tf}\n  data: {dat}\n  idea_source: audit brief\n  hypothesis: {h}\n  rules: See prereg.\n  parameters_tested: '{n}'\n  n_variants: {n}\n  prereg: {p}\n  splits: see prereg\n  costs: see prereg\n  gates: see prereg\n  results: {res}\n  verdict: {v}\n  audit_verdict: {'VERIFIED'}\n  audit_true_utc: \"n/a\"\n  known_issues: See audit/DECISIONS.md\n  provenance:\n  - audit/phaseE\n  status_of_number: found\n  publish_class: public\n")
    t = t.rstrip("\n") + "\n" + "".join(b)
    open(Y, "w", encoding="utf-8", newline="\n").write(t)
    C = os.path.join(REG, "experiments.csv")
    r = list(csv.DictReader(open(C, encoding="utf-8", newline="")))
    fn = list(r[0])
    with open(C, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fn)
        w.writeheader()
        w.writerows(r)
        for i, fam, m, tf, dat, h, n, p, res, v in E:
            w.writerow(dict(id=i, date=D, family=fam, market=m, timeframe=tf, n_variants=n, prereg=p, verdict=v, publish_class="public", status_of_number="found", results=res, known_issues="See audit/DECISIONS.md", audit_verdict="VERIFIED", audit_true_utc="n/a"))
print("ledger rows", len(rows) + len(add))
