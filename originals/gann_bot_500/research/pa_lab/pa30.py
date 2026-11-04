"""PA-30-MAX5 (2026-10-23): user asked "backtest pa 30 timeframe max 5 dollars profit". Follow-up to PA-15/30, which
tested only TP $5 and $10. Same data, setups, entries, stops, costs, twin and pessimistic same-bar rule as pa1.py;
only the target changes. Pre-declared before any result was looked at.

M30 only. Targets $1, $2, $3, $4, $5 (the user's "max 5"). 4 setups x 5 targets = 20 tests.
PASS = n >= 150, net > 0 and PF >= 1.2 in BOTH halves (split 2024-09-01), beats >= 95% of 1000 coin-flip twins,
t >= 3.0. ($5 rows repeat PA-15/30 and must match it.)
Blind prediction (Claude): all 20 FAIL. Smaller targets raise the win rate (to ~80-90% at $1) but the losers are
$2-$15, so PF stays < 1.1 and the spread ($0.22+) eats the $1-$2 targets (net negative there).

    python pa30.py
"""
import numpy as np

from pa1 import SPLIT, load, run, stats, twin

TPS = (1.0, 2.0, 3.0, 4.0, 5.0)


def main():
    D = load()["M30"]
    print(f"{'test':14s} {'n':>5s} {'net$/lot':>10s} {'PF':>5s} {'win':>5s} {'t':>5s} | {'H1 net':>8s} {'PF':>5s} | "
          f"{'H2 net':>8s} {'PF':>5s} | {'avg loss':>8s} | twin% | verdict")
    for name in ("PIN", "ENG", "IB", "BO20"):
        for tp in TPS:
            tr = run(D, name, tp, 1800)
            p = np.array([x["p"] for x in tr]); h2 = np.array([x["t"] >= SPLIT for x in tr])
            s, s1, s2 = stats(p), stats(p[~h2]), stats(p[h2])
            beat = float(np.mean(twin(D, tr, tp, 1800) < p.sum()))
            ok = (s["n"] >= 150 and s1["net"] > 0 and s2["net"] > 0 and s1["pf"] >= 1.2 and s2["pf"] >= 1.2
                  and beat >= 0.95 and s["t"] >= 3.0)
            al = p[p < 0].mean() if (p < 0).any() else 0
            print(f"M30 {name:4s} TP${tp:<3.0f} {s['n']:5d} {s['net']:+10.0f} {s['pf']:5.2f} {s['win']:5.0%} {s['t']:+5.1f} | "
                  f"{s1['net']:+8.0f} {s1['pf']:5.2f} | {s2['net']:+8.0f} {s2['pf']:5.2f} | {al:+8.0f} | {beat:5.0%} | {'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
