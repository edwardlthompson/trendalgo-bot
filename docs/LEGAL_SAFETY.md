# Legal Safety — Prompt 8 Monetization Rules

> **Hard constraints (ADR-0008).** CI enforces via `scripts/check-legal-compliance.sh`.

## Never ship

| Forbidden | Reason |
|-----------|--------|
| Auto-withdraw from exchange | MSB / custodial |
| Stripe or card processing for license | Money transmitter adjacency |
| Operator-held withdrawal keys | Custody |
| Subaccount fee routing | Custodial collection |
| Marketing "we collect your fees automatically" | Regulatory + R-006 |
| Community untrusted strategy imports | Liability (ADR-0009) |
| Hosted multi-tenant trading keys | Custodial SaaS |

## Always ship

| Required | Implementation |
|----------|----------------|
| Calculation-only license module | Sprint 10 M1–M4 |
| User-initiated settlement UX | Copy address + QR (M7/M22) |
| Terms + install UUID consent log | S10 L4 — no IP/email |
| Dry-run default | Until go-live gate |
| Software-only disclaimers | UI, TERMS, AI output |
| Trade-only API key guidance | `docs/SECURITY.md`, M11 |

## Edge cases (Sprint 10)

Documented in `docs/MONETIZATION.md`: withdraw-before-pay, partial fills, disputes, net-loss months, manual trades outside bot.

## Verification

```bash
bash scripts/check-legal-compliance.sh
python3 scripts/check_risk_mitigations.py --sprint 0
```

R-006 status: **eliminated**.
