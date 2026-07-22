# Agent Router

1. **First read:** `docs/START_HERE.md`
2. **Cursor modes:** `docs/CURSOR_MODES.md` (Ask / Plan / Agent / Debug routing)
3. **Bootstrap mode:** `docs/INITIALIZATION_PROMPT.md`
4. **Reference mode:** `docs/FOR_AGENTS.md` + `TEMPLATE_INDEX.json`
5. **Task board:** `BUILD_PLAN.md` (Sequential before Parallel) — status: 🔲 open · ✅ done · ❌ blocked
6. **Parallel dispatch:** parallel-first when Sequential clear; `/build` automates HUMAN/ADB first, backlogs failures to `HUMAN_BACKLOG.md` / `docs/HUMAN_BACKLOG.md`, never halts on human labels — `scripts/build-sprint-status.sh --lane child`
7. **Living memory:** update `AGENT_MEMORY.md` only at milestone boundaries
8. **Alignment:** `docs/BOOTSTRAP_ALIGNMENT.md` (upstream FOSS surface v0.15.1; product `.template-version` stays on release-please; CI non-parity)

> Legacy `.cursorrules` is deprecated. Use `.cursor/rules/*.mdc` and this file instead.

## Architecture Constraints

- Pure FOSS under MIT license; no proprietary closed-source SDKs in production path
- Max 250 lines per view file (web UI adapters: 300 per `check-file-limits.sh`), 150 lines per logic file
- Strict type safety and runtime validation at all data boundaries
- Core business logic decoupled from layout framework (MVVM / Clean / Hexagonal)
- Opt-in only telemetry; GDPR/CCPA compliant

## Coding Style

- Conventional Commits for all changes
- Small, modular functions; keep files within token-optimal size
- Read-before-write: inspect types/interfaces via `@filename` before editing
- Cursor mode routing per `docs/CURSOR_MODES.md`; Plan for non-trivial tasks with `### Critique`

## Session Protocol

- On session start: read `START_HERE.md`, pick mode via `docs/CURSOR_MODES.md`, then `BUILD_PLAN.md` Sequential lane
- On milestone end: update `AGENT_MEMORY.md`, append to `DECISION_LOG.md` or `docs/adr/`
- On 3-strike failure: halt and escalate to human
- On context bloat: write `.cursor-session-state`, ask human to clear chat
- Sprint 2+ features: after each AGENT step run `scripts/watch-agent-gates.sh --once --autofix` (see `docs/FEATURE_MODULES.md`)
- Destructive operations require `[HUMAN]` approval (see `.cursor/rules/destructive-ops.mdc`)
- Repo hygiene: track source only; run `scripts/check-repo-hygiene.sh` before push (see `docs/REPO_HYGIENE.md`)
- Log significant agent actions in `DECISION_LOG.md` at milestone boundaries

## Module Activation

Activate only the modules matching this product stack:

- ✅ Python — `modules/python/MODULE.md` · `src/trendalgo/`
- ✅ Web / PWA — `modules/web/MODULE.md` · `examples/web/`

Do not re-add pruned Android/Node/Rust/Go/Lightroom modules unless the human explicitly expands scope.

## Cursor FOSS integrations

Shipped (see `docs/CURSOR_INTEGRATIONS.md`):

- **Hooks** — `.cursor/hooks.json` enforces destructive-ops + UTF-8 (fail-open; `/push` session override)
- **Skills (7)** — `.cursor/skills/` progressive-load companions for `/gates`, `/scope`, `/fix`, hygiene, Sprint 0, features, canvas status
- **Subagents (3)** — `.cursor/agents/` verifier, gate-fixer, explorer
- **Local compute first** — `.cursor/rules/local-compute.mdc`: This Computer + parallel Task/worktrees/`/best-of-n` before Cloud; multi-core bootstrap checks
- **Worktrees** — `.cursor/worktrees.json` + fail-soft OS setup (`/worktree`, `/best-of-n`)
- **Auto-review** — `.cursor/permissions.json` dual layer with hooks

Validate: `python3 scripts/agent-run.py check-cursor-hooks -- --smoke`, `python3 scripts/agent-run.py check-cursor-integrations -- --tier foss`

Commercial Cursor integrations are out of scope for this FOSS product (`distribution_tier: foss`).

## Ecosystem-Specific Rules

- **Web/PWA:** Offline-first service workers; Lighthouse budget gates
- **Python:** Strict typing (mypy), ruff lint/format, locked dependencies (uv)
