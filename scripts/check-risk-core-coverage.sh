#!/usr/bin/env bash
# HOUSE-03: risk-core-only coverage gate (high floor).
# Measures trendalgo.risk + trading + exchanges without the package-wide omit noise.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FLOOR="${RISK_CORE_COV_FLOOR:-89}"
# Prefer `uv` on PATH; fall back to `python -m uv` (Windows Git Bash).
if command -v uv >/dev/null 2>&1; then
  UV=(uv)
elif command -v python3 >/dev/null 2>&1; then
  UV=(python3 -m uv)
else
  UV=(python -m uv)
fi
# Clear package-wide addopts so this gate measures only the risk core.
exec env PYTEST_ADDOPTS='' "${UV[@]}" run pytest \
  -o addopts= \
  --cov=trendalgo.risk \
  --cov=trendalgo.trading \
  --cov=trendalgo.exchanges \
  --cov-config="$ROOT/scripts/risk-core.coveragerc" \
  --cov-report=term-missing \
  --cov-fail-under="$FLOOR" \
  tests/test_risk tests/test_trading tests/test_exchanges \
  "$@"
