#!/usr/bin/env bash
# Sprint 0 founder + risk gates (non-strict by default).
# Usage: scripts/check-sprint0-founder-gates.sh [--strict]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STRICT=""
[ "${1:-}" = "--strict" ] && STRICT="--strict"

echo "=== check-sprint0-founder-gates ==="
ERR=0

run_py() {
  if ! python3 "$@"; then
    ERR=1
  fi
}

[ -f docs/risk-catalog.json ] || { echo "FAIL missing docs/risk-catalog.json"; exit 1; }
[ -f scripts/founder_gate.py ] || { echo "FAIL missing scripts/founder_gate.py"; exit 1; }

run_py scripts/check_risk_mitigations.py --sprint 0 $STRICT
run_py scripts/founder_gate.py preflight-sprint --sprint 0 $STRICT

if command -v bash >/dev/null 2>&1; then
  bash scripts/check-legal-compliance.sh || ERR=1
else
  python3 -c "
import subprocess, sys
from pathlib import Path
root = Path('.')
# minimal ADR-0009 check
adr = root / 'docs/adr/0009-ai-recommended-strategies.md'
sys.exit(0 if adr.exists() else 1)
" || ERR=1
fi

exit $ERR
