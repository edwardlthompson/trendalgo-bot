#!/usr/bin/env bash
# TrendAlgo — L2 production build preview
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

[ -f .env ] || cp .env.example .env
export TRENDALGO_DATA_DIR="${TRENDALGO_DATA_DIR:-$ROOT/data/dev}"
export TRENDALGO_MODE=dry-run
export TRENDALGO_API_PORT=8000
mkdir -p "$TRENDALGO_DATA_DIR"

cleanup() {
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd examples/web
[ -d node_modules ] || npm ci
npm run build
cd "$ROOT"

python -m trendalgo.api.main &
API_PID=$!
sleep 2

echo "vite preview: http://localhost:4173 (API :8000)"
cd examples/web
npm run preview
