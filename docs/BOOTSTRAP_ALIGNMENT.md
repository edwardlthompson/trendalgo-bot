# Bootstrap Alignment - TrendAlgo Bot

> Gap analysis and migration notes for aligning this child repo with
> [agent-project-bootstrap](https://github.com/edwardlthompson/agent-project-bootstrap) **v1.10.0**.
> First written 2026-07-21 (v0.15.1). Updated 2026-08-14; catch-up 2026-10-08 to v1.9.0; catch-up 2026-10-16 to v1.10.0. Update only at alignment milestones.

## Summary

TrendAlgo is a live Python + Web product. Alignment is **additive and surgical**.
Product code under `src/trendalgo/` and `examples/web/` is preserved.
Product `.template-version` tracks release-please (currently **0.6.2**).
Upstream FOSS surface is recorded as `upstream_aligned_version` in `.template-update.json`.

| Item | Local | Upstream v1.10.0 | Action |
|------|-------|------------------|--------|
| `.template-version` | 0.6.2 (product) | 1.10.0 (template) | Keep product version |
| `upstream_aligned_version` | 1.9.0 → **1.10.0** | — | Bumped after FOSS surface copy |
| Stack | Python + Web (pruned) | Multi-example | Keep python+web only |
| CI matrix | Product-tuned | Full multi-stack | **Keep product CI** (H-BA-9 for pin cherry-pick) |
| Skills.sh / TDD | Recipes in repo; marketplace install is human | `docs/SKILLS_RECIPES.md` | H-BA-19 |
| Branding kit | Preview mode | Handshake logos + `/brand` | Preview only; live README kept |
## Already matched (since 0.15.1)

- Agent routers, batch commands, emoji BUILD_PLAN, `HUMAN_BACKLOG` pointer
- FOSS Cursor hooks, skills, 3 agents, local-compute, worktrees, permissions
- Security surface + product CI (encoding, feature-gate, CodeQL, Scorecard, Dependabot)
- High npm pins: `js-yaml >=4.3.0`, `brace-expansion >=1.1.16 <2`

## Adopted 2026-10-16 (1.9.0 → 1.10.0)

- `/shape` + `/brand` commands, `shape-idea` skill, help docs
- `docs/SKILLS_RECIPES.md`, `docs/MCP_RECIPES.md`, specs, `mcp.web.example`
- Coverage summarize scripts + related tests
- Preferences / Coverage / Directory Rules docs; product-brief-anti-amnesia feature stub
- Branding handshake assets under `branding/template/` (`product.json` stays `mode: template`)
- Cline workflows `shape` / `build`; batch-command registry refresh
- HUMAN_BACKLOG **H-BA-19/20/9/12** install steps for skills / rules / MCP

## Adopted 2026-08-14 (0.15.1 → 0.17.0) and 2026-10-08 (→ 1.9.0)

- Plan `### Critique`, Codex opt-in, expanded `/prerelease` / `/ship`
- Branding kit in template/preview mode
- Canon/Mixed catch-up to v1.9.0 (commands, scripts, schemas, adapters)

## Intentionally skipped

- Commercial Cursor / Bugbot / COMMERCIAL_GOLDEN_PATH adoption
- Upstream multi-stack CI jobs and inactive examples
- `generate-project-readme.py` **product mode** (would overwrite the live self-hosted README)
- Blind overwrite of `INITIALIZATION_PROMPT.md`, product `BUILD_PLAN.md` rows, or app code
- CI workflow merge until **H-BA-9** reviews CodeQL `@v4` cherry-pick
- Golden Path feature ports (GP-1…GP-8) — separate `/feature` work

## Conflicts resolved

| Conflict | Resolution |
|----------|------------|
| File limits vs upstream 300/150 | Keep TrendAlgo `check-file-limits` (250 / 300 / 150) |
| HUMAN_BACKLOG location | Root stub → `docs/HUMAN_BACKLOG.md` |
| Template version | Product 0.6.2; `upstream_aligned_version` 1.10.0 |
| TEMPLATE_INDEX version field | Keep product `0.6.2`; merge upstream `files` inventory |
## Recommended stack

**Python + Web PWA** (already active). Do not re-add pruned modules/examples.

## Risk areas

1. Codex CLI / `OPENAI_API_KEY` — `/prerelease` must skip (exit 3), never block release
2. CI required-check names — not changed until H-BA-9
3. Marketplace skills are user-local — not vendored into git
4. Secrets — never commit `.env` or live `.cursor/mcp.json`
5. Do not set `.template-version` to 1.10.0

## Migration notes (human)

### Done by AGENT

- 2026-10-16: Canon/Mixed catch-up to upstream **v1.10.0** (shape/brand, skills+MCP recipes, coverage tools, branding handshake, docs); product CI workflows **not** modified; `.template-version` remains 0.6.2
- 2026-10-08: Canon/Mixed catch-up to upstream **v1.9.0**
- 2026-07-21 / 2026-08-14: earlier FOSS surface + Codex / branding

### Still needs HUMAN

- **H-BA-19** install TDD + companion skills ([`docs/HUMAN_BACKLOG.md`](HUMAN_BACKLOG.md))
- **H-BA-9** CI pin review; **H-BA-12** Sacred `AGENTS.md` review; **R-BA.H1** this file
- Attorney review H-006 / R-Audit-8.9
- Optional: Codex workflow secret; GitHub Pages

### Do not

- Force-push or rewrite history for alignment
- Import inactive-stack CI jobs
- Overwrite product business logic or switch `branding/product.json` to `"mode": "product"` without `[HUMAN]` approval
