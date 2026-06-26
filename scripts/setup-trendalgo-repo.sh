#!/usr/bin/env bash
# TrendAlgo repo bootstrap (H-001).
# Usage: scripts/setup-trendalgo-repo.sh [owner/repo]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
REPO="${1:-edwardlthompson/trendalgo-bot}"

echo "=== setup-trendalgo-repo ($REPO) ==="

if ! command -v gh >/dev/null 2>&1; then
  echo "FAIL gh CLI required — install https://cli.github.com/"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "FAIL gh not authenticated — run: gh auth login"
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "Creating repo and origin..."
  gh repo create "$REPO" --public --source=. --remote=origin \
    --description "Self-hosted crypto algo bot: Freqtrade, LTS Scanner, portfolio tracker, AI-recommended strategies. AGPL." \
    || gh repo set-default "$REPO" 2>/dev/null || true
else
  echo "OK   origin remote exists"
fi

if [ -f scripts/setup-github-repo.sh ]; then
  bash scripts/setup-github-repo.sh "$REPO" || true
fi

python3 scripts/founder_gate.py preflight H-001 || true
echo "Next: bash scripts/founder-gate.sh approve H-001"
