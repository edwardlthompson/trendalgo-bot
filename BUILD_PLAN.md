# TrendAlgo Bot — BUILD_PLAN

<!-- remaining-tally -->
**Remaining:** AGENT 0 · LOCAL 0 · CLOUD 0 · AUTO 0 · HUMAN 0 · ADB 0 · **0 open**
<!-- /remaining-tally -->
> **Detail:** [`docs/CANONICAL_PLAN.md`](docs/CANONICAL_PLAN.md) · **Human gates:** [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md) · **Risks:** [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md)
> **Archive:** [`COMPLETED_TASKS.md`](COMPLETED_TASKS.md) · **Post-delivery:** [`docs/POST_DELIVERY_PLAN.md`](docs/POST_DELIVERY_PLAN.md) · **Exchange:** [`docs/EXCHANGE_ROADMAP.md`](docs/EXCHANGE_ROADMAP.md) · **DEX:** [`docs/DEX_ROADMAP.md`](docs/DEX_ROADMAP.md)

### Product (do not drift)

<!-- product-brief-sync:begin -->
> Read `AGENT.md` before any sprint row.

**One-liner:** Photoreal Cycles icons from a locked seed, camera, and lighting.
**Do not drift:** camera, messages, tame, neon

**Rules:**
- Generate store/PWA icons from a JSON manifest (seed, camera, lighting).
- Machine QA only — do not ask a human to review thousands of frames.
- Cycles OptiX is local GPU; CI stays CPU/headless or skip if Blender is missing.
- Do not overwrite live `branding/assets/*.svg` (Sacred vector SoT).

**First milestone:** Seeded icon factory with QA JSON; sample manifest in CI; 4000+ run on This Computer.
<!-- product-brief-sync:end -->

## Current sprint

> **Now:** Board clear of AGENT/AUTO. **Sprint PF** archived in COMPLETED_TASKS.md @ `c3b46fb`+. Open HUMAN: PF-H1 (optional calendar keys) + carry-forward / R-Audit-8.9.

| Marker | State |
|--------|-------|
| 🔲 | Open |
| ✅ | Done |
| ❌ | Blocked |
🔲 [HUMAN] PF-H1 Optional: mint CoinMarketCal and/or Coindar API keys for live calendar (wizard walks signup; not required for empty-state CI) — see [`docs/HUMAN_BACKLOG.md`](docs/HUMAN_BACKLOG.md)

> **R-BA-17** / template FOSS surface archived in COMPLETED_TASKS. Alignment: [`docs/BOOTSTRAP_ALIGNMENT.md`](docs/BOOTSTRAP_ALIGNMENT.md) (`upstream_aligned_version` 1.10.0). Skills: [`docs/SKILLS_RECIPES.md`](docs/SKILLS_RECIPES.md).

---

## Program status (summary)

| Program | Sprints | AGENT | Open human gates |
|---------|---------|-------|------------------|
| Core (S0–S12) | Setup → platform, Risk Register Zero | ✅ | Open H-* in HUMAN_BACKLOG (H-001/H-005 archived) |
| Exchange | S13–S20 · 9 venues · ADR-0010 | ✅ | **H-032** (H-030/H-031 ✅) |
| DEX | S21–S24 · Base Phase 1 · ADR-0011 | ✅ | **H-036** live (H-035 ✅) |
| Reviews | R-Audit … R-Audit-8 · GP-Template-1.9 ✅ | ✅ | H-006 |
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
| Sprint PF | 2026-10-16 | Modular Dashboard (PF-0…PF-10; see COMPLETED_TASKS) |
| GP-Template-1.9 | 2026-10-16 | Golden Path → device app (GP-1…GP-8; see COMPLETED_TASKS) |
| HUMAN clearances + template v1.10.0 | 2026-10-16 | H-001/H-005/H-021/H-034 + agent catch-up (see COMPLETED_TASKS) |
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
