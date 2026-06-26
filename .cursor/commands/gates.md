# Local validation gates

Run Sprint 0 / pre-push validation (Git Bash on Windows):

```bash
bash scripts/validate-bootstrap.sh --quick
bash scripts/feature-gate.sh --stack multi
bash scripts/check-repo-hygiene.sh
```

## Founder gates (TrendAlgo)

```bash
bash scripts/apply-founder-defaults.sh
bash scripts/check-human-backlog.sh --sprint 0
bash scripts/check-risk-mitigations.sh --sprint 0
bash scripts/check-legal-compliance.sh
bash scripts/founder-gate.sh status
```

Pre-Sprint-1: `bash scripts/founder-gate.sh approve-bundle pre-sprint-1`

Sprint 0 sign-off bundle: `bash scripts/check-sprint0-founder-gates.sh` (or `--strict` when scaffold complete).

Founder preflight in agent gate loop: `bash scripts/watch-agent-gates.sh --once --founder`

Report pass/fail per script. Fix failures in scope before marking BUILD_PLAN items complete.

When the sprint is fully ✅, run @.cursor/commands/cleanup.md before ending the session.

Begin now.
