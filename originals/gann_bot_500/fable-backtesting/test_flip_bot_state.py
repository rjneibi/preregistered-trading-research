"""Offline regression tests for the flip_bot v1.2 state fixes.

    py -3.11 test_flip_bot_state.py

No broker, no terminal: `MetaTrader5` is stubbed into sys.modules before
flip_bot is imported, and the clock is driven by hand. Each test states the
v1.1 behaviour it locks out, so a regression names its own bug.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---------------------------------------------------------------- MT5 stub
class Rc:
    # v1.5: the real MT5 result carries the price the broker FILLED at, which
    # is the only source of observed slippage. The old stub omitted it, so
    # `getattr(r, "price", 0)` returned 0 and every slippage assertion would
    # have passed vacuously against a None.
    def __init__(self, retcode, price=None):
        self.retcode = retcode
        self.price = price


class Pos:
    def __init__(self, ticket, ptype, price_open, volume, t):
        self.ticket, self.type, self.price_open = ticket, ptype, price_open
        self.volume, self.magic, self.time = volume, 20260703, t


class World:
    """Everything the stub answers from; tests mutate it directly."""
    def __init__(self):
        self.positions: list[Pos] = []
        self.bid = self.ask = 3300.0
        self.equity = 10_000.0
        self.orders: list[dict] = []
        self.close_retcode = 10009            # TRADE_RETCODE_DONE
        # v1.5: $/oz the broker moves the fill AGAINST us on every order.
        # A BUY order fills higher, a SELL order fills lower — that single
        # rule covers entries and closes in both directions.
        self.slippage = 0.0
        self.server_offset_h = 0
        self.now = datetime(2026, 8, 25, 20, 0, tzinfo=timezone.utc)  # Tuesday
        # v1.4: brokers can decline to price a contract; t13 exercises the path
        self.calc_profit_available = True
        # XAUUSD, 100oz/lot, USD account — the case the old hardcode assumed
        self.spec = {"filling_mode": 1, "point": 0.01, "volume_step": 0.01,
                     "volume_min": 0.01, "volume_max": 100.0,
                     "visible": True,          # v1.5 boot() Market Watch guard
                     "trade_contract_size": 100.0, "trade_tick_size": 0.01,
                     "trade_tick_value": 1.0, "trade_tick_value_loss": 1.0,
                     "currency_profit": "USD"}


W = World()


def _make_mt5(w: World):
    m = types.ModuleType("MetaTrader5")
    m.TIMEFRAME_H1 = 16385
    m.ORDER_FILLING_FOK, m.ORDER_FILLING_IOC = 0, 1
    m.ORDER_TYPE_BUY, m.ORDER_TYPE_SELL = 0, 1
    m.POSITION_TYPE_BUY, m.POSITION_TYPE_SELL = 0, 1
    m.TRADE_ACTION_DEAL = 1
    m.TRADE_RETCODE_DONE = 10009
    m.ACCOUNT_TRADE_MODE_DEMO = 0

    m.initialize = lambda **k: True
    m.last_error = lambda: (0, "ok")
    m.account_info = lambda: types.SimpleNamespace(
        login=123, equity=w.equity, trade_mode=0, currency="USD")
    m.symbol_info = lambda s: types.SimpleNamespace(**w.spec)
    m.symbol_info_tick = lambda s: types.SimpleNamespace(
        bid=w.bid, ask=w.ask,
        time=int(w.now.timestamp()) + w.server_offset_h * 3600)
    m.positions_get = lambda **k: list(w.positions)
    m.symbol_select = lambda s, on=True: bool(w.spec.get("visible"))

    def copy_rates_from_pos(sym, tf, start, n):
        # n closed H1 bars ending at the last completed hour, broker-stamped
        end = int(w.now.timestamp()) // 3600 * 3600
        out = []
        for i in range(n, 0, -1):
            t = end - i * 3600
            px = 3300.0 + (t // 3600 % 24) * 0.5
            out.append({"time": t + w.server_offset_h * 3600, "open": px,
                        "high": px + 3.0, "low": px - 3.0, "close": px})
        return out
    m.copy_rates_from_pos = copy_rates_from_pos

    def order_send(req):
        w.orders.append(dict(req))
        s = 1 if req["type"] == m.ORDER_TYPE_BUY else -1
        fill = req["price"] + s * w.slippage
        if "position" in req:                     # a close
            if w.close_retcode == 10009:
                for p in list(w.positions):
                    if p.ticket == req["position"]:
                        if req["volume"] >= p.volume - 1e-9:
                            w.positions.remove(p)
                        else:
                            p.volume = round(p.volume - req["volume"], 2)
            else:
                fill = None                       # a reject has no fill price
            return Rc(w.close_retcode, fill)
        w.positions.append(Pos(999, req["type"], fill,
                               req["volume"], int(w.now.timestamp())))
        return Rc(10009, fill)
    m.order_send = order_send

    def order_calc_profit(action, sym, vol, p_open, p_close):
        """The broker's P/L engine. Modelled from trade_contract_size, which is
        what the REAL broker demo feed server was measured to agree with — and
        which trade_tick_value on that server does NOT agree with (it is quoted
        per 0.1 lot there, i.e. 10x low)."""
        if not w.calc_profit_available:
            return None
        cs = w.spec.get("trade_contract_size", 0) or 0
        if not cs:
            return None
        d = (p_close - p_open) if action == m.ORDER_TYPE_BUY else (p_open - p_close)
        return cs * vol * d
    m.order_calc_profit = order_calc_profit
    return m


sys.modules["MetaTrader5"] = _make_mt5(W)
if "requests" not in sys.modules:                 # news_calendar imports it
    try:
        import requests                                          # noqa: F401
    except ImportError:
        _rq = types.ModuleType("requests")
        _rq.get = _rq.post = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("offline test: no network"))
        sys.modules["requests"] = _rq
sys.path.insert(0, str(HERE))
import flip_bot as fb                                            # noqa: E402


class FakeTime:
    """Replaces flip_bot's `time` module: advances W.now, bounds the loop."""
    def __init__(self, ticks):
        self.left = ticks

    def time(self):
        return W.now.timestamp()

    def sleep(self, _s):
        self.left -= 1
        if self.left <= 0:
            raise KeyboardInterrupt("bounded loop")
        W.now += timedelta(seconds=20)


def reset(tmp: Path, now: datetime):
    global W
    W = World()
    W.now = now
    sys.modules["MetaTrader5"].__dict__.update(_make_mt5(W).__dict__)
    fb.mt5 = sys.modules["MetaTrader5"]
    fb.STATE = tmp / "state.json"
    fb.JOURNAL = tmp / "journal.csv"
    fb.OFFSET_H = 0
    fb.FILL = 0
    fb.utcnow = lambda: W.now
    fb.notify = lambda *_a, **_k: None
    return W


def rows(kind=None):
    if not fb.JOURNAL.exists():
        return []
    with open(fb.JOURNAL, newline="") as f:
        rs = list(csv.DictReader(f))
    return [r for r in rs if kind is None or r["event"] == kind]


def open_state(direction="BUY", px=3300.0, atr=10.0, hivol=True, age_h=0.0):
    return {"dir": direction, "px": px, "atr": atr, "hivol": hivol,
            "t": (W.now - timedelta(hours=age_h)).isoformat(),
            "derisked": False, "mae": 0.0}


# ---------------------------------------------------------------- tests
def t1_open_survives_utc_midnight(tmp):
    """v1.1: main() REBOUND st at the day rollover, destroying st['open'].

    Asserting only `"open" in st` is BLIND: adopt() re-creates an entry for the
    orphaned position, so the wipe heals itself and the test passes anyway
    (caught by mutation check, 2026-08-24). What adoption CANNOT recover is
    accumulated manager state — the running MAE, and the derisked flag, whose
    loss lets a hivol position take the -1.2xATR half-out a second time. Assert
    on those, and on the absence of an ADOPT row.
    """
    reset(tmp, datetime(2026, 8, 25, 23, 59, 30, tzinfo=timezone.utc))
    W.positions.append(Pos(1, 0, 3300.0, 0.10, int(W.now.timestamp())))
    seeded = dict(open_state(), mae=7.5, derisked=True)
    fb.STATE.write_text(json.dumps(
        {"day": "2026-08-25", "signals": {"BUY": ["h1", "h4"]}, "done": ["BUY"],
         "day_start_eq": 10_000.0, "peak": 10_000.0, "open": seeded}))
    fb.time = FakeTime(ticks=4)                    # 80s: crosses midnight
    try:
        fb.main()
    except KeyboardInterrupt:
        pass
    st = json.loads(fb.STATE.read_text())
    assert st["day"] == "2026-08-26", st["day"]
    assert "open" in st, "REGRESSION: st['open'] destroyed at the day rollover"
    assert st["open"]["px"] == 3300.0
    assert not rows("ADOPT"), (
        "REGRESSION: the position was orphaned at midnight and only recovered "
        "by adopt() — state must survive the rollover in the first place")
    assert st["open"]["mae"] == 7.5, (
        f"REGRESSION: running MAE reset at the rollover ({st['open']['mae']}); "
        "adoption cannot recover it and the forward test is judged on winner-MAE")
    assert st["open"]["derisked"] is True, (
        "REGRESSION: derisked flag reset at the rollover — the hivol half-out "
        "can now fire a second time on the same position")
    assert st["done"] == [] and st["signals"] == {}, "day-scoped keys must reset"
    return "open, MAE and derisked all survive midnight; day keys still reset"


def t2_managed_exits_alive_after_midnight(tmp):
    """v1.1: manage() hit `if not o: return` after the wipe, so ts24h never
    fired for an overnight position. Position is 25h old across a rollover."""
    reset(tmp, datetime(2026, 8, 25, 23, 59, 30, tzinfo=timezone.utc))
    entry = W.now - timedelta(hours=25)
    W.positions.append(Pos(1, 0, 3300.0, 0.10, int(entry.timestamp())))
    fb.STATE.write_text(json.dumps(
        {"day": "2026-08-25", "signals": {}, "done": [],
         "day_start_eq": 10_000.0, "peak": 10_000.0,
         "open": dict(open_state(), t=entry.isoformat())}))
    fb.time = FakeTime(ticks=4)
    try:
        fb.main()
    except KeyboardInterrupt:
        pass
    assert not W.positions, "REGRESSION: ts24h never fired after the rollover"
    ex = rows("EXIT")
    assert len(ex) == 1, f"expected 1 EXIT row, got {len(ex)}: {ex}"
    assert ex[0]["note"] == "ts24h", ex[0]["note"]
    return "ts24h fires across midnight and journals once"


def t3_no_duplicate_exit_row(tmp):
    """v1.1: a managed close left st['open'] set, so the NEXT tick saw an empty
    position list with live state and journalled a second EXIT row as
    'server_tp_sl_or_manual' — double-counting every managed exit's MAE."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    entry = W.now - timedelta(hours=25)
    W.positions.append(Pos(1, 0, 3300.0, 0.10, int(entry.timestamp())))
    st = {"open": dict(open_state(), t=entry.isoformat())}
    fb.manage(st)                                  # closes via ts24h
    fb.manage(st)                                  # the tick that used to dupe
    fb.manage(st)
    ex = rows("EXIT")
    assert len(ex) == 1, f"REGRESSION: {len(ex)} EXIT rows, expected 1: {ex}"
    assert ex[0]["note"] == "ts24h"
    assert "open" not in st, "state must be dropped once the close confirms"
    return "one EXIT row per managed exit; no phantom server_tp_sl row"


def t4_failed_close_keeps_state(tmp):
    """A rejected close must NOT drop manager state — otherwise the position is
    orphaned live. One EXIT_FAIL row, not one per 20s tick, then a clean retry."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    entry = W.now - timedelta(hours=25)
    W.positions.append(Pos(1, 0, 3300.0, 0.10, int(entry.timestamp())))
    W.close_retcode = 10004                        # requote
    st = {"open": dict(open_state(), t=entry.isoformat())}
    for _ in range(5):
        fb.manage(st)
    assert W.positions, "stub should not have closed on a reject"
    assert "open" in st, "REGRESSION: state dropped on a close that never filled"
    assert len(rows("EXIT_FAIL")) == 1, rows("EXIT_FAIL")
    assert len(rows("EXIT")) == 0
    W.close_retcode = 10009                        # broker recovers
    fb.manage(st)
    assert not W.positions and "open" not in st
    assert len(rows("EXIT")) == 1, rows("EXIT")
    return "failed close retries, journals once, then exits cleanly"


def t5_orphan_position_is_adopted(tmp):
    """v1.1: a live position with no state fell through `if not o: return` and
    had NO manager for its entire life. Now adopted, with age de-offset."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    W.server_offset_h = 3
    fb.OFFSET_H = 3
    entry = W.now - timedelta(hours=25)
    W.positions.append(Pos(1, 0, 3300.0, 0.10,
                           int(entry.timestamp()) + 3 * 3600))   # broker-stamped
    fb.JOURNAL.write_text(
        "ts,event,dir,lot,px,sl,tp,atr,hivol,adx,news_w,mae,note\n"
        f"{entry.isoformat()},ENTRY,BUY,0.10,3300.0,3276.0,3308.0,10.0,True,30,1.0,0,10009\n")
    st = {}
    fb.manage(st)
    assert len(rows("ADOPT")) == 1, "orphan was not adopted"
    assert rows("ADOPT")[0]["atr"] == "10.0", "entry ATR must come from journal"
    assert not W.positions, "adopted position should have hit ts24h at 25h"
    assert len(rows("EXIT")) == 1 and rows("EXIT")[0]["note"] == "ts24h"
    return "orphan adopted with journal ATR and correct de-offset age"


def t6_no_stacking_across_midnight(tmp):
    """v1.1: the wipe cleared st['open'] AND st['done'], so `not st.get('open')`
    went true and the bot could stack a second position on a live one."""
    reset(tmp, datetime(2026, 8, 25, 23, 59, 30, tzinfo=timezone.utc))
    W.bid = W.ask = 9_999.0                        # far above any R3 -> BUY fires
    W.positions.append(Pos(1, 0, 3300.0, 0.10, int(W.now.timestamp())))
    fb.STATE.write_text(json.dumps(
        {"day": "2026-08-25", "signals": {}, "done": [],
         "day_start_eq": 10_000.0, "peak": 10_000.0, "open": open_state()}))
    W.now = datetime(2026, 8, 26, 12, 0, 10, tzinfo=timezone.utc)  # Wed session
    fb.time = FakeTime(ticks=6)
    try:
        fb.main()
    except KeyboardInterrupt:
        pass
    entries = [o for o in W.orders if "position" not in o]
    assert not entries, f"REGRESSION: stacked {len(entries)} entries on a live position"
    assert len(W.positions) == 1
    return "no second entry while a position is live"


def t7_sizing_matches_legacy_on_xauusd(tmp):
    """v1.3 must not silently re-size the live XAUUSD demo. On a 100oz USD
    contract the derived value/price-unit is exactly the old 100.0 hardcode."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    info = fb.mt5.symbol_info("XAUUSD")
    assert fb.value_per_price_unit(info) == 100.0
    lot, act = fb.lot_for(risk_usd=100.0, sl_dist=24.0)   # 1% of 10k, 2.4xATR@10
    assert lot == 0.04, f"expected 0.04, got {lot}"       # 100/(24*100)=0.04166
    assert abs(act - 96.0) < 1e-9, act
    return "XAUUSD 100oz: value/unit 100.0, lot 0.04, realised $96.00"


def t8_sizing_correct_for_other_contract_sizes(tmp):
    """THE HARDCODE BUG. /100.0 understates XAGUSD (5,000oz/lot) by 50x and
    overstates a 1oz mini-gold symbol by 100x. Derived sizing gets both right."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    legacy = lambda risk, sl: risk / sl / 100.0          # noqa: E731  (v1.2)

    W.spec.update({"trade_contract_size": 5000.0, "trade_tick_size": 0.001,
                   "trade_tick_value": 5.0, "trade_tick_value_loss": 5.0})
    assert fb.value_per_price_unit(fb.mt5.symbol_info("X")) == 5000.0
    lot, act = fb.lot_for(risk_usd=100.0, sl_dist=1.0)   # silver, $1 stop
    assert lot == 0.02, f"XAGUSD expected 0.02, got {lot}"
    assert abs(act - 100.0) < 1e-9, act
    assert abs(legacy(100.0, 1.0) / lot - 50.0) < 0.01, "should be a 50x error"

    W.spec.update({"trade_contract_size": 1.0, "trade_tick_size": 0.01,
                   "trade_tick_value": 0.01, "trade_tick_value_loss": 0.01})
    assert fb.value_per_price_unit(fb.mt5.symbol_info("X")) == 1.0
    lot, act = fb.lot_for(risk_usd=100.0, sl_dist=24.0)
    assert lot == 4.16, f"1oz mini expected 4.16, got {lot}"
    return "XAGUSD 5,000oz -> 0.02 (legacy was 50x too big); 1oz -> 4.16"


def t9_never_rounds_up_past_the_budget(tmp):
    """v1.2 rounded to the NEAREST step, so any remainder over half a step
    sized ABOVE the risk budget. v1.3 floors.

    The invariant of flooring is exact: realised risk is never above budget,
    and never more than ONE STEP of risk below it. Assert that, not an invented
    tolerance. Budgets below the volume_min floor are excluded — that is the
    broker's granularity, tested separately in t11.
    """
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    sl, vpu, step = 24.0, 100.0, 0.01
    step_risk = step * sl * vpu                       # $24 of risk per 0.01 lot
    worst, n = 0.0, 0
    for i in range(400):
        risk = step_risk * 1.05 + i * 0.37            # always above volume_min
        lot, act = fb.lot_for(risk, sl_dist=sl)
        assert act <= risk + 1e-9, f"OVER BUDGET: risk={risk} realised={act}"
        assert risk - act < step_risk + 1e-9, (
            f"undershoot {risk - act:.2f} exceeds one step of risk {step_risk}")
        worst, n = max(worst, (risk - act) / risk), n + 1
    return (f"{n} budgets: never over, never more than one step "
            f"(${step_risk:.0f}) under; worst {worst:.1%}")


def t12_step_granularity_effect_is_documented(tmp):
    """NOT a bug — a recorded consequence. At 2026 ATR on a $10k account the
    ideal lot falls between steps, so floor and round-to-nearest differ by a
    full 2x. Flooring under-risks; v1.2's rounding over-risked. Under a
    drawdown-first mandate under-risking is the correct failure direction, but
    the size of the effect must be on the record, not discovered live."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    eq, atr_2026 = 10_000.0, 21.09        # cycle-3 measured 2026 mean H1 ATR
    sl = 2.4 * atr_2026
    lot, act = fb.lot_for(eq * 0.01, sl)
    legacy = round((eq * 0.01) / sl / 100.0 / 0.01) * 0.01
    assert lot == 0.01 and legacy == 0.02, (lot, legacy)
    assert abs(act - 50.62) < 0.01, act
    return (f"2026 ATR {atr_2026}: floor 0.01 (${act:.0f} risk) vs v1.2 round "
            f"0.02 (${legacy * sl * 100:.0f}, 1.01x over a $100 budget)")


def t10_refuses_to_size_unpriceable_contract(tmp):
    """v1.2 fell back to /100.0 and produced a plausible XAUUSD lot even when
    the broker described nothing. v1.3 refuses and sends no order."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    W.spec.update({"trade_contract_size": 0, "trade_tick_size": 0,
                   "trade_tick_value": 0, "trade_tick_value_loss": 0})
    assert fb.value_per_price_unit(fb.mt5.symbol_info("X")) is None
    assert fb.lot_for(100.0, 24.0) == (None, None)
    st = {}
    fb.open_trade("BUY", {"atr": 10.0, "hivol": True, "adx": 30.0},
                  st, eq=10_000.0, peak=10_000.0)
    assert not W.orders, "REGRESSION: order sent with an unpriceable contract"
    assert "open" not in st
    assert len(rows("SIZE_FAIL")) == 1, rows()
    return "refuses to size, sends no order, journals SIZE_FAIL"


def t11_volume_min_overrisk_is_reported(tmp):
    """A budget below volume_min is silently sized UP to volume_min. Behaviour
    is unchanged (that is the broker's floor) but it must now be visible."""
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    lot, act = fb.lot_for(risk_usd=5.0, sl_dist=24.0)     # wants 0.002 lots
    assert lot == 0.01, lot
    assert abs(act - 24.0) < 1e-9, act                    # 4.8x the budget
    st = {}
    fb.open_trade("BUY", {"atr": 10.0, "hivol": False, "adx": 20.0},
                  st, eq=1_000.0, peak=1_000.0)           # -> $2.50 budget
    note = rows("ENTRY")[0]["note"]
    assert "risk_req=" in note and "risk_act=" in note, note
    mult = float(note.split("(")[1].split("x")[0])
    assert mult > 1.10, f"over-risk should be flagged, note={note}"
    return f"volume_min floor surfaced in the journal ({mult:.1f}x budget)"


def t13_real_broker_spec_beats_tick_value(tmp):
    """THE v1.3 BUG, pinned to the spec that produced it.

    MEASURED on broker demo feed 2026-08-24: this server quotes trade_tick_value
    per 0.1 lot, so v1.3's tick_value/tick_size derivation returned 10 for gold
    and 500 for silver against true values of 100 and 5,000. A value-per-unit
    that is 10x LOW sizes the position 10x LARGE — a "1% risk" became 9.1% of
    the account. order_calc_profit() is the arbiter and agreed with
    trade_contract_size at every volume tested.
    """
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))

    # --- the real gold spec, verbatim from the live server ---
    W.spec.update({"trade_contract_size": 100.0, "trade_tick_size": 0.01,
                   "trade_tick_value": 0.1, "trade_tick_value_loss": 0.1,
                   "currency_profit": "USD"})
    info = fb.mt5.symbol_info("XAUUSD")
    assert fb.value_per_price_unit(info) == 100.0, "must not trust tick_value"
    v13 = 0.1 / 0.01                                  # what v1.3 would have used
    assert v13 == 10.0
    lot, act = fb.lot_for(risk_usd=100.0, sl_dist=24.0)
    assert lot == 0.04, f"expected 0.04, got {lot}"
    assert abs(act - 96.0) < 1e-9, act
    bad_lot = round(math.floor(100.0 / (24.0 * v13) / 0.01 + 1e-9) * 0.01, 2)
    bad_risk = bad_lot * 24.0 * 100.0                 # priced at the TRUE value
    assert abs(bad_lot - 0.41) < 1e-9, bad_lot
    assert abs(bad_risk - 984.0) < 1e-6, bad_risk

    # --- the real silver spec ---
    W.spec.update({"trade_contract_size": 5000.0, "trade_tick_size": 0.001,
                   "trade_tick_value": 0.5, "trade_tick_value_loss": 0.5})
    assert fb.value_per_price_unit(fb.mt5.symbol_info("X")) == 5000.0

    # --- fallback: broker declines to price, but profit ccy == account ccy ---
    W.spec.update({"trade_contract_size": 100.0, "currency_profit": "USD"})
    W.calc_profit_available = False
    assert fb.value_per_price_unit(fb.mt5.symbol_info("X")) == 100.0

    # --- refuse: cannot price AND the contract settles in another currency ---
    W.spec.update({"currency_profit": "EUR"})
    assert fb.value_per_price_unit(fb.mt5.symbol_info("X")) is None
    assert fb.lot_for(100.0, 24.0) == (None, None)
    W.calc_profit_available = True
    return (f"tick_value route gave {v13} -> lot {bad_lot} = ${bad_risk:.0f} risk "
            f"(9.8x a $100 budget); v1.4 sizes 0.04 = $96")


def t14_door3_cap_and_the_dead_risk_ladder(tmp):
    """v1.5 (a)+(b), pinned together because on a $2,000 account they interact.

    The cap is DERIVED, not the SL_CAP_USD constant: 1% of notional equity
    bought at the broker's volume_min. On $2,000 / 0.01 lot / 100 $-per-oz
    that is exactly $20/oz, and at the live 2026 ATR of 22.08 the 2.4xATR
    stop ($52.99) is capped to it.

    The second assertion is the uncomfortable one and it belongs on the
    record: at $2,000 the three risk tiers (1.0%, the 0.5% below-peak
    de-risk, and the 0.25% adx+lovol tier) ALL floor to volume_min, so the
    bot cannot reduce risk below 1% under any condition. If a future change
    makes this test fail because the tiers diverge, that is good news and the
    test should be updated, not deleted.
    """
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    atr_live = 22.08                       # measured on the demo, 2026-08-25
    st = {}
    fb.open_trade("BUY", {"atr": atr_live, "hivol": True, "adx": 30.0},
                  st, eq=2_000.0, peak=2_000.0)
    e = rows("ENTRY")[0]
    assert float(e["lot"]) == 0.01, e["lot"]
    assert abs(float(e["px"]) - float(e["sl"]) - 20.0) < 1e-9, (
        f"stop must be the $20 cap, got {float(e['px']) - float(e['sl']):.2f}")
    assert abs(2.4 * atr_live - 52.99) < 0.01                # uncapped would be
    assert "capped=True" in e["note"] and "cap=20.00" in e["note"], e["note"]
    assert st["open"]["capped"] is True and st["open"]["cap"] == 20.0
    assert not rows("ATR_WARN"), "22.08 is below the 23.95 warn line"

    # the ladder: 1.0% / 0.5% / 0.25% budgets all buy the same minimum lot
    lots = {b: fb.lot_for(2_000.0 * b, 20.0)[0] for b in (0.01, 0.005, 0.0025)}
    assert set(lots.values()) == {0.01}, lots
    realised = fb.lot_for(2_000.0 * 0.0025, 20.0)[1]
    assert abs(realised - 20.0) < 1e-9, realised          # 4x the $5 budget

    # and the warning DOES fire once ATR crosses the line
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    fb.open_trade("BUY", {"atr": 24.0, "hivol": True, "adx": 30.0},
                  st, eq=2_000.0, peak=2_000.0)
    assert len(rows("ATR_WARN")) == 1, "ATR 24.0 >= 23.95 must journal a warning"
    return ("$20 cap derived from $2k/0.01 lot binds at ATR 22.08 (2.4xATR "
            "52.99); all three risk tiers collapse to 0.01 lot = 1.00%")


def t15_slippage_is_recorded_on_both_sides(tmp):
    """v1.5 (c). Slippage has been a MODELLED constant for this whole program
    and cycle 9 showed the backtest verdict sits inside its error bar. The
    forward test only answers that if the number is actually written down.

    Sign convention, asserted in both directions: positive = ADVERSE.
    """
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    W.slippage = 0.30
    st = {}
    fb.open_trade("BUY", {"atr": 10.0, "hivol": True, "adx": 30.0},
                  st, eq=2_000.0, peak=2_000.0)
    e = rows("ENTRY")[0]
    assert abs(float(e["slip"]) - 0.30) < 1e-9, (
        f"BUY filled 0.30 above intent = adverse +0.30, journalled {e['slip']}")
    assert abs(float(e["fill_px"]) - (float(e["px"]) + 0.30)) < 1e-9
    assert st["open"]["entry_slip"] == 0.3
    assert e["spread"] == "0.0", e["spread"]
    assert float(e["notional_eq"]) == 2000.0 and float(e["real_eq"]) == 10_000.0

    # a SELL fills BELOW intent; that is the same adverse sign
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    W.slippage = 0.30
    st = {}
    fb.open_trade("SELL", {"atr": 10.0, "hivol": True, "adx": 30.0},
                  st, eq=2_000.0, peak=2_000.0)
    e = rows("ENTRY")[-1]          # reset() reuses the journal path in this tmp
    assert abs(float(e["slip"]) - 0.30) < 1e-9, e["slip"]
    assert float(e["fill_px"]) < float(e["px"]), "a SELL must fill lower"

    # and on the exit: closing a long SELLS, so a low fill is adverse too
    reset(tmp, datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc))
    W.slippage = 0.25
    entry = W.now - timedelta(hours=25)
    W.positions.append(Pos(1, 0, 3300.0, 0.10, int(entry.timestamp())))
    st = {"open": dict(open_state(), t=entry.isoformat())}
    fb.manage(st)                                        # ts24h close
    x = rows("EXIT")[0]
    assert abs(float(x["slip"]) - 0.25) < 1e-9, (
        f"exit slip should be +0.25 adverse, got {x['slip']}")
    return "entry BUY/SELL and exit all journal adverse slippage as positive"


def main() -> int:
    tests = [t1_open_survives_utc_midnight, t2_managed_exits_alive_after_midnight,
             t3_no_duplicate_exit_row, t4_failed_close_keeps_state,
             t5_orphan_position_is_adopted, t6_no_stacking_across_midnight,
             t7_sizing_matches_legacy_on_xauusd,
             t8_sizing_correct_for_other_contract_sizes,
             t9_never_rounds_up_past_the_budget,
             t10_refuses_to_size_unpriceable_contract,
             t11_volume_min_overrisk_is_reported,
             t12_step_granularity_effect_is_documented,
             t13_real_broker_spec_beats_tick_value,
             t14_door3_cap_and_the_dead_risk_ladder,
             t15_slippage_is_recorded_on_both_sides]
    fails = 0
    with tempfile.TemporaryDirectory() as td:
        for i, t in enumerate(tests, 1):
            d = Path(td) / f"t{i}"
            d.mkdir()
            try:
                msg = t(d)
                print(f"  PASS  {t.__name__:<38} {msg}")
            except AssertionError as e:
                fails += 1
                print(f"  FAIL  {t.__name__:<38} {e}")
            except Exception as e:
                fails += 1
                print(f"  ERROR {t.__name__:<38} {type(e).__name__}: {e}")
    print(f"\n{len(tests) - fails}/{len(tests)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
