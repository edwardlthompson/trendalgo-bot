# Start Here

> **Read this file first** — whether you are a human or a Cursor agent.

## What is this?

**TrendAlgo Bot** — self-hosted crypto trading platform: native CCXT engine, LTS opportunity scanner, CoinStats-class portfolio, AI-recommended strategies, and performance-based licensing. See [`README.md`](../README.md) and [`docs/EXCHANGE_ROADMAP.md`](EXCHANGE_ROADMAP.md). Bootstrapped from `agent-project-bootstrap`.

For template-only usage, see upstream [agent-project-bootstrap](https://github.com/edwardlthompson/agent-project-bootstrap).

## Which repo mode are you in?

- **Child / product (this repo):** TrendAlgo Bot — Python + Web PWA. Read `docs/CURSOR_MODES.md`, then `AGENTS.md` + `BUILD_PLAN.md` Sequential. Template alignment: [`BOOTSTRAP_ALIGNMENT.md`](BOOTSTRAP_ALIGNMENT.md).
- **Bootstrap:** New project from **Use this template** → read `docs/CURSOR_MODES.md`, then `docs/INITIALIZATION_PROMPT.md`
- **Reference:** Existing project using this repo as rules reference → read `docs/CURSOR_MODES.md`, then `docs/FOR_AGENTS.md`

## How agents should work in this repo

1. Read this file → pick Cursor mode (`docs/CURSOR_MODES.md`) → open `BUILD_PLAN.md` **Sequential** first
2. Prefer local compute (`.cursor/rules/local-compute.mdc`) over Cloud Agents
3. After each `[AGENT]` feature step: `bash scripts/watch-agent-gates.sh --once --autofix`
4. Human/legal/go-live gates live in [`HUMAN_BACKLOG.md`](HUMAN_BACKLOG.md) / root pointer — never fake-approve hard gates
5. Conventional Commits; no push without `[HUMAN]` / `/push` / `/ship`

## Cursor modes (Plan / Agent / Debug / Ask)

See [`docs/CURSOR_MODES.md`](CURSOR_MODES.md) — pick the Cursor mode before editing code.

## Agent shortcuts

Type **`/`** in Cursor Agent chat for shortcut workflows. Start with **[docs/help/BATCH_COMMANDS.md](help/BATCH_COMMANDS.md)** — try `/verify` before merge or `/maintain` for weekly hygiene.

## Bootstrap Read Order

1. `README.md`
2. `docs/START_HERE.md`
3. `docs/CURSOR_MODES.md`
4. `docs/INITIALIZATION_PROMPT.md`
5. `AGENTS.md`
6. `BUILD_PLAN.md` Sequential lane
7. Active `modules/{stack}/MODULE.md` only
8. Active `examples/{stack}/` only
9. `docs/WEB_PROJECT_LAYOUT.md` when stack includes web (folder roles, GitHub Pages)
10. `docs/DESIGN_GUIDE.md` when stack includes web or Android UI (tokens, themes, i18n)
11. `docs/FEATURE_MODULES.md` when implementing Sprint 2+ incremental features (vertical slices)

## Reference Read Order

1. `docs/START_HERE.md`
2. `docs/CURSOR_MODES.md`
3. `docs/FOR_AGENTS.md`
4. `TEMPLATE_INDEX.json`
5. `AGENTS.md`
6. Matching `modules/{stack}/MODULE.md` only

## Do Not Read Yet

- Inactive `examples/` folders
- `KNOWLEDGE_BASE.md` — reference when debugging (KB-001–KB-008)
- `docs/MAINTAINING_THE_TEMPLATE.md` (maintainers only)

## BUILD_PLAN Labels

`AGENT` | `HUMAN` | `ADB` | `AUTO` — filter with `grep '\[AGENT\]' BUILD_PLAN.md`

**Status markers:** 🔲 open · ✅ done · ❌ blocked — emoji only (not `- [ ]` checkboxes). Applies to all repo checklists; see legend in `BUILD_PLAN.md`.

## Security

Enable Dependabot alerts on GitHub (Settings → Code security and analysis). Weekly CVE triage: `docs/SECURITY_TRIAGE.md`. Vulnerability reporting: `SECURITY.md`.

## Agent Prompts

**Bootstrap:** Read @docs/START_HERE.md, @docs/CURSOR_MODES.md, and @docs/INITIALIZATION_PROMPT.md. Pick Cursor mode per CURSOR_MODES. Follow Section 8. Use BUILD_PLAN Sequential lane.

**Reference:** Read @docs/CURSOR_MODES.md, @docs/FOR_AGENTS.md, and @TEMPLATE_INDEX.json. Pick Cursor mode per CURSOR_MODES. Apply matching rules. Do not copy examples/ wholesale.
