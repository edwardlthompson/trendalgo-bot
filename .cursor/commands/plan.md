# Feature or ADR plan (Plan Mode)

Read `docs/CURSOR_MODES.md` + active BUILD_PLAN row.

> Skills (when present under `.agents/skills/`): use `implement-spec` to turn an approved `/shape` spec into a concrete plan + BUILD_PLAN row; keep `### Critique` Issue→Resolution.

- From `/build`: decide internally (Critique + Parallelization), then execute — no user pause.
- Standalone: trivial → Agent; else present single approach + resolved `### Critique` before coding.

Critique = Issue→Resolution table (null/empty, timeouts, races, exceptions; UI: empty/error/loading, focus, tokens, primary, i18n). No open risks. UI law: `docs/ux-ui-guidelines.md`.

Begin now.
