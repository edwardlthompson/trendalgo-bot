# skills.sh recipes (curated)

Source catalog: [skills.sh](https://www.skills.sh/). **Do not vendor the whole leaderboard.** Prefer MIT-compatible skills; ask the human before adding.

## Recommended for this template

| Skill | Why | Install note |
|-------|-----|--------------|
| find-skills | Discover more later | vercel-labs/skills |
| tdd / test-driven-development | Matches repo test-first law | mattpocock or obra/superpowers |
| grill-me / grill-with-docs | Complements `/shape` | mattpocock/skills |
| implement-spec / writing-plans | Spec → build after `/shape` | mattpocock / obra |
| handoff | Complements `/compact` `/resume` | mattpocock/skills |
| verification-before-completion | Before marking BUILD_PLAN ✅ | obra/superpowers |
| frontend-design / web-design-guidelines | Web Golden Path | anthropics / vercel-labs |
| setup-pre-commit | Matches pre-commit gates | mattpocock/skills |
| caveman-commit | Small frequent commits | juliusbrussee/caveman |

## Project skills shipped here

See [`.cursor/skills/`](../.cursor/skills/) (gates, feature slice, ux-review, …).

**Custom Modes are optional.** Preferred: wire skills.sh installs into slash commands (see `.cursor/commands/{shape,feature,build,plan,verify,compact,resume,ux-review,setup,coach}.md`). Agents read `.agents/skills/` when those commands run — no Alt+Enter mode required.

| skills.sh skill | Wired into |
|-----------------|------------|
| `grill-me` / `grill-with-docs` / `implement-spec` | `/shape`, `/plan` |
| `tdd` | `/feature`, `/build` |
| `verification-before-completion` | `/build`, `/verify` |
| `handoff` | `/compact`, `/resume` |
| `frontend-design` / `web-design-guidelines` | `/ux-review` |
| `setup-pre-commit` | `/setup` |
| `find-skills` | `/coach` (only if capability gap) |

Optional: still pin as Custom Modes per [`CURSOR_INTEGRATIONS.md`](CURSOR_INTEGRATIONS.md) if you prefer Alt+Enter shortcuts.

## Out of FOSS default

Feishu/Lark packs, Twitter automation, Azure-only packs (unless commercial tier), unbounded image/video generators.
