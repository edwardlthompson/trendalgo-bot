# Legal Overview — TrendAlgo Bot

> **Not legal advice.** Tier A (owner-only + FOSS): founder residual-risk posture (H-006 / H-022 / H-023, ADR-0020). Tier B: counsel/clinic before non-owner billing (H-006b).

## Operator role

TrendAlgo Bot is **software** — a self-hosted tool that calculates signals, tracks portfolio, and computes performance license amounts. The operator is a **software vendor**, not:

- An investment adviser
- A broker-dealer or exchange
- A money services business (MSB)
- A custodian of user funds

## User responsibilities

- Own exchange accounts and API keys (trade-only, no Withdraw permission recommended)
- Initiate license payments externally when enrolled
- Comply with local tax and securities laws
- Accept TERMS version logged at enrollment (install UUID only)

## Document map

| Doc | Purpose |
|-----|---------|
| [`LEGAL_SAFETY.md`](LEGAL_SAFETY.md) | Prompt 8 anti-MSB rules |
| [`LEGAL.md`](LEGAL.md) | This overview + links |
| [`LICENSE_MODEL.md`](LICENSE_MODEL.md) | Performance license (Sprint 10) |
| [`DATA_MINIMIZATION.md`](DATA_MINIMIZATION.md) | GDPR/CCPA-aligned collection |
| [`adr/0007-legal-framework.md`](adr/0007-legal-framework.md) | ADR |
| [`adr/0008-legal-safe-monetization.md`](adr/0008-legal-safe-monetization.md) | ADR |
| [`adr/0020-legal-research-desk.md`](adr/0020-legal-research-desk.md) | Legal Research Desk + tiers |
| [`legal-desk/`](legal-desk/) | Desk corpus + `/legal-desk` |
| [`FOUNDER_LEGAL_POSTURE.md`](FOUNDER_LEGAL_POSTURE.md) | Tier A residual-risk checklist |
## Legal review packet

Generate: `bash scripts/generate-legal-review-packet.sh` (Tier A / optional Tier B counsel).
