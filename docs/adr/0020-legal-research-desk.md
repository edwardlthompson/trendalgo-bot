# ADR-0020: Legal Research Desk + tiered legal gates

- **Status:** Accepted
- **Date:** 2026-11-15
- **Deciders:** Founder (owner-only + FOSS ship scope)
- **Relates to:** ADR-0007, ADR-0008, ADR-0017, ADR-0018, H-006 / H-022 / H-023 / H-006b

## Context

Hard gates H-006, H-022, and H-023 required a paid attorney before public beta. That is unaffordable and blocked FOSS distribution of an owner-only product. An LLM “attorney bot” cannot practice law and must not mint “attorney approved” stamps.

## Decision

1. **Legal Research Desk** — in-repo Cursor skill `/legal-desk`, corpus under `docs/legal-desk/`, expanded legal packet. Output is research and consistency tooling **only**, with a mandatory not-legal-advice banner.
2. **Tier A (closable without counsel):** owner-only operation + public FOSS / source-available download after Founder Legal Posture, packet regen, TERMS/ELv2 alignment, and CI `check-legal-compliance`. Close H-006 / H-022 / H-023 via `founder_gate.py approve … --note "residual-risk owner-only+foss …"`.
3. **Tier B (deferred, hard):** non-owner commercial billing / performance-fee enrollment. Tracked as **H-006b**. Never AUTO. Requires real counsel, clinic, or equivalent before charging others.
4. **Ban fake counsel** — approve notes containing `attorney approved` are refused unless a file exists under `docs/legal-desk/counsel/`.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Attorney Grok Bot that “signs off” | Unauthorized practice of law; false security |
| Keep all legal gates blocked forever | Blocks FOSS publish of owner-only software |
| Close Tier B without counsel | Unacceptable residual risk for charging others |

## Consequences

- Public FOSS download OK after Tier A; billing enrollment UX stays off until H-006b.
- ADR-0008 / ADR-0017 status language updated to Tier A founder posture vs Tier B counsel.
- R-008 control: Tier A residual risk accepted by founder; Tier B still blocks fee beta.

### Critique

| Issue | Resolution |
|-------|------------|
| False “attorney approved” stamp | Ban phrase in approve notes; honesty banner on desk |
| Diluting R-008 | Tier B keeps non-owner billing hard |
| Empty posture file | Preflight fails closed until Accepted-scope + date |
| Stale sources | Date-stamp `sources.md`; desk skill re-checks links |
