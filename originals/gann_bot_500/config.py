"""
config.py — Central configuration for gann_bot (XAUUSD algorithmic trading bot).

Every tunable parameter for the bot lives in this module. No other file should
hardcode credentials, magic numbers, risk parameters, or level-calculation
constants. Import from here everywhere.

This bot is fully isolated: it uses a unique MAGIC number so its trades never
collide with any other Expert Advisor or bot running on the same account.

════════════════════════════════════════════════════════════════════════════
TWO SETTLED LOGICS
════════════════════════════════════════════════════════════════════════════
The fleet runs exactly two strategies. This file configures Logic 1 (Profile D);
Logic 2 (Profile R) is isolated in its own standalone config — see the note at
the bottom of PROFILES.

  Logic 1 — "Core + Polarity"  (Profile D, this file)
    Zone hit → H4 EMA50 bias → H4 Fib retracement → Polarity flip →
    H1 body-close confirm.   TP 3.0×ATR, SL 1.0×ATR, ADX off, polarity ON.

  Logic 2 — "Pure Core"        (Profile R, profiles/R/config_R.py)
    Zone hit → H4 EMA50 bias → H4 Fib retracement → H1 body-close confirm.
    TP 2.5×ATR, SL 1.5×ATR, ADX off, polarity OFF.

Profiles A and B (which ran the ADX filter ON) are RETIRED — backtesting proved
the ADX gate net-negative. Their historical state/log files are kept for
reference, but the profiles are no longer defined here.
"""

import os

# ── Identity ──────────────────────────────────────────────
SYMBOL   = "XAUUSD"

# ── Telegram notifications ────────────────────────────────
# Shared across all profiles. Leave blank to disable (notifier.send() will
# simply log a warning on each failed post and never raise).
TELEGRAM_TOKEN   = ""
TELEGRAM_CHAT_ID = ""

# ── Multi-account profiles ────────────────────────────────
# Each account needs its OWN MetaTrader 5 terminal installation (a separate
# folder) and its OWN bot process, selected via --profile or GANNBOT_PROFILE.
# One terminal can only be logged into one account, and the MetaTrader5 Python
# package drives one terminal per process — so TERMINAL_PATH MUST point at a
# DIFFERENT terminal64.exe for each profile.
#
# Only Profile D lives here. Profile R is fully isolated in its own standalone
# profiles/R/config_R.py (its own account/terminal/runtime files); bot.py loads
# that file directly for `--profile R`, so R never appears in this dict.
PROFILES = {
    # Profile D — LOGIC 1 "Core + Polarity" — WALK-FORWARD VALIDATED
    #   Validated 2026-06-04: PF 1.20, +0.146 R/trade, 162 OOS trades 2025–2026.
    #   The ATR_TP_MULT / ATR_SL_MULT / ADX_THRESHOLD / POLARITY_FLIP keys below
    #   OVERRIDE the module defaults for this profile only.
    #     TP fixed 900 pts ($9.00) · SL 1.0×ATR · ADX filter OFF · polarity flip ON.
    "D": {
        "MAGIC":         20260604,
        "LOGIN":         0,
        "PASSWORD":      "",
        "SERVER":        "",
        "TERMINAL_PATH": "",
        "ACCOUNT_LABEL": "",
        # TP is now a FIXED 900-point distance (900 × POINT 0.01 = $9.00),
        # replacing the former 3.0×ATR TP. ATR_TP_MULT is kept for reference /
        # dashboards but is IGNORED while TP_FIXED_POINTS > 0 (see
        # risk.calculate_sl_tp). SL + partial close stay ATR-based, unchanged.
        "TP_FIXED_POINTS": 900,   # fixed take-profit = 900 pts × 0.01 = $9.00
        "ATR_TP_MULT":   3.0,     # (legacy ref only — ignored while TP_FIXED_POINTS>0)
        "ATR_SL_MULT":   1.0,     # validated stop-loss   = 1.0 × ATR
        "ADX_THRESHOLD": 0,       # ADX trend filter OFF (0 = disabled)
        "POLARITY_FLIP": True,    # "Core + Polarity": zone polarity flip ON
    },
}

# Profile DI — "D-Inverse": Profile D's exact logic and SAME account/terminal, with
# every signal traded in the OPPOSITE direction (bot.py, INVERT_SIGNAL). Its own
# MAGIC keeps its positions, cap, zone ledger and daily-loss P&L separate from D's.
# Requires a HEDGING account (bot.py refuses to start otherwise).
PROFILES["DI"] = {**PROFILES["D"],
                  "MAGIC":         20260611,
                  "ACCOUNT_LABEL": "",
                  "INVERT_SIGNAL": True}

# Which profile this process runs. Set via --profile or GANNBOT_PROFILE; defaults
# to "D" (Logic 1) so a plain `python bot.py` runs the validated profile.
# Portable mode keeps each terminal copy's data inside its own install folder,
# guaranteeing profiles never share state. Required for multi-account.
PORTABLE = True

PROFILE = os.environ.get("GANNBOT_PROFILE", "D").upper()
if PROFILE not in PROFILES:
    raise ValueError(
        f"GANNBOT_PROFILE={PROFILE!r} is not defined in config.PROFILES "
        f"(valid: {', '.join(PROFILES)}). Profile R uses profiles/R/config_R.py "
        f"and is selected with `python bot.py --profile R`."
    )

_active        = PROFILES[PROFILE]
MAGIC          = _active["MAGIC"]          # isolates this bot's trades on its account
LOGIN          = 0
PASSWORD       = ""
SERVER         = ""
TERMINAL_PATH  = ""
ACCOUNT_LABEL  = ""

# ── Risk ──────────────────────────────────────────────────
RISK_PCT            = 0.5    # % of balance risked per trade
MAX_OPEN_TRADES     = 1      # hard cap on concurrent open positions (single source of truth)
# Profile D keeps the original one-trade-per-zone-per-day rule (no re-entry).
MAX_ZONE_TRADES_PER_DAY      = 1     # D: 1 trade per zone per UTC day
ZONE_REENTRY_REQUIRES_PROFIT = True  # (no effect at limit 1; documented for parity)
# Profile D: Fixed 900-point TP (900 × POINT = $9.00), set via PROFILES["D"]
# TP_FIXED_POINTS and resolved below. Replaces the former 3.0×ATR TP.
MAX_SPREAD_POINTS   = 40     # skip trading if spread (in points) exceeds this
DAILY_LOSS_LIMIT    = 0.03   # 3% hard daily stop (fraction of start balance)
TICK_SLEEP_MS       = 500    # main loop pause between ticks (milliseconds)
TRADE_COOLDOWN_S    = 60     # seconds to wait before another trade in same direction

# ── Level calculation ─────────────────────────────────────
PIVOT_TYPE          = "fibonacci"   # "fibonacci" or "classic"
GANN_DEGREES        = [45, 90, 135, 180, 225, 270, 315, 360]
FIB_LEVELS          = [0.382, 0.500, 0.618, 0.786]
SWING_LOOKBACK_H4   = 50     # bars to look back for H4 swing detection
ATR_ZONE_WIDTH_MULT = 0.3    # zone = level ± 0.3 × ATR(H1)

# ── Confirmation ──────────────────────────────────────────
CONFIRM_TF          = "H1"   # candlestick close confirmation timeframe
BIAS_TF             = "H4"   # trend bias timeframe

# ── Trend strength filter (ADX) ───────────────────────────
# Module default 0 = filter OFF. Both settled logics keep it off (the ADX gate
# was found net-negative). A profile may re-enable it via an ADX_THRESHOLD
# override > 0; bot.py treats use_adx = (ADX_THRESHOLD > 0).
ADX_THRESHOLD       = 0

# ── Zone polarity flip ────────────────────────────────────
# When True (Logic 1), a support broken to the downside on H4 is re-evaluated as
# resistance (and vice-versa) before deciding direction. bot.py passes this to
# signals.evaluate_signal(use_polarity=...). Module default True; Profile D sets
# it True explicitly, Profile R (config_R) sets it False.
POLARITY_FLIP       = True

# ── Trail / SL / TP ───────────────────────────────────────
# Break-even trigger and trailing distance are max(1.0 × ATR, FLOOR) — see
# risk.check_breakeven / check_trailing. The floor is configurable below
# (ATR_BE_FLOOR / ATR_TRAIL_FLOOR). The former ATR_BE_MULT / ATR_TRAIL_MULT knobs
# were dead (nothing read them) and were removed.
ATR_SL_MULT         = 1.5    # stop loss distance  = 1.5 × ATR (default; D overrides → 1.0)
ATR_TP_MULT         = 2.5    # take profit distance = 2.5 × ATR (default; D overrides → 3.0)

# ── Break-even / trailing floors (PRICE UNITS, not points) ─
# Break-even trigger and trailing distance are both max(1.0 × ATR, FLOOR). The
# floor is in PRICE UNITS — for XAUUSD $1 = 100 points, so 15.0 = a $15 move.
#
# WARNING: a 1.0×ATR trailing stop (ATR ≈ $16 on gold) is TIGHT relative to the
# 3.0×ATR take-profit. After the 1.0×ATR partial close moves the stop to entry,
# only a ~1×ATR pullback is tolerated before a break-even / trailed stop-out, so
# a winner can give back its open profit before reaching TP. Retained for the
# demo phase observation; consider widening (e.g. 1.5–2.0×ATR trail, or a larger
# floor) for production after a fresh XAUUSD walk-forward. Do not change live
# without re-validating PF / win-rate.
ATR_BE_FLOOR        = 15.0   # break-even trigger floor, price units ($15 = 1500 pts)
ATR_TRAIL_FLOOR     = 15.0   # trailing distance floor, price units ($15 = 1500 pts)

# ── Partial close (both profiles) ─────────────────────────
# At PARTIAL_CLOSE_ATR_MULT × ATR of unrealised profit, close 50% of the position
# and move the remaining stop to entry (locking the trade risk-free). Fires at
# most once per ticket. Set PARTIAL_CLOSE_ENABLED = False to opt this profile out.
PARTIAL_CLOSE_ENABLED  = True   # enable the 50% partial close
PARTIAL_CLOSE_ATR_MULT = 1.0    # ATR multiplier for the partial-close trigger

# ── Option C — M1 pullback entry timing ───────────────────
# After H1 confirmation, instead of entering immediately at the next tick (which
# chases the end of the H1 move), wait on M1 for price to pull back toward the
# zone and body-close in the trade direction inside the pullback zone before
# committing. Hard timeout of OPTION_C_BARS M1 bars; abandon if price runs more
# than OPTION_C_RUNAWAY_MULT × ATR beyond the zone first.
OPTION_C_ENABLED      = True    # enable M1 pullback entry timing
OPTION_C_BARS         = 15      # M1 bars to wait for the pullback
OPTION_C_RUNAWAY_MULT = 1.5     # ATR mult beyond zone = runaway, skip

# ── Fix C — M5 RSI overextension filter ───────────────────
# Final gate (after all strategy gates, before pending/immediate entry): if M5
# RSI(14) is already overextended in the trade direction at H1 confirmation,
# momentum is exhausted — skip. Fail-open on a data error (never kill a valid
# signal on an MT5 hiccup).
RSI_FILTER_ENABLED    = False   # M5 RSI overextension gate DISABLED (per ops decision)
RSI_FILTER_PERIOD     = 14      # RSI period
RSI_FILTER_OB         = 70      # overbought — blocks BUY when M5 RSI > this
RSI_FILTER_OS         = 30      # oversold — blocks SELL when M5 RSI < this

# ── Per-profile overrides ─────────────────────────────────
# A profile may override these by adding the matching key to its PROFILES entry
# (Profile D overrides all four). Profiles without a key keep the module default.
ATR_TP_MULT   = _active.get("ATR_TP_MULT", ATR_TP_MULT)
ATR_SL_MULT   = _active.get("ATR_SL_MULT", ATR_SL_MULT)
ADX_THRESHOLD = _active.get("ADX_THRESHOLD", ADX_THRESHOLD)
POLARITY_FLIP = _active.get("POLARITY_FLIP", POLARITY_FLIP)
INVERT_SIGNAL = _active.get("INVERT_SIGNAL", False)   # Profile DI: trade opposite direction

# Profile D: Fixed 900-point TP (replaces 3.0×ATR). When TP_FIXED_POINTS > 0,
# risk.calculate_sl_tp uses a fixed TP of TP_FIXED_POINTS × POINT price units
# instead of ATR_TP_MULT × ATR; SL stays ATR-based. POINT = XAUUSD point size.
TP_FIXED_POINTS = _active.get("TP_FIXED_POINTS", 0)
POINT           = 0.01   # XAUUSD point size (price per point; $1 move = 100 points)

# ── Files (runtime artifacts, created on first run) ───────
# Suffixed per profile so simultaneous instances never clobber each other's
# log, daily-state gate, or daily summary CSV. Anchored (absolute) to this file's
# directory and split into logs/ (text logs) and runtime/ (live state JSON + CSV)
# so the project ROOT stays free of runtime clutter, regardless of launch CWD.
_ROOT_DIR    = os.path.dirname(os.path.abspath(__file__))
_LOGS_DIR    = os.path.join(_ROOT_DIR, "logs")
_RUNTIME_DIR = os.path.join(_ROOT_DIR, "runtime")
os.makedirs(_LOGS_DIR, exist_ok=True)
os.makedirs(_RUNTIME_DIR, exist_ok=True)

LOG_FILE            = os.path.join(_LOGS_DIR, f"gannbot_{PROFILE}.log")
DAILY_STATE_FILE    = os.path.join(_RUNTIME_DIR, f"daily_state_{PROFILE}.json")
DAILY_LOG_CSV       = os.path.join(_RUNTIME_DIR, f"daily_log_{PROFILE}.csv")
STATE_FILE          = os.path.join(_RUNTIME_DIR, f"bot_state_{PROFILE}.json")  # live snapshot for dashboard

# ── Broker connection behavior ────────────────────────────
CONNECT_RETRIES     = 3      # MT5 connect attempts before giving up
CONNECT_RETRY_DELAY = 5      # seconds between connect attempts
RECONNECT_SLEEP     = 60     # seconds to sleep after exhausting reconnects

# ── Confluence ────────────────────────────────────────────
CONFLUENCE_ATR_MULT = 0.5    # zones within 0.5 × ATR of entry count as confluence

# ── Profile L — LIVE London ICT M1 scalper (DEMO-ONLY) ────────────────────────
# Standalone runtime in ict_london_bot.py; reads these L_* names if present.
# DEMO credentials only — master/trader password (NOT the read-only investor pwd).
# MAGIC 20260609 is hardcoded in the bot; L_MAGIC here is informational only.
L_LOGIN          = 0
L_PASSWORD       = ""
L_SERVER         = ""
L_TERMINAL_PATH  = ""
L_MAGIC          = 20260609                      # LIVE Profile-L identity (informational)
L_FIXED_LOT      = 1.00                          # fixed lot size (DEMO only; 1-lot analysis)
