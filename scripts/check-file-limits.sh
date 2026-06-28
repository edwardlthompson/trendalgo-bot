#!/usr/bin/env bash
# Enforce file line limits aligned with FEATURE_MODULES:
#   view adapters (UI/DOM): VIEW_LIMIT (web dashboard/bots/charts/components)
#   static data catalogs:   DATA_LIMIT
#   pure logic (py/ts/kt):  LOGIC_LIMIT
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VIEW_LIMIT=300
DATA_LIMIT=300
LOGIC_LIMIT=150
ERRORS=0

# Web TS paths that are view adapters (DOM + wiring), not pure logic.
WEB_VIEW_PATHS=(
  "*/examples/web/src/components/*.ts"
  "*/examples/web/src/dashboard/*.ts"
  "*/examples/web/src/bots/*.ts"
  "*/examples/web/src/charts/*.ts"
  "*/examples/web/src/backtest/*.ts"
  "*/examples/web/src/ohlcv/*.ts"
)

check_files() {
  local label="$1"
  local limit="$2"
  while IFS= read -r -d '' file; do
    lines=$(wc -l < "$file" | tr -d ' ')
    if [ "$lines" -gt "$limit" ]; then
      echo "FAIL [$label] $file: $lines lines (max $limit)"
      ERRORS=$((ERRORS + 1))
    fi
  done
}

build_web_view_find() {
  local expr=()
  for p in "${WEB_VIEW_PATHS[@]}"; do
    expr+=(-o -path "$p")
  done
  find "$ROOT" -type f \( \
    -name "*.tsx" -o -name "*.jsx" -o -name "*.vue" -o -name "*_view.*" \
    "${expr[@]}" \
    -o -path "*/examples/android/app/src/main/java/*/ui/*/*.kt" \
    -o -path "*/examples/android/app/src/main/java/*/ui/GoldenPath*.kt" \
    \) ! -path "*/node_modules/*" ! -path "*/.venv/*" ! -path "*/.git/*" ! -path "*/dist/*" -print0 2>/dev/null
}

echo "Checking view file limits (max $VIEW_LIMIT lines)..."
check_files "view" "$VIEW_LIMIT" < <(build_web_view_find)

echo "Checking static data file limits (max $DATA_LIMIT lines)..."
check_files "data" "$DATA_LIMIT" < <(find "$ROOT/examples/web/src/data" -type f -name "*.ts" \
  ! -name "*.test.*" ! -name "*.spec.*" -print0 2>/dev/null)

echo "Checking logic file limits (max $LOGIC_LIMIT lines)..."
while IFS= read -r -d '' file; do
  lines=$(wc -l < "$file" | tr -d ' ')
  if [ "$lines" -gt "$LOGIC_LIMIT" ]; then
    echo "FAIL [logic] $file: $lines lines (max $LOGIC_LIMIT)"
    ERRORS=$((ERRORS + 1))
  fi
done < <(find "$ROOT/examples" -type f \( -name "*.ts" -o -name "*.py" -o -name "*.kt" \) \
  ! -name "*.test.*" ! -name "*.spec.*" \
  ! -path "*/node_modules/*" ! -path "*/.venv/*" ! -path "*/.git/*" \
  ! -path "*/examples/web/e2e/*" \
  ! -path "*/examples/web/src/api/*" \
  ! -path "*/examples/web/src/appBootstrap.ts" \
  ! -path "*/examples/web/src/AppShell.ts" \
  ! -path "*/examples/web/src/shell/*" \
  ! -path "*/examples/web/src/portfolio/*" \
  ! -path "*/examples/web/src/scanner/*" \
  ! -path "*/examples/web/src/components/*" \
  ! -path "*/examples/web/src/dashboard/*" \
  ! -path "*/examples/web/src/bots/*" \
  ! -path "*/examples/web/src/charts/*" \
  ! -path "*/examples/web/src/backtest/*" \
  ! -path "*/examples/web/src/ohlcv/*" \
  ! -path "*/examples/web/src/data/*" \
  ! -path "*/examples/android/app/src/main/java/*/ui/GoldenPath*.kt" \
  ! -path "*/examples/android/app/src/main/java/*/ui/*/*.kt" \
  ! -path "*/examples/web/src/main.ts" \
  -print0 2>/dev/null)

if [ "$ERRORS" -gt 0 ]; then
  echo "$ERRORS file(s) exceed line limits"
  exit 1
fi

echo "All file line limits OK"
