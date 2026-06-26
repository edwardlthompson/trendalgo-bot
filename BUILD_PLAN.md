# TrendAlgo Bot — BUILD_PLAN

> **Detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Archive:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

## Current sprint: **Post-Delivery / maintenance**

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

**170 tests** · **~86%** coverage · Risk Register Zero ✅

**Agent rule:** `[AGENT]` sequential · after each step → `bash scripts/watch-agent-gates.sh --once --autofix`

**Human gates** (H-030–H-036, go-live, legal): [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) — not duplicated here.

---

## Program status (summary)

| Program | Sprints | AGENT | Open human gates |
|---------|---------|-------|------------------|
| Core (S0–S12) | Setup → platform, Risk Register Zero | ✅ | H-001–H-029 backlog |
| Exchange | S13–S20 · 9 venues · ADR-0010 | ✅ | **H-032** worldwide live |
| DEX | S21–S24 · Base Phase 1 · ADR-0011 | ✅ | **H-035** scope · **H-036** live |
| Reviews | R-Audit … R-Audit-4 | ✅ | — |

Task-level history: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md). Critique mitigations CM-1–CM-11: closed in [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md).

---

## Open work

Founder gates, VPS, legal, go-live, and recurring controls — full checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

| Track | Owner | Status |
|-------|-------|--------|
| Founder preflights S0–S12 | HUMAN | 🔲 |
| Legal (H-006, H-023) | HUMAN | 🔲 blocks public beta |
| VPS + secrets (H-004, H-008, H-011) | HUMAN | 🔲 |
| Go-live per venue (H-010, H-028) | HUMAN | 🔲 |
| Exchange live worldwide (H-032) | HUMAN | 🔲 |
| DEX live (H-035, H-036) | HUMAN | 🔲 |
| CI green + v0.2.0 tag | AGENT/HUMAN | 🔲 see KB-012 |
| Risk Register Zero | AUTO | ✅ |
| Scope preflights H-013–H-025 | AGENT | ✅ |

### Maintenance cadence

| Cadence | Owner | Item |
|---------|-------|------|
| Weekly | AUTO | `check_risk_mitigations.py` · CI/CodeQL on `main` · Dependabot triage |
| Monthly | AUTO | portfolio integrity · production cost · backup dry-run (R-020) |
| Pre-live | AUTO/HUMAN | `go-live-gate.sh --check-only` → `--approve` (H-010/H-028) |

Local preview (S13+ UI/API): [`docs/LOCAL_DEV.md`](docs/LOCAL_DEV.md) · `scripts/dev-local.ps1`

Founder gate CLI: [`docs/FOUNDER_GATES.md`](docs/FOUNDER_GATES.md) · `python scripts/founder_gate.py status`

---

## Owner labels

| Label | Owner |
|-------|-------|
| `AGENT` | Code, docs, tests |
| `HUMAN` | Credentials, legal, go-live |
| `AUTO` | CI / gate scripts |

**Hard gates (never AUTO):** H-006, H-008, H-010, H-011, H-023, H-028, H-031, H-032, H-036

---

## Archived sprints

Full task lists: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md).

| Sprint | Closed | Archive |
|--------|--------|---------|
| DEX S21–S24 | 2026-06-26 | Plugin engine → dry-run → Base live (see COMPLETED_TASKS) |
| Exchange S13–S20 | 2026-06-26 | Native CCXT → worldwide Phase 2 → ops |
| R-Audit-4 | 2026-06-26 | Doc sync post DEX S21–S24 |
| R-Audit … R-Audit-3 | 2026-06-25 | Post-program doc sync |
| S0–S12 | 2026-06-25 | MVP → platform · Risk Register Zero |
| Post-Delivery | 🔲 open | [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) |
