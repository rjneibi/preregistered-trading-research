"""HPF verdict runner — Powell presser-fade OOS confirmation.

Frozen per HPF_PREREGISTRATION.md. Runs the pinned config family on the
LOCKED OOS sample (Powell-chair FOMC presser meetings 2023-01-01..2026-05-31)
and evaluates the numbered gates. Warsh-era events are measured and reported
descriptively only (transfer gate is explicitly not passable at n~1).

Usage: py -3.11 powell_verdict.py          # run OOS verdict (post-freeze only)
       py -3.11 powell_verdict.py test     # synthetic self-test pack
"""
import json
import random
import statistics
import sys
from datetime import date
from pathlib import Path

from powell_lab import (FOMC, SLIP_LEVELS, chair, has_presser, measure_event,
                        perf, trade_pnl)

HERE = Path(__file__).resolve().parent
OOS_START = date(2023, 1, 1)
POWELL_END = date(2026, 5, 31)

PRIMARY = ("fade", 0.0, "x1600")          # fade_t0_1600ET, pinned
FADE_FAMILY = [("fade", t, x) for t in (0.0, 3.0, 6.0) for x in ("x1530", "x1600")]

GATE_PF_REALISTIC = 1.20
GATE_MIN_EVENTS = 22
PERM_REPS = 1000
PERM_PCTL = 0.95
PERM_SEED = 20260708


def config_pnls(events, direction, thresh, exit_key, slip):
    sign = -1 if direction == "fade" else 1
    pnls = []
    for ev in events:
        if abs(ev["stmt_move"]) < thresh or ev["stmt_move"] == 0:
            continue
        d_ = sign * (1 if ev["stmt_move"] > 0 else -1)
        pnls.append(trade_pnl(ev, d_, exit_key, slip))
    return pnls


def permutation_test(events, exit_key, slip, actual_mean):
    """Random-direction baseline on the same events/timestamps/costs."""
    rng = random.Random(PERM_SEED)
    tradeable = [ev for ev in events if ev["stmt_move"] != 0]
    means = []
    for _ in range(PERM_REPS):
        pnls = [trade_pnl(ev, rng.choice((1, -1)), exit_key, slip)
                for ev in tradeable]
        means.append(statistics.mean(pnls))
    means.sort()
    p95 = means[int(PERM_PCTL * PERM_REPS) - 1]
    beaten = sum(1 for m in means if m < actual_mean) / PERM_REPS
    return {"p95_random_mean": round(p95, 3), "actual_mean": round(actual_mean, 3),
            "pct_of_random_beaten": round(beaten, 3), "pass": actual_mean > p95}


def run_verdict():
    oos_powell, warsh = [], []
    for s in FOMC:
        d = date.fromisoformat(s)
        if d < OOS_START or not has_presser(d):
            continue
        ev = measure_event(d)
        if ev is None:
            print(f"  no data: {s}")
            continue
        (warsh if chair(d) == "warsh" else oos_powell).append(ev)
    print(f"OOS Powell events: {len(oos_powell)}, Warsh events: {len(warsh)}")

    slip_real = SLIP_LEVELS["realistic"]
    slip_worst = SLIP_LEVELS["worst"]

    primary_real = config_pnls(oos_powell, *PRIMARY[:2], PRIMARY[2], slip_real)
    primary_worst = config_pnls(oos_powell, *PRIMARY[:2], PRIMARY[2], slip_worst)
    p_real = perf(primary_real)
    p_worst = perf(primary_worst)

    family = {}
    fam_pass = 0
    for direction, t, x in FADE_FAMILY:
        key = f"{direction}_t{int(t)}_{x}"
        pp = perf(config_pnls(oos_powell, direction, t, x, slip_real))
        family[key] = pp
        if pp.get("n", 0) and pp["pf"] >= 1.0:
            fam_pass += 1

    perm = permutation_test(oos_powell, PRIMARY[2], slip_real,
                            p_real["mean"]) if p_real["n"] else {"pass": False}

    gates = {
        "1_n_events_ge_22": len(oos_powell) >= GATE_MIN_EVENTS,
        "2_primary_pf_ge_1.20_realistic": p_real.get("pf", 0) >= GATE_PF_REALISTIC,
        "3_primary_total_gt_0_worst": p_worst.get("total", 0) > 0,
        "4_fade_family_ge_4of6_pf_ge_1.00": fam_pass >= 4,
        "5_permutation_beats_p95": perm["pass"],
    }
    verdict = "PASS" if all(gates.values()) else "FAIL"

    warsh_desc = [{**{k: ev[k] for k in ("date", "stmt_move", "presser_move")},
                   "fade_pnl_realistic": round(trade_pnl(
                       ev, -1 if ev["stmt_move"] > 0 else 1, "x1600", slip_real), 3)}
                  for ev in warsh if ev["stmt_move"] != 0]

    out = {"verdict": verdict, "gates": gates,
           "primary": {"config": "fade_t0_1600ET",
                       "realistic": p_real, "worst": p_worst},
           "fade_family_realistic": family, "permutation": perm,
           "fade_family_pf_ge_1_count": fam_pass,
           "warsh_descriptive_no_gate": warsh_desc,
           "n_oos_powell": len(oos_powell)}
    (HERE / "HPF_run.json").write_text(
        json.dumps(out, indent=1, default=lambda o: o.item()))

    print(f"\nprimary fade_t0_1600ET realistic: {p_real}")
    print(f"primary fade_t0_1600ET worst:     {p_worst}")
    print(f"fade family PF>=1.0: {fam_pass}/6")
    print(f"permutation: {perm}")
    print("\n== GATES ==")
    for g, ok in gates.items():
        print(f"  {g}: {'PASS' if ok else 'FAIL'}")
    print(f"\n== VERDICT: HPF {verdict} ==")
    if warsh_desc:
        print(f"\nWarsh descriptive (NO GATE): {warsh_desc}")
    print("\nwrote HPF_run.json")


# ---------------------------------------------------------------- self-tests
def _fake_ev(stmt_move, entry=2000.0, x1600=None, spread=0.30):
    x1600 = entry if x1600 is None else x1600
    h = spread / 2
    return {"date": "2099-01-01", "stmt_move": stmt_move,
            "entry_bid": entry - h, "entry_ask": entry + h,
            "x1530_bid": x1600 - h, "x1530_ask": x1600 + h,
            "x1600_bid": x1600 - h, "x1600_ask": x1600 + h,
            "presser_move": x1600 - entry}


def test():
    ok = 0
    # 1: fade of a +move is a short; price falls $5 -> pnl = 5 - spread - 2*slip
    ev = _fake_ev(+4.0, entry=2000, x1600=1995)
    got = trade_pnl(ev, -1, "x1600", 0.10)
    assert abs(got - (5 - 0.30 - 0.20)) < 1e-9, got; ok += 1
    # 2: fade of a -move is a long; price rises $5 -> same net
    ev = _fake_ev(-4.0, entry=2000, x1600=2005)
    got = trade_pnl(ev, +1, "x1600", 0.10)
    assert abs(got - (5 - 0.30 - 0.20)) < 1e-9, got; ok += 1
    # 3: flat price -> pnl = -(spread + 2*slip) exactly
    got = trade_pnl(_fake_ev(+4.0), +1, "x1600", 0.10)
    assert abs(got - (-0.50)) < 1e-9, got; ok += 1
    # 4: config_pnls fade direction: +move -> short
    evs = [_fake_ev(+4.0, entry=2000, x1600=1995)]
    (p,) = config_pnls(evs, "fade", 0.0, "x1600", 0.0)
    assert abs(p - (5 - 0.30)) < 1e-9, p; ok += 1
    # 5: momentum mirrors fade before costs
    (m,) = config_pnls(evs, "momentum", 0.0, "x1600", 0.0)
    assert abs((p + 0.30) + (m + 0.30)) < 1e-9, (p, m); ok += 1
    # 6: threshold excludes small moves
    assert config_pnls([_fake_ev(+2.0)], "fade", 3.0, "x1600", 0.0) == []; ok += 1
    # 7: zero stmt_move excluded
    assert config_pnls([_fake_ev(0.0)], "fade", 0.0, "x1600", 0.0) == []; ok += 1
    # 8: permutation calibration — pure-noise events: actual(=0 edge) must NOT beat p95
    rng = random.Random(1)
    noise = [_fake_ev(rng.choice((1, -1)) * 4.0, entry=2000,
                      x1600=2000 + rng.gauss(0, 5)) for _ in range(30)]
    pnls = config_pnls(noise, "fade", 0.0, "x1600", 0.10)
    perm = permutation_test(noise, "x1600", 0.10, statistics.mean(pnls))
    assert perm["pct_of_random_beaten"] < 0.99, perm; ok += 1
    # 9: permutation detects a planted one-sided edge (every fade wins $5)
    planted = [_fake_ev(+4.0 if i % 2 else -4.0, entry=2000,
                        x1600=1995 if i % 2 else 2005) for i in range(30)]
    pnls = config_pnls(planted, "fade", 0.0, "x1600", 0.10)
    perm = permutation_test(planted, "x1600", 0.10, statistics.mean(pnls))
    assert perm["pass"], perm; ok += 1
    # 10: perf PF math
    pp = perf([2.0, -1.0, 2.0, -1.0])
    assert pp["pf"] == 2.0 and pp["win_rate"] == 0.5, pp; ok += 1
    print(f"self-test: {ok}/10 pass")


if __name__ == "__main__":
    if "test" in sys.argv:
        test()
    else:
        run_verdict()
