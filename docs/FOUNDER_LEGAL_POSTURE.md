# Founder Legal Posture (Tier A)

> **Not legal advice.** By filling the fields below you accept residual regulatory risk for the stated scope.
> Desk: [`docs/legal-desk/`](legal-desk/) · ADR: [`docs/adr/0020-legal-research-desk.md`](adr/0020-legal-research-desk.md)

## Accepted scope

```
Accepted-scope: owner-only+foss
Accepted-date: 2026-11-15
Accepted-by: Edward L. Thompson (founder)
```

## Checklist (founder)

- [x] I understand the Legal Research Desk is **not** a licensed attorney and does not provide legal advice.
- [x] Ship scope is **owner-only** operation plus public **FOSS / source-available** download (ELv2).
- [x] I will **not** enroll or charge non-owners Alpha Share / performance fees until **H-006b** (counsel or clinic).
- [x] Product keeps ADR-0008 controls: calculation-only billing math, user-initiated settlement, no custody, dry-run default until go-live gates.
- [x] I have reviewed TERMS.md, LEGAL.md, LEGAL_SAFETY.md, and the generated legal-review-packet.

## Explicitly deferred (Tier B)

- Non-owner performance-license enrollment UX
- Public marketing that requires others to pay a performance fee
- Any auto-collection or custodial payment path (already forbidden)

## Approve commands (after this file is filled)

```bash
python scripts/founder_gate.py approve H-006 --note "residual-risk owner-only+foss ADR-0020"
python scripts/founder_gate.py approve H-022 --note "residual-risk owner-only+foss license ADRs"
python scripts/founder_gate.py approve H-023 --note "residual-risk owner-only+foss TERMS ELv2"
```
