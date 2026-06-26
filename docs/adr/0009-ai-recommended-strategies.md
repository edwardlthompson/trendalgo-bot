# ADR-0009 — AI-Recommended Strategies (Not Community Marketplace)

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

Community strategy imports (G3, IX1, IX2) introduce untrusted code and liability. Product value is operator-curated AI recommendations.

## Decision

1. **Reject** community uploads, custom indicator marketplace, user-imported strategies.
2. **Ship AI5–AI8:** recommender, scanner-to-strategy pipeline, curated library, NL draft with user confirmation.
3. **User confirms all params** before live; backtest-first flow.
4. **Disclaimers:** not financial advice (`docs/AI_STRATEGIES.md`).

## Consequences

Sprint 11 scope; `check-legal-compliance.sh` blocks community import paths; R-012 accepted (AGPL fork).
