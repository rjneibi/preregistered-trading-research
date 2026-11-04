# What the audit changed

Originals are untouched. Stored claims stay in the registry next to the audit figures. This file records both changed numbers and changed stories.
Full evidence for the clock is in `findings/CLOCK_BUG.md`.

## Conclusions

- No failed experiment became a pass. No Phase D or E experiment passed.
- Four results recorded as passing are exact but fragile: XM-1-A1, SW-1, EDGE-1-F6 and TUNE-1-DIP. TUNE-1-DIP never passed its registered test, and it is the same rule as XM-1-A1. None clears the deflated Sharpe at the full ledger count. EDGE-1-F6 clears it only at its family count, which decides nothing.
- Claims that looked close to passing, such as H-B, H-N, H-P and the FINAL rules, moved well away once the clock was right.

## Narratives changed

| Old story | Status | New reading |
|---|---|---|
| Hour 20 is a cash-close effect at 20:00 UTC | **Retired** | The cohort mixed 19:00 and 20:00 UTC trades. On true UTC its PF is 1.08 at p90 and Sidak p since 2023 is 0.999. H-20's premise is gone |
| News days are the best trades | **Retired** | H-N PF 0.914, new era 1.03 |
| FINAL_v4 won 86% in 2025 | **Retired** | 76.9%, PF 1.13, n=52 |
| FINAL_v3 net $70,596, DD $6,935 | **Replaced** | PF 1.25, DD $14,959. Drawdown doubles and net halves |
| The new era is sharply better than the old | **Weakened** | Old-era PF tops out at 1.07 across the FINAL and H rules, and the gap between eras narrows on true UTC. H1 new era 1.114, H-B 1.162 |
| Zero of 360 winners reach $20 | **Retired** | 4 of 353, max $37.86. DOOR-3's stop argument came from the mislabelled sample |
| Live flip_bot trades the tested edge | **Replaced** | The bot runs on true UTC, so its rule is the true-UTC column: H1 PF 1.009, p90 0.933, measured spread 0.952 |
| XM-1-A1 and SW-1 passed | **Qualified** | The numbers are exact. Ledger-count DSR is 0.29 and 0.21. A1 is in the market 11% of days, with a similar Sharpe, a smaller drawdown and a far lower return than buy-and-hold, and PF falls about a quarter with a one-bar delay |
| Sweep fade works on M5 and M15 | **Stays invalid** | Round 4 leak, also present in rounds 8 and 9 |
| `ta_lab` EU-date conversion is wrong (Phase B B4) | **Withdrawn** | It was correct: 1,098 of 1,098 days |

## Number changes

| ID | Metric | Stored | Audit, true UTC |
|---|---|---|---|
| H1 | PF, n | 1.130, 472 | 1.009, 481 |
| H1 | p90 PF | 1.045 | 0.933 |
| H1 | Max drawdown | $7,108 | $11,291 |
| H2 | PF, n | 1.174, 193 | 1.035, 200 |
| H-N | PF | 1.443 | 0.914 |
| H-P | PF | 1.279 | 1.033 |
| H-B | PF | 1.376 | 1.040 |
| HR | Routed PF | 1.336 | 1.075 |
| H-M | Filtered PF | 1.102 | 0.999 |
| FINAL_v3 | Pooled PF, net | 1.667, $70,596 | 1.254, $33,520 |
| FINAL_v4 | Pooled PF, net | 1.331, $39,875 | 1.145, $20,185 |
| DR D | No-spread PF | 1.326 | 1.505. At matrix cost 1.099, at p90 1.001 |
| DR R | No-spread PF | 1.06 | 1.014. At matrix cost 0.780 |
| DOOR-3 | Winners reaching $20 | 0 of 360 | 4 of 353 |
| FR-L | Reference n, PF | 679, 0.587 | 623, 0.497 |
| FR-M | M0, M4 PF, partial matrix | 0.102, 0.372 | 0.086, 0.350 |
| Hour 20 | p90 PF, net | 1.793, +$11,700 | 1.081, +$1,948 |
| CYCLES | Net sup-F, date | 2.40, 2018-12-19 | 3.65, 2019-10-24 |

The H1 row's stored line is the full-coverage confirmation. Its earlier partial-coverage PF 1.24 stays in the registry.

Some numbers rose on true UTC: DR D, HCRT, HSW and two raw flip grid cells. All still fail.

## Stored figures that needed context

- H-P, SZ, H-R, H-M, H-S and FR-M reproduce exactly only on the partial matrix of their own date. FR-M on the full matrix is M0 0.019, M4 0.173.
- FINAL_v3 net depends on gap policy. Its harness fills no gaps on either side, which scores a +$94 weekend target at the barrier. The audit engine gets $80,379 recorded and $43,623 true. The harness figure is the lower, so the table above keeps it.
- XM-1-A1's PF of 2.37 is the full sample at next-open fills, whose halves are 1.65 and 3.45. The stored 1.72 and 3.79 are the halves of the signal-close fill, 2.54 overall. All reproduce.
- EDGE-1-F9 Sharpe 3.01 used five streams. The script later gained a sixth, which reads 2.58.
- TUNE-1-DIP HOLD-M has n=2,159 in the rewrite against 2,158 stored.
- SC-1 fills a break at the range edge even when the bar opened beyond it (3.2% of trades). Filling at the open gives PF 1.247 against 1.259.

## Audit mistakes, corrected

- **First clock fix wrong.** Phase B used US switch dates for all years, and the extra anchor showed that. The H1 figures given at that stage are withdrawn.
- **Original results folder touched.** `xm_lab` and `news_lab` import `fable-backtesting/build_calendar.py` by absolute path, and that file rewrites `calendar/news_days.json` on import. A sandbox rerun did this once. Contents are byte-identical (SHA-256 unchanged), but the modified time moved from 2026-10-14 17:22 to 2026-10-31 10:26:52. Restoring the time was not attempted. `phaseC/sandbox_paths.py` prevents a repeat. DECISIONS 18.
- **Lookahead control was too weak.** The Phase B harness stopped one row short, so a one-bar peek could pass. It was fixed and rerun clean.
- **First TA-LAB gap patch overstated the effect.** Replaced, DECISIONS 22.
- **FR-M looked identical to the original before it had rerun.** That was a stale copied file. The real rerun shows the partial-matrix dependence above.

## Added after Checkpoint B

- **TVS-1 Phase 2 defect.** `phase2.py` seeds its grid with `hash((asset, tf))`, and Python salts that hash per process, so the stored search cannot be replayed. A rerun drew 64,431 configs, mostly new, and also gives 0 of 20. All 1,020 stored configs checked, including the top 20, re-evaluate exactly. The verdict moves from UNVERIFIED to VERIFIED-WITH-CORRECTIONS.
- **LABELSIZING-CORE** reran in its own pinned environment. All gating asserts pass. It holds no market result.
- **H3-SILVER** ran as frozen and FAILED at its validity gate: half-life 504 hours on true UTC, 488 recorded, against a limit of 240.
- **Ledger count.** Primary DSR now uses 179,000 variants. Phase C files keep 114,500. Every DSR falls slightly.
- **FINAL_v3 and FINAL_v4 gates are now named.** VERDICTS has a table for every PF above 1.1.
- **TA-LAB same-bar check.** Under both orderings, no row at or below zero turns positive. Rows above zero fall from 89 to 53, so the failures were not understated, and the positive figures were overstated.
- **ASSUMED-CLOCK.** 2010-2012 removed from eight gold reruns. No pass or fail line moves. EXIT-2-FLIP E5 falls from PF 1.01 to 0.97.
- **EDGE-1-F6 costs.** Sharpe 1.52 becomes 1.47 on spot VIP0, 1.49 with the BNB discount and 1.36 on perpetuals with funding. Adding eight collapsed coins gives 1.51.

## Run bugs in the audit's own new code, logged under the prereg rule

| Run | Bug | Before | After |
|---|---|---|---|
| E1 first run | Exit test inverted, so every trade closed on the next bar | XAU/XAG V3 dev n=297, PF 0.006 | superseded |
| E1 all runs | Month check dropped months whose window opened on a weekend or missing hour | 35 of 139 XAU/XAG months lost, V3 n=105 | All months run, V3 n=109, PF 0.030 |
| E1 data | Half a spread added to prices that were already mid | about 1bp | removed |
| E4 first run | FINAL rules kept the flat cost, against the prereg | FINAL_v3 1.254, FINAL_v4 1.142 | FINAL_v3 1.056, FINAL_v4 0.898 |
| E5 first run | "passes" label skipped CR-1's twin gate and used a weak ETH check | 3 trend rules marked as passing | 0 trend rules pass. MR3 clears CR-1's gate on one tier at n=82, with p values that cannot be told apart from the failing tiers. Opened slices cannot improve a verdict |
| E5 first run | Perp fee used before a coin's perp listed | Sharpe 1.364 | Sharpe 1.358 |
| E6 first run | Exit gap and backtest R omitted | not reported | 6 matched trades: median exit gap $11.66 |

The E1 entry band of 2 to 4 was first called a bug fix. The review showed it is a rule change: the prereg says only |z| >= 2. The frozen rule is therefore primary, and the band is shown beside it as a logged deviation with 9 more variants in the ledger.

None of these fixes moved a result to a pass.

## Found by the Phase F review

- **Raw ETF prices.** Daily ETF files are not split-adjusted. `phaseC/split_events.json` lists the jumps. TUNE-1-DIP HOLD-M falls from PF 1.59 to 1.36 and its finalists stay failed. EDGE-1-F1 moves from Sharpe -0.27 to -0.26. Reruns of XM-1, SW-1, VS-1, combo and edge rules change figures in cells but no verdict line.
- **CFD data hole.** US500, US30, US2000 and USTEC have no bars from 2025-07-16 to 2025-09-09, and DE40 has a 48-day hole. Bar-count indicators run across it. No A1 trade spans it.
- **H3 half-life.** 57% of movement in the joined spread comes from month-end beta jumps. Without them there is no mean reversion at all, so the failure is stronger than 504 hours suggests.
- **Open small items.** DR n reads 1,351, 1,352 or 1,353 by file. TUNE-1-DIP rewrite n=2,159 against stored 2,158 stays unexplained. FINAL_v3 with real gap fills is PF 1.329.

## Not verified

CHANNEL-B-SCORE (scored file missing). iFVG was not run because its spec was never received.

## Found by the final clean run

- **Spread file format.** `phaseE/e4_spreads.json` was committed with a hand rewrite in a different indent. Values were identical. The committed copy now has the bytes the code writes. See DECISIONS 59.

## Found by the release's cold review, 2026-11-03

Wording and labels only. No rule, input or computed number changed, and the verdict counts are the same.

- **Sample-size labels.** VERDICTS now gives n for the FINAL_v4 2025 slices (51 and 52) and the HR routed trades (107 and 105), labels H-N, TA-LAB-R11, the FINAL_v4 2025 slices and E5's MR3 `INSUFFICIENT SAMPLE`, and states that any figure under 100 trades is `INSUFFICIENT SAMPLE`. Before, only some of these rows carried the label.
- **TVS-1 DSR.** VERDICTS now says that TVS-1's best config has a DSR of 0.957 stored and 0.969 rerun, on TVS-1's own trial count, and that a pass needed eight conditions at once. Before, the DSR above 0.95 was in `phaseC/tvs_recheck.json` without comment.
- **TRIAL_COUNT.md** now states the TVS-1 exception to "reruns count 0", from DECISIONS 46.
- **Wording.** "Excluded by your instruction" and "INCOMPLETE by your decision" now name the author. H-20's note says the audit did not open the sealed prediction. `|corr|` is written `abs(corr)`, because the pipes broke the table row.

## Found by the second release review, 2026-11-03

Six fresh reviewers checked the release for truth, organisation and completeness. Each change below shows the old text beside the new. No verdict changed.

| Item | Was | Now | Evidence |
|---|---|---|---|
| HCRT true-UTC PF in VERDICTS | "PF 0.914" | "n=605 PF 0.913". The 0.914 was H-N's figure, copied by mistake | `HCRT_run.json` arm E1_filtered, pf_real 0.9134 |
| TA-LAB-R4 fixed, 2025+ slice, twin gate | "Beats 50% of twins" | "Beats 45% of twins". 50% is the M5 row's figure | `phaseC/logs_L1/recorded.ta_lab.round12_py.log` |
| AUDIT_REPORT, the audit's own clean run | "74 output files matched by hash, 0 differed" | One file differed in formatting only, with equal values; after its committed copy was replaced, the comparison read 74 same, 0 different | DECISIONS 59 |
| Forward test, time to 100 trades | "about four to eight years" for the US500 rules | About 3.5 years for SW-1 (397 trades in about 13.5 years) and about 11 for XM-1-A1 (124 trades) | `phaseC/pass_audit.json` |
| Figures with no saved output | SW-1 PF 1.54 without 2020; F6 Sharpe 0.33 since 2025 and its lag Sharpes; H3's 57%; DR-EDGE true PFs; XM-1-A1's Sharpe against buy-and-hold | Unchanged, now backed by saved output. All reproduced | DECISIONS 63, `review_f/out/`, `phaseC/logs_L1/*.dr_backtest_report.md` |
| TA-LAB-R11 as a check of FINAL_v4 | The original FINAL_v4 note says it was killed "by H1 and TA-LAB round 11", and the R11 page called it a FINAL_v4 check | Round 11 tests a different level: the classic floor R3 = H + 2(PP - L) on M15 bars, not FINAL_v4's R3 = PP + (H - L) on H1. It is not evidence about FINAL_v4. FINAL_v4's verdict rests on its own rerun, n=577 PF 1.145 on true UTC, below the 1.20 gate | `originals/gann_bot_500/research/ta_lab/round11.py` line 29; `originals/gann_bot_500/research/goldbot/goldbot/pivots.py` lines 11-12 |

### Process issues disclosed by the second release review

These do not change a stored number. They change how far a result can be trusted, and each experiment page now states them.

- **TUNE-1-DIP selection.** The three finalists have plateau ratios of 1.01 to 1.06, below the frozen plateau rule of 1.2, and they come from a hand-written JSON. No published file records the "weakened, disclosed" gate. TUNE-1-DIP is in the forward test; its frozen rules are unchanged.
- **TUNE-1-ORB grid.** The code ran 800 configurations where the frozen grid gives 640, and how its 3 finalists were chosen is not recorded.
- **TVS-1 ranking.** The top 20 configurations were ranked on out-of-sample Sharpe, so its out-of-sample read is not clean.
- **Partial cost matrix.** HR's stored PF 1.484 (n=107), H-S's 0.307 and H-M's 1.206 use the earlier partial matrix. On the full matrix HR reads 1.336 and H-S 0.200; both still fail.
- **FLIP-BOT-DEFECTS tests.** The 15/15 pass was seen on the console only. The audit's stored log shows the suite failing to import a module.
- **FORWARD-FLIP-DEMO gate.** The 0.906 x ATR gate value appears in no published file, and `flip_bot.py` uses 0.835.
- **E5 swing twin.** The twin is charged 5% a year financing while the rule pays none, which favours the rule.
- **E4 NFP dates.** They come from a first-Friday rule, not the real release calendar.
- **Ledger counts.** 18 rows count fewer configurations than were run. The counts sit beside the ledger in `registry/ledger_corrections.csv`, and `stats/TRIAL_COUNT.md` gives the corrected total.
- **Random twin.** `phaseE/lib.py` `twin_p` gives each twin trade a random side, so a long-only rule can beat it on drift alone. This makes the gate easier to pass, so it cannot have caused a failure.



## Audit commit log

This repository starts from a fresh history, because the audit's own history holds personal paths (see the root DECISIONS.md, item 2). This is that history in summary. Times are local, UTC+4. The hashes refer to a private repository, so a reader cannot check them.

| Commit | Time | What |
|---|---|---|
| `1b74f1f` | 2026-10-31 08:54 | Phase B: infrastructure checks, audit engine, H1 clock measurement |
| `332983a` | 2026-10-31 08:54 | Correct signal comparison count in Phase B report |
| `bb4de2a` | 2026-10-31 11:34 | Phase C: verify results on both clocks, record verdicts, changes and clock finding |
| `e57fd68` | 2026-10-31 11:37 | Correct rerun count and HPF, VP-FILTER clock notes |
| `03539c9` | 2026-10-31 13:03 | Bring registry under version control, add audit env lock, record third-round decisions |
| `0fab84c` | 2026-10-31 13:26 | Freeze H3 completion note and E1-E7 preregistrations before any data is loaded |
| `40023f2` | 2026-10-31 13:58 | Phases D and E: H3-SILVER, E1-E7 results, TVS-1 and LABELSIZING verified, gate, DSR and clock tables |
| `36447fd` | 2026-10-31 14:00 | Add make audit pipeline, traceability check and clean-run hash comparison |
| `51567cc` | 2026-10-31 14:00 | Clear queue markers before a clean run |
| `60c4d32` | 2026-10-31 14:34 | Apply Phase F review fixes |
| `73ea90c` | 2026-10-31 14:38 | Resolve the clean-run workdir to an absolute path |
| `ba84b81` | 2026-10-31 16:06 | Complete clean-run sandboxes and stop stale files passing the hash check |
| `69dc2e8` | 2026-10-31 17:46 | Fix remaining clean-run gaps |
| `e62ffea` | 2026-10-31 19:28 | Record final clean run, restore e4_spreads.json to the bytes the code writes |
| `ef96092` | 2026-10-31 19:29 | Freeze forward strategies: FW-XM-1-A1, FW-SW-1, FW-TUNE-1-DIP, FW-EDGE-1-F6 |
| `e12be17` | 2026-10-31 19:29 | Record the freeze hash and UTC time in FORWARD_TEST.md |
| `fd9de48` | 2026-10-31 19:29 | Separate FR-L's unverified figure from its graded reference run in the report |
| `b8d7e3f` | 2026-10-31 22:39 | State which forward rules overlap, add delay note and reporting summary, log changes since the clean run |
