# Legal Research Desk — primary-source pointers

> **Not legal advice.** Links are research starting points. Verify each URL still resolves before relying on a memo.
> **Corpus date:** 2026-11-15

## Money transmission / MSB (US federal themes)

| Pointer | Why it matters for TrendAlgo |
|---------|------------------------------|
| [FinCEN MSB overview](https://www.fincen.gov/money-services-business-definition) | Framing: who is a money services business |
| [FinCEN Bank Secrecy Act](https://www.fincen.gov/resources/statutes-regulations/bank-secrecy-act) | Registration / AML themes for transmitters |
| Product map | ADR-0008 + `docs/LEGAL_SAFETY.md` — calculation-only, user-initiated settlement, no custody |

## Investment adviser / “advice” perception (US federal themes)

| Pointer | Why it matters |
|---------|----------------|
| [SEC Investment Advisers Act overview](https://www.sec.gov/investment/investment-advisers-act-1940) | When software + recommendations may look like advice |
| Product map | `docs/LEGAL.md`, TERMS § software-only / not investment advice; ADR-0009 AI strategies |

## Puerto Rico / US entity notes (research only)

| Pointer | Why it matters |
|---------|----------------|
| [PR DDEC / business resources](https://www.ddec.pr.gov/) | Entity / local compliance starting point for a PR/US operator |
| Product map | TERMS governing-law placeholder; founder LLC facts are human-owned |

## Map to Never / Always (`docs/LEGAL_SAFETY.md`)

| Never | Always |
|-------|--------|
| Auto-withdraw, Stripe, operator withdrawal keys, custodial SaaS | Calculation-only billing, user-initiated UX, dry-run default, disclaimers |

## Desk hygiene

On every `/legal-desk` run: spot-check at least three links above; if a link is dead, mark it `DEAD` in the memo and prefer an alternate official URL.
