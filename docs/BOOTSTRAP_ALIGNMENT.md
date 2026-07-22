# Bootstrap Alignment - TrendAlgo Bot

> Gap analysis and migration notes for aligning this child repo with
> [agent-project-bootstrap](https://github.com/edwardlthompson/agent-project-bootstrap) **v0.15.1**.
> Written 2026-07-21. Update only at alignment milestones.

## Summary

TrendAlgo was already bootstrapped at template **0.5.0** with a mature Python + Web product.
The gap vs upstream **0.15.1** is staleness of agent/Cursor FOSS tooling and scripts - not missing product entrypoints.
Alignment is **additive and surgical**. Product code under `src/trendalgo/` and `examples/web/` is preserved.

| Item | Local (pre-align) | Upstream | Action |
|------|-------------------|----------|--------|
| `.template-version` | 0.5.0 (product / release-please) | 0.15.1 (template) | **Keep product version**; record `upstream_aligned_version` in `.template-update.json` |
| Stack | Python + Web (pruned) | Multi-example | Keep python+web only |
| Agent routers | Present | Parallel dispatch + Cursor FOSS section | Refresh |
| `.cursor/rules` | 13 FOSS | + local-compute | Add FOSS-only |
| Hooks / skills / agents | Missing | Present | Adopt FOSS |
| CI matrix | Product-tuned | Full multi-stack | **Keep product CI** (intentional non-parity) |
| HUMAN_BACKLOG | `docs/HUMAN_BACKLOG.md` | Root file | Root pointer to docs |
| BUILD_PLAN | Product R-Audit-8 | Template sprints | Add alignment lane only |

## Already matched

- `AGENTS.md`, `docs/START_HERE.md`, `docs/CURSOR_MODES.md`, `docs/FOR_AGENTS.md`
- Batch commands (26) + registry + help cheat sheet
- Memory: `AGENT_MEMORY.md`, `DECISION_LOG.md`, `KNOWLEDGE_BASE.md`, `COMPLETED_TASKS.md`
- Security: `SECURITY.md`, `docs/SECURITY_TRIAGE.md`, `docs/THREAT_MODEL.md`, `docs/PRIVACY.md`
- Hygiene/gates scripts and core workflows (encoding, feature-gate, validate-bootstrap, CodeQL, Scorecard, Dependabot)
- Stack selection: `.cursor/stack-selection.json` = web + python
- Emoji BUILD_PLAN status markers; no legacy `.cursorrules`

## Adopted in this alignment

- `.cursor/rules/local-compute.mdc`
- FOSS Cursor stack: hooks, 7 skills, 3 agents, `permissions.json`, `worktrees.json`, setup-worktree scripts
- Docs: `CURSOR_INTEGRATIONS.md`, `CURSOR_CLI.md`, `CURSOR_FEATURE_RADAR.md`, `CURSOR_FEATURE_REGISTRY.json`, `FILE_SIZE_GUIDE.md`, help Cursor features
- Scripts: `agent-run.py`, parallel/backlog helpers, cursor-hooks/integrations checkers, related lib modules
- Root `HUMAN_BACKLOG.md` pointer + example
- Upstream FOSS surface aligned to **v0.15.1** via `.template-update.json` -> `upstream_aligned_version` (product `.template-version` stays on release-please **0.5.0**)
- CI matrix intentional non-parity (python+web only)

## Intentionally skipped

- Commercial-only: `commercial-compliance.mdc`, commercial Automations/Bugbot/mcp examples
- Upstream multi-stack CI jobs (android / node / rust / go / lightroom)
- Blind overwrite of `docs/INITIALIZATION_PROMPT.md`, product `BUILD_PLAN.md`, or `examples/`
- Mass conversion of historical `- [ ]` checklists in product docs
- Setting `.template-version` to upstream 0.15.1 (would break release-please product sync)

## Conflicts resolved

| Conflict | Resolution |
|----------|------------|
| Freqtrade in INIT prompt | Corrected to native CCXT (ADR-0010) |
| File limits vs upstream 300/150 | Keep TrendAlgo `check-file-limits` (250 views / 300 web adapters / 150 logic) |
| HUMAN_BACKLOG location | Root stub -> canonical `docs/HUMAN_BACKLOG.md` |
| Template version claim | `.template-version` = product 0.5.0; `upstream_aligned_version` = 0.15.1; product CI matrix retained |

## Recommended stack

**Python + Web PWA** (already active). Do not re-add pruned modules/examples.

## Risk areas

1. Cursor hooks shell-deny - FOSS fail-open; validate with `check-cursor-hooks`
2. CI required-check renames - avoided; no workflow matrix rewrite
3. `validate-bootstrap` new required files - index + scripts updated together
4. Secrets - merge `.env.example` only; never touch `.env`
5. Version files - do not set `.template-version` to upstream 0.15.1 (breaks release-please sync); use `upstream_aligned_version` instead

## Migration notes (human)

### Done by AGENT

- Gap analysis (this file)
- FOSS Cursor integrations + local-compute
- Agent surface refresh + INIT prompt Freqtrade fix
- Missing gate/parallel scripts + `upstream_aligned_version: 0.15.1` (product version unchanged)
- Validation: `bash scripts/validate-bootstrap.sh --quick` passed (2026-07-21)
- CI workflows: **not modified** (product matrix retained; no inactive-stack jobs imported)

### Still needs HUMAN

- Attorney review H-006 / R-Audit-8.9 (legal packet)
- GitHub Pages enable if public docs hosting desired
- Review branch protection if any workflow pins change later
- Weekly Dependabot / security triage cadence (`docs/SECURITY_TRIAGE.md`)

### Do not

- Force-push or rewrite history for alignment
- Import inactive-stack CI jobs from upstream
- Overwrite product business logic for template parity
