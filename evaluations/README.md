# Evaluations of external material

Reviews of strategies and tools that came from outside this research. Nothing here endorses the material, and copyrighted content is not reproduced.

| Material | How it was tested | Outcome | Entry |
|---|---|---|---|
| TradingAgents, an LLM multi-agent framework (Xiao et al. 2024) | Preregistered study with leakage audit and baselines | No result. The study broke with 4,947 error rows and stays INCOMPLETE | [TAEVAL-1](../experiments/llm-agent/TAEVAL-1/README.md) |
| VWAP and 9 EMA video strategy, promoted with a paid membership | Replicated, then a search over TradingView built-ins | 0 of 20 pass | [TVS-1](../experiments/indicator-search/TVS-1/README.md) |
| Liquidity sweep video, H1 swing with an M5 wick | Exact replication with variants | Failed | [SWEEP-MTF-1](../experiments/ict-smc/SWEEP-MTF-1/README.md) |
| Published gold strategies from the literature | Replicated | All 6 failed | [GOLD-LIT-1](../experiments/literature-replication/GOLD-LIT-1/README.md) |
| Public signal channels | Calls scored against random twins, anonymised | Failed, or UNVERIFIED where the scored file is missing | [Experiments](../experiments/README.md) |
| A "$3k/month" Alpaca bot guide | Not tested. The code was never found | UNVERIFIED | Not in the registry |
| Google Trends as a signal | Not tested. Past vintages do not exist, so any backtest would carry lookahead | Not tested | [FUTURE_WORK.md](../FUTURE_WORK.md) |
| Two social-media reels | Tested in a separate study after the registry closed | No edge, not audited here | [FUTURE_WORK.md](../FUTURE_WORK.md) |
