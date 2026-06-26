#!/usr/bin/env bash
# TrendAlgo — L1 local dev (API :8000 + Vite :5173)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

export TRENDALGO_DATA_DIR="${TRENDALGO_DATA_DIR:-$ROOT/data/dev}"
export TRENDALGO_MODE=dry-run
export TRENDALGO_API_PORT=8000
mkdir -p "$TRENDALGO_DATA_DIR"
export DATABASE_URL="sqlite:///${TRENDALGO_DATA_DIR}/trendalgo.db"

cleanup() {
  [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "Starting API on http://127.0.0.1:8000 (data: $TRENDALGO_DATA_DIR)"
python -m trendalgo.api.main &
API_PID=$!
sleep 2

echo "Starting Vite on http://localhost:5173"
cd examples/web
[ -d node_modules ] || npm ci
npm run dev
