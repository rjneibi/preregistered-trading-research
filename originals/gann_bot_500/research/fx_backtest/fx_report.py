"""
fx_report.py — assemble the FX transfer-test comparison report from the per-run
JSON summaries written by fx_dr_backtest.py and fx_s_backtest.py.

Produces results/FX_BACKTEST_REPORT.md: the single comparison table (9 runs + the
Profile D gold baseline reference row), directional/USD-correlation bias analysis,
the Profile S FX go/no-go benchmark proposal, and conclusions. Pure formatting —
reads only the JSON files, never MT5.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "results")


def load(name):
    with open(os.path.join(RES, name), encoding="utf-8") as f:
        return json.load(f)


def pf_str(v):
    if isinstance(v, str):
        return v
    if v == float("inf"):
        return "inf"
    return f"{v:.2f}"


def num(v):
    """Coerce pf that may be 'inf'/Infinity/float to float for comparisons."""
    if isinstance(v, str):
        return float("inf") if v == "inf" else float(v)
    return float(v)


def ls(r):
    """Long/short counts — top-level for S, inside 'full' for D/R."""
    f = r["full"]
    lo = f.get("longs", r.get("longs", 0))
    sh = f.get("shorts", r.get("shorts", 0))
    return lo, sh


# ── Gold baselines (reference) ────────────────────────────────────────────────
GOLD_D = {"pf": 1.20, "exp_R": 0.146, "oos_n": 162, "note": "walk-forward validated"}


def main():
    dr = load("summaries_DR.json")
    s = load("summaries_S.json")
    by = {(r["profile"], r["symbol"]): r for r in dr}
    for r in s:
        by[(r["profile"], r["symbol"])] = r

    pairs = ["EURUSD", "GBPUSD", "AUDUSD"]
    profiles = ["D", "R", "S"]
    L = []
    A = L.append

    A("# FX Transfer Test — Profiles D, R, S on EURUSD / GBPUSD / AUDUSD")
    A("")
    A("Backtest-only study. No live trading, Telegram, or config.py change was made. "
      "The live Profiles D/R/S and the running fleet are untouched.")
    A("")
    A("## Methodology")
    A("")
    A("- **Data**: broker demo feed, verified bare symbol names "
      "`EURUSD`/`GBPUSD`/`AUDUSD` (no broker suffix). 7-year window "
      "2019-06 → 2026-06, fetched via `copy_rates_range`. All three share identical "
      "contract specs: digits 5, point 1e-5, tick_value $1.0, tick_size 1e-5, "
      "contract 100 000 → point value **$1 / point / lot**.")
    A("- **Walk-forward**: 70/30 chronological in-sample/out-of-sample split "
      "(same methodology as the gold D/R validation). Locked, already-validated "
      "parameters — **no per-pair re-optimisation** of any gate. All ATR-relative "
      "params (SL/TP/BE/trail/confluence/ADX/swing) identical across pairs.")
    A("- **D/R engine**: reuses the live six-gate logic in `research/backtest.py` "
      "**unchanged**. FX OHLC scaled ×10 000 so FX's 1e-5 point maps onto the "
      "engine's gold-calibrated 0.01 (2-decimal) tick granularity — otherwise the "
      "live `levels.py` rounding collapses every FX level and forces ATR to 0. "
      "All performance metrics (R, win%, PF, expectancy, MaxDD) are scale-invariant.")
    A("- **S engine**: reuses `backtest_s.py` **unchanged** (raw-float math, no 2dp "
      "rounding) — runs natively at 1e-5. Adds a currency-aware news blackout on top "
      "of the engine's weekend-gap control.")
    A("- **Costs (realistic, after-cost expectancy)**: per-symbol spread + $7/lot "
      "round-trip commission, charged once per trade. S additionally charges nightly "
      "swap (dynamic, from `symbol_info`).")
    A("")
    A("### Step 2 — symbol-aware sizing & spread (per-symbol config)")
    A("")
    A("`risk.calculate_lot_size()` was audited: it already reads `trade_tick_value`, "
      "`trade_tick_size`, `point`, and `volume_min/max/step` from `symbol_info()` per "
      "symbol — fully symbol-agnostic, **no gold hardcoding, no change needed**. "
      "The only instrument-specific knob in scope is the spread filter. "
      "`MAX_SPREAD_POINTS=40` is gold-tuned (~10× a typical FX spread → effectively "
      "disabled on FX), so per-symbol values are derived from 7y of recorded bar "
      "spreads:")
    A("")
    A("| Symbol | 7y H1 spread (median / mean / p90, pts) | Backtest spread cost (pts) | Proposed live `MAX_SPREAD_POINTS` |")
    A("|---|---|---|---|")
    A("| EURUSD | 2 / 3.4 / 8 | 8 (+7 commission) | 15 |")
    A("| GBPUSD | 3 / 5.9 / 18 | 12 (+7 commission) | 30 |")
    A("| AUDUSD | 4 / 5.5 / 16 | 11 (+7 commission) | 25 |")
    A("")
    A("Backtest spread cost ≈ 2× the recorded mean (a conservative retail markup over "
      "this tight demo feed); proposed live threshold ≈ p90 + buffer so it blocks only "
      "genuine news-spike spreads. These are **proposals documented here only** — no "
      "live config.py change was applied (task guardrail).")
    A("")

    # ── Master comparison table ──
    A("## Master comparison table (9 runs + gold baseline)")
    A("")
    A("Metrics are **FULL period** unless the column says OOS. PF and expectancy are "
      "in R, net of spread + commission. MaxDD% is on a 1%-fixed-fractional equity "
      "curve (same basis for all profiles). "
      "‘Pol-flip win%’ = win rate of trades where the polarity gate flipped vs didn’t "
      "(D); for S the polarity/break-retest gate is mandatory so it equals the overall "
      "win rate.")
    A("")
    hdr = ("| Profile | Pair | Trades (full / OOS) | Win% (full / OOS) | "
           "PF (full / OOS) | MaxDD% (full / OOS) | Exp R (full / OOS) | "
           "Pol-flip win% (flip / no-flip) | Long/Short | Meets gold PF≥1.20? |")
    A(hdr)
    A("|" + "---|" * 11)

    def fmt_run(prof, pair):
        r = by[(prof, pair)]
        f, o = r["full"], r["oos"]
        pol = r["polarity_full"]
        if prof in ("D", "R"):
            flip = f"{pol['flip_w']}/{pol['flip_n']}={pol['flip_wr']:.0f}%" if pol["flip_n"] else "—"
            noflip = f"{pol['noflip_w']}/{pol['noflip_n']}={pol['noflip_wr']:.0f}%" if pol["noflip_n"] else "—"
            polcell = f"{flip} / {noflip}"
        else:
            polcell = f"{pol['flip_wr']:.0f}% (all {pol['flip_n']}) / —"
        meets = "✅" if (num(f["pf"]) >= 1.20 and num(o["pf"]) >= 1.20) else "❌"
        lo, sh = ls(r)
        return (f"| {prof} | {pair} | {f['n']} / {o['n']} | "
                f"{f['win_rate']:.0f}% / {o['win_rate']:.0f}% | "
                f"{pf_str(f['pf'])} / {pf_str(o['pf'])} | "
                f"{f['maxdd']:.0f}% / {o['maxdd']:.0f}% | "
                f"{f['exp_R']:+.3f} / {o['exp_R']:+.3f} | "
                f"{polcell} | {lo}/{sh} | {meets} |")

    for prof in profiles:
        for pair in pairs:
            A(fmt_run(prof, pair))
    A(f"| **D (gold ref)** | **XAUUSD** | — / {GOLD_D['oos_n']} | — | "
      f"**{GOLD_D['pf']:.2f}** (OOS) | ≤25% | **{GOLD_D['exp_R']:+.3f}** | n/a | — | "
      f"baseline ({GOLD_D['note']}) |")
    A("")

    # ── Directional bias ──
    A("## Directional / USD-correlation bias")
    A("")
    A("EUR, GBP and AUD all trade **against USD**, so a directional tilt that is "
      "*consistent across pairs within a profile* is concentrated USD exposure, not "
      "diversification — even when each pair's PF looks independent.")
    A("")
    A("| Profile | EURUSD L/S | GBPUSD L/S | AUDUSD L/S | Cross-pair tilt |")
    A("|---|---|---|---|---|")
    for prof in profiles:
        cells = []
        tilts = []
        for pair in pairs:
            lo, sh = ls(by[(prof, pair)])
            tot = lo + sh
            pctL = 100.0 * lo / tot if tot else 0
            cells.append(f"{lo}/{sh} ({pctL:.0f}% L)")
            tilts.append(pctL)
        avg = sum(tilts) / len(tilts)
        if avg >= 58:
            tilt = f"**long-biased (~{avg:.0f}% L) — correlated USD-short**"
        elif avg <= 42:
            tilt = f"**short-biased (~{avg:.0f}% L) — correlated USD-long**"
        else:
            tilt = f"balanced (~{avg:.0f}% L)"
        A(f"| {prof} | {cells[0]} | {cells[1]} | {cells[2]} | {tilt} |")
    A("")

    # ── Step 5 benchmark proposal ──
    A("## Step 5 — Profile S go/no-go benchmarks on FX")
    A("")
    A("Gold benchmarks: PF ≥ 1.20, **≥100 OOS trades**, MaxDD ≤ 25%, polarity-gate "
      "win rate > 56%.")
    A("")
    soos = {r["symbol"]: r["oos"]["n"] for r in s}
    sfull = {r["symbol"]: r["full"]["n"] for r in s}
    A(f"**Observed S trade counts over 7y (full / OOS):** "
      f"EURUSD {sfull['EURUSD']}/{soos['EURUSD']}, "
      f"GBPUSD {sfull['GBPUSD']}/{soos['GBPUSD']}, "
      f"AUDUSD {sfull['AUDUSD']}/{soos['AUDUSD']}.")
    A("")
    A("**Proposal.** The ≥100-OOS-trade bar cannot transfer: Profile S is a "
      "low-frequency Daily/H4 swing system, and across a *full 7-year* FX window each "
      "pair produced only ~24–41 trades total and **5–16 OOS** — versus gold's recent "
      "high-volatility regime that generated 100+ OOS trades in ~1.5y. I therefore "
      "propose, applied consistently to all three pairs:")
    A("")
    A("1. **Minimum sample for any verdict: ≥30 OOS trades.** Below this, PF/win-rate "
      "are statistically meaningless and the verdict is **INCONCLUSIVE (NO-GO by "
      "insufficient data)** regardless of the point estimate. *(All three FX pairs "
      "fail this floor — 5/16/12 OOS.)*")
    A("2. PF ≥ 1.20, MaxDD ≤ 25%, polarity-gate win > 56% **retained unchanged** — "
      "they are scale-free quality bars — but only *evaluated* once the sample floor "
      "is met.")
    A("")
    spf = {r["symbol"]: pf_str(r["full"]["pf"]) for r in s}
    A("Under this rule every FX pair is **NO-GO for Profile S on data-sufficiency "
      f"grounds alone**; the sub-1.0 full-period PFs ({spf['EURUSD']} / "
      f"{spf['GBPUSD']} / {spf['AUDUSD']}) reinforce it. "
      "The news blackout (NFP + RBA windows) blocked 0 entries — with only ~30 setups "
      "in 7y, the chance of one landing in a monthly 3-hour window is negligible; "
      "ECB/BoE/FOMC decision days are not fixed-date and are not reproducible without "
      "a historical calendar feed (unavailable via the MT5 Python API).")
    A("")

    # ── Verdicts vs gold ──
    A("## Verdict vs the gold PF 1.20 baseline")
    A("")
    A("- **Profile D**: fails on every FX pair — full-period PF 0.72 / 0.80 / 0.73, "
      "negative expectancy (−0.24 / −0.17 / −0.24 R), OOS PF 0.63 / 0.81 / 0.68. "
      "Does **not** transfer.")
    A("- **Profile R**: best of the three but still sub-baseline — full PF 0.90 / "
      "0.88 / 0.84. Only **EURUSD OOS** crosses break-even (PF 1.03, +0.019 R over "
      "372 trades), and only marginally; well under PF 1.20. Does **not** meet the "
      "gold bar.")
    A("- **Profile S**: insufficient OOS sample on every pair (NO-GO by data floor) "
      "and sub-1.0 full-period PF.")
    A("")
    A("**No pair/logic combination meets or exceeds the gold PF 1.20 benchmark.** The "
      "gold-validated edge is volatility-regime-specific and does not transfer to "
      "EUR/GBP/AUD on the existing, un-retuned logic. A notable structural reason: "
      "FX's ATR-to-price ratio (~0.1%) is far below gold's (~0.7%), so the Gann "
      "Square-of-9 confluence levels (spaced ~1–2% of price) fall outside the 10×ATR "
      "zone-relevance window and contribute essentially nothing — FX zone construction "
      "rests on Fib pivots + retracements alone.")
    A("")
    A("## Artifacts")
    A("")
    A("Per-run trade logs (daily_log format + full per-trade reasoning) and JSON "
      "summaries are in `research/fx_backtest/results/`: "
      "`trades_{D,R,S}_{EURUSD,GBPUSD,AUDUSD}.csv`, `summary_*.json`.")
    A("")

    out = os.path.join(RES, "FX_BACKTEST_REPORT.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("Wrote", out)
    print("\n".join(L))


if __name__ == "__main__":
    main()
