# Decision Log

> Chronological register of major technical trade-offs, accepted architectures, and rejected alternatives.
> **Treat past entries as immutable history; append only.**

## Format

```markdown
### YYYY-MM-DD — [Title]
- **Status:** Accepted | Rejected | Superseded
- **Context:** ...
- **Decision:** ...
- **Alternatives considered:** ...
- **Consequences:** ...
```

## Entries

### 2026-06-26 — Release v0.2.0 — DEX program + exchange S19–S20
- **Status:** Accepted
- **Context:** `/ship` after DEX S21–S24 and exchange S19–S20 AGENT completion; R-Audit-4 doc sync; CI on v0.1.0 main red (TEMPLATE_INDEX drift, ruff, web TS).
- **Decision:** Release `0.2.0` with venue plugin engine, DEX dry-run/live (Base Phase 1), exchange Phase 2 + ops hardening; fix CI blockers (TEMPLATE_INDEX, ruff, web lint) in same commit.
- **Verification:** `python scripts/run-trendalgo-tests.py` (170 pass, 85.08%); `npm run lint` (web); `validate-template-index.sh`; `check-template-version-sync.sh` (0.2.0).

### 2026-06-25 — Release v0.1.0 — TrendAlgo platform (S0–S18)
- **Status:** Accepted
- **Context:** First `/ship` after exchange program S13–S18; pre-release gate run on Windows (npm/WSL gaps; CI pending post-push).
- **Decision:** Release `0.1.0` with native CCXT engine, 9 portfolio / 7 trading venues, Freqtrade removed; gate script tweaks for multi-stack local runs.
- **Verification:** `python scripts/run-trendalgo-tests.py` (130 pass, 85.85%); `feature-gate.sh --stack multi --strict` (local); Risk Register Zero.

### 2026-06-25 — Review R-Audit — repo health sign-off (AGENT scope)
- **Status:** Accepted
- **Context:** `/audit` command after Sprint 12 completion; bash gates unavailable on Windows dev host.
- **Decision:** AGENT remediated F-003–F-006 (README, ARCHITECTURE link, Archived Sprints table, `TRENDALGO_CORS_ORIGINS`, KB-007). Human gates F-001/F-002/F-008/F-009 remain open in HUMAN_BACKLOG.
- **Verification:** `python scripts/run-trendalgo-tests.py` (89 pass, 85.76%); `check_risk_mitigations.py --strict --all` (0 active).

### 2026-06-25 — Sprint 12 — Risk Register Zero sign-off
- **Status:** Accepted
- **Context:** Sprint 12 delivered platform extensions (on-chain read-only sync, pair forager, funding/perps hooks, unified trading router, Postgres migration path) and closed the scheduled risk register.
- **Decision:** Terminal statuses applied in `docs/risk-catalog.json`; `python scripts/check_risk_mitigations.py --strict --all` reports 0 active risks and 0 pending critiques; critiques archived in `docs/RISK_REGISTER_CLOSED.md`.
- **Verification:** 89 tests passing; 85.74% `trendalgo` coverage; `bash scripts/postgres-migrate-dry-run.sh` validates schema without live DB.
- **Consequences:** BUILD_PLAN sequential lane complete; ongoing risks (R-003, R-005, etc.) remain **ongoing** terminal status with verification artifacts — not active backlog items.

### 2026-06-25 — TrendAlgo Sprint 0 — ADR-0001–0009 accepted
- **Status:** Accepted
- **Context:** Scaffold from agent-project-bootstrap; canonical plan in `docs/CANONICAL_PLAN.md`
- **Decision:** Freqtrade-as-engine (0001), external VPS only (0002), CoinStats portfolio (0004), calculation-only license (0005/0008), LTS absorption (0006), AI-not-community (0009)
- **Consequences:** `src/trendalgo/` layout, founder gates, Risk Register Zero schedule

_Seed template ADR: `docs/adr/0000-template-baseline.md`. Child repos use `docs/adr/0001-core-architecture.md`._

### 2026-06-20 — Repo-wide checklist status markers
- **Status:** Accepted
- **Context:** BUILD_PLAN and scattered checklists used mixed ⬜ / `- [ ]` / ✅ formats; inconsistent in Markdown Preview vs source
- **Decision:** Standardize on 🔲 open · ✅ done · ❌ blocked emoji markers repo-wide; document in `BUILD_PLAN.md` legend and agent read order
- **Alternatives considered:** GitHub `- [ ]` task lists (rejected: poor Preview readability and agent parsing); keep ⬜ white square (rejected: visually similar to ✅ in some fonts)
- **Consequences:** All new checklist rows use emoji; `agent-progress.sh` accepts legacy ⬜ for child repos during transition

### 2026-06-18 — Release automation hardening (M29)
- **Status:** Accepted
- **Context:** v0.11.0 release lacked SBOM assets (GITHUB_TOKEN cannot chain `release` → `release.yml`); Release Please skipped `extra-files`; `health-check.yml` registered as path name caused 0-job push failures
- **Decision:** `release-please.yml` runs `sync-template-version.sh` on release PR branches and dispatches `release.yml` on `release_created`; rename workflow to `weekly-health-check.yml`; fix sync script for Windows Git Bash
- **Alternatives considered:** PAT with workflow scope for release chaining (rejected: secrets management); manual SBOM backfill only (rejected: repeated human step each release)
- **Consequences:** Release Please needs `actions: write`; future releases should ship SBOM assets without manual dispatch

### 2026-06-17 — Batch instruction templates (M27)
- **Status:** Accepted
- **Context:** Agents and child-repo owners needed repeatable shortcuts for bootstrap, verify, build, ship, and maintenance workflows without re-pasting long prompts
- **Decision:** Ship 25 slash commands in `.cursor/commands/` (20 atomic + 5 super), bare-word expansion via `batch-commands.mdc`, human cheat sheet at `docs/help/BATCH_COMMANDS.md`, registry at `docs/BATCH_COMMANDS.md`; `/push` and `/ship` grant explicit push approval
- **Alternatives considered:** `beforeSubmitPrompt` hook for bare words (rejected: Cursor API cannot rewrite prompts); single mega-doc for humans and agents (rejected: overwhelms first-time users)
- **Consequences:** `alwaysApply` rule adds ~25 lines per session; `check-batch-commands.sh` prevents registry drift; child repos cherry-pick via `UPGRADING_FROM_TEMPLATE.md`

### 2026-06-13 — @lhci/cli npm overrides for transitive CVEs
- **Status:** Accepted
- **Context:** Lighthouse CI (`@lhci/cli`) bundles transitive dependencies (`tmp`, `uuid`) with known CVEs; no patched `@lhci/cli` release available at triage time
- **Decision:** Add npm `overrides` in `examples/web/package.json` forcing `tmp >= 0.2.6` and `uuid >= 11.1.1`; document in KB-007
- **Alternatives considered:** Dismiss Dependabot alert (rejected: hides real risk); remove Lighthouse CI job (rejected: loses performance gate)
- **Consequences:** Lockfile must be regenerated after override changes; overrides should be removed when `@lhci/cli` ships fixed dependencies

### 2026-06-13 — Ship all optional ecosystem modules (M3)
- **Status:** Accepted
- **Context:** Sprint M3 asked whether to ship Lightroom, Rust, and Go optional modules in the template maintainer repo
- **Decision:** Ship all three with Golden Path stubs, MODULE.md guides, and path-gated CI jobs (`lightroom`, `rust`, `go`) that skip when child repos remove the directories
- **Alternatives considered:** Lightroom-only (rejected: Rust/Go stubs are low-cost and popular); defer all optional modules (rejected: COMPLETED_TASKS M3 work already landed)
- **Consequences:** Template CI runs more jobs on `main`; child repos can delete unused `examples/` folders to skip jobs via `hashFiles` guards

