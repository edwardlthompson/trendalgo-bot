# Agent Memory — TrendAlgo Bot

> Update at session start, milestone boundaries, or architectural pivots only.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Trading | Native CCXT runner (ADR-0010) | `strategies/runtime/` + `trading/runner/` |
| Backend | Python 3.12+ (uv) | `src/trendalgo/` hexagonal modules |
| Device UI | PySide6 (ADR-0016) | `src/trendalgo/device/` — PWA/`examples/web` retired |
| Host | `botd` headless | Device-initiated sync; no inbound to PC |
| DB MVP | SQLite on VPS | Postgres path Sprint 12 |
| Exchange | 9 portfolio / 7 trading venues | Registry v5; worldwide Phase 1 (S18) |
| DEX | Venue plugin engine (ADR-0011) | S21–S24; Base Phase 1 live path; H-036 open |
| Scanner | linear-trend-spotter → `scanner/` | ADR-0006 absorption S4.5 |
| License | Performance software license | Calculation-only; user pays externally (ADR-0008) |
## Active Modules

- ✅ Python (`modules/python/MODULE.md`)
- ✅ Web module retained in stack-selection for FOSS surface; product UI is device

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

**Current sprint:** Board clear of AGENT/AUTO after `/ship` v0.7.2. Open: HUMAN PF-H1 (optional calendar keys) + carry-forward (attorney H-006, ops, H-032/H-036).

**Tests:** watch-agent-gates OK; local pre-release-gate PASS; GitHub CI/CodeQL/Security Scan green @ `1a27a65` then Release Please #49 → `v0.7.2`.

**Recent:** `/ship` 2026-10-20 — window geometry + FlowLayout; scanner cold-open/hour-align; local/UTC time display; About updates/Venmo; live rails; ccxt/fastapi/httpx2 bumps; gitleaks fixture fix; restore `codeql-action@v4` after upd invalid pin again.

**Canonical plan:** `docs/CANONICAL_PLAN.md` (prompts 1–9, feature matrix).

## Retrospectives

### Sprint Oracle-SS (2026-10-18)

- Sauce split: **Secret Sauce TA** (Oracle×catalog coincidence, live) vs **Secret Sauce Lab** (async refine, #2 under Oracle)
- All-TA wall clock dominated by catalog Pass 2 — parallel workers; live partial JSON streams Results
- Child board needs `### Sprint …` numbered rows for `smoke-sprint` parse

### Sprint PF — Modular Dashboard (2026-10-16)

- Nav **Dashboard**; grid canvas with magnetic snap; Customize + page tabs
- Calendar: official CMC/Coindar APIs only; CredMgr wizard; no CryptoCraft scrape
- PF-H1 optional for live keys; empty-state CI path works without them

### GP-Template-1.9 → device (2026-10-16)

- Retargeted scopes off deleted `examples/web` onto PySide6 device
- GP-1…GP-8 ✅; smoke-sprint PASS; `/cleanup` archived
- Do not run WSL `bash`/`uv` against this repo — it recreates Linux `.venv` on the Windows tree

### Ship prepare (deps + device) (2026-10-16)

- `update-deps --apply` + `uv lock`; audit 0 HIGH/CRITICAL after `anyio>=4.14.2` constraint
- Local `pre-release-gate --local` green (9 feature-gate stages)
- README preview template restored `## For humans` / `## For agents`
- HUMAN still open: R-BA.H1, attorney H-006, branch-protection H-003 (token perms)

### Bootstrap align to upstream v0.17.0 (2026-08-14)

- Adopted Issue→Resolution critique, `/codex-review` (opt-in), expanded `/prerelease`
- npm overrides: undici / ip-address / nanoid / postcss; js-yaml 5.2.2+; brace 1.x 1.1.18+
- Adopted branding kit + pitch README generator in **template** mode (live README preserved)
- Still skipped: Biome/fast-check/TS 7, multi-stack CI, product-mode README overwrite
- `validate-bootstrap.sh --quick` green; HUMAN R-BA.H1 + H-006 still open

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
