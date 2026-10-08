# TrendAlgo Bot — BUILD_PLAN

> **Detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Archive:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

## Current sprint: **GP-Template-1.9 — Golden Path adoption (2026-10-08)**

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |

**Source:** Template upgrade catch-up to agent-project-bootstrap **v1.9.0**. Port patterns into existing feature folders; never copy `examples/` over the app. One feature per `/feature` task. Thin wiring ≤10 lines.

**Agent rule:** `[AGENT]` sequential · after each step → `bash scripts/watch-agent-gates.sh --once --autofix`

> **R-BA-17** / template FOSS surface archived context in COMPLETED_TASKS / prior sections. Alignment: [`docs/BOOTSTRAP_ALIGNMENT.md`](docs/BOOTSTRAP_ALIGNMENT.md) (`upstream_aligned_version` 1.9.0).

## Sequential — GP-Template-1.9

| ID | Task | Owner | Status |
|----|------|-------|--------|
| GP-1 | Port crash-capture vertical slice into examples/web (ref stub; no overwrite) · [`docs/features/crash-capture.md`](docs/features/crash-capture.md) | `[AGENT]` | 🔲 |
| GP-2 | Port feedback clipboard/inbox slice into examples/web · [`docs/features/feedback.md`](docs/features/feedback.md) | `[AGENT]` | 🔲 |
| GP-3 | Port GitHub feedback bridge into examples/web · [`docs/features/github-feedback.md`](docs/features/github-feedback.md) | `[AGENT]` | 🔲 |
| GP-4 | Port privacy-report sanitize/fingerprint slice into examples/web · [`docs/features/privacy-report.md`](docs/features/privacy-report.md) | `[AGENT]` | 🔲 |
| GP-5 | Adopt Settings-only header chrome (tour/coach pattern) without ripping product ThemeToggle blindly — Plan first · [`docs/features/settings-chrome.md`](docs/features/settings-chrome.md) | `[AGENT]` | 🔲 |
| GP-6 | Harden About/donations + update-check patterns vs template stub · [`docs/features/donations-updates.md`](docs/features/donations-updates.md) | `[AGENT]` | 🔲 |
| GP-7 | Port deep-link feedback entry into examples/web · [`docs/features/deep-link-feedback.md`](docs/features/deep-link-feedback.md) | `[AGENT]` | 🔲 |
| GP-8 | Adopt crash-inbox ops docs/scripts for local review queue · [`docs/features/crash-inbox.md`](docs/features/crash-inbox.md) | `[AGENT]` | 🔲 |

### Human & device

| ID | Task | Owner | Status |
|----|------|-------|--------|
| R-BA.H1 | Review alignment doc (`docs/BOOTSTRAP_ALIGNMENT.md`) | `[HUMAN]` | 🔲 |
| GP-H1 | Approve Settings-only chrome change vs current ThemeToggle (GP-5) before AGENT implements | `[HUMAN]` | 🔲 |

---


## Program status (summary)

| Program | Sprints | AGENT | Open human gates |
|---------|---------|-------|------------------|
| Core (S0–S12) | Setup → platform, Risk Register Zero | ✅ | H-001–H-029 backlog |
| Exchange | S13–S20 · 9 venues · ADR-0010 | ✅ | **H-032** worldwide live |
| DEX | S21–S24 · Base Phase 1 · ADR-0011 | ✅ | **H-035** scope · **H-036** live |
| Reviews | R-Audit … R-Audit-8 · GP-Template-1.9 open | 🔲 | H-006 · GP-H1 · R-BA.H1 |
Task-level history: [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md). Critique mitigations CM-1–CM-11: closed in [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md).

---

## Open work

### R-Audit-8 — Post product-rec audit (2026-07-12)

AGENT 8.1–8.8 ✅ (see [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md)). Remaining:

| ID | Task | Owner | Status |
|----|------|-------|--------|
| R-Audit-8.9 | Attorney review of legal packet (F-010 / R-Audit-7.10) | HUMAN | 🔲 |
| R-Audit-8.10 | Triage PR #13 release + PR #12 web deps after CI green (F-011) | AGENT | ✅ |

### Carry-forward (HUMAN)

| Track | Owner | Status |
|-------|-------|--------|
| Founder preflights S0–S12 | HUMAN | 🔲 |
| Legal (H-006, H-023) | HUMAN | 🔲 blocks public beta |
| VPS + secrets (H-004, H-008, H-011) | HUMAN | 🔲 |
| Go-live per venue (H-010, H-028) | HUMAN | 🔲 |
| Exchange live worldwide (H-032) | HUMAN | 🔲 |
| DEX live (H-035, H-036) | HUMAN | 🔲 |
| CI green + v0.4.x tag | AGENT/HUMAN | ✅ v0.4.1 tagged 2026-07-12 |
| Risk Register Zero | AUTO | ✅ |
| Scope preflights H-013–H-025 | AGENT | ✅ |

Founder gates, VPS, legal, go-live, and recurring controls — full checklist: [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md).

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
| R-Bootstrap-Align | 2026-07-21 | FOSS agent surface → upstream v0.15.1 (see COMPLETED_TASKS) |
| S27 | 2026-06-29 | TA fleet backtest + v0.4.0 Settings/billing (see COMPLETED_TASKS) |
| S25–S26 | 2026-06-26 | TA cache epic + file-limit gate alignment (see COMPLETED_TASKS) |
| DEX S21–S24 | 2026-06-26 | Plugin engine → dry-run → Base live (see COMPLETED_TASKS) |
| Exchange S13–S20 | 2026-06-26 | Native CCXT → worldwide Phase 2 → ops |
| R-Audit-8 | 2026-07-12 | Post product-rec · Lightning 501 · e2e · **v0.5.0** |
| R-Audit-7 | 2026-07-12 | Post-audit hygiene · charts pin · version sync · PR #7 → 0.4.1 |
| R-Audit-6 | 2026-07-11 | Post v0.4.0 CI mypy (AGENT ✅; HUMAN → R-Audit-7.9/7.10) |
| R-Audit-5 | 2026-06-26 | CI axe + offline e2e + KB-013 |
| R-Audit-4 | 2026-06-26 | Doc sync post DEX S21–S24 |
| R-Audit … R-Audit-3 | 2026-06-25 | Post-program doc sync |
| S0–S12 | 2026-06-25 | MVP → platform · Risk Register Zero |
| Post-Delivery | 🔲 open | [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) |
