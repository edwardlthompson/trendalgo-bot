# Agent Memory — TrendAlgo Bot

> Update at session start, milestone boundaries, or architectural pivots only.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Trading | Native CCXT runner (ADR-0010) | `strategies/runtime/` + `trading/runner/` |
| Backend | Python 3.12+ (uv) | `src/trendalgo/` hexagonal modules |
| Web | Vite + TypeScript PWA | `examples/web/` |
| DB MVP | SQLite on VPS | Postgres path Sprint 12 |
| Exchange | 9 portfolio / 7 trading venues | Registry v5; worldwide Phase 1 (S18) |
| DEX | Venue plugin engine (ADR-0011) | S21–S24; Base Phase 1 live path; H-036 open |
| Scanner | linear-trend-spotter → `scanner/` | ADR-0006 absorption S4.5 |
| License | Performance software license | Calculation-only; user pays externally (ADR-0008) |
## Active Modules

- ✅ Python (`modules/python/MODULE.md`)
- ✅ Web / PWA (`modules/web/MODULE.md`)

## Project Constraints

| Constraint | Rule |
|------------|------|
| Legal (#0) | No KYC · No custodial funds · No MSB · User-initiated license payment |
| Cost | Production **< $10/mo**; Oracle Always Free → Hetzner fallback |
| Puerto Rico | **Never** live/production on local PR hardware |
| Dry-run | Default until go-live gate (H-010/H-028) |
| Secrets | Never in VCS; Gitleaks pre-commit |
| Telemetry | Opt-in only |
## Threat Model

- ✅ `docs/THREAT_MODEL.md` — TrendAlgo trust boundaries (Sprint 0 draft)
- ✅ ADR-0007 data minimization; install UUID only for consent
- ✅ Trade API keys: no Withdraw permission (R-009)

## Persistent Context

**Purpose:** Self-hosted Kraken spot algo bot with LTS scanner, CoinStats replacement portfolio, AI-recommended strategies, and transparent performance license.

**Current sprint:** Post-alignment carry-forward — HUMAN R-BA.H1 + attorney H-006 open.

**Tests:** 347 pass · ~86% coverage (2026-07-12; pyproject cov-fail-under=86%).

**Recent:** Shipped **v0.5.1** (2026-07-22) — bootstrap FOSS alignment + ruff/lock/security follow-ups. Product `.template-version` = 0.5.1; `upstream_aligned_version` = 0.15.1. See `docs/BOOTSTRAP_ALIGNMENT.md`.

**Canonical plan:** `docs/CANONICAL_PLAN.md` (prompts 1–9, feature matrix).

## Retrospectives

### Ship v0.5.1 (2026-07-22)

- Merged Release Please PR #15 → tag v0.5.1; synced `uv.lock`; cleared Dependabot High (js-yaml / brace-expansion overrides)
- CI/Security Scan/CodeQL green on `b251300`
- HUMAN still open: R-BA.H1 alignment review, attorney H-006, Pages enable

### Bootstrap align to upstream v0.15.1 (2026-07-21)

- Adopted FOSS Cursor hooks, 7 skills, 3 agents, local-compute, parallel/backlog scripts
- Kept product CI matrix; product version via release-please; `upstream_aligned_version` for template drift checks
- HUMAN: review `docs/BOOTSTRAP_ALIGNMENT.md`; attorney H-006 still open

### Ship v0.5.0 (2026-07-12)

- Merged Release Please PR #13 → tag v0.5.0; SBOM assets on GitHub Release
- Closed Dependabot PR #12 (TypeScript 7 major deferred)
- CI green after uv.lock 0.5.0 sync; Pages still 404 (Pages not enabled — HUMAN)
- Local `pre-release-gate` / license still WSL1-blocked; CI is source of truth

### R-Audit-8 (2026-07-12)

- Main CI red on `uv sync --locked` (lock version drift 0.2.0→0.4.1); 0 Dependabot alerts; CodeQL green
- AGENT: Lightning demote 501, Playwright More-menu e2e, smoke `testIgnore`, env docs, runner_bridge tests
- HUMAN open: attorney H-006 (R-Audit-8.9), PR #13 / #12 after CI green (R-Audit-8.10)
- Local `feature-gate` web-lint still fails under WSL1 Node; Windows `npx tsc --noEmit` preferred

### R-Audit-7 (2026-07-11)

- 332 tests, ~87% coverage; main CI/CodeQL/Security Scan green; 0 vuln alerts
- AGENT: charts pin (block LC v5), file-limits `.venv*`, version sync 0.4.0, legal packet, root pip Dependabot, hygiene gitignore
- HUMAN open: enable dependency graph/alerts (F-002), merge PR #7, attorney H-006
- Local `feature-gate` web-lint still fails under WSL1 Node; Windows `npx tsc --noEmit` passes

### R-Audit-5 (2026-06-26)

- 170 tests, ~85% coverage; CI blockers triaged (axe timeline label, offline e2e, sw.js API bypass)
- KB-013 documents Windows gate fallbacks; push required to confirm GitHub CI green + v0.2.0 tag

### R-Audit (2026-06-25)

- 89 tests, ~86% coverage; Risk Register Zero verified
- AGENT fixes: README test path, ARCHITECTURE link, CORS env, Archived Sprints table, KB-007
- Blockers for go-live/public beta: H-001–H-025 founder gates, H-023 TERMS, Dependabot alerts
