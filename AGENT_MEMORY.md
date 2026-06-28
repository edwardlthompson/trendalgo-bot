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

**Current sprint:** Post-Delivery / maintenance (BUILD_PLAN); human gates H-032, H-035, H-036 open.

**Tests:** 170 pass · ~85% coverage (2026-06-26 v0.2.0 release).

**Canonical plan:** `docs/CANONICAL_PLAN.md` (prompts 1–9, feature matrix).

## Retrospectives

### R-Audit-5 (2026-06-26)

- 170 tests, ~85% coverage; CI blockers triaged (axe timeline label, offline e2e, sw.js API bypass)
- KB-013 documents Windows gate fallbacks; push required to confirm GitHub CI green + v0.2.0 tag

### R-Audit (2026-06-25)

- 89 tests, ~86% coverage; Risk Register Zero verified
- AGENT fixes: README test path, ARCHITECTURE link, CORS env, Archived Sprints table, KB-007
- Blockers for go-live/public beta: H-001–H-025 founder gates, H-023 TERMS, Dependabot alerts
