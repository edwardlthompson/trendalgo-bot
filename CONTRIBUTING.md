# Contributing — TrendAlgo Bot

Thank you for contributing to **TrendAlgo Bot** — a self-hosted, source-available crypto trading stack (Elastic License 2.0).

## Who contributes what

| Label | Contributor | Examples |
|-------|-------------|----------|
| `AGENT` | Cursor Agent | `src/trendalgo/`, tests, docs, CI |
| `HUMAN` | Founder | Approvals, credentials, VPS, attorney gates |
| `AUTO` | CI/scripts | Gates, Dependabot, legal compliance grep |

## Getting started

1. Read `docs/START_HERE.md`, `BUILD_PLAN.md` Sequential lane, and `docs/CURSOR_MODES.md`.
2. Copy `.env.example` → `.env` (never commit `.env`).
3. Run `bash scripts/apply-founder-defaults.sh`.
4. Follow Conventional Commits; run pre-commit before PR.

## Architecture rules

- Extend Freqtrade — do not fork (ADR-0001)
- Max 250 lines/view, 150 lines/logic file
- No auto-withdraw, Stripe, or custodial patterns (ADR-0008 — CI enforced)
- No community strategy imports (ADR-0009)

## Elastic License 2.0 + billing

Application code: Elastic License 2.0 per root `LICENSE` (ADR-0018). Free for your own trading; no hosted-service resale; do not strip billing or license-key protections. Performance license fee terms: see `docs/LICENSE_MODEL.md` and ADR-0005 (monetization shape).

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/).

## Template improvements

Use the **Template Improvement** issue template for feedback.

## Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

Includes repo hygiene checks (`scripts/check-repo-hygiene.sh`). See [`docs/REPO_HYGIENE.md`](docs/REPO_HYGIENE.md).

## Security triage

Maintainers run a weekly CVE triage pass per `docs/SECURITY_TRIAGE.md`. Review Dependabot alerts before each release.

## Release process (maintainers)

See `docs/MAINTAINING_THE_TEMPLATE.md` for the full semver release checklist.
