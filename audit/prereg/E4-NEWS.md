# E4 News-window execution

Blind prediction (Claude): spreads at the release run 3x to 6x normal. PFs fall by under 0.03, because few trades touch a window. Blackout changes PF by under 0.05. Nothing passes.

Data: Dukascopy XAUUSD ticks on disk, 2015-01 to 2026-06, read only.
Events: NFP and CPI 08:30 New York, FOMC 14:00 New York, from `fable-backtesting/build_calendar.py` as copied into the sandbox. Only dates in that file count.
Windows, minutes around the release: -30..-5, -5..0, 0..1, 1..5, 5..30, 30..60.
Measure: median and p90 of tick spread per event type and window, and the ratio to the same hour on non-event days of that year.

Strategy rerun, true-UTC trades from Phase C: H1, FINAL_v3, FINAL_v4.
- Event-aware: a trade entry or exit inside a window pays that window's measured p90 spread for its event type and year, instead of the matrix value. Trades outside windows keep the matrix cost.
- Blackout variant: drop trades whose entry falls in -30..+30 of an event. The trade list is filtered, not regenerated, so a dropped trade does not free a later signal. That is a known approximation.
Trades after 2026-06 use the 2026 values.

Gates: as H1's frozen gate, PF >= 1.20 at these costs. This is a cost revision of failed rules, so a figure above 1.20 would still go to a fresh test and not be a pass.
Ledger: 6 variants.
