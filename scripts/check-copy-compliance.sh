#!/usr/bin/env bash
# Forbidden billing/marketing copy (R-025) — Sprint 10.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FORBIDDEN="we took your fee|auto-collect|auto collect|we collect your fees automatically"
if rg -i "$FORBIDDEN" "$ROOT/docs" "$ROOT/examples/web/src" "$ROOT/TERMS.md" 2>/dev/null; then
  echo "FAIL forbidden copy found"
  exit 1
fi
echo "OK copy compliance"
exit 0
