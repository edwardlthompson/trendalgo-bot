# Data Minimization

> ADR-0007. GDPR/CCPA-aligned defaults for self-hosted single-user MVP.

## Collected (official build)

| Field | Purpose | Retention |
|-------|---------|-----------|
| Install UUID | Terms consent, license gate | Until uninstall |
| TERMS version + timestamp | Legal consent log | Append-only |
| Trade/fee ledger | License calculation | Configurable TTL (S10) |
| Portfolio snapshots | P/L history | User-controlled export/delete |

## Not collected by default

- Email, name, phone
- IP address in fee ledger
- Government ID / KYC
- Exchange withdrawal credentials

## Pseudonymous growth (S11)

- Referral codes: random, not tied to PII
- Leaderboard: opt-in, anonymized handles only

## User rights

Self-hosted operator is data controller for their VPS instance. Export via CSV (portfolio, statements). Delete via retention job (S10 LS20).

## Verification

R-019 closes Sprint 10; R-034/R-035 Sprint 7/11.
