# ADR-0008: Legal-Safe Monetization — Anti-MSB

- **Status:** Proposed (H-006 attorney sign-off required)
- **Date:** 2026-06-25

## Context

Auto-collect from exchange accounts triggers MSB/money-transmitter risk. Retail crypto settlement must stay user-initiated.

## Decision

1. **Calculation-only** — billing module computes license amounts; never moves funds.
2. **Voluntary payment** — user sends crypto externally; operator never holds user keys for withdrawal.
3. **Non-custodial** — no pooled wallets, no Stripe, no auto-debit.
4. **CI enforcement** — `scripts/check-legal-compliance.sh` greps forbidden patterns (R-006 eliminated).
5. **Marketing** — never claim auto-collect or guaranteed fee extraction.

## Rejected

Stripe; auto-withdraw; institutional auto-collect; hosted custodial SaaS.

## Consequences

R-006 eliminated; Sprint 10 billing UX; `docs/LEGAL_SAFETY.md`.
