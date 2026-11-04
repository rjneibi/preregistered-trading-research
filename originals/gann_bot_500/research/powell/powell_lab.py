"""Powell-strategy lab: FOMC statement-move fade during the press conference.

Mechanism under test (literature: IJCB v22n1 "The Market Impact of Fed
Communications: The Role of the Press Conference"; CEPR VoxEU column):
under Chair Powell, the initial market reaction to the 14:00 ET FOMC
statement is partially REVERSED during the 14:30 ET press conference.
Documented on Treasuries/equities; tested here on XAUUSD.

Data: Dukascopy decoded tick streams, fable-backtesting/download/xauusd-bi5-YYYY-MM.csv
      (timestamp ms UTC, askPrice, bidPrice). Costs are REAL bid/ask at the
      actual event timestamps (buy at ask, sell at bid) + slippage stress.

Eras: Yellen presser meetings 2015-2017 (quarterly, n=12) = control.
      Powell presser meetings 2018-03..2026-04.
      Warsh 2026-06-17 (n=1, reported only).

Splits: IS = events < 2023-01-01. OOS = 2023+ (LOCKED: requires --oos flag,
        to be run only after prereg freeze per protocol).

Exclusions (pinned): unscheduled/emergency meetings 2019-10-04, 2020-03-03,
        2020-03-15 (irregular statement/presser times).

Config family (pinned, 12 = 2 directions x 3 thresholds x 2 exits):
  direction: fade | momentum (of the 14:00->14:30 statement move)
  threshold on |statement move|: $0 | $3 | $6 per oz
  exit: 15:30 ET | 16:00 ET
Primary config (literature version): fade / $0 / 15:30.

Usage: py -3.11 powell_lab.py            # IS only
       py -3.11 powell_lab.py --oos      # post-freeze confirmation
"""
import csv
import json
import statistics
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
DOWNLOAD = HERE.parent.parent / "fable-backtesting" / "download"
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")

FOMC = """2015-01-28 2015-03-18 2015-04-29 2015-06-17 2015-07-29 2015-09-17
2015-10-28 2015-12-16 2016-01-27 2016-03-16 2016-04-27 2016-06-15 2016-07-27
2016-09-21 2016-11-02 2016-12-14 2017-02-01 2017-03-15 2017-05-03 2017-06-14
2017-07-26 2017-09-20 2017-11-01 2017-12-13 2018-01-31 2018-03-21 2018-05-02
2018-06-13 2018-08-01 2018-09-26 2018-11-08 2018-12-19 2019-01-30 2019-03-20
2019-05-01 2019-06-19 2019-07-31 2019-09-18 2019-10-30 2019-12-11
2020-01-29 2020-04-29 2020-06-10 2020-07-29 2020-09-16
2020-11-05 2020-12-16 2021-01-27 2021-03-17 2021-04-28 2021-06-16 2021-07-28
2021-09-22 2021-11-03 2021-12-15 2022-01-26 2022-03-16 2022-05-04 2022-06-15
2022-07-27 2022-09-21 2022-11-02 2022-12-14 2023-02-01 2023-03-22 2023-05-03
2023-06-14 2023-07-26 2023-09-20 2023-11-01 2023-12-13 2024-01-31 2024-03-20
2024-05-01 2024-06-12 2024-07-31 2024-09-18 2024-11-07 2024-12-18 2025-01-29
2025-03-19 2025-05-07 2025-06-18 2025-07-30 2025-09-17 2025-10-29 2025-12-10
2026-01-28 2026-03-18 2026-04-29 2026-06-17""".split()
# note: 2019-10-04, 2020-03-03, 2020-03-15 removed (unscheduled; pinned above)

PRESSER_MONTHS_PRE2019 = {3, 6, 9, 12}  # SEP-meeting quarterly pressers
IS_CUTOFF = date(2023, 1, 1)
SLIP_LEVELS = {"optimistic": 0.0, "realistic": 0.10, "worst": 0.30}  # $/oz per side


def chair(d: date) -> str:
    if d <= date(2018, 1, 31):
        return "yellen"
    if d <= date(2026, 5, 31):
        return "powell"
    return "warsh"


def has_presser(d: date) -> bool:
    return d.year >= 2019 or d.month in PRESSER_MONTHS_PRE2019


def et_utc(d: date, hh: int, mm: int) -> datetime:
    return datetime.combine(d, time(hh, mm), tzinfo=ET).astimezone(UTC)


def load_event_ticks(d: date) -> pd.DataFrame | None:
    """Ticks for 13:30-16:10 ET on the event day, cached per event."""
    cached = CACHE / f"event_{d.isoformat()}.csv"
    if cached.exists():
        df = pd.read_csv(cached)
        if df.empty:
            return None
        df["ts"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df
    src = DOWNLOAD / f"xauusd-bi5-{d.year}-{d.month:02d}.csv"
    if not src.exists():
        print(f"  MISSING month file {src.name}")
        cached.write_text("timestamp,askPrice,bidPrice\n")
        return None
    lo = et_utc(d, 13, 30).timestamp() * 1000
    hi = et_utc(d, 16, 10).timestamp() * 1000
    parts = []
    for chunk in pd.read_csv(src, chunksize=1_000_000):
        w = chunk[(chunk.timestamp >= lo) & (chunk.timestamp <= hi)]
        if len(w):
            parts.append(w)
    df = pd.concat(parts) if parts else pd.DataFrame(
        columns=["timestamp", "askPrice", "bidPrice"])
    df.to_csv(cached, index=False)
    if df.empty:
        return None
    df["ts"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def last_at(df: pd.DataFrame, cutoff: datetime) -> pd.Series | None:
    w = df[df.ts <= cutoff]
    return w.iloc[-1] if len(w) else None


def first_at(df: pd.DataFrame, start: datetime) -> pd.Series | None:
    w = df[df.ts >= start]
    return w.iloc[0] if len(w) else None


def mid(row) -> float:
    return (row.askPrice + row.bidPrice) / 2


def measure_event(d: date) -> dict | None:
    df = load_event_ticks(d)
    if df is None or len(df) < 100:
        return None
    base = last_at(df, et_utc(d, 13, 59) - timedelta(seconds=5))
    pre30 = last_at(df, et_utc(d, 14, 30) - timedelta(seconds=1))  # 14:29:59
    entry = first_at(df, et_utc(d, 14, 30))
    x1530 = last_at(df, et_utc(d, 15, 30))
    x1600 = last_at(df, et_utc(d, 16, 0))
    if any(v is None for v in (base, pre30, entry, x1530, x1600)):
        return None
    # entry must be within 2 min of 14:30, exits within 5 min of target
    if entry.ts > et_utc(d, 14, 32):
        return None
    stmt_move = mid(pre30) - mid(base)
    return {
        "date": d.isoformat(), "chair": chair(d), "presser": has_presser(d),
        "is_sample": d < IS_CUTOFF,
        "base_mid": round(mid(base), 3), "stmt_move": round(stmt_move, 3),
        "entry_bid": entry.bidPrice, "entry_ask": entry.askPrice,
        "x1530_bid": x1530.bidPrice, "x1530_ask": x1530.askPrice,
        "x1600_bid": x1600.bidPrice, "x1600_ask": x1600.askPrice,
        "presser_move": round(mid(x1530) - mid(entry), 3),
    }


def trade_pnl(ev: dict, direction: int, exit_key: str, slip: float) -> float:
    """$/oz: buy at ask+slip, sell at bid-slip."""
    if direction > 0:
        return (ev[f"{exit_key}_bid"] - slip) - (ev["entry_ask"] + slip)
    return (ev["entry_bid"] - slip) - (ev[f"{exit_key}_ask"] + slip)


def perf(pnls: list[float]) -> dict:
    if not pnls:
        return {"n": 0}
    wins = sum(p for p in pnls if p > 0)
    losses = -sum(p for p in pnls if p < 0)
    return {
        "n": len(pnls),
        "total": round(sum(pnls), 2),
        "mean": round(statistics.mean(pnls), 3),
        "median": round(statistics.median(pnls), 3),
        "pf": round(wins / losses, 3) if losses > 0 else float("inf"),
        "win_rate": round(sum(1 for p in pnls if p > 0) / len(pnls), 3),
    }


def run(include_oos: bool) -> None:
    events = []
    for s in FOMC:
        d = date.fromisoformat(s)
        if not has_presser(d):
            continue
        if not include_oos and d >= IS_CUTOFF:
            continue
        ev = measure_event(d)
        if ev:
            events.append(ev)
        else:
            print(f"  no data: {s}")
    print(f"\nevents measured: {len(events)}")

    out = {"events": events, "configs": {}}
    rows = []
    for dir_name, sign in [("fade", -1), ("momentum", 1)]:
        for thresh in [0.0, 3.0, 6.0]:
            for exit_key, exit_name in [("x1530", "1530ET"), ("x1600", "1600ET")]:
                key = f"{dir_name}_t{int(thresh)}_{exit_name}"
                out["configs"][key] = {}
                for slip_name, slip in SLIP_LEVELS.items():
                    for era in ["yellen", "powell", "all"]:
                        pnls = []
                        for ev in events:
                            if era != "all" and ev["chair"] != era:
                                continue
                            if ev["chair"] == "warsh":
                                continue
                            if abs(ev["stmt_move"]) < thresh or ev["stmt_move"] == 0:
                                continue
                            d_ = sign * (1 if ev["stmt_move"] > 0 else -1)
                            pnls.append(trade_pnl(ev, d_, exit_key, slip))
                        out["configs"][key][f"{slip_name}_{era}"] = perf(pnls)
                p = out["configs"][key]["realistic_powell"]
                rows.append((key, p))

    # reversal diagnostic: corr(stmt_move, presser_move) by era
    for era in ["yellen", "powell"]:
        xs = [e["stmt_move"] for e in events if e["chair"] == era]
        ys = [e["presser_move"] for e in events if e["chair"] == era]
        if len(xs) >= 5:
            c = statistics.correlation(xs, ys)
            out[f"corr_stmt_presser_{era}"] = round(c, 3)
            print(f"corr(stmt_move, presser_move) {era}: {c:+.3f} (n={len(xs)})")

    print(f"\n{'config':26s} {'n':>3s} {'total$':>8s} {'mean':>7s} {'PF':>6s} {'WR':>5s}   (realistic slip, Powell era)")
    for key, p in rows:
        if p["n"]:
            print(f"{key:26s} {p['n']:3d} {p['total']:8.2f} {p['mean']:7.3f} {p['pf']:6.3f} {p['win_rate']:5.1%}")

    tag = "oos" if include_oos else "is"
    (HERE / f"powell_lab_{tag}.json").write_text(json.dumps(out, indent=1))
    with open(HERE / f"powell_events_{tag}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(events[0].keys()))
        w.writeheader()
        w.writerows(events)
    print(f"\nwrote powell_lab_{tag}.json / powell_events_{tag}.csv")


if __name__ == "__main__":
    run(include_oos="--oos" in sys.argv)
