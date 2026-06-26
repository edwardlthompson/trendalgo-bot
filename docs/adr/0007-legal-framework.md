# ADR-0007: Legal Framework — Pseudonymous, Software-Only

- **Status:** Accepted (Sprint 0)
- **Date:** 2026-06-25

## Context

US/PR regulatory exposure for trading tools and performance-linked fees.

## Decision

1. **No KYC** — install UUID + terms version for consent log only.
2. **Software vendor framing** — not investment advice, not a broker/dealer.
3. **Data minimization** — no IP/email in fee ledger by default (`docs/DATA_MINIMIZATION.md`).
4. **Disclaimers** in UI, TERMS, and AI output (S7/S11).
5. **Attorney review** before public beta (H-006, H-023).

## Consequences

`docs/LEGAL.md`, TERMS draft S10; pseudonymous referral/leaderboard S11.
