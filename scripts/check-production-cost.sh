#!/usr/bin/env bash
# Production cost budget check (H-012 / H-027) — runs CM-6 load test first (S17).
# Usage: scripts/check-production-cost.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BUDGET="${VPS_MONTHLY_USD:-10}"
COST="${VPS_MONTHLY_USD_ACTUAL:-}"

echo "=== check-production-cost (budget <= $BUDGET USD/mo) ==="

if bash scripts/load-test-portfolio-sync.sh; then
  echo "OK   CM-6 portfolio load test passed"
else
  echo "FAIL CM-6 portfolio load test"
  exit 1
fi

if [ -n "$COST" ]; then
  if awk -v c="$COST" -v b="$BUDGET" 'BEGIN { exit (c <= b) ? 0 : 1 }'; then
    echo "OK   VPS_MONTHLY_USD_ACTUAL=$COST"
    exit 0
  fi
  echo "FAIL VPS_MONTHLY_USD_ACTUAL=$COST exceeds budget $BUDGET"
  exit 1
fi

if [ -f config/founder.defaults.json ]; then
  echo "OK   set VPS_MONTHLY_USD_ACTUAL after first invoice; budget in founder.defaults.json"
  exit 0
fi
echo "SCHEDULED apply founder defaults first"
exit 0
