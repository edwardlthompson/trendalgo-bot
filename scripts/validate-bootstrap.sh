#!/usr/bin/env bash
# Verify required bootstrap artifacts exist and pass delegated checks
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

QUICK=false
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=true ;;
  esac
done

REQUIRED=(
  README.md
  LICENSE
  CONTRIBUTING.md
  SECURITY.md
  CODE_OF_CONDUCT.md
  BUILD_PLAN.md
  AGENTS.md
  AGENT_MEMORY.md
  HUMAN_BACKLOG.md
  docs/START_HERE.md
  docs/CURSOR_MODES.md
  docs/INITIALIZATION_PROMPT.md
  docs/BOOTSTRAP_ALIGNMENT.md
  .cursor/rules/cursor-modes.mdc
  .cursor/rules/local-compute.mdc
  docs/DESIGN_GUIDE.md
  docs/WEB_PROJECT_LAYOUT.md
  docs/SECURITY_TRIAGE.md
  docs/THREAT_MODEL.md
  docs/PRIVACY.md
  docs/RUNBOOK.md
  docs/FEATURE_MODULES.md
  docs/CURSOR_INTEGRATIONS.md
  .github/dependabot.yml
  .github/CODEOWNERS
  THIRD_PARTY_LICENSES.md
  .env.example
  design-tokens/design-tokens.json
  docs/help/BATCH_COMMANDS.md
  docs/BATCH_COMMANDS.md
  .cursor/rules/batch-commands.mdc
  CODE_REVIEW.md.example
  RELEASE_NOTES.md.example
)

BATCH_COMMANDS=(
  audit cleanup debug gates triage dependabot push prerelease regress
  feature fix init prune ci docs upgrade setup plan restore compact scope
  bootstrap verify build ship maintain
)

for cmd in "${BATCH_COMMANDS[@]}"; do
  REQUIRED+=(".cursor/commands/${cmd}.md")
done

ERRORS=0

run_check() {
  if ! "$@"; then
    ERRORS=$((ERRORS + 1))
  fi
}

for f in "${REQUIRED[@]}"; do
  if [ ! -e "$f" ]; then
    echo "MISSING: $f"
    ERRORS=$((ERRORS + 1))
  fi
done

if [ -f LICENSE ] && [ ! -s LICENSE ]; then
  echo "EMPTY: LICENSE"
  ERRORS=$((ERRORS + 1))
fi

if [ -f examples/web/package.json ] && [ ! -f examples/web/package-lock.json ]; then
  echo "MISSING: examples/web/package-lock.json (required when web example present)"
  ERRORS=$((ERRORS + 1))
fi

if [ -f examples/node/package.json ] && [ ! -f examples/node/package-lock.json ]; then
  echo "MISSING: examples/node/package-lock.json (required when node example present)"
  ERRORS=$((ERRORS + 1))
fi

if [ -f pyproject.toml ] && grep -q 'name = "trendalgo-bot"' pyproject.toml && [ ! -f uv.lock ]; then
  echo "MISSING: uv.lock (required for trendalgo-bot root Python project)"
  ERRORS=$((ERRORS + 1))
fi

if [ -f examples/python/pyproject.toml ] && [ ! -f examples/python/uv.lock ]; then
  echo "MISSING: examples/python/uv.lock (required when python example present)"
  ERRORS=$((ERRORS + 1))
fi

run_check bash scripts/check-python-pytest-workflow.sh

if ! grep -q '\[AGENT\]' BUILD_PLAN.md && ! grep -q '\[HUMAN\]' BUILD_PLAN.md; then
  echo "MISSING: BUILD_PLAN.md owner labels"
  ERRORS=$((ERRORS + 1))
fi

# Writes first (must stay sequential)
run_check bash scripts/sync-exemplar-config.sh

# Independent read-only checks — use local CPU (BOOTSTRAP_CHECK_JOBS overrides)
if ! python3 scripts/lib/run_checks_parallel.py \
  check-file-encoding.sh \
  check-design-cohesion.sh \
  check-markdown-tables.sh \
  check-changelog-unreleased.sh \
  check-repo-hygiene.sh \
  check-batch-commands.sh \
  check-cursor-hooks.sh \
  check-build-plan-parallel.sh \
  check-template-version-sync.sh \
  validate-template-index.sh
then
  ERRORS=$((ERRORS + 1))
fi

TIER="foss"
if [ -f .cursor/stack-selection.json ]; then
  TIER="$(python3 -c "import json;print(json.load(open('.cursor/stack-selection.json')).get('distribution_tier','foss'))" 2>/dev/null || echo foss)"
fi
# Writes manifest — before integrations check
python3 scripts/sync-cursor-features.py --root "$ROOT" --tier "$TIER"
run_check bash scripts/check-cursor-integrations.sh --tier "$TIER"

if [ "$QUICK" = false ]; then
  run_check bash scripts/validate-workflow-actions.sh
fi

# TrendAlgo product gates (keep after template FOSS checks)
if [ -f docs/risk-catalog.json ]; then
  run_check python3 scripts/check_risk_mitigations.py --sprint 0
  if [ -f scripts/check-sprint0-founder-gates.sh ]; then
    if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
      echo "SKIP: check-sprint0-founder-gates (CI — human gates deferred to founder_gate.py)"
    elif ! command -v gh >/dev/null 2>&1; then
      # Git Bash on Windows often lacks gh on PATH even when GitHub CLI is installed.
      echo "SKIP: check-sprint0-founder-gates (gh not on PATH — run: python scripts/founder_gate.py status)"
    else
      run_check bash scripts/check-sprint0-founder-gates.sh
    fi
  fi
fi

if [ "$ERRORS" -gt 0 ]; then
  echo "$ERRORS bootstrap check(s) failed"
  exit 1
fi

if [ "$QUICK" = true ]; then
  echo "Bootstrap validation passed (--quick: skipped validate-workflow-actions)"
else
  echo "Bootstrap validation passed"
fi
