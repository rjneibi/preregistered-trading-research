# Data-Sourcing Execution Plan (from user's research doc, 2026-07-03)

## Stage 1 — Dukascopy ticks (FIRST; free, no registration)
- XAUUSD ticks from 2003-05-04, XAGUSD from 2003-05-05. Bid+ask per tick
  → spread = ask-bid. Fixes the two blind spots (no-spread, no sub-minute).
- Tool: `npx dukascopy-node -i xauusd -from 2015-06-01 -to 2026-06-19 -t tick -f csv`
  (or Python `pip install tick-vault`). ~10-15GB. Rate-limited: use backoff.
- .bi5 format if raw: LZMA, 20-byte rows (ms-in-hour, ask, bid, askvol,
  bidvol), XAUUSD price divisor 1000, struct ">3I2f".
- Validate: resample ticks→M1, compare closes vs HistData M1.

## Stage 2 — Empirical cost matrix (replaces flat 20pts)
- (hour × day-of-week) spread distribution from ticks + separate news-window
  regime (±5min around releases). Expect ~15-25pts normal, 60-200pts news.
- MT5 deal history: `mt5.history_deals_get()` → swap/commission per deal;
  slippage = order requested price vs deal price. MT5 does NOT log spread —
  deploy a SYMBOL_SPREAD-logging EA on demo going forward.
- GO/NO-GO: re-run v5.1 + portfolio with time-varying costs. If the edge
  only survives flat-20, it was a cost artifact — stop and redesign.

## Stage 3 — News timing ("first flip after release", raw PF 2.4 material)
- DON'T buy EODHD (events only from 2020; needs €59.99 tier).
- Hard-code fixed times: NFP/CPI/PPI/retail 08:30 ET, FOMC 14:00 ET
  (BLS/BEA/Fed schedules) + ForexFactory scrape for the rest.
- FXMacroData ($25/mo, second-level timestamps, no enterprise gating) is the
  paid option if needed. Trading Economics $149-299/mo — calendar gated to
  Enterprise; skip.
- Test sub-minute post-release entries under 3 fill regimes (optimistic /
  realistic / worst-case: far spread + p95 slippage + gap-through). Must
  beat base strategy under REALISTIC to adopt.

## Stage 4 — Silver (XAGUSD) robustness test
- Structurally motivated (shared drivers: real rates, DXY, safe-haven) but
  cointegration is time-varying/regime-dependent — pre-register that
  transfer may fail; that's non-fatal.
- Source: Dukascopy XAGUSD ticks (primary), HistData XAGUSD M1 (cross-check;
  bid-only, EST-no-DST timestamps — convert to UTC carefully; pivots are
  boundary-sensitive).
- Use silver-specific (wider) costs; judge regime-segmented results.

## Key traps recorded
- HistData M1 = bid-only, no spread, unreliable volume, EST-no-DST.
- Dukascopy = Swiss ECN aggregate ≠ our broker's book: use for spread
  DYNAMICS; broker-absolute levels from our own MT5 tick logs.
- MT5 python pkg is Windows-only, needs logged-in terminal.
- Stops can trigger on spread widening the bid chart never shows —
  replicate quote-side fills in the sim.
