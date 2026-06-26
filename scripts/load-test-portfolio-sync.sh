#!/usr/bin/env bash
# CM-6 N-exchange ops validation — 9+ venues sync + trading status (< 30s dry-run).
# Usage: scripts/load-test-portfolio-sync.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export TRENDALGO_SYNC_STAGGER_SEC=0
if command -v uv >/dev/null 2>&1; then
  uv run python scripts/load-test-portfolio-sync.py
else
  PYTHONPATH=src python scripts/load-test-portfolio-sync.py
fi
