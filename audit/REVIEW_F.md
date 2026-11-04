# Independent review F

The reviewer was a separate Claude agent, started fresh, that had not seen this work before. This review is dated: it gives the trial count as 178,991 over 168 rows, before the last six rows took it to 179,000 over 174. Scripts are in `audit/review_f/`. Nothing else was changed. Git HEAD during review was 40023f2, moving to 51567cc (tooling commits only).

## Bottom line

The arithmetic is strong. The clock finding and all three re-derivations came back exact. No failed result turns into a pass under any fix below.

The write-up is not ready. Five items are blocking: one published PF is a stock-split artefact, one result row is on the wrong cost basis, one verdict contradicts the audit's own frozen rule, one "PASS" was never a pass by its prereg, and one PASS row quotes a false statistic.

"Blocking" means a published number or label is wrong and must be fixed before release. It does not mean a strategy's fate changes.

---

## Blocking findings

### B1. TUNE-1-DIP HOLD-M PF 1.587 is a reverse-split artefact, and the "DSR about 0" is the same artefact

- **Where:** `VERDICTS.md:74`, `stats/pass_audit.py:289-294` and `:22-34`, `_copy/rs_recorded/research/tune1/tune_dip.py:36-44`.
- **What is wrong:** the ETF files in `research/cross_market/data_edge` are raw prices, not split-adjusted. On 2016-11-07 EWJ's close of 12.39 is followed by an open of 49.75, a 1-for-4 reverse split. One RSI2 trade signalled 2016-11-02 books **+295%**. It is the largest trade in the pool by a factor of 16.
- **Evidence** (`review_f/tune.py`):

| Pooled HOLD-M | As stored | Splits adjusted |
|---|---:|---:|
| n | 2,158 | 2,195 |
| PF | 1.585 | **1.361** |
| Avg per trade | +35.5bp | +21.9bp |
| Skew, kurtosis | 39.8, 1,757 | -1.65, 11.3 |
| EWJ PF | 4.15 | 1.18 |
| DSR at N=2,000 | 0.003 | **0.912** |
| DSR at ledger N | about 0 | **0.648** |

  Nine split events hit eight of the thirteen ETFs in HOLD-M: EWJ, EWU, EFA, EEM (two), FXI, SMH, XLK, XLE. They also corrupt the SMA200 filter for about 200 bars each.
- **Why the audit missed it:** "byte-identical" only proves the rewrite copies the same bad input. `trade_checks/TUNE-1-DIP.csv` has no EWJ rows, so "Spot checks 20/20" never touched HOLD-M. No audit document mentions splits on these files.
- **Impact:** the verdict label stays, because the ledger DSR still misses 0.95. But PF 1.587 is overstated by about 0.22, and "about 0 on pooled HOLD-M" is badly understated. The row's fragility argument rests on a bad number. 15 of 18 markets stay above PF 1, so the out-of-market confirmation survives at a lower level.
- **Spread:** `review_f/splits.py` lists raw split jumps in IWM, GDX, SLV, USO and others. `edge_lab.universe()` feeds these ETF files into EDGE-1-F1. XM-1 stress and VS-1 use some of them. None was checked. EDGE-1-F1 and other failed results that use these files need a rerun on adjusted data before "Reruns exact" can stand.

### B2. E4-NEWS reports FINAL_v3 and FINAL_v4 on the wrong cost basis, and the printed figure clears its own gate

- **Where:** `phaseE/e4_news.py:142-146`, `VERDICTS.md:86`.
- **What is wrong:** `prereg/E4-NEWS.md` says trades outside windows "keep the matrix cost", and the gate is PF >= 1.20 "at these costs". The code starts from the stored flat $20 PnL instead.
- **Evidence** (`review_f/e4x.py`, same approximation as `stats/gate_table.py`):

| Rule | VERDICTS "event-aware" | Frozen basis |
|---|---:|---:|
| FINAL_v3 | 1.254 | **1.056** |
| FINAL_v4 | 1.142 | **0.898** |

- **Impact:** the row says FAILED while showing 1.254 against a 1.20 gate, so it contradicts itself. FAILED is correct, the printed number is not. Replace both figures.
- **Smaller defects in the same block:**
  - Line 142 uses 0.75 x 2 = 1.5 times the spread gap for one side. One side costs 1.0 times under the matrix formula.
  - Line 146 counts `extra > 0`, not trades in a window. V3 has 0 either way, V4 has 15 in windows against 14 reported.
  - The prereg's window ratio to the same hour on non-event days is never produced. Line 157 gives one pooled number.
  - The blind prediction of 3x to 6x spreads is never scored.

### B3. E1-PAIRS verdict, its logged fixes and "holdouts stay sealed" do not hold up

- **Where:** `VERDICTS.md:83`, `DECISIONS.md:39-40`, `CHANGES.md:84-88`, `phaseE/e1_pairs.py:132,187,246`.

1. **Wrong label.** All nine cells have dev n below 100 (0 to 31). `prereg/COMMON.md` says such a slice is `INSUFFICIENT SAMPLE` and "is not called a fail". VERDICTS says FAILED. DECISIONS 40 says "most cells". It is every cell.
2. **Unlogged bug: 35 of 139 XAU/XAG months were skipped.** Line 132 tests `t[f0] > t[s0] - 90d`. `searchsorted` returns the first bar at or after that instant, so the test is true whenever the instant falls on a weekend or missing hour. The month is dropped without notice: no formation, no entries, and open positions get no exit checks. Coverage is 104 months as run, 139 when fixed (`review_f/e1_check.py`). The prereg says formation runs every month. The reported cointegration rates sit on the reduced set: 3.8% as run, 3.6% fixed.
3. **Fix 1, inverted exit: genuine.** The first-run JSON shows every exit as `cross`, on the next bar, consistent with the description. The buggy source was never committed, so this rests on outputs alone.
4. **Fix 2, entry band 2 to 4: a rule change, not a bug fix.**
   - `prereg/E1-PAIRS.md` says "Entry |z| >= 2". `COMMON.md` allows only bug fixes after the first run. DECISIONS 39 calls it a judgment call, but CHANGES and the ledger (`AUD-E1-FIX2`) call it a bug.
   - It is not tuning for gain. It lowered BTC/ETH V2 from 1.43 to 1.135 and raised XAU/XAG V3 from 0.010 to 0.025. No cell passes either way.
   - It does change status. On the frozen rule, XAU/XAG V3 (n=105) and BTC/ETH V3 (n=310, PF 0.618) are real FAILs at dev. The fix turned them into `INSUFFICIENT SAMPLE`. CHANGES shows only one of the two.
   - It does not stop the churn it claims to stop. The final file still has a re-entry stopped one bar later on 2016-01-07.
5. **Sealed slices were not sealed.** `run()` trades the whole span, and line 246 writes all trades to git-tracked CSVs. XAU/XAG V3 alone has 19 trades past dev and 10 in holdout, with gross and cost. Say "not evaluated", not "stay sealed". E7 does the same with `n_total` and `why`.

**Correct row:** seven cells `INSUFFICIENT SAMPLE`, two FAIL on the frozen entry rule, none reached validation. Rerun with line 132 fixed, then show frozen-rule and band results side by side.

### B4. TUNE-1-DIP was never a PASS by its prereg

- **Where:** `VERDICTS.md:74`, `CHANGES.md:9`, `registry/experiments.yaml:1847-1851`.
- **What is wrong:** the prereg defines PASS for finalists. All three FAILed (`dip_final.txt`), so the hypothesis "tuning beats the live dip rules" was rejected. "PASSED" was attached afterwards to a baseline that had no gate of its own. The prereg itself warns HOLD-T is not virgin for that baseline. The Original column keeps PASSED, the row never says 0/3, and CHANGES counts it as one of "four results reported as passing".
- **Also:** it is the same rule as XM-1-A1, with US500 in both samples. It is not a fourth independent survivor.
- **Also:** DSR 0.489 treats 122 trades in four US indices as independent. They fall on 81 signal days in 60 weeks. Averaging by week gives T=60, t=2.78 against 4.47, and DSR **0.142** at ledger N (`review_f/tune.py`). The HOLD-T PF of 3.05 has a much weaker basis than the row suggests.
- **Impact:** the row must say the registered test failed, 0 of 3, and that only an unregistered baseline read is reported.

### B5. XM-1-A1 row states two false things

- **"4 of 9 years lose"** (`VERDICTS.md:55`, typed by hand at `phaseC/build_verdicts.py:63`). `stats/pass_audit.json` has 14 years with 4 negative: 2018, 2020, 2022, 2023. Four of nine is true only of 2018-2026, a window nobody states. My recount agrees. The row overstates fragility.
- **"PF 2.37... stored 1.72 and 3.79 are its two halves"** (`CHANGES.md:58`). False. 2.372 is next-open, whose halves are 1.655 and 3.453. 1.72 and 3.79 belong to the signal-close fill, pooled 2.54. The row's Recorded column has the same mix-up. The registry gives both sets correctly.

---

## High

### H1. DSR formula is right, its inputs are not as solid as claimed

- **Formula:** `phaseE/lib.py:26-37` and `stats/pass_audit.py:123-133` match Bailey and Lopez de Prado. Sharpe is not annualised. T matches units: trades for A1, SW-1, TUNE, days for F6. Skew is standard, kurtosis is non-excess, and the (g4-1)/4 term is right. My code reproduces every table DSR to three places (table below).
- **`V[SR] = 1/T` is a floor, not an estimate.** The paper uses the measured variance across trials. Real trials differ in mean, so this understates the hurdle.
- **N is treated as independent trials.** The paper asks for an effective count. TVS-1 and its redraw (129k together) sample one grid on one market set. LBO-1 adds 36,864 cells that are near-duplicates. This overstates the hurdle.
- **So `stats/TRIAL_COUNT.md`'s "the primary DSR is if anything generous" is unsupported.** The two errors pull opposite ways and neither is measured. Call the DSR an order-of-magnitude reading.
- **Ledger N includes work done after each result existed.** XM-1 and SW-1 date from 10-13, when the ledger stood at 569. F6 stood at 625. TUNE-1 at 71,185. The audit's own TVS redraw moved A1 from 0.315 to 0.29 with no bearing on how A1 was chosen. At dated N, A1 is about 0.70 and F6 0.928. All still miss 0.95, so the verdicts stand. The "harsh on purpose" argument should show this column.
- **The gate cannot be met.** At N=178,991, DSR 0.95 needs t of about 6.16. A holdout of n=100 needs a per-trade Sharpe of 0.62. F6 over 3,284 days would need an annual Sharpe of 2.05. `COMMON.md` gate 5 therefore closes the door on nearly any holdout. "Fails the ledger DSR" carries little information alone, and should not be the sole definition of FRAGILE.

### H2. Challenge to each fragile verdict

- **XM-1-A1.** Numbers exact. "Earns less than buy-and-hold" (`CHANGES.md:23`) misleads: exposure is 11%. Mine, daily: Sharpe 0.78 against 0.76, max drawdown 14% against 35%. Fair statement: same Sharpe, smaller drawdown, far lower return. PBO 0.508 comes from a 12-cell grid the audit invented, not the selection that happened. One-bar delay is real (1.80). The delay curve is not monotonic (1.84, 2.00), which suggests noise more than decay.
- **SW-1.** Numbers exact. Row quotes DSR 0.957 at N=10, which clears 0.95, while the ledger count is 50 (0.867). Quoting N=10 flatters. PBO 0.167 uses 10 rules on one market, not the 50 cells searched, and the rule set is mostly unrelated trend rules, so the winner is obvious in advance. Treat PBO as flattering. Ex-2020 PF is 1.54 and ledger DSR 0.06. The row omits this.
- **EDGE-1-F6.** Numbers exact. Fragility is overstated on one point and understated on two.
  - PBO 0.742 on 5 variants: the audit's rule counts rank 3 of 5 as a failure, so pure noise reads 0.60, not 0.50. All five variants earn Sharpe 1.03 to 1.52, and PBO here measures which neighbour won, not whether trend has an edge.
  - Delay is robust: Sharpe 1.52, 1.50, 1.43 at lags 1, 2, 3. The row does not say so, though it reports delay for A1 and SW-1.
  - Omitted: Sharpe 0.33 since 2025. The rise to 1.51 with dead coins tests only eight added losers. The twelve hindsight winners stay, so survivorship is not cleared.
  - Family N=14 omits CR-1's 20 crypto variants, its direct ancestor.
- **TUNE-1-DIP.** See B1 and B4.

---

## Medium

- **M1. Prereg `COMMON.md` manifest missing.** "Inputs and outputs hashed in `phaseE/MANIFEST.sha256`". The file does not exist, and `phaseC/MANIFEST.sha256` has no phaseD or phaseE entries.
- **M2. E5 label conflict** (`CHANGES.md:88`, `phaseE/e5_crypto.py:161-162`). The table says "0 pass" and "MR3 passes" together. MR3 clears CR-1's frozen gate at spot VIP0 (n=82, 33 and 49 per half), and that gate has no n>=100 test. The audit's sample label is not CR-1's rule. The real reasons it stays failed are the prereg's "verdicts cannot improve" and noise: p 0.003, 0.007, 0.008 come from a shared RNG, and the tier with the worst PF got the best p. With 2,000 draws those p values cannot be told apart. Say that.
- **M3. E5 perp tier departs from the frozen spec** (`phaseE/e5_crypto.py:181`). Coin-days before perp listing (16.7%) get the perp fee with zero funding, where the prereg says spot only. Fixing it moves Sharpe from 1.364 to 1.358. Negligible, but it is a deviation.
- **M4. E6 omits frozen comparisons** (`phaseE/e6_paper.py:53`). No exit price gap and no backtest P&L in R. The label INSUFFICIENT SAMPLE is unaffected.
- **M5. E2 twin uses H1's holding times for V3 and V4** (`phaseE/e2_silver.py:91,97`), against "same holding time". Night fee is also left out for V3 and V4. All fail on PF, so no impact.
- **M6. E1 and E7 treat Dukascopy mid as bid.** `XAUUSD.npz` is built as (bid+ask)/2 (`london-breakout/src/lbo/data.py`).
  - `e1_pairs.py:31` adds half a spread to prices the prereg calls mid, about 1bp of noise.
  - `e7_indicators.py:164-165` was written for bid. On mid data it charges about 3 spreads round trip where the prereg's half-spread reading gives 2.
  - Both are harmless to verdicts, since FX gross PF is under 1 anyway.
- **M7. H3 half-life of 504h is an artefact, though the failure is real.** 57% of all movement in the stitched in-sample spread comes from 63 month-end beta jumps. Remove the jumps, or use one beta, and phi is at or above 1.0, so no mean reversion exists at all. DECISIONS 38 understates this. The 4.4% monthly valid share is mostly test power: t >= 3 on 500 bars requires a half-life under 19h. So it is weak support. Gate 1 still fails on every reading, and this conclusion is stronger than stated.
- **M8. 55-day hole in CFD data, undisclosed.** US500, US30, US2000 and USTEC have no bars from 2025-07-16 to 2025-09-09. DE40 has a 48-day hole. SMA and RSI run across it by bar count, and it is inside the HOLD-T window. No A1 trade spans it. No audit document mentions it.
- **M9. Trial count code.** `stats/trial_count.py:11` turns a blank into 0, so NQ-TRANSFER counts as nothing without notice. Immaterial in size. The family map (line 18) omits CR-1 for F6 and adds ORB to TUNE-1-DIP, an unrelated market family.
- **M10. Stale figures side by side.** VERDICTS rows use N=114,500 and the tables use 178,991: A1 0.315 and 0.29, SW-1 0.231 and 0.207. `CHANGES.md:23` keeps 0.32 and 0.23. Disclosed in one line, confusing in practice.
- **M11. `stats/gate_table.py` SC-1 row** cites "a PF >= 1.0 requirement". The TUNE-1 prereg has no such gate for the live ORB baseline.

## Low

- **L1. CLOCK_BUG understates its support for 2010-2012.** It says only reopen and break hours support the US rule. Macro anchors exist in the US/EU gap weeks. NFP 2010-11-05 at stamp 13:31, NFP 2012-11-02 at 13:30, and CPI 2012-03-16 at 13:33 all sit at true 12:30 + 1h, which is the US rule. FOMC gap-week dates were not clean. Worth adding.
- **L2. DR n differs by one or two** across the registry (1351), `dr_matrix.json` (1352) and `l2_more.json` (1353).
- **L3. Rewrite n=2,159 is unexplained.** My independent count equals the stored 2,158.
- **L4. FINAL_v3 and v4 DSR** in `stats/gate_table.py` uses flat-cost returns, not matrix-cost ones. Both are near 0 either way.
- **L5. FINAL_v3 with honest gap fills** is PF 1.329 (net $43,623). CHANGES gives the net but not the PF.

---

## Preregistration discipline

- `prereg/` has no change after 0fab84c. Commit time 09:26:55 UTC matches DECISIONS 37.
- Result files and run scripts all date after the freeze. Silver downloads began before it (`dk_xag` 2015 file at 13:19 local), as disclosed.
- Departures from the frozen text:
  - E1: entry band, month skip.
  - E4: cost basis, missing ratio.
  - E5: perp pre-listing.
  - E6: missing comparisons.
  - E2: twin holds.
  - COMMON: manifest, "not called a fail".
  - E3: stream source (disclosed, DECISIONS 41).
- Only E3's and part of E1's are disclosed.

## Lookahead and leakage: checked, clean

No lookahead found in the rule logic of these files. Each was read line by line for signal timing, fill timing, window edges and pre-entry data use.

- `e1_pairs.py`: formation ends before the month's first bar. Kalman uses the pre-update state. Fills at next open. Slices are by entry time.
- `e2_silver.py`: `prep` and `h1_trades` are causal. The sandbox silver CSV really is silver. The clock shift is not double-applied. No gold-dollar constant is reached on these paths.
- `e4_news.py`: event times and DST are right. Per-year p90 spreads use a whole year, normal for a cost model.
- `e5_crypto.py`: signals lag returns by one bar. Twin uses open-to-open at t+1.
- `e6_paper.py`: journal stamps are true UTC, shown by matched entries at -0.0 minutes and gaps of $0 to $0.72.
- `e7_indicators.py`: spells and FX exits are causal, stop tested before target.
- `h3_run.py`: beta and z are causal.
- `lib.py`: slices, twin and gates match COMMON.

Yahoo adjusted GDX embeds later dividends in earlier prices. The effect is tiny and the prereg chose it.

## Other items checked and clean

- Clock claim in full (table below), including the 62.1% share, 28 segments and 3,474 days.
- FOMC counts, 162 months, minimum monthly correlation 0.916, 803 switch days (`clock_anchors.json`).
- `trial_count.py` total and `TRIAL_COUNT.md`: 178,991, 168 rows, no duplicate ids. Registry and ledger agree on all 89 shared rows but one blank.
- E1 fix 1, E5 fix (first run flagged the three trend rules as described).
- Verdict tally 38, 24, 11, 4, 1, plus 18 excluded, sums to the 96 registry entries.
- No failed rule turns positive in any test I ran.

## Spot-check of numbers

46 scripted comparisons in `review_f/spots.py`, no mismatch. A further 30 or so by eye from the JSON files, with four exceptions, all reported above.

| Group | Numbers checked |
|---|---|
| H1 | n 481, PF 1.009, p90 0.933, old 0.831, new 1.114, DD $11,291, recorded 1.130, 1.045, $7,108, splits 11 and 8, measured 0.952, Hour-20 n=102, 1.081, +$1,948 |
| FINAL_v3, v4 | 436, 1.254, $33,520, $14,959, 1.667, $70,596, $6,935, 577, 1.145, $20,185, 2025: 52, 76.9%, 1.13, $3,338, 86.3%, 2.90, 1.331, $39,875 |
| H family | H-B 1.040, 0.847, 9, 0.989; H-N 0.914, 65; H-P 1.033; HR 1.075, +0.007; H-M 0.999; H-S 0.197, 55,477 |
| DR, DOOR-3, CYCLES | 1.099, 1.001, 0.974, 0.780; 4 of 353, $37.86; 0 of 360, $17.60; 3.65, 2019-10-24, 2.40, 2018-12-19, Sidak 0.954, 0.182 |
| SC-1 | 1.259, 1.247, 0.0025, 0.81, 0.03, 0.88, 3.2% |
| Phase E | E1 all three runs, E2 0.487, 0.683, 0.450, E4 1.008, E5 1.47, 1.49, 1.36, 1.51, E6 6 of 19, H3 504h, 488h, TVS 1,020, 64,431 |
| Exceptions | "4 of 9 years" (B5), "1.72 and 3.79 are its halves" (B5), DR n (L2), HOLD-M n (L3) |

---

## Three re-derivations

Own code, no audit or original code imported. For (c) the prose spec was not enough, so I read the harness for three details: the 10-H4-close dead check, the 10 x ATR zone filter, and ATR as of the last H1 before midnight. That makes (c) a faithful second implementation of the harness, not proof the harness matches the live rule.

| Claim | Audit | My number | Gap | Explanation |
|---|---|---|---:|---|
| (a) Days mapped against Dukascopy | 3,474 | 3,474 | 0 | Tested 17 lags at minute resolution, not whole hours only |
| (a) Distinct lags, segments | 2, 28 | 2 (0 and +60 min), 28 | 0 | No 1-minute offset. Margin is wide: median best corr 0.996, second best 0.05 |
| (a) Two-regime rule, using tz database not audit bounds | no exception | 0 mismatches of 3,474 | 0 | The 242 days where US and EU disagree split cleanly: all US through 2018, all EU from 2019. The boundary is only pinned between 2018-11-02 and 2019-03-11 |
| (a) Share of bars shifted | 62.1% | 62.06% | 0 | 2010-2012 by assumption, see L1 |
| (b) XM-1-A1 n | 124 | 124 | 0 | Same trades |
| (b) PF next open, halves | 2.372, 1.655, 3.453 | 2.372, 1.655, 3.453 | 0 | Wilder RSI gives the same |
| (b) PF close fill | 2.542 | 2.540 | 0.002 | I count nights from fill dates |
| (b) DSR at 12, 17, 114,500, 178,991 | 0.949, 0.934, 0.315, 0.29 | 0.949, 0.934, 0.315, 0.290 | 0 | Independent formula |
| (b) One-bar delay PF | 1.80 | 1.796 | 0 | |
| (c) FINAL_v3 true UTC, n | 436 | 436 | 0 | All 436 entries same time and side |
| (c) PF, net, max DD | 1.254, $33,520, $14,959 | 1.254, $33,520, $14,959 | 0 | Trade PnL equal to within 1e-12 |
| (c) Eras | 240 at 1.066, 196 at 1.371 | same | 0 | |
| (c) Net with gap fills | $43,623 | $43,623 | 0 | PF 1.329 |
| SW-1 (extra) | 397, 1.741, 0.207 at ledger | 397, 1.741, 0.207 | 0 | |
| EDGE-1-F6 (extra) | Sharpe 1.52, DSR 0.52 | 1.522, 0.520 | 0 | |
| TUNE-1-DIP HOLD-T (extra) | 122, 3.049, 0.489 | 122, 3.049, 0.489 | 0 | Exact, but see B4 |
| TUNE-1-DIP HOLD-M (extra) | n 2,159, PF 1.587 | n 2,158, PF 1.585 raw; n 2,195, **PF 1.361** adjusted | 0.22 | Gap is the split artefact, B1 |
