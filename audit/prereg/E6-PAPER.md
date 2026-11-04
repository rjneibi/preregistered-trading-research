# E6 Paper vs backtest

Blind prediction (Claude): under 100 trades, so INSUFFICIENT SAMPLE. Match rate under 70%.

Source: `research/trades.db`, table `trades`, 19 rows for profiles D and R on XAUUSD, June and July 2026, MT5 demo. These are the user's own bots, not the analyst strategy, and are demo only. Balance and equity tables are not read. The `ict_*` tables are not read, because they hold backtest output.
No other journals exist: Binance Testnet, Alpaca paper and flip_bot demo have no trade files.

Backtest side: `dr_backtest` profiles D and R on the same dates, on Dukascopy M1, with entries after the first journal open and exits before the last.
Comparison, trade by trade: matched entries within 60 minutes and same side, entry price gap, exit price gap, exit reason, missed trades on each side, and P&L in R.
Labelled `INSUFFICIENT SAMPLE` if n < 100, with no gate. Ledger: 1 variant.
