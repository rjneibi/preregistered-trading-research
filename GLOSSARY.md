# Glossary

| Term | Meaning |
|---|---|
| ASSUMED-CLOCK | Gold data from 2010 to 2012, where the clock rule could not be measured and is assumed |
| ATR | Average true range. A measure of recent price movement |
| Bid, ask, spread | Best selling price, best buying price, and the gap between them. Crossing the spread is a cost |
| Cointegration | Two prices that wander individually, while a combination of them stays near a level |
| CONTAMINATED | A holdout read more than once, so it no longer counts as unseen |
| CPCV, CSCV | Cross-validation schemes that test many combinations of time blocks |
| Deflated Sharpe ratio (DSR) | The probability a Sharpe is above zero after allowing for how many variants were tried. 0.95 is the usual gate |
| Drawdown | The fall from a peak in equity to the next low |
| Dukascopy | A Swiss bank whose historical tick data is free to download |
| Engle-Granger, Johansen | Two standard tests for cointegration |
| FVG | Fair value gap. A three-bar pattern where the middle bar leaves a gap between the outer two |
| Half-life | How long a mean-reverting spread takes to close half of a gap |
| Holdout | The last slice of data, kept unread until the end |
| IBS | Internal bar strength. Where the close sits within the bar's range, from 0 to 1 |
| ICT, SMC | Retail trading schools built around liquidity narratives, with little published evidence |
| INSUFFICIENT SAMPLE | Under 100 trades, too few to conclude anything |
| Lookahead | A backtest using information that was not available at the time |
| M1, M5, H1, D1 | One-minute, five-minute, one-hour and daily bars |
| Mean reversion | The tendency of a price to return toward an average |
| Meta-labeling | Using a model to decide whether to take a primary signal's trades |
| n | Number of trades |
| Ornstein-Uhlenbeck (OU) | A simple model of a mean-reverting process |
| PBO | Probability of backtest overfitting. How often the best variant in sample ranks below the median out of sample |
| PF | Profit factor. Gross profit divided by gross loss. Above 1 is profitable before any doubt about luck |
| Pivot, R3, S3 | Levels computed from the prior period's high, low and close |
| Preregistration | Freezing a test's rules before running it |
| PSR | Probabilistic Sharpe ratio. The probability a Sharpe beats a threshold, given sample length and return shape |
| R-multiple | A trade's result as a multiple of the amount risked |
| Random twin | A fake strategy with the same number of trades and holding times, entered at random. A real rule should beat most twins |
| RSI | Relative strength index. A momentum oscillator from 0 to 100 |
| Sharpe ratio | Average return divided by its volatility |
| Slippage | The gap between the expected fill price and the actual one |
| Survivorship bias | Testing only assets that still exist, which flatters results |
| Sweep | Price briefly moving past a recent high or low, then coming back |
| Trial, variant | One distinct rule, parameter set and market combination that produced a result |
| Triple barrier | A labelling method with a profit target, a stop and a time limit |
| True UTC | Stamps after the HistData clock correction |
| Twin p | The share of random twins that do at least as well as the rule |
| VWAP | Volume-weighted average price |
| Walk-forward | Repeatedly fitting on one window and testing on the next |
