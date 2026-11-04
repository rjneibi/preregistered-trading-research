> Copy of the frozen preregistration `audit/prereg/E5-CRYPTO.md`.

# E5 Crypto cost realism

Blind prediction (Claude): CR-1 stays failed. F6's Sharpe falls by 0.05 to 0.15 from fees and more from survivorship, and F6 still beats buy-and-hold on Sharpe in the fixed universe.

Rerun: the CR-1 rules (BTC, ETH) and EDGE-1-F6 (12 coins, SMA50, equal risk), as stored.

Costs, three tiers: Binance spot VIP0 taker 0.10% per side, spot with BNB discount 0.075%, USD-M perpetual taker 0.05%. Slippage 2 bp per side for BTC and ETH, 10 bp for other coins [ESTIMATE].
Historic order-book depth is not available for free, so no depth-based slippage is possible. That is a limitation, and today's book is not used for past trades.
Funding: Binance USD-M funding history for each coin, public API, applied to held perp positions in the perp tier. Coins with no perp history before a date use spot only.

Survivorship for F6: the universe was picked with hindsight in 2026. Add these names, chosen before any data was read, on the rule "large-cap coin that collapsed or was delisted from Binance": LUNA (old chain), FTT, UST, SRM, WAVES, MITH, BTS, ANC. Each joins on the date of its first Binance kline and leaves at its last, at last close less a 50% exit haircut [ESTIMATE] if the final kline is a delisting.
A coin whose klines the API no longer serves is listed as unavailable. The check then understates the effect, and the report says so.

Slices: same halves as the originals, which are already opened, so results are cost corrections, not fresh tests. Verdicts cannot improve.
Ledger: 2 experiments x 3 tiers, 6 variants, plus 1 survivorship.
