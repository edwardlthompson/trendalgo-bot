# ADR-0005: Monetization — Performance License Model

- **Status:** Proposed (H-022 attorney review Sprint 10)
- **Date:** 2026-06-25

## Context

Sustainable revenue without custodial payment processing or MSB exposure.

## Decision

1. **Performance-contingent software license** — fee calculated on bot-attributed net-positive closed trades.
2. **User-initiated settlement** — copy address, QR, optional Lightning invoice; no Stripe.
3. **AGPL** codebase + proprietary-friendly billing module boundary (CM4).
4. **Grace period:** 7 days; suspend live trading if unpaid (not exchange access).
5. **Net-loss months:** $0 license; drawdown pause on accrual (M3/M12).

## Rejected

Auto-withdraw from exchange; Stripe/fiat; operator custody; subaccount routing.

## Consequences

Sprint 10 M1–M22; `docs/MONETIZATION.md`, `docs/LICENSE_MODEL.md`; H-006/H-023 legal gates.
