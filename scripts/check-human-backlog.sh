#!/usr/bin/env bash
# AUTO preflight for HUMAN backlog items.
# Usage: scripts/check-human-backlog.sh [--sprint N] [--strict]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SPRINT=""
STRICT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --sprint) SPRINT="$2"; shift 2 ;;
    --strict) STRICT="--strict"; shift ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

echo "=== check-human-backlog ==="
if [ -n "$SPRINT" ]; then
  exec python3 scripts/founder_gate.py preflight-sprint --sprint "$SPRINT" $STRICT
fi

# Default: sprint 0 preflights
exec python3 scripts/founder_gate.py preflight-sprint --sprint 0 $STRICT
