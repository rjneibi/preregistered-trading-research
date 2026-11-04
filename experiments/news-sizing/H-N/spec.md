> Copied as found from `originals/gann_bot_500/research/goldbot/prereg/HN_PREREGISTRATION.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# HN_PREREGISTRATION — news-day edge at measured costs (first-flip-after-news)

**STATUS: FROZEN 2026-07-06** (predictions filled pre-commit; no result seen). Repo-nominated open
question (STRATEGY_SPECIFICATION.md §9.3): news days (FOMC/NFP/CPI) were the
BEST trades at flat costs (PF 2.40 new era, 1.19 old) and the live bot sizes
them 1.5×. External evidence agrees gold's adjustment continues after the
shock (intraday-inefficiency literature). Never priced at measured costs —
and news-time spreads are exactly where flat-cost assumptions lie most.
**This trial is decision-relevant for the LIVE bot: a FAIL removes the 1.5×
news sizing multiplier.**

**Hypothesis:** *conviction trades on FOMC/NFP/CPI days retain concentrated
edge after measured costs, including a p90 cost stress standing in for
news-widened spreads.*

**Registered predictions:**
- Claude (Fable 5): MARGINAL — passes at median costs, fails or scrapes the
  p90 stress gate; news-window spread widening is the honest killer and p90
  only partially proxies it.
- Rashed: FAIL — the news edge is a flat-cost artifact; the 1.5× multiplier
  should go. (Recorded 2026-07-06 pre-commit.)

## Pinned inputs (zero degrees of freedom)
- Trade set: the 472 H1-verdict conviction trades, subset where the event's
  UTC day ∈ fable-backtesting/calendar/news_days.json.
- Comparison set: the non-news complement (descriptive, no gate).
- Costs: matrix median and p90 stress, H1-verdict wiring. HONESTY NOTE: the
  matrix has no news-window cells (tick coverage too thin for ±15-min pools);
  p90 is the pinned stand-in and this limitation is recorded, not patched.

## Gates — ALL required
1. News-subset full-period PF ≥ 1.50 at median costs.
2. News-subset PF ≥ 1.20 at p90 costs.
3. Each era news-subset PF ≥ 1.10.
4. n(news trades) ≥ 60.

## Decision tree (committed)
- PASS → the live 1.5× news sizing stands, now cost-validated; a dedicated
  news-window sub-strategy becomes a legitimate future prereg.
- FAIL → REMOVE the 1.5× news multiplier from flip_bot (operator-confirmed
  live change); news edge recorded as flat-cost artifact.

## Ledger delta: | 45 | H-N news-day edge at matrix costs | pending |
