# Legal memo — Tier A owner-only + FOSS posture

> **Not legal advice.** Not a licensed attorney. Residual risk remains with the founder.
> **Date:** 2026-11-15 · **Scope:** owner-only+foss

## Issue

Hard gates H-006 / H-022 / H-023 blocked public FOSS distribution pending paid counsel. Need an honest path for owner-only use and source-available download without fake “attorney approved” stamps.

## Sources

- `docs/legal-desk/sources.md` (FinCEN / SEC / PR pointers — verify on each desk run)
- ADR-0007, ADR-0008, ADR-0017, ADR-0018, ADR-0020
- `docs/LEGAL.md`, `docs/LEGAL_SAFETY.md`

## Product mapping

| Control | Where enforced |
|---------|----------------|
| No auto-withdraw / Stripe / custody | `scripts/check-legal-compliance.sh`, ADR-0008 |
| Software-only / not investment advice | TERMS.md, UI disclaimers |
| Owner-only v1; no non-owner charge | ADR-0017, H-006b |
| ELv2 product license | ADR-0018, LICENSE |

## Residual risk

Founder still bears regulatory residual risk even with calculation-only settlement and dry-run defaults. Public fee marketing and non-owner enrollment remain higher risk.

## Recommended control

Complete `docs/FOUNDER_LEGAL_POSTURE.md`, regenerate legal packet, approve H-006 / H-022 / H-023 with `residual-risk owner-only+foss`. Keep H-006b open until counsel/clinic before any non-owner charge.
