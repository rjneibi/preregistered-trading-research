"""broker_fit.py — is this broker usable at my account size?

Point it at ANY broker's demo terminal and it answers one question in real
money: can this account express the risk ladder, or does the broker's minimum
volume force every trade above budget?

    python broker_fit.py --equity 2000
    python broker_fit.py --equity 2000 --terminal "<mt5-terminal-path>"

Read-only. It places nothing, modifies nothing, and refuses to run against a
live account.

WHY THIS EXISTS
---------------
Broker marketing talks about "micro lots", "cent accounts" and "nano lots".
None of those labels are the binding quantity. The binding quantity is

    minimum risk per trade = min_lot x stop_distance x value_per_price_unit

measured in the ACCOUNT currency. Two brokers can both advertise "0.01 minimum
lot" and differ 100x in that number, because the contract size behind the lot
differs. Measure it; do not read it off a webpage.
"""
from __future__ import annotations

import argparse
import sys

import MetaTrader5 as mt5

TIERS = (("full", 0.0100), ("derisked", 0.0050), ("adx+lovol", 0.0025))
ATR_MULT = 2.4                      # the spec's stop, in ATR units
TOL = 1.10                          # a tier is "inside budget" at <=1.10x


def wilder_atr(sym: str, n: int = 14, bars: int = 400):
    r = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 1, bars)
    if r is None or len(r) < n + 2:
        return None
    prev, tr = r[0]["close"], []
    for b in r[1:]:
        tr.append(max(b["high"] - b["low"], abs(b["high"] - prev),
                      abs(b["low"] - prev)))
        prev = b["close"]
    atr = sum(tr[:n]) / n
    for x in tr[n:]:
        atr = (atr * (n - 1) + x) / n
    return atr


def value_per_price_unit(sym: str, info):
    """Account-currency P/L for 1.00 lot per 1.0 of price. order_calc_profit is
    authoritative: some servers quote trade_tick_value per 0.1 lot, which makes
    the tick_value route silently 10x wrong."""
    t = mt5.symbol_info_tick(sym)
    px = getattr(t, "bid", 0) or 0
    if px > 0:
        p = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, sym, 1.0, px, px + 1.0)
        if p and p > 0:
            return float(p), px, "order_calc_profit"
    acc = mt5.account_info()
    cs = getattr(info, "trade_contract_size", 0) or 0
    if cs > 0 and acc and getattr(info, "currency_profit", None) == acc.currency:
        return float(cs), px, "trade_contract_size"
    return None, px, "UNRESOLVABLE"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--equity", type=float, default=None,
                    help="account size to test (default: the real equity)")
    ap.add_argument("--terminal", default=None, help="path to terminal64.exe")
    ap.add_argument("--symbols", default="XAUUSD,XAGUSD")
    a = ap.parse_args()

    ok = mt5.initialize(path=a.terminal) if a.terminal else mt5.initialize()
    if not ok:
        print(f"mt5.initialize() failed: {mt5.last_error()}")
        print("open the broker's terminal, log into the DEMO account, retry.")
        return 2

    acc = mt5.account_info()
    if acc is None:
        print("not logged in — log the terminal into the demo account first.")
        return 2
    MODE = {0: "DEMO", 1: "CONTEST", 2: "*** REAL / LIVE MONEY ***"}
    label = MODE.get(acc.trade_mode, "?")
    print(f"broker    {acc.company}")
    print(f"server    {acc.server}    account {label}")
    print(f"currency  {acc.currency}   equity {acc.equity:,.2f}   "
          f"leverage 1:{acc.leverage}")
    if acc.trade_mode == 2:
        print("\nREFUSING: this is a live account. Run it against a demo.")
        return 3

    eq = a.equity if a.equity else acc.equity
    print(f"\ntesting at equity {eq:,.2f} {acc.currency}   "
          f"stop = {ATR_MULT} x ATR(H1,14)\n")

    verdicts = {}
    for sym in [s.strip() for s in a.symbols.split(",") if s.strip()]:
        info = mt5.symbol_info(sym)
        if info is None:
            print(f"{sym:<10} NOT OFFERED by this broker")
            continue
        if not info.visible:
            mt5.symbol_select(sym, True)
            info = mt5.symbol_info(sym)
        vpu, px, src = value_per_price_unit(sym, info)
        atr = wilder_atr(sym)
        print("=" * 74)
        print(f"{sym}   {info.description}")
        if vpu is None or atr is None:
            print("  cannot price this contract — treat the broker as UNUSABLE")
            verdicts[sym] = False
            continue
        stop = ATR_MULT * atr
        minrisk = info.volume_min * stop * vpu
        print(f"  price {px}   contract_size {info.trade_contract_size}   "
              f"min/step/max {info.volume_min}/{info.volume_step}/{info.volume_max}")
        print(f"  value per 1.0 price move, 1.00 lot: {vpu:,.2f} {acc.currency}"
              f"   (via {src})")
        print(f"  ATR(H1,14) {atr:,.4f}   stop {stop:,.4f}")
        print(f"  MINIMUM RISK PER TRADE = {info.volume_min} x {stop:,.4f} x "
              f"{vpu:,.2f} = {minrisk:,.2f} {acc.currency} "
              f"({minrisk / eq * 100:.2f}% of {eq:,.0f})")
        allok = True
        print(f"\n  {'tier':<12}{'budget':>10}{'wants':>11}{'gets':>10}"
              f"{'realised':>11}{'vs budget':>12}")
        for lbl, pct in TIERS:
            budget = eq * pct
            want = budget / (stop * vpu)
            step, vmin = info.volume_step or 0.01, info.volume_min
            lot = max(vmin, (want // step) * step) if want >= vmin else vmin
            risk = lot * stop * vpu
            mult = risk / budget
            if mult > TOL:
                allok = False
            print(f"  {lbl:<12}{budget:>10.2f}{want:>11.5f}{lot:>10.4f}"
                  f"{risk:>11.2f}{mult:>11.2f}x"
                  + ("" if mult <= TOL else "  OVER"))
        verdicts[sym] = allok
        print(f"\n  -> {sym} at {eq:,.0f}: "
              + ("USABLE — every tier fits" if allok else
                 "NOT USABLE — the minimum volume forces trades above budget"))
        if not allok:
            need = minrisk / TIERS[-1][1]
            print(f"     either find a broker whose minimum risk is <= "
                  f"{eq * TIERS[-1][1]:,.2f}, or fund to {need:,.0f}")

    print("\n" + "=" * 74)
    if verdicts and all(verdicts.values()):
        print("VERDICT: this broker can express the risk ladder at this size.")
    else:
        print("VERDICT: this broker CANNOT express the risk ladder at this size.")
        print("The ladder collapsing means de-risking is a no-op, which defeats")
        print("the drawdown-first mandate. Do not run the bot here at this size.")
    print("\nATR moves. Re-run this when volatility changes; do not cache it.")
    mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
