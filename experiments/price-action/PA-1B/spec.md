> Copied as found from `originals/gann_bot_500/research/price_action/PREREG_IB.md`. The claims in it are the original work's, not the audit's, and may be superseded: the audit's reading is in [README.md](README.md) and [audit/VERDICTS.md](../../../audit/VERDICTS.md). "The user" means the author. Redactions, if any, are listed in the root DECISIONS.md, item 20.

# PA-1b — D1 inside-bar breakout confirmation on other markets (pre-registered 2026-10-14, before any run)

Rule copied unchanged from PA-1 (PREREG.md sha 2a0618d57046): D1 inside bar (h<h[i-1], l>l[i-1]); OCO stop entries at
the mother bar high/low for the next 3 D1 bars; stop at the other side (floored 0.25 ATR14); target 2R; else close after
10x24h; same fine bar holding stop and target -> stop; both sides on one fine bar -> skip; fill bar's favourable extreme
ignored; one position at a time. Random-direction twins (20 seeds), same moment/price/risk.
Markets/data (PC broker demo feed exports, research/cross_market/data): D1 signal bars = broker D1.
  XAGUSD: walked on H1 2018-05..2026 (primary); US500, US30: M1 2012-08..2026; USTEC: M1 2022-07..2026.
Costs: 1.5x median recorded spread per round trip; financing per calendar night held at the symbol's current swap
(XAG long -0.0023 short +0.0002 $/oz; indices from D1 swl/sws, $/unit). Gold PA-1 result re-shown with its swap.
PASS = the inside bar is a general price-action edge, requires ALL of:
  (1) net avg R > 0 in at least 3 of the 4 markets; (2) pooled (4 markets) real - twin >= 0.05R with t >= 2.0;
  (3) pooled net avg R > 0 in both halves of each market's sample. Else FAIL (gold near-miss = gold drift / chance).
Blind prediction: FAIL. Indices may show a long-side bias (they drift up too); silver ~0 after its spread.
