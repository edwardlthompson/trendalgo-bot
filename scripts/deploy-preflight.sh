#!/usr/bin/env bash
# Reject local PR / non-VPS production targets (R-004).
# Usage: scripts/deploy-preflight.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== deploy-preflight ==="
if [ -f config/founder.defaults.json ]; then
  if grep -q '"production_hosting".*"external_vps_only"' config/founder.defaults.json 2>/dev/null || \
     grep -q 'external_vps_only' config/founder.defaults.json; then
    echo "OK   production_hosting=external_vps_only in founder.defaults.json"
  fi
fi

FORBIDDEN_HOST="${DEPLOY_TARGET:-}"
case "$FORBIDDEN_HOST" in
  *localhost*|*127.0.0.1*|*PR*|*puerto*)
    echo "FAIL DEPLOY_TARGET suggests local/PR hardware: $FORBIDDEN_HOST"
    exit 1
    ;;
esac

if [ -f docs/DEPLOYMENT.md ]; then
  echo "OK   DEPLOYMENT.md documents external VPS only"
  exit 0
fi
echo "SCHEDULED — docs/DEPLOYMENT.md missing"
exit 2
