# Bootstrap Alignment - TrendAlgo Bot

> Gap analysis and migration notes for aligning this child repo with
> [agent-project-bootstrap](https://github.com/edwardlthompson/agent-project-bootstrap) **v0.17.0**.
> First written 2026-07-21 (v0.15.1). Updated 2026-08-14. Update only at alignment milestones.

## Summary

TrendAlgo is a live Python + Web product. Alignment is **additive and surgical**.
Product code under `src/trendalgo/` and `examples/web/` is preserved.
Product `.template-version` tracks release-please (currently **0.5.1**).
Upstream FOSS surface is recorded as `upstream_aligned_version` in `.template-update.json`.

| Item | Local | Upstream v0.17.0 | Action |
|------|-------|------------------|--------|
| `.template-version` | 0.5.1 (product) | 0.17.0 (template) | Keep product version |
| `upstream_aligned_version` | 0.15.1 → **0.17.0** | — | Bump after FOSS surface green |
| Stack | Python + Web (pruned) | Multi-example | Keep python+web only |
| CI matrix | Product-tuned | Full multi-stack | **Keep product CI** |
| Codex / expanded `/prerelease` | Missing (pre-0.16) | Present | Adopt FOSS opt-in |
| Branding kit | Adopted (`mode: template`) | `branding/` + generator | Preview only; live README kept |

## Already matched (since 0.15.1)

- Agent routers, batch commands, emoji BUILD_PLAN, `HUMAN_BACKLOG` pointer
- FOSS Cursor hooks, 7 original skills, 3 agents, local-compute, worktrees, permissions
- Security surface + product CI (encoding, feature-gate, CodeQL, Scorecard, Dependabot)
- High npm pins: `js-yaml >=4.3.0`, `brace-expansion >=1.1.16 <2`

## Adopted 2026-08-14 (0.15.1 → 0.17.0)

- Plan `### Critique` as Issue → Resolution (`core-directives`, `CURSOR_MODES`, `/plan`, `AGENTS.md`)
- Opt-in Codex: `/codex-review`, skill, `docs/CODEX_REVIEW.md`, `.github/codex/*`, workflow **example** (not a required check)
- Expanded `/prerelease` / `/ship`: autofix → optional Codex → hard gate
- Scripts: `prerelease-autofix`, `apply-suggested-gate-fixes`, `run-codex-review`, `codex-findings-to-markdown.py`
- `feature-autofix.sh` runs ruff on root `src/` + `scripts/` (TrendAlgo has no `examples/python`)
- npm overrides: `undici >=7.29.0`, `ip-address >=10.3.1`, `nanoid >=3.3.17`, `postcss >=8.5.23`; `js-yaml >=5.2.2` (lhci already on 5.x); `brace-expansion >=1.1.18 <2`
- Branding kit: `branding/` + `scripts/generate-project-readme.py`; `product.json` seeded for TrendAlgo; `"mode": "template"` so the generator writes `branding/generated/README.preview.md` only

## Intentionally skipped

- Commercial Cursor / Bugbot
- Upstream multi-stack CI jobs and inactive examples
- `generate-project-readme.py` **product mode** (would overwrite the live self-hosted README)
- Biome / fast-check / TypeScript 7 on `examples/web`
- `js-yaml` 5.x and `brace-expansion` 5.x (5.x brace pin broke Vitest)
- Blind overwrite of `INITIALIZATION_PROMPT.md`, product `BUILD_PLAN.md`, or app code

## Conflicts resolved

| Conflict | Resolution |
|----------|------------|
| File limits vs upstream 300/150 | Keep TrendAlgo `check-file-limits` (250 / 300 / 150) |
| HUMAN_BACKLOG location | Root stub → `docs/HUMAN_BACKLOG.md` |
| Template version | Product 0.5.1; `upstream_aligned_version` 0.17.0 |
| npm High overrides | Adopt undici/ip-address/nanoid; keep 4.x/1.x yaml/brace pins |

## Recommended stack

**Python + Web PWA** (already active). Do not re-add pruned modules/examples.

## Risk areas

1. Codex CLI / `OPENAI_API_KEY` — `/prerelease` must skip (exit 3), never block release
2. CI required-check names — not changed
3. `validate-bootstrap` new required files — `docs/CODEX_REVIEW.md` + `/codex-review` indexed together
4. Secrets — never commit `.env` or API keys
5. Do not set `.template-version` to 0.17.0

## Migration notes (human)

### Done by AGENT

- 2026-07-21: FOSS Cursor surface to v0.15.1
- 2026-08-14: critique hardening, Codex opt-in, expanded `/prerelease`, extra npm overrides
- 2026-08-14: branding kit + pitch README generator in **template** mode (preview only)
- CI workflows: **not modified** (product matrix retained)

### Still needs HUMAN

- R-BA.H1 review this file
- Attorney review H-006 / R-Audit-8.9
- GitHub Pages enable if desired
- Optional: copy `.github/workflow-examples/codex-review.yml` → workflows + set `OPENAI_API_KEY` secret

### Do not

- Force-push or rewrite history for alignment
- Import inactive-stack CI jobs
- Overwrite product business logic or switch `branding/product.json` to `"mode": "product"` without `[HUMAN]` approval
