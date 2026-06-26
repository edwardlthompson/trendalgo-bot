#!/usr/bin/env bash
# Sprint scope preflight — priority stack order.
# Usage: scripts/sprint-preflight.sh --sprint N
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SPRINT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sprint) SPRINT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

if [ -z "$SPRINT" ]; then
  echo "Usage: scripts/sprint-preflight.sh --sprint N"
  exit 1
fi

echo "=== sprint-preflight (Sprint $SPRINT) ==="
bash scripts/check-human-backlog.sh --sprint "$SPRINT" || true
bash scripts/check-risk-mitigations.sh --sprint "$SPRINT" || true
echo "Review BUILD_PLAN Sprint $SPRINT scope; then: bash scripts/founder-gate.sh approve H-xxx"
