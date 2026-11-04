"""H-S verdict run — HS_PREREGISTRATION.md (commit 55539b9) applied verbatim.

Order (CLAUDE_CODE_PROMPT_HS.md): exhibits first, then the 12 pinned configs
under the H1 purged-split protocol (selection on train folds, same config
evaluated OOS), then the permutation reality check, then gates + decision tree.

Speed note (sanctioned, semantics frozen): scalp_lab.dollar_barrier is pure
Python; this runner uses a vectorized engine that is asserted EXACTLY
equivalent (t1, exit price, reason, ambiguity) against scalp_lab on random
samples for every config before any result is computed. Same for the
vectorized cost lookup vs CostMatrix.spread_usd. Any mismatch aborts the run.

Cost wiring (pinned): per-oz cost EXCLUDING commission = spread(entry-hour) x
(1 + 2*k_slip) with k_slip=0.5; $7/lot RT commission charged separately
(pf_net convention). Frontier c = per-oz + $0.07 (commission per oz).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from goldbot.config import load_config, resolve_path  # noqa: E402
from goldbot.data import load_ohlc  # noqa: E402
from cost_matrix import CostMatrix  # noqa: E402
from scalp_lab import (breakeven_frontier, dollar_barrier, momo_burst_events,  # noqa: E402
                       move_vs_cost, session_mask, zscore_fade_events)

RESULTS = ROOT / "results"
MATRIX = RESULTS / "cost_matrix.json"
START = pd.Timestamp("2015-06-19T00:00:00Z")
ERA_SPLIT = pd.Timestamp("2021-06-19T00:00:00Z")
K_SLIP = 0.5
COMMISSION_RT = 7.0
CONTRACT_OZ = 100
HORIZON = 30
GEOMETRIES = ((0.5, 0.5), (1.0, 1.0), (1.5, 0.75))
SESSIONS = (None, (12, 20))
N_PERM = 200

REASON_CODES = {0: "time", 1: "sl_gap", 2: "tp_gap", 3: "ambiguous->sl",
                4: "sl", 5: "tp"}


# ── vectorized barrier engine (equivalence-proven vs scalp_lab) ──────────
def fast_dollar_barrier(o, h, l, c, events, sides, tp_usd, sl_usd,
                        horizon=HORIZON, chunk=60_000):
    n = len(o)
    keep = events + 1 < n
    events, sides = events[keep], sides[keep]
    outs = []
    amb_total = 0
    for k0 in range(0, len(events), chunk):
        ev = events[k0:k0 + chunk]
        sd = sides[k0:k0 + chunk].astype(float)
        i0 = ev + 1
        entry = o[i0]
        tp = entry + sd * tp_usd
        sl = entry - sd * sl_usd
        end = np.minimum(i0 + horizon, n - 1)
        width = horizon + 1
        W = i0[:, None] + np.arange(width)[None, :]
        valid = W <= end[:, None]
        Wc = np.minimum(W, n - 1)
        O, Hh, Ll = o[Wc], h[Wc], l[Wc]
        sd2 = sd[:, None]
        tp2, sl2 = tp[:, None], sl[:, None]
        # per-bar conditions in scalp_lab priority order
        c1 = np.where(sd2 > 0, O <= sl2, O >= sl2) & valid            # sl_gap
        c2 = np.where(sd2 > 0, O >= tp2, O <= tp2) & valid & ~c1      # tp_gap
        htp = np.where(sd2 > 0, Hh >= tp2, Ll <= tp2)
        hsl = np.where(sd2 > 0, Ll <= sl2, Hh >= sl2)
        c3 = htp & hsl & valid & ~c1 & ~c2                            # dual -> sl
        c4 = hsl & valid & ~c1 & ~c2 & ~c3                            # sl
        c5 = htp & valid & ~c1 & ~c2 & ~c3 & ~c4                      # tp
        anyhit = c1 | c2 | c3 | c4 | c5
        has = anyhit.any(axis=1)
        j = np.argmax(anyhit, axis=1)
        rowsel = np.arange(len(ev))
        code = np.zeros(len(ev), dtype=int)
        code[has & c1[rowsel, j]] = 1
        code[has & c2[rowsel, j]] = 2
        code[has & c3[rowsel, j]] = 3
        code[has & c4[rowsel, j]] = 4
        code[has & c5[rowsel, j]] = 5
        t1 = np.where(has, W[rowsel, j], end)
        exit_px = c[end].copy()                                       # time
        gap_px = O[rowsel, j]
        exit_px = np.where(code == 1, gap_px, exit_px)
        exit_px = np.where(code == 2, gap_px, exit_px)
        exit_px = np.where((code == 3) | (code == 4), sl, exit_px)
        exit_px = np.where(code == 5, tp, exit_px)
        amb_total += int((code == 3).sum())
        outs.append(pd.DataFrame({
            "t0": i0, "t1": t1, "side": sd.astype(int),
            "entry": entry, "exit_price": exit_px,
            "exit_reason": [REASON_CODES[x] for x in code]}))
    t = (pd.concat(outs, ignore_index=True) if outs else
         pd.DataFrame(columns=["t0", "t1", "side", "entry", "exit_price",
                               "exit_reason"]))
    return t, amb_total


def assert_engine_equivalence(df, o, h, l, c, events, sides, tp, sl, tag,
                              sample=1200, seed=99):
    rng = np.random.default_rng(seed)
    if len(events) > sample:
        pick = np.sort(rng.choice(len(events), sample, replace=False))
        ev, sd = events[pick], sides[pick]
    else:
        ev, sd = events, sides
    ref, ref_amb = dollar_barrier(df, ev, sd, tp, sl, HORIZON)
    fast, fast_amb = fast_dollar_barrier(o, h, l, c, ev, sd, tp, sl)
    assert len(ref) == len(fast), f"{tag}: row count {len(ref)} vs {len(fast)}"
    for col in ("t0", "t1", "side"):
        assert (ref[col].to_numpy() == fast[col].to_numpy()).all(), f"{tag}:{col}"
    for col in ("entry", "exit_price"):
        assert np.allclose(ref[col], fast[col], rtol=0, atol=0), f"{tag}:{col}"
    assert (ref["exit_reason"].to_numpy() == fast["exit_reason"].to_numpy()).all(), \
        f"{tag}:reason"
    assert ref_amb == fast_amb, f"{tag}: ambiguous {ref_amb} vs {fast_amb}"


# ── vectorized cost lookup (equivalence-proven vs CostMatrix) ────────────
class VecCost:
    def __init__(self, matrix_path, stat):
        self.cm = CostMatrix.load(matrix_path, stat=stat, k_slip=K_SLIP,
                                  commission_per_lot_rt=COMMISSION_RT)
        m = self.cm.m
        self.cell = {(int(y), int(hh)): float(v[stat])
                     for y, hs in m["years"].items() for hh, v in hs.items()}
        self.yfall = {int(y): float(v.get(stat, v["median"]))
                      for y, v in m["fallback"].items() if y != "_global"}
        g = m["fallback"]["_global"]
        self.gfall = float(g.get(stat, g["median"]))
        self.fallback_hits = 0

    def spread(self, years, hours):
        out = np.empty(len(years))
        for i, (y, hh) in enumerate(zip(years, hours)):
            v = self.cell.get((y, hh))
            if v is None:
                self.fallback_hits += 1
                v = self.yfall.get(y, self.gfall)
            out[i] = v
        return out

    def per_oz(self, years, hours):
        """per-oz cost EXCLUDING commission: spread x (1 + 2*k_slip)."""
        return self.spread(years, hours) * (1.0 + 2.0 * K_SLIP)

    def assert_equivalence(self, index_utc, sample_pos):
        for p in sample_pos:
            ts = index_utc[p]
            ref = self.cm.spread_usd(ts)
            got = self.spread(np.array([ts.year]), np.array([ts.hour]))[0]
            assert abs(ref - got) < 1e-12, f"cost lookup mismatch at {ts}"


def pf_exp(net: np.ndarray) -> tuple[float, float, int]:
    if len(net) == 0:
        return float("nan"), float("nan"), 0
    w, lo = net[net > 0].sum(), net[net <= 0].sum()
    pf = float(w / abs(lo)) if lo != 0 else float("inf")
    return pf, float(net.mean()), int(len(net))


def main() -> int:
    assert MATRIX.exists(), "cost matrix missing"
    cfg = load_config(ROOT / "config.yaml")
    mjson = json.loads(MATRIX.read_text())

    # ── cost levels computed FROM the matrix (no hardcoded brackets) ──────
    buckets = [(int(y), int(hh), v) for y, hs in mjson["years"].items()
               for hh, v in hs.items()]
    w = np.array([v["n"] for _, _, v in buckets], float)
    med = np.array([v["median"] for _, _, v in buckets])
    p90 = np.array([v["p90"] for _, _, v in buckets])
    mean_spread = float((med * w).sum() / w.sum())
    p90_spread = float((p90 * w).sum() / w.sum())
    old_hours = {}
    for y, hh, v in buckets:
        if 2015 <= y <= 2018:
            a, b = old_hours.get(hh, (0.0, 0.0))
            old_hours[hh] = (a + v["median"] * v["n"], b + v["n"])
    best_old_spread = min(a / b for a, b in old_hours.values())
    lvl = {"matrix_mean": mean_spread * 2, "best_session_old": best_old_spread * 2,
           "p90_stress": p90_spread * 2}                     # per-oz excl comm
    allin = {k: v + COMMISSION_RT / CONTRACT_OZ for k, v in lvl.items()}
    print("cost levels (per-oz excl comm | all-in):")
    for k in lvl:
        print(f"  {k}: {lvl[k]:.3f} | {allin[k]:.3f}")

    # ── exhibits FIRST (descriptive) ─────────────────────────────────────
    frontier = breakeven_frontier(costs=tuple(round(allin[k], 3) for k in
                                              ("best_session_old", "matrix_mean",
                                               "p90_stress")),
                                  geometries=GEOMETRIES)
    print("\n== EXHIBIT: breakeven frontier (required win rate) ==")
    print(frontier.to_string(index=False))

    print("\nloading full M1 ...", flush=True)
    m1_full = load_ohlc(resolve_path(cfg, cfg.data.m1_path),
                        data_tz=cfg.data.data_tz)
    mvc = move_vs_cost(m1_full, cost_usd_oz=allin["matrix_mean"])
    print("\n== EXHIBIT: |move| per horizon vs all-in cost (full history) ==")
    print(mvc.to_string(index=False))
    (RESULTS / "HS_exhibits.md").write_text(
        "# H-S exhibits (descriptive, no gate)\n\n"
        f"cost levels per-oz excl comm: {json.dumps(lvl)}\n"
        f"all-in (+$0.07 commission): "
        f"{json.dumps({k: round(v, 4) for k, v in allin.items()})}\n\n"
        "## Breakeven frontier — required win rate w* = (SL+c)/(TP+SL)\n\n```\n"
        + frontier.to_string(index=False) +
        "\n```\n\n## Move vs cost (full real M1 history, matrix-mean all-in cost)\n\n```\n"
        + mvc.to_string(index=False) + "\n```\n", encoding="utf-8")

    # ── data slice + signals ─────────────────────────────────────────────
    df = m1_full[(m1_full.index >= START - pd.Timedelta(days=1))]
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    idx = df.index
    print(f"\nM1 slice: {len(df):,} bars {idx[0]} -> {idx[-1]}")

    ev_z, sd_z = zscore_fade_events(df)
    ev_m, sd_m = momo_burst_events(df)
    print(f"events: z-fade {len(ev_z):,} | momo-burst {len(ev_m):,}")

    configs = []
    for sig, (ev, sd) in (("z_fade", (ev_z, sd_z)), ("momo", (ev_m, sd_m))):
        for tp, sl in GEOMETRIES:
            for sess in SESSIONS:
                mask = session_mask(idx, ev, sess)
                configs.append({"name": f"{sig}_tp{tp}_sl{sl}_"
                                        f"{'all' if sess is None else 'ldn_ny'}",
                                "tp": tp, "sl": sl, "horizon": HORIZON,
                                "events": ev[mask], "sides": sd[mask]})
    assert len(configs) == 12, "the pinned family is exactly 12 configs"

    # ── run configs (engine equivalence proven per config) ───────────────
    vc_med = VecCost(MATRIX, "median")
    vc_p90 = VecCost(MATRIX, "p90")
    vc_med.assert_equivalence(idx, np.linspace(70, len(df) - 2, 25, dtype=int))
    years_all = idx.year.to_numpy()
    hours_all = idx.hour.to_numpy()
    era_new_start = idx.searchsorted(ERA_SPLIT)
    hr_all = idx.asi8 // 3_600_000_000_000

    trades = {}
    for cf in configs:
        assert_engine_equivalence(df, o, h, l, c, cf["events"], cf["sides"],
                                  cf["tp"], cf["sl"], cf["name"])
        t, amb = fast_dollar_barrier(o, h, l, c, cf["events"], cf["sides"],
                                     cf["tp"], cf["sl"])
        pos = t["t0"].to_numpy()
        gross = (t["side"] * (t["exit_price"] - t["entry"])).to_numpy() * CONTRACT_OZ
        cm_ = vc_med.per_oz(years_all[pos], hours_all[pos]) * CONTRACT_OZ
        cp_ = vc_p90.per_oz(years_all[pos], hours_all[pos]) * CONTRACT_OZ
        trades[cf["name"]] = {
            "cfg": cf, "n": len(t), "ambiguous": amb, "pos": pos,
            "t_hr": hr_all[pos], "era_new": pos >= era_new_start,
            "net_med": gross - cm_ - COMMISSION_RT,
            "net_p90": gross - cp_ - COMMISSION_RT,
        }
        pf_all, exp_all, n_ = pf_exp(trades[cf["name"]]["net_med"])
        print(f"  {cf['name']:>28}: n={n_:,} amb={amb:,} "
              f"full-period PF={pf_all:.3f} exp=${exp_all:,.2f}")

    # ── purged-split protocol (identical params to H1) ───────────────────
    all_t = np.concatenate([v["t_hr"] for v in trades.values()])
    lo_t, hi_t = int(all_t.min()), int(all_t.max())
    edges = np.linspace(lo_t, hi_t + 1, 7).astype(int)
    bounds = [(int(edges[g]), int(edges[g + 1]) - 1) for g in range(6)]
    TAU, MARGIN = 24, max(24, 40)

    split_rows, oos_by_cfg = [], {k: [] for k in trades}
    for sid, tg in enumerate(combinations(range(6), 2)):
        spans = [bounds[g] for g in tg]
        best_name, best_pf = None, -np.inf
        masks = {}
        for name, tr in trades.items():
            th = tr["t_hr"]
            test = np.zeros(len(th), bool)
            purge = np.zeros(len(th), bool)
            for g_lo, g_hi in spans:
                test |= (th >= g_lo) & (th <= g_hi)
                purge |= (th >= g_lo - TAU) & (th <= g_hi + MARGIN)
            train = ~test & ~purge
            masks[name] = test
            pf_tr, _, n_tr = pf_exp(tr["net_med"][train])
            if n_tr >= 50 and np.isfinite(pf_tr) and pf_tr > best_pf:
                best_pf, best_name = pf_tr, name
        test_net = trades[best_name]["net_med"][masks[best_name]]
        pf_te, exp_te, n_te = pf_exp(test_net)
        split_rows.append({"split": sid, "test_groups": tg,
                           "selected": best_name, "train_pf": round(best_pf, 3),
                           "oos_pf": round(pf_te, 3), "oos_n": n_te,
                           "oos_exp": round(exp_te, 2)})
        oos_by_cfg[best_name].append((sid, masks[best_name]))

    print("\n== purged splits (selection on train, evaluated OOS) ==")
    for r in split_rows:
        print(f"  split {r['split']:>2} {r['test_groups']}: "
              f"selected {r['selected']} (train PF {r['train_pf']}) -> "
              f"OOS PF {r['oos_pf']} n={r['oos_n']:,} exp=${r['oos_exp']}")

    sel_counts = {k: len(v) for k, v in oos_by_cfg.items() if v}
    winner = max(sel_counts, key=sel_counts.get)
    wt = trades[winner]
    w_mask = np.zeros(wt["n"], bool)
    for _, m in oos_by_cfg[winner]:
        w_mask |= m
    w_med = wt["net_med"][w_mask]
    w_p90 = wt["net_p90"][w_mask]
    w_new = wt["era_new"][w_mask]
    pf_w, exp_w, n_w = pf_exp(w_med)
    pf_w90, _, _ = pf_exp(w_p90)
    pf_old, _, n_old = pf_exp(w_med[~w_new])
    pf_new, _, n_new = pf_exp(w_med[w_new])
    print(f"\nwinning config: {winner} (selected in {sel_counts[winner]}/15 splits; "
          f"all selections: {sel_counts})")
    print(f"  OOS (unique test trades): n={n_w:,} PF={pf_w:.3f} exp=${exp_w:,.2f}")
    print(f"  eras: old PF={pf_old:.3f} (n={n_old:,}) new PF={pf_new:.3f} (n={n_new:,})")
    print(f"  p90-cost OOS PF={pf_w90:.3f}")

    # ── permutation reality check (matched counts, matrix-mean cost) ──────
    print(f"\npermutation reality check: {N_PERM} replicates ...", flush=True)
    rng = np.random.default_rng(0)
    n_bars = len(df)
    perm_cost = lvl["matrix_mean"] * CONTRACT_OZ
    best = np.empty(N_PERM)
    for r in range(N_PERM):
        pfs = []
        for name, tr in trades.items():
            k = tr["n"]
            cf = tr["cfg"]
            ev = np.sort(rng.choice(n_bars - HORIZON - 2, size=k, replace=False))
            sds = rng.choice([-1, 1], size=k)
            tt, _ = fast_dollar_barrier(o, h, l, c, ev, sds, cf["tp"], cf["sl"])
            g = (tt["side"] * (tt["exit_price"] - tt["entry"])).to_numpy() * CONTRACT_OZ
            pfs.append(pf_exp(g - perm_cost - COMMISSION_RT)[0])
        best[r] = np.nanmax(pfs)
        if (r + 1) % 25 == 0:
            print(f"  {r+1}/{N_PERM} (running p95={np.percentile(best[:r+1],95):.3f})",
                  flush=True)
    perm_p95 = float(np.percentile(best, 95))
    perm_med = float(np.median(best))
    print(f"permutation best-of-12: median {perm_med:.3f}, p95 {perm_p95:.3f}")

    # ── gates (HS_PREREGISTRATION.md verbatim) ───────────────────────────
    gates = {
        "1_oos_pf_ge_1.30": pf_w >= 1.30,
        "2_each_era_oos_pf_ge_1.10": pf_old >= 1.10 and pf_new >= 1.10,
        "3_p90_oos_pf_ge_1.10": pf_w90 >= 1.10,
        "4_oos_n_ge_500": n_w >= 500,
        "5_beats_permutation_p95": pf_w > perm_p95,
    }
    hs_pass = all(gates.values())
    verdict = "BAR-LEVEL PASS (weak by construction -> tick-level stage)" \
        if hs_pass else "BAR-LEVEL FAIL -> scalping/HFT line CLOSED with evidence"
    print(f"\n  H-S gates: {gates}\n== VERDICT: {verdict} ==")

    out = {"cost_levels_per_oz_excl_comm": lvl, "all_in": allin,
           "config_summary": {k: {"n": v["n"], "ambiguous": v["ambiguous"],
                                  "full_pf_med": pf_exp(v["net_med"])[0],
                                  "full_exp_med": pf_exp(v["net_med"])[1]}
                              for k, v in trades.items()},
           "splits": split_rows, "selections": sel_counts, "winner": winner,
           "winner_oos": {"n": n_w, "pf": pf_w, "exp": exp_w,
                          "pf_old": pf_old, "n_old": n_old,
                          "pf_new": pf_new, "n_new": n_new, "pf_p90": pf_w90},
           "permutation": {"n_perm": N_PERM, "median": perm_med, "p95": perm_p95},
           "fallback_hits": {"median": vc_med.fallback_hits,
                             "p90": vc_p90.fallback_hits},
           "gates": gates, "pass": hs_pass, "verdict": verdict}
    (RESULTS / "HS_run.json").write_text(json.dumps(out, indent=1, default=str))

    with open(RESULTS / "DECISIONS.log", "a", encoding="utf-8") as f:
        f.write(f"{date.today().isoformat()}  H-S VERDICT RUN (prereg 55539b9, "
                f"matrix costs, partial coverage deviation carries).\n")
        f.write(f"            frontier (all-in $/oz): "
                f"{json.dumps({k: round(v, 3) for k, v in allin.items()})}; "
                f"required WR at matrix mean for (0.5,0.5) = "
                f"{(0.5 + allin['matrix_mean']) / 1.0:.0%}, (1,1) = "
                f"{(1 + allin['matrix_mean']) / 2:.0%}, (1.5,0.75) = "
                f"{(0.75 + allin['matrix_mean']) / 2.25:.0%}\n")
        for k, v in gates.items():
            f.write(f"            H-S gate {k}: {'PASS' if v else 'FAIL'}\n")
        f.write(f"            winner {winner}: OOS PF {pf_w:.3f} (old {pf_old:.3f}"
                f" / new {pf_new:.3f}, p90 {pf_w90:.3f}, n={n_w}), permutation "
                f"best-of-12 p95 {perm_p95:.3f}\n")
        f.write(f"            H-S: {verdict}\n")
        f.write(f"            predictions were: Claude FAIL, Rashed PASS -> "
                f"{'Rashed' if hs_pass else 'Claude'} called it\n")
    print(f"\nresults -> {RESULTS / 'HS_run.json'}, exhibits -> HS_exhibits.md, "
          f"verdict appended to DECISIONS.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
