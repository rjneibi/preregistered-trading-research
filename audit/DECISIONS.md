# Audit decisions log

> This log was kept during the audit by the AI assistant that ran it (Claude, through Claude Code) and reported to the author, Rashed Al Jneibi. "I" is the assistant. "The author" and "the brief" are the author and the author's written instructions. In this public copy, second-person wording and details of the author's machines were rewritten, and nothing else changed. The root DECISIONS.md, item 20, lists every change.

1. **Checkpoint 1 questions treated as follows.** The author's new brief runs the gap-filling work and keeps the
   analyst strategy untested, so those two are settled. Name, repo name and TradingAgents stay open.
2. **Analyst entries are OUT, not L5.** There are 18. They are not tested and stay as ledger counts. The brief
   forbids testing the copy-traded strategy, so this is a scope exclusion, not a failure to verify.
3. **Public-channel entries stay in scope.** CHANNEL-A, CHANNEL-C and CHANNEL-B-SCORE concern public channels, not the
   excluded analyst. They are audited and stay anonymised. EXCLUDED-03 and the public group test are OUT: the first
   benchmarks against the analyst and has no located code, the second needs the private signals archive.
4. **Bars that only came from MT5 are not refetched.** Rule 9 bars broker logins. Entries depending on them drop
   to L2 from saved trade lists, or L5 where no trade list exists (D baseline, HA additions, NQ transfer).
5. **Levels are provisional for code that was not opened.** Existence was checked, not whether it runs.
   A script that fails to run moves to L2, and DOOR-3 moves too if no run script turns up.
6. **Audit folder gets its own local git repo** to record prereg commit hashes. It has no remote.
7. **H-20 stays unrun unless the author decides otherwise.** It failed its own power gate, and running it would produce a
   number its authors already called empty.
8. **E9 needs no new experiment.** SWEEP-MTF-1 is the exact sweep replication, and TVS-1's Phase 1 output includes
   3-minute bars for the VWAP rule. Both are verified at L1. Only variants missing from their preregs would be new.
9. **Author decisions recorded 2026-10-31.** Numpy second engine, gated on known-answer tests (passed 19/19). E8 skipped.
   Spot checks: 20+ manual for headline or PASS, automated replay for the rest, disagreement escalates to manual. H-20 unrun.
   TradingAgents INCOMPLETE, no GPU runs.
10. **Tests moved to copies** after the first attempt in the original folders was rejected. Originals stay untouched.
11. **iFVG spec not received.** No `IFVG_PREREG_SPEC.md` is on disk or attached, so `audit/recovered/` is empty.
    Searches for tz_audit.py, fvg.py and ifvg found no code or results; hits were passing mentions and one
    non-iFVG file. `ict_snr_bot.zip` has a plain FVG finder, not iFVG. So iFVG is L4 once the spec arrives.
12. **claude-alpaca-bot.zip not found** in the author's files. Stays UNVERIFIED.
13. **True-UTC H1 is a correction beside the original, not a retune.** Only timestamps change. The cost matrix is unchanged.
14. **Fresh holdout as specified has about one day of data.** Dukascopy gold runs to 2026-10-29. See checkpoint note.
15. **Author decisions recorded 2026-10-31 (second round).** Fresh holdout: publish with the forward test labelled RUNNING. At the end
    of the audit freeze every survivor (rules, parameters, data source, cost model) in one commit, record hash and UTC time in
    FORWARD_TEST.md, ship it in the public release, append results monthly whatever the outcome, never re-freeze. A changed
    strategy is a new strategy with its own freeze. claude-alpaca-bot stays UNVERIFIED and is not re-created. MT5 exports skipped
    for this release, listed in FUTURE_WORK. The clock bug is a first-class finding (`findings/CLOCK_BUG.md`), and verdicts for
    SUSPECT results rest on true UTC only, with both clocks reported.
16. **flip_bot checked, no live exposure.** `boot()` exits on any non-demo account (`flip_bot.py:622-623`), no flip_bot process runs
    on the PC, the last run log is dated 2026-08-25, and the task list on the author's other machine was rebuilt without it on 2026-10-20. That machine was not
    queried; that last point comes from an earlier note. Nothing needs pausing.
17. **iFVG spec still absent.** The instruction says it was saved to `audit/recovered/`, but that folder is empty and a filename
    search of the author's drives found nothing. iFVG stays blocked; everything else proceeds.
18. **Breach, disclosed: one original file was rewritten by an import.** `research/cross_market/xm_lab.py` and `d_revival/news_lab.py`
    import `fable-backtesting/build_calendar.py` by absolute path, and that module writes `calendar/news_days.json` on import. My
    pre-run check covered write sites in the research folders but not imported modules outside them, so reruns on 2026-10-31
    regenerated that file. Its SHA-256 (ac34e31d...) equals the copy taken before the runs, so the content is unchanged, and only the
    modified time moved. A scan for anything newer than the pre-run marker finds this file alone in both trees. It read 2026-10-14 17:22 before the runs. That earlier
    time was not restored, because that would be one more edit to an original. Sandbox copies now import a local copy.
19. **Clock correction is two-regime, from the data.** US switch dates through 2018, EU from 2019, measured on 3,474 days with no exception. 2010-2012 are
    assumed to follow the US rule because no Dukascopy overlap exists. This replaces the Phase B fix.
20. **`d_revival/m1.npz` "true" run is a New York clock run.** That file is broker time, and from 2019 its switch dates already match the broker. Runs in `rs_true`
    therefore measure sensitivity to a New York clock (PF 0.87 to 0.88 for D-REVIVAL). They are reported as sensitivity, not as a correction.
21. **H-M guard edited in the true sandbox only.** `hm_runner.py` asserts 472 trades, which is correct for the recorded clock. The true-clock copy asserts 481. No rule changed.
22. **Gap test rewritten after it overstated.** The first TA-LAB patch also filled stops that the ladder moved inside the previous bar, which dropped M15 win rates by 15 points.
    Only real gaps count now: last bar closed safe and this bar opened through. The first version stays in `phaseC/logs_talab/gap.*` and is not used.
    TA-LAB still moves a ladder stop on the bar's high without testing that bar's low against it, which is optimistic. All those rounds failed anyway, so it cannot change a verdict.
23. **PASS verdicts use the full ledger count.** The brief asks for DSR with the ledger count, about 114,500 variants. That is the floor of everything tried across unrelated markets, so it is
    harsh. Family-level DSR is reported beside it, and the verdict uses the ledger figure. No threshold was changed after seeing results.
24. **Null variance in DSR is 1/T.** Trial Sharpes across the ledger are not on disk in one form, so the variance of trial Sharpes uses the null value.
25. **TVS-1 Phase 2 not rerun.** It needs `optuna`, which is absent from the audit environment. Phase 1 reruns; Phase 2 stays as stored, and the verdict says so.
26. **`labelsizing_core` not rerun.** It needs `xgboost`, which is absent. It holds no market result.
27. **Spot-check charts are drawn without matplotlib,** which is absent. V3 and V4 sheets check entries and barriers only. Their exits rest on the trade-by-trade match with the audit engine.
28. **Sealed slices were reread in sandboxes only.** LBO-1, TUNE-1 and H-series reruns reproduce stored results on copies. These are reproductions of an opening that already happened, not new
    openings, and the hypothesis is unchanged. True-UTC reruns of a sealed result do read the slice with shifted bars, so they are labelled corrections, not fresh tests. LBO's OOS uses Dukascopy and had no clock rerun.
29. **Runs from before the full matrix use the partial matrix.** H-P, SZ, H-R, H-M, H-S and FR-M date from 2026-07-06, before the full-tick matrix of 07-07. Each reproduces exactly on the matrix of its date (commit 977fff5).
    Current figures use the full matrix. FR-M shows both.
30. **DR screen costed after the fact.** D rose on true UTC with no spread in the screen, so the project's cost matrix was applied to the same entries to read that rise fairly. No rule moved, and no further variant was tried.
    `run_1pz.py` was rerun as an existing script.
31. **FX runs need no clock correction.** They do not use the gold HistData file. Only stored trades exist, so the check is arithmetic.
32. **Author decisions recorded 2026-10-31 (third round).** Phases D and E approved, E8 stays skipped. E3 is descriptive only: no selection, no optimised weights, no PASS verdict. Optuna and xgboost go in a
    separate pinned environment. VERDICTS must name the gate each true-UTC PF above 1.1 fails. 2010-2012 are labelled ASSUMED-CLOCK with metrics shown with and without them. DSR keeps the ledger count as primary, with a family-count
    column as secondary, and the count is documented. FR-L's PF 2.90 and CHANNEL-B-SCORE stay out of summaries. TA-LAB's failed rounds are rerun with the pessimistic same-bar rule. `registry/` moves into the audit repo.
33. **iFVG spec still not received.** The third-round message ended at the line introducing the spec, with no text after it, and a filename search of the home folder found no copy. The instruction was not to invent it, so iFVG remains blocked and the spec is not reconstructed.
34. **news_days.json proof.** The file has no git history and no older backup. The proof is a sandbox copy taken 2026-10-31 08:47:09, before the rewrite at 10:26:52: `_copy/flip/calendar/news_days.json`. Both hash to
    ac34e31dfbd04bfc42dd7fefd1354a276d04f7195b876b7c3856463bfb64534a, 4,661 bytes. The copy's mtime and birth time are both 08:47:09, so the content before and after the rewrite is byte-identical. This proves equality with a same-day copy, taken before any rerun, not with a historic version.
35. **Two pinned environments, not one.** `infrastructure/requirements_audit_env.txt` holds the TVS pins plus statsmodels (for Johansen), xgboost and scikit-learn. `labelsizing_core` needs older pins (xgboost<2.2, numpy<2.2), so it keeps its own lock file. Pip in the new venv
    reached PyPI through the Windows trust store (`--use-feature=truststore`), per process only.
36. **`registry/` moved to `audit/registry/`.** Nothing else changed in the move. Scripts now point there.
37. **Prereg freeze.** H3 note and E1-E7 specs frozen in commit 0fab84c at 2026-10-31 09:26 UTC, before any experiment data was read. GDX, funding and silver downloads ran to the sandbox and were not opened before the freeze commit, except the row counts of the demo journal and the schema of its `trades` table, needed to write E6.
38. **H3 open calls.** Listed in `prereg/H3-SILVER.md`. Gate 1 uses the spread with each month's beta joined together, which adds jumps at month ends and can lengthen the fitted half-life. Fits inside single months are valid in only 4.4% of months, so the conclusion does not rest on that choice. Nothing was rerun to rescue it.
39. **E1 bug fixes.** Two logged in `CHANGES.md`. The entry band of 2 to 4 is a reading of the frozen rule: an entry past its own stop has no meaning. The prereg's text gives only the lower bound, so this is a judgment call, shown with both results. All cells stay short of validation either way.
40. **E1 gate outcome.** Most cells fall under 100 trades at dev, which reads `INSUFFICIENT SAMPLE`. Cointegration passes both tests in 3% to 5% of months, which is about the rate a 5% test gives by chance. That is the finding: the three spreads were not cointegrated in the sense a trader needs.
41. **E3 streams.** The prereg named saved trades, but those files hold only 20 sampled rows, so streams come from `stats/pass_audit.py`, which matched the originals exactly. The Sharpe in E3 annualises by 365 for every stream on a calendar-day index, so its level is not comparable with the stored index Sharpes.
42. **E4 scope.** CPI dates exist only for 2015 and 2025-26 in the source file, which is why 29 CPI events appear. FINAL_v3 and v4 save no exit time, so only entries are re-costed.
43. **E5 reading.** Slices were already opened, so cost changes cannot improve a verdict, as the prereg states. MR3 clears CR-1's gate on one tier only, with p .003 against .007 on a cheaper tier, at n=82. It stays failed and is `INSUFFICIENT SAMPLE`. F6 rose with the dead coins because the trend filter holds them only while they rise and diversifies the book. My blind prediction was wrong on this point.
44. **E6 match.** One-per-zone-day is applied to the backtest to approximate the live throttle. The bot trails stops and the backtester does not, so P&L is not compared trade by trade, only entries and exit reasons. 19 trades cannot support any conclusion. Dukascopy and broker prices differ, shown by entry gaps of $0.16 to $0.41.
45. **E7 full-sample figures.** The with-and-without rule for 2010-2012 means full-sample figures exist for gold, which reads the sealed slices. E7A was marked CONTAMINATED before the run, so nothing was lost. Its PF on 57 spells is not a headline: `INSUFFICIENT SAMPLE`, and spells cannot reach 100 trades at all, which was a flaw in applying the trade-count gate to a slow rule.
46. **Ledger counts TVS's new draw.** A rerun normally counts 0. This one drew mostly new configs, so 64,431 are added. The total rises to 178,991 and every primary DSR drops slightly.
47. **Silver M1.** The tick feed answered 503 at the needed rate, so 2022-26 silver comes from Dukascopy M1 bid and ask candles, for all years, for E1 and E2. Flat zero-volume padded bars are dropped for E2. H3 uses the ticks as its spec says. Downloaded with the `dukascopy-node` tool already installed under `london-breakout/tools`, written only to the sandbox.
48. **Family count for gold.** `goldbot pre-July ledger` holds 41 variants because the ledger has rows with inner variants uncounted, so the family N is a floor and the secondary DSR for FINAL rules is generous.
49. **Live bot.** Not touched. Its code is not in this release, and it is a candidate for a later one.
50. **Phase F review.** A fresh reviewer's findings are in `REVIEW_F.md`. All blocking, high and medium items were fixed. Results stayed where they were, and no fix moved a verdict toward a pass.
51. **E1 entry band.** The band of 2 to 4 was logged as a bug fix on the second run. The prereg says only |z| >= 2, so it is a rule change. The frozen rule is primary and the band sits beside it, counted as 9 more variants. That is why the ledger total went from 178,991 to 179,000.
52. **Split adjustment.** `phaseC/split_fix.py` finds one-day jumps in 19 ETF files and makes an adjusted sandbox, leaving originals alone. Some of the 27 events may be real moves. The adjusted rerun is reported as a sensitivity, not as a replacement result, because the stored numbers are what the verdicts grade. TUNE-1-DIP HOLD-M is the one place a headline changes.
53. **Departures from the preregistrations.** E1: entry band shown beside the frozen rule, and silver spreads come from M1. E2: silver M1 for 2022-26 (DECISIONS 47), FINAL twins reuse H1 holding times, no night fees. E4: exits use the matrix spread because no exit time is saved, and CPI dates exist only for 2015 and 2025-26. E5: no depth-based slippage. E6: one-per-zone-day throttle (DECISIONS 44), and the backtester has no trailing stop. E7: FX cost charged on mid with a measured spread. H3: run as frozen. Each is a limit on the reading. None helped a rule pass.
54. **TUNE-1-DIP stays in the fragile group.** Its registered test failed, and PF 3.05 belongs to the unregistered baseline. Keeping the REPRODUCES-BUT-FRAGILE label grades the number as reproducible. The verdict note, the gate table and the report all say it never passed.
55. **Forward spreads.** Each frozen rule keeps the spread of its own backtest: US500 0.45 for A1 and SW-1, and the TUNE-1 floor for FW-TUNE-1-DIP. The first draft used the floor for all three, which `forward/parity.log` exposed.
56. **Forward feed.** The original bars came from a broker demo feed. The audit uses no broker login, so forward bars come from Dukascopy. This is the same index on a different feed, and the author should confirm it at Checkpoint C.
57. **Monthly schedule.** Updates run on the first UTC day of each month, first on 2026-12-01. No job is scheduled yet. That needs the author's choice of where it runs.
58. **Clean-run findings.** The first clean runs showed sandboxes built partly by hand, so `tools/sandbox_extra.py` now copies those inputs from the originals, and `phaseC/combo5.py` is kept in the repo. `lookahead2.json` and `e4_result.json` had been written without a fixed hash seed. Both were regenerated with PYTHONHASHSEED=0. Only signal counts and key order changed, and no check result moved. The hash check used to treat an output no stage rewrote as a match. It now reports those as not regenerated. `phaseC/deferred_checks.json` cannot be rewritten, because its Yahoo and exchange inputs were not kept, and `tools/expected_diffs.txt` says so.
59. **Final clean run.** `make audit` ran on commit 69dc2e8 from a fresh clone with fresh environments. All 70 stages passed. One file differed: `phaseE/e4_spreads.json`. Every value matched. In 69dc2e8 I had sorted `by_type` in the committed copy by hand and rewrote it with indent 1, while the code writes indent 0. I replaced the committed copy with the bytes of the clean run and did not add an exception. The same clean tree then reads 74 files same, 0 different, 0 unexplained. `phaseC/deferred_checks.json` cannot be regenerated and keeps its stated reason in `tools/expected_diffs.txt`. No code changed after that run, and the e4 stage rewrites this file before reading it, so I did not repeat the full run. `tools/CLEAN_RUN.json` and `tools/CLEAN_STAGES.txt` were the record. In the public tree they are `tools/CLEAN_RUN.json` and `tools/CLEAN_RUN_stages.txt`, from the release's own clean run.
60. **Changes after the clean run.** The full run was on 69dc2e8. `git diff --stat 69dc2e8..fd9de48` lists: AUDIT_REPORT.md (3 lines), CHANGES.md (4), DECISIONS.md (1), FORWARD_TEST.md (8), forward/strategies.json (10), phaseE/e4_spreads.json (2,540, whitespace only), stats/traceability.json (2), stats/traceability.py (2), tools/CLEAN_RUN.json (14), tools/CLEAN_STAGES.txt (70). The only code change is one added entry in the file list of `stats/traceability.py`, which is reporting code. No experiment code changed. The hash check and traceability were rerun on the final commit.
61. **Author decisions at Checkpoint C.** Author Rashed Al Jneibi, repo `preregistered-trading-research`, exclusions confirmed, the 18 excluded entries kept as ledger counts with a one-line reason. Dukascopy confirmed as the forward feed. The monthly job moves to GitHub Actions. iFVG is published as a preregistration and run only after the push. The repository stayed private until the author approved publication.
62. **Forward rule groups.** `forward/rule_groups.json` and `forward/summarize.py` are reporting code, not part of the freeze. They count each rule on each market once. Overlap comes from the full trade lists on the audited bars, not the 20-trade spot-check samples.
63. **Stored output for review numbers (release review, 2026-11-03).** A second release review found that some quoted figures had no saved output: SW-1 PF 1.54 without 2020, EDGE-1-F6 Sharpe 0.33 since 2025 and its lag-1/2/3 Sharpes, H3's 57% share from month-end jumps, and DR-EDGE's true-UTC PF 1.505 and 1.014. `review_f/f6.py` and `review_f/h3.py` were run once more, unchanged, and their output saved in `review_f/out/`. Every figure reproduced: SW-1 ex-2020 PF 1.541 at n=355, F6 2025+ Sharpe 0.33, lags 1.522/1.501/1.432, H3 share 0.568. `review_f/xm1.py` was run the same way for XM-1-A1's "similar Sharpe to buy-and-hold": daily Sharpe 0.78 against 0.76, max drawdown -14.3% against -34.8%, in the market 11.4% of days. The DR figures come from the report the true-UTC run writes (n=1,307 PF 1.505; n=1,025 PF 1.014; one ambiguous trade dropped, so the logs show 1,308 and 1,026 signals). `phaseC/run_dr_flip.sh` now copies both reports into `phaseC/logs_L1/`. These are reruns of existing code, so they add no variants to the ledger. No figure changed.
64. **iFVG withdrawn from this release.** On 2026-11-03 the author decided not to publish an iFVG spec in this release. Item 61's plan, to publish it as a preregistration and run it after the push, is withdrawn. Nothing was run.
63. **Public repository.** The root `DECISIONS.md` covers the release. `registry/` moved to the repository root and `audit/tools/make_audit.sh`, `render_paths.py` and `assemble_data.py` replace reads from the author's folders. The monthly forward job now runs as the GitHub Actions workflow `.github/workflows/forward.yml`, which replaces DECISIONS 57.
