"""
analyze_results.py — Compare the four VP-backtest configurations.

Loads the per-config trade/summary CSVs produced by backtest_vp.py and emits:

  1. A side-by-side summary table -> console + results/comparison_table.csv
  2. Equity curves (baseline vs VP overlay) -> results/equity_curve_D.png,
     results/equity_curve_R.png   (saved, never shown)
  3. VP filter impact analysis (console): trades removed per sub-filter, win rate
     of filtered-out vs kept trades, and the POC-distance distribution split by
     win/loss.
  4. Gate contribution analysis (console, Profile_D_VP): polarity True/False
     split + win rates, and ADX-bin vs outcome.
  5. The full text report -> results/vp_analysis_report.txt

matplotlib uses the non-interactive "Agg" backend so nothing is displayed.
"""

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")            # headless: save PNGs, never display
import matplotlib.pyplot as plt  # noqa: E402

_THIS = Path(__file__).resolve()
_RESULTS_DIR = _THIS.parent / "results"

_CONFIGS = ["Profile_D_Baseline", "Profile_D_VP",
            "Profile_R_Baseline", "Profile_R_VP"]


class _Tee:
    """Write to both the console and an in-memory buffer (for the report file)."""

    def __init__(self):
        self.buf = io.StringIO()

    def __call__(self, *args):
        line = " ".join(str(a) for a in args)
        print(line)
        self.buf.write(line + "\n")


def _safe_read_csv(path):
    """
    Read a CSV, returning an empty DataFrame for a missing/empty/header-less file.

    An empty pandas DataFrame written by to_csv leaves a file with no parseable
    columns; guarding here keeps the analysis robust when a config took 0 trades.

    Params:
        path (Path): CSV path.

    Returns:
        DataFrame: parsed rows, or an empty frame.
    """
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _load_trades(config_name):
    """
    Load a config's taken-trades CSV into a DataFrame (empty frame if missing).

    Params:
        config_name (str): e.g. "Profile_D_VP".

    Returns:
        DataFrame: taken trades (possibly empty).
    """
    path = _RESULTS_DIR / f"{config_name}.csv"
    return _safe_read_csv(path)


def _load_filtered(config_name):
    """
    Load a VP config's filtered-out signals CSV (empty frame if missing).

    Params:
        config_name (str): e.g. "Profile_D_VP".

    Returns:
        DataFrame: filtered-out signals (possibly empty).
    """
    path = _RESULTS_DIR / f"{config_name}_filtered.csv"
    return _safe_read_csv(path)


def _load_summary(config_name):
    """
    Load a config's one-row summary CSV (None if missing).

    Params:
        config_name (str): e.g. "Profile_D_VP".

    Returns:
        dict or None: the summary row.
    """
    path = _RESULTS_DIR / f"{config_name}_summary.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return df.iloc[0].to_dict() if len(df) else None


def comparison_table(out):
    """
    Print + save the side-by-side summary table.

    Params:
        out (_Tee): logging sink.

    Returns:
        DataFrame: the comparison table.
    """
    rows = []
    for cfg in _CONFIGS:
        s = _load_summary(cfg)
        if s is None:
            continue
        rows.append({
            "Config": s["Config"], "Trades": s["Trades"],
            "WinRate%": s["WinRate%"], "PF": s["PF"],
            "Expectancy": s["Expectancy"], "MaxDD_pts": s["MaxDD_pts"],
            "VP_PassRate%": s.get("VP_PassRate%", ""),
        })
    table = pd.DataFrame(rows)
    table.to_csv(_RESULTS_DIR / "comparison_table.csv", index=False)
    out("\n" + "=" * 70)
    out("SIDE-BY-SIDE COMPARISON")
    out("=" * 70)
    out(table.to_string(index=False))
    return table


def equity_curves(out):
    """
    Save baseline-vs-VP equity-curve overlays for Profile D and Profile R.

    Params:
        out (_Tee): logging sink.
    """
    for prof in ("D", "R"):
        base = _load_trades(f"Profile_{prof}_Baseline")
        vpc = _load_trades(f"Profile_{prof}_VP")
        plt.figure(figsize=(11, 6))
        for label, df, style in ((f"Profile {prof} Baseline", base, "-"),
                                 (f"Profile {prof} VP", vpc, "--")):
            if len(df) and "pnl_points" in df:
                eq = df["pnl_points"].cumsum().to_numpy()
                plt.plot(range(1, len(eq) + 1), eq, style, label=label)
        plt.axhline(0, color="grey", lw=0.8)
        plt.title(f"Equity Curve (cumulative points) — Profile {prof}")
        plt.xlabel("Trade #")
        plt.ylabel("Cumulative points")
        plt.legend()
        plt.grid(True, alpha=0.3)
        out_path = _RESULTS_DIR / f"equity_curve_{prof}.png"
        plt.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close()
        out(f"[analyze] saved {out_path.name}")


def vp_filter_impact(out):
    """
    Report how the VP filter reshaped each profile's trade set.

    For each profile: count filtered-out signals per failing sub-filter, compare
    win rate of filtered-out vs kept trades, and print the POC-distance
    distribution split by winners/losers.

    Params:
        out (_Tee): logging sink.
    """
    out("\n" + "=" * 70)
    out("VP FILTER IMPACT ANALYSIS")
    out("=" * 70)
    for prof in ("D", "R"):
        kept = _load_trades(f"Profile_{prof}_VP")
        filt = _load_filtered(f"Profile_{prof}_VP")
        out(f"\n--- Profile {prof} ---")
        out(f"Kept (VP-passed) trades : {len(kept)}")
        out(f"Filtered-out signals    : {len(filt)}")

        if len(filt):
            for col, name in (("fail_poc", "POC proximity"),
                              ("fail_va", "Value-Area context"),
                              ("fail_lvn", "LVN path")):
                if col in filt:
                    out(f"   removed by {name:<20}: "
                        f"{int(filt[col].sum())}")

            f_win = (filt["pnl_points"] > 0).mean() * 100.0
            out(f"Win rate of FILTERED-OUT trades : {f_win:.1f}%  "
                f"(avg pnl {filt['pnl_points'].mean():.1f} pts)")
        if len(kept):
            k_win = (kept["pnl_points"] > 0).mean() * 100.0
            out(f"Win rate of KEPT trades         : {k_win:.1f}%  "
                f"(avg pnl {kept['pnl_points'].mean():.1f} pts)")
        if len(filt) and len(kept):
            verdict = ("removed mostly LOSERS (good)"
                       if (filt["pnl_points"] > 0).mean()
                       < (kept["pnl_points"] > 0).mean()
                       else "removed mostly WINNERS (bad)")
            out(f"=> Filter {verdict}")

        # POC distance distribution split by outcome (kept trades).
        if len(kept) and "poc_distance_atr" in kept:
            k = kept.dropna(subset=["poc_distance_atr"])
            if len(k):
                w = k[k["pnl_points"] > 0]["poc_distance_atr"]
                l = k[k["pnl_points"] <= 0]["poc_distance_atr"]
                out("POC distance (ATR) — winners vs losers:")
                out(f"   winners: n={len(w)} "
                    f"mean={w.mean():.3f} median={w.median():.3f}"
                    if len(w) else "   winners: none")
                out(f"   losers : n={len(l)} "
                    f"mean={l.mean():.3f} median={l.median():.3f}"
                    if len(l) else "   losers : none")
                _hist_ascii(out, w, l)


def _hist_ascii(out, winners, losers, bins=(0, 0.25, 0.5, 0.75, 1.0)):
    """
    Print a compact ASCII histogram of POC distance for winners vs losers.

    Params:
        out (_Tee): logging sink.
        winners (Series): poc_distance_atr for winning trades.
        losers (Series): poc_distance_atr for losing trades.
        bins (tuple): bin edges (in ATR units).
    """
    edges = list(bins) + [float("inf")]
    out("   poc_dist bin   wins  losses")
    for lo, hi in zip(edges[:-1], edges[1:]):
        wc = int(((winners >= lo) & (winners < hi)).sum()) if len(winners) else 0
        lc = int(((losers >= lo) & (losers < hi)).sum()) if len(losers) else 0
        label = f"{lo:.2f}-{'inf' if hi == float('inf') else f'{hi:.2f}'}"
        out(f"   {label:<12} {wc:>5} {lc:>7}")


def gate_contribution(out):
    """
    Profile_D_VP gate-contribution analysis: polarity split + ADX-bin outcomes.

    Params:
        out (_Tee): logging sink.
    """
    out("\n" + "=" * 70)
    out("GATE CONTRIBUTION ANALYSIS (Profile_D_VP)")
    out("=" * 70)
    df = _load_trades("Profile_D_VP")
    if not len(df):
        out("No Profile_D_VP trades to analyse.")
        return

    # Polarity True vs False split.
    if "polarity_flipped" in df:
        for flag in (True, False):
            sub = df[df["polarity_flipped"] == flag]
            if len(sub):
                wr = (sub["pnl_points"] > 0).mean() * 100.0
                pct = len(sub) / len(df) * 100.0
                out(f"polarity={flag!s:<5}: {len(sub):>3} trades "
                    f"({pct:4.1f}%)  win%={wr:5.1f}  "
                    f"avgPnl={sub['pnl_points'].mean():.1f}")

    # ADX bin vs outcome.
    if "adx_value" in df:
        out("\nADX bin vs outcome:")
        bins = [(25, 30), (30, 40), (40, np.inf)]
        for lo, hi in bins:
            sub = df[(df["adx_value"] >= lo) & (df["adx_value"] < hi)]
            label = f"{lo}-{'inf' if hi == np.inf else hi}"
            if len(sub):
                wr = (sub["pnl_points"] > 0).mean() * 100.0
                out(f"   ADX {label:<7}: {len(sub):>3} trades  win%={wr:5.1f}  "
                    f"avgPnl={sub['pnl_points'].mean():.1f}")
            else:
                out(f"   ADX {label:<7}:   0 trades")
        # Point-biserial correlation between ADX and win/loss.
        adx = df["adx_value"].to_numpy(dtype=float)
        win = (df["pnl_points"] > 0).astype(float).to_numpy()
        if len(df) > 2 and adx.std() > 0 and win.std() > 0:
            corr = np.corrcoef(adx, win)[0, 1]
            out(f"   corr(ADX, win) = {corr:.3f}")


def main():
    """
    Produce all comparison artefacts and write the text report.

    Returns:
        int: 0 on success, 1 if no result CSVs were found.
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if not any((_RESULTS_DIR / f"{c}_summary.csv").exists() for c in _CONFIGS):
        print("[analyze] No summary CSVs found — run backtest_vp.py first.")
        return 1

    out = _Tee()
    out("VOLUME PROFILE BACKTEST — ANALYSIS REPORT")
    comparison_table(out)
    equity_curves(out)
    vp_filter_impact(out)
    gate_contribution(out)

    report_path = _RESULTS_DIR / "vp_analysis_report.txt"
    report_path.write_text(out.buf.getvalue(), encoding="utf-8")
    out(f"\n[analyze] Full report saved to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
