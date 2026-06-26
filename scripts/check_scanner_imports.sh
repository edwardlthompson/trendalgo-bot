#!/usr/bin/env bash
# Forbidden import boundary for Opportunity Scanner (LTS_INTEGRATION.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCANNER_DIR="$ROOT/src/trendalgo/scanner"
FAIL=0

for pattern in "linear_trend_spotter" "from main import" "import main"; do
  if grep -rE "$pattern" "$SCANNER_DIR" --include="*.py" 2>/dev/null; then
    echo "FAIL: forbidden pattern '$pattern' in scanner"
    FAIL=1
  fi
done

if grep -rE "notifications" "$SCANNER_DIR" --include="*.py" 2>/dev/null | grep -v "scanner/alerts"; then
  echo "FAIL: direct LTS notifications import in scanner"
  FAIL=1
fi

if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
echo "check_scanner_imports: PASS"
