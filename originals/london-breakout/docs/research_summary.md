# Research summary: Asian-range / London-open / opening-range breakouts

Written 2026-10-30, before any backtest in this project was run. It records what was known
going in, so the results can be judged against it.

## 1. What the academic literature says

| Source | Market / period | Finding | Relevance |
|---|---|---|---|
| Gao, Han, Li & Zhou (2018), "Market Intraday Momentum", *JFE* 129(2) 394-414 ([RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414)) | SPY 1993-2013 plus 10 other ETFs | The first half-hour return (from the prior close) predicts the last half-hour return. Stronger on volatile, high-volume and macro-news days. | The direction of the early session carries information, but the payoff is realised at the *close*, not via a tight bracket. Out-of-sample R² is about 0.02 ([Alpha Architect](https://alphaarchitect.com/2014/08/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/)). [CXO Advisory](https://cxoadvisory.com/calendar-effects/first-and-last-half-hours-of-trading-linked) judged it too small to trade after frictions. |
| Li, Sakkas & Urquhart (2022), "Intraday time series momentum: global evidence", *J. Financial Markets* 57 ([RePEc](https://ideas.repec.org/a/eee/finmar/v57y2022ics138641812100001x.html), [accepted version](https://reading-9.eprints-hosting.org/95566/1/Accepted-Version.pdf)) | 16 developed markets | Intraday time-series momentum is significant in most markets, including the UK and Germany. It is stronger with low liquidity, high volatility and discrete news. | Supports *some* directional persistence in DAX/FTSE intraday, mainly on high-volatility days. |
| Holmberg, Lönnbark & Lundström (2013), "Assessing the profitability of intraday opening range breakout strategies", *Finance Research Letters* 10(1) 27-33 ([RePEc](https://ideas.repec.org/a/eee/finlet/v10y2013i1p27-33.html)) | Crude oil futures | ORB returns are significantly above zero, with a success rate above a fair game. Lundström's follow-ups show the returns are concentrated in high-volatility states (crude, S&P), and apply leverage to DAX futures. | Classic ORB evidence. It comes from futures with low costs, and from an older sample. |
| Zarattini & Aziz (2023), "Can Day Trading Really Be Profitable?" ([SSRN 4416622](https://papers.ssrn.com/abstract=4416622)) | QQQ 5-min ORB, 2016-2023 | Strong headline returns with leverage. | Written by authors who sell day-trading education. An [independent replication on NQ/SPX/Dow/DAX/FTSE CFDs, 2015-2026](https://www.mql5.com/en/blogs/post/776235) reproduced the gross result (+0.13R on NQ, +0.10R on DAX, +0.07R on FTSE) but found **net ≈ 0 or negative on every market**. The first candle beat random direction by 0.10-0.13R (t≈2-2.5) on DAX and FTSE. That gap is about the size of round-trip costs. |
| Crabel (1990), *Day Trading with Short Term Price Patterns and Opening Range Breakout* ([futures.io summary](https://futures.io/articles/trading/ORB)) | US futures, 1980s | The original ORB. The earlier in the session the stop-entry triggers, the better the trade performs. | Practitioner origin. Several sources ([Quantified Strategies](https://quantifiedstrategies.substack.com/p/opening-range-breakout-trading-strategies)) report that simple ORBs have largely decayed since. |
| Ito & Hashimoto, "Intraday seasonality in activities of the FX market" ([NBER w12413](https://www.nber.org/papers/w12413.pdf)); Cyree, Griffiths & Winters (EUR/USD GARCH) | FX | Volatility and activity spike at the Tokyo, London and NY opens (U-shape). | The London open *is* a volatility expansion point. Volatility expansion is not the same as direction, though: a breakout rule needs the move to continue past the box, not just a larger range. |

## 2. Published practitioner backtests of the London / Asian-range breakout

- **GBP/USD, 15m, 2016-2026** ([Backtrex](https://backtrex.com/en/backtests/london-breakout-gbp-usd)): Asian range 00:00-06:00 UTC, close-cross entry 07:00-11:00 UTC, 20-pip stop and 40-pip target. Result: 2,432 trades, 33.7% winners, PF 0.72, -60%, **every calendar year negative**. A 2:1 bracket needs about 33% winners before costs, and that is what it got: zero gross edge, so the costs did all the damage.
- **EUR/USD** ([Backtrex](https://backtrex.com/en/backtests/london-breakout-eur-usd)): 36.3% winners on a 2:1 bracket. That is barely above the 33.3% break-even before costs.
- **XAUUSD London breakout, 2023-2026** ([MQL5 blog](https://www.mql5.com/en/blogs/post/777540)): PF 1.37 over 715 trades. Settings were fitted on 2023-2025, and the "unseen" 2026 sample is only 157 trades. Costs are not stated, and the author sells the EA. Low evidential weight. This user's own TA-LAB work found that "Asia breakout" on gold has no edge.
- Forum and vendor claims (Babypips threads, Gumroad "Asian range" products) give no verifiable statistics.
- No independent DAX or UK100 Asian-box backtest was found.

## 3. What is known, in short

- **Typical edge:** at best a few hundredths to about 0.1R per trade gross on index opens. The direction of the first move carries weak information. Volatility does rise at the open, which makes it *look* as if breakouts work.
- **Typical failure modes:**
  1. Costs: spread is widest exactly at the open, and tight stops make costs a large share of R.
  2. False breakouts: price breaks the box, then comes back in.
  3. Fixed-RR brackets turn a weak directional signal into near coin-flip outcomes, so win rate ≈ stop/(stop+target).
  4. Over-fitting session windows and RR to one instrument.
  5. Overnight (Asian) ranges on European indices are thin, and gaps at the cash open distort them.
- **Decay:** the evidence for decay is anecdotal. The classic ORB is widely reported as weaker than in the 1980s-90s. The 2015-2026 CFD replication found 2015-2017 negative everywhere and no period significantly positive net. Prior expectation going in: **no net edge on DAX/UK100 after costs**, with a possible small gross directional signal.

## 4. Hypotheses to test (all frozen before results were seen)

- **H1 (core, Variant A):** a strong 1m/5m/15m candle closing outside the Asian box after the London open predicts continuation. Expectancy is > 0R after 1x costs on GER40 and UK100, in the validation set.
- **H2 (directional information):** breakout-direction trades beat (a) random direction at the same entry times and (b) fading the breakout, at p < 0.05.
- **H3 (Variant B):** a break of previous-session 15m levels in the first 30 minutes of a session has positive net expectancy at RR ≥ 1:3. Tested per session (Asia, London, NY) and per level definition (session H/L, fractal swings, pivots).
- **H4 (volume):** requiring tick volume ≥ k × the same-time-of-day median improves expectancy over ignoring volume.
- **H5 (candle quality):** "strong candle" filters (body %, range/ATR, close location) improve expectancy over any close beyond the level.
- **H6 (stop placement):** inside-box stops beat candle-extreme or ATR stops, or the reverse. There is no prior on which.
- **H7 (box size):** narrow boxes (compression) break out better than wide boxes. This is the common practitioner claim.
- **H8 (volatility regime):** the edge, if any, is concentrated in high-volatility regimes (Lundström; Li et al.).
- **H9 (trade management):** break-even at +1R, partial take-profit and ATR trailing (the author's "paid" features) improve risk-adjusted results versus a plain bracket. Prior: they only reshape the win rate.
- **H10 (news):** excluding ECB/BoE/NFP/CPI days improves results.
- **H11 (trend filter):** trading only in the direction of the daily trend (EMA, previous close vs box) improves expectancy.
- **H12 (confirmation):** requiring DAX and UK100 to break the same way improves expectancy.
- **H13 (retest):** a pullback/retest entry beats immediate entry.
- **H14 (decay):** any edge shrinks over 2013-2026.
- **H15 (generality):** any edge found on GER40/UK100 also shows up on US30, NAS100, EURUSD, GBPUSD and XAUUSD at their own session opens.
