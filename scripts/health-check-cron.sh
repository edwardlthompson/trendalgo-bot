#!/usr/bin/env bash
# Cron-friendly health probe + Telegram down-alert hook (OPS4).
# Usage: scripts/health-check-cron.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_URL="${TRENDALGO_HEALTH_URL:-http://127.0.0.1:8080/api/v1/health}"
echo "=== health-check-cron ==="

if curl -fsS "$API_URL" >/dev/null; then
  echo "OK API healthy"
  exit 0
fi

echo "FAIL API unhealthy at $API_URL"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=TrendAlgo API health check FAILED: ${API_URL}" || true
fi
exit 1
