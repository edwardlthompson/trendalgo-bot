# ADR-0003: Competitive Feature Adoption

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

Competitor analysis (Prompt 3) lists 25+ features. Solo-dev scope requires extend-Freqtrade-first, defer exotic strategies.

## Decision

1. **Adopt via Freqtrade:** DCA/grid templates, webhooks, multi-bot, backtest UI (S1–S8).
2. **TrendAlgo differentiators:** LTS Opportunity Scanner (S4.5), CoinStats portfolio (S5), AI recommender (S11).
3. **Defer:** Market making, arb auto-trade, perps/funding (S12+ platform).
4. **Reject:** Community strategy marketplace (see ADR-0009).

## Consequences

Feature IDs in `docs/FEATURE_ROADMAP.md`; no MM/arb in MVP BUILD_PLAN.
