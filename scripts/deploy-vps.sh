#!/usr/bin/env bash
# Deploy TrendAlgo to external VPS (dry-run default). Never target local PR hardware.
# Usage: DEPLOY_HOST=user@vps scripts/deploy-vps.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash scripts/deploy-preflight.sh

HOST="${DEPLOY_HOST:-}"
if [ -z "$HOST" ]; then
  echo "FAIL set DEPLOY_HOST=user@your-vps"
  exit 1
fi

REMOTE_DIR="${DEPLOY_REMOTE_DIR:-/opt/trendalgo-bot}"
echo "=== deploy-vps → $HOST:$REMOTE_DIR ==="

rsync -az --delete \
  --exclude .git --exclude .venv --exclude node_modules --exclude examples/web/dist \
  ./ "${HOST}:${REMOTE_DIR}/"

ssh "$HOST" "cd ${REMOTE_DIR} && docker compose -f docker/docker-compose.prod.yml up -d --build trendalgo-api"
echo "OK deploy smoke: curl http://VPS:8080/api/v1/health"
